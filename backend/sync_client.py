"""Cliente de sincronizacion para el modo de escritorio (Fase 3).

Corre en un hilo de fondo dentro de app_desktop.py. Habla con el servidor
central (el VPS) usando los mismos endpoints /sync/cambios y /sync/subir
que ya construyo y verifico la Fase 2.

Si SYNC_SERVER_URL, SYNC_USERNAME o SYNC_PASSWORD no estan configurados,
todo aqui queda inactivo — la app sigue funcionando 100% local, exactamente
igual que antes de esta fase. No hace falta nada para seguir usandola
puramente offline.

Protocolo de cada ciclo: primero PUSH (sube los cambios locales desde el
ultimo cursor), despues PULL (baja lo que cambio en el servidor desde ese
mismo cursor), y recien entonces el cursor local avanza al server_time que
devolvio el pull. Ese orden importa: empujar primero le da al servidor la
oportunidad de resolver cualquier conflicto ANTES de traer la version ya
resuelta — el cliente nunca necesita su propia logica de conflictos, solo
aplica lo que el servidor ya decidio que es la verdad.
"""
import os
import json
import threading
import time
from datetime import datetime

import requests
from sqlalchemy.orm import sessionmaker

import models
from database import engine
from main import SYNCABLE_MODELS, _row_to_sync_dict, _apply_sync_fields

SYNC_SERVER_URL = os.getenv("SYNC_SERVER_URL")  # ej. https://api.medglobal.erpgest.com.pe
SYNC_USERNAME = os.getenv("SYNC_USERNAME")
SYNC_PASSWORD = os.getenv("SYNC_PASSWORD")
SYNC_INTERVAL_SEGUNDOS = int(os.getenv("SYNC_INTERVAL_SEGUNDOS", "30"))

_CURSOR_FILE = "sync_cursor.json"

LocalSession = sessionmaker(bind=engine)

# Estado compartido entre el hilo de fondo (que lo escribe) y el endpoint
# GET /sync/estado (que lo lee) -- no hace falta un lock porque cada campo
# se reemplaza en una sola asignacion atomica (GIL), nunca se muta en su
# lugar.
_estado = {"estado": "desactivado", "ultima_sincronizacion": None, "ultimo_error": None}


def obtener_estado():
    return dict(_estado)


def sync_habilitado():
    return bool(SYNC_SERVER_URL and SYNC_USERNAME and SYNC_PASSWORD)


def _leer_cursor():
    if not os.path.exists(_CURSOR_FILE):
        return None
    try:
        with open(_CURSOR_FILE) as f:
            return json.load(f).get("last_synced_at")
    except (OSError, json.JSONDecodeError):
        return None


def _guardar_cursor(valor):
    with open(_CURSOR_FILE, "w") as f:
        json.dump({"last_synced_at": valor}, f)


def esta_en_linea():
    if not SYNC_SERVER_URL:
        return False
    try:
        r = requests.get(f"{SYNC_SERVER_URL}/docs", timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _login():
    try:
        r = requests.post(
            f"{SYNC_SERVER_URL}/auth/login",
            data={"username": SYNC_USERNAME, "password": SYNC_PASSWORD},
            timeout=10,
        )
    except requests.RequestException:
        return None
    if r.status_code == 200:
        return r.json()["access_token"]
    return None


def _empujar_cambios(token, since, db):
    cambios = {}
    for tabla, model in SYNCABLE_MODELS.items():
        query = db.query(model)
        if since:
            query = query.filter(model.updated_at > _parse_iso(since))
        rows = query.all()
        if not rows:
            continue
        items = []
        for row in rows:
            item = _row_to_sync_dict(row)
            if tabla == "atenciones":
                item["medicamentos"] = [
                    {"medicamento_id": am.medicamento_id, "cantidad": am.cantidad}
                    for am in row.medicamentos
                ]
            items.append(item)
        cambios[tabla] = items

    if not cambios:
        return
    requests.post(
        f"{SYNC_SERVER_URL}/sync/subir",
        headers={"Authorization": f"Bearer {token}"},
        json={"since": since, "cambios": cambios},
        timeout=30,
    ).raise_for_status()


def _traer_cambios(token, since, db):
    params = {"since": since} if since else {}
    r = requests.get(
        f"{SYNC_SERVER_URL}/sync/cambios",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    for tabla, filas in data["cambios"].items():
        model = SYNCABLE_MODELS.get(tabla)
        if model is None:
            continue
        for fila in filas:
            row_id = fila.get("id")
            if not row_id:
                continue
            medicamentos = fila.pop("medicamentos", None)
            existing = db.query(model).filter(model.id == row_id).first()
            if existing is None:
                nuevo = model(id=row_id)
                # trusted_source=True: esto viene del servidor, no de otro
                # dispositivo — folio y stock_actual SI se aceptan tal cual,
                # a diferencia de cuando el servidor recibe un push.
                _apply_sync_fields(nuevo, fila, tabla, trusted_source=True)
                db.add(nuevo)
                db.flush()
                if tabla == "atenciones" and medicamentos:
                    for med in medicamentos:
                        db.add(models.AtencionMedicamento(
                            atencion_id=nuevo.id,
                            medicamento_id=med.get("medicamento_id"),
                            cantidad=med.get("cantidad", 1),
                        ))
            else:
                _apply_sync_fields(existing, fila, tabla, trusted_source=True)

    db.commit()
    return data["server_time"]


def _parse_iso(value):
    return datetime.fromisoformat(value)


def sincronizar_una_vez():
    """Un ciclo completo: push, luego pull. Devuelve True si se completo bien."""
    if not sync_habilitado():
        return False
    token = _login()
    if not token:
        return False

    db = LocalSession()
    try:
        since = _leer_cursor()
        _empujar_cambios(token, since, db)
        nuevo_cursor = _traer_cambios(token, since, db)
        _guardar_cursor(nuevo_cursor)
        return True
    except requests.RequestException:
        return False
    finally:
        db.close()


def iniciar_hilo_sincronizacion():
    """Arranca el ciclo de sync en segundo plano. No hace nada si SYNC_* no
    esta configurado — la app sigue 100% local sin cambio de comportamiento."""
    if not sync_habilitado():
        return

    # El cursor persistido ya es, en los hechos, la hora del ultimo pull
    # exitoso -- lo usamos para que "ultima sincronizacion" no aparezca en
    # blanco cada vez que se reinicia la app (p.ej. tras reiniciar la PC)
    # aunque haya sincronizado bien minutos antes.
    _cursor_inicial = _leer_cursor()
    if _cursor_inicial:
        _estado["ultima_sincronizacion"] = _cursor_inicial + "Z"

    def loop():
        while True:
            if esta_en_linea():
                if sincronizar_una_vez():
                    _estado["estado"] = "en_linea"
                    # +"Z": datetime.utcnow().isoformat() no incluye marca de
                    # zona horaria, y new Date(...) en JS interpreta un ISO
                    # sin zona como hora LOCAL, no UTC -- sin la Z el
                    # indicador del frontend mostraba la ultima sync como si
                    # hubiera sido en el futuro.
                    _estado["ultima_sincronizacion"] = datetime.utcnow().isoformat() + "Z"
                    _estado["ultimo_error"] = None
                else:
                    _estado["estado"] = "error"
                    _estado["ultimo_error"] = "hay conexion pero la sincronizacion fallo -- revisar usuario/password de sync"
            else:
                _estado["estado"] = "fuera_de_linea"
            time.sleep(SYNC_INTERVAL_SEGUNDOS)

    threading.Thread(target=loop, daemon=True).start()
