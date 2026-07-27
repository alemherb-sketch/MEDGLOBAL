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
import glob
import logging
import os
import json
import sqlite3
import threading
import time
from datetime import datetime

import requests
from sqlalchemy.orm import sessionmaker

import models
from database import engine
from main import SYNCABLE_MODELS, _row_to_sync_dict, _apply_sync_fields

logger = logging.getLogger(__name__)

SYNC_SERVER_URL = os.getenv("SYNC_SERVER_URL")  # ej. https://api.medglobal.erpgest.com.pe
SYNC_USERNAME = os.getenv("SYNC_USERNAME")
SYNC_PASSWORD = os.getenv("SYNC_PASSWORD")
SYNC_INTERVAL_SEGUNDOS = int(os.getenv("SYNC_INTERVAL_SEGUNDOS", "30"))

# Timeouts generosos: una sincronizacion manual despues de varios dias sin
# internet puede mover miles de filas de una sola vez, y cortarla a los 30
# segundos obligaria a reintentar el ciclo entero.
PUSH_TIMEOUT_SEGUNDOS = int(os.getenv("SYNC_PUSH_TIMEOUT", "300"))
PULL_TIMEOUT_SEGUNDOS = int(os.getenv("SYNC_PULL_TIMEOUT", "300"))

_CURSOR_FILE = "sync_cursor.json"

# Respaldos de la base local previos a cada sincronizacion. Se conservan los
# ultimos RESPALDOS_A_CONSERVAR y se van rotando.
_CARPETA_RESPALDOS = "respaldos"
RESPALDOS_A_CONSERVAR = int(os.getenv("SYNC_RESPALDOS", "10"))

# Serializa los ciclos de sincronizacion. El hilo de fondo y el boton
# "Sincronizar ahora" comparten este lock: sin el, dos ciclos simultaneos
# podrian empujar las mismas filas dos veces y, sobre todo, escribir el
# archivo de cursores uno encima del otro dejando un punto de sincronizacion
# incoherente.
_lock = threading.Lock()

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


def _leer_cursores():
    """Devuelve (last_pulled_at, last_pushed_at).

    Son DOS cursores distintos porque se comparan contra dos relojes distintos:

      - last_pulled_at es el server_time que devolvio el ultimo pull, o sea el
        reloj del SERVIDOR. Se usa como parametro 'since' de /sync/cambios y
        /sync/subir, que el servidor interpreta con su propio reloj.

      - last_pushed_at es la hora LOCAL en que se hizo el ultimo push. Se usa
        para filtrar 'updated_at > since' sobre la base local, y updated_at lo
        escribe el reloj de esta PC.

    Antes habia un solo cursor y se usaba para las dos cosas: el filtro local
    comparaba updated_at (reloj de la PC) contra el server_time (reloj del
    servidor). En una PC con el reloj atrasado respecto al servidor — habitual
    en la clinica, sin NTP — todo lo que se editaba nacia con updated_at menor
    que el cursor y no se subia NUNCA, porque el cursor solo avanza. No era un
    retraso: era perdida silenciosa de datos.

    Compatibilidad: un sync_cursor.json del formato viejo ({"last_synced_at":
    ...}) se lee como last_pulled_at y deja last_pushed_at en None, con lo que
    el primer push despues de actualizar reenvia todo lo local. Eso es
    justamente lo que recupera los cambios que el bug habia dejado sin subir;
    el servidor los aplica de forma idempotente por id.
    """
    if not os.path.exists(_CURSOR_FILE):
        return None, None
    try:
        with open(_CURSOR_FILE) as f:
            datos = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None, None
    last_pulled = datos.get("last_pulled_at") or datos.get("last_synced_at")
    return last_pulled, datos.get("last_pushed_at")


def _guardar_cursores(last_pulled_at, last_pushed_at):
    with open(_CURSOR_FILE, "w") as f:
        json.dump(
            {
                "last_pulled_at": last_pulled_at,
                "last_pushed_at": last_pushed_at,
                # Se mantiene la clave vieja para que un downgrade del
                # ejecutable no pierda el punto de sincronizacion.
                "last_synced_at": last_pulled_at,
            },
            f,
        )


def _respaldar_base_local():
    """Copia la base local antes de sincronizar. Devuelve la ruta del respaldo,
    o None si no aplica (base que no es SQLite) o si no se pudo hacer.

    Existe porque el pull no es puramente aditivo: _limpiar_colisiones_locales
    borra filas locales que choquen en una columna unique con una fila que
    llega del servidor. Es lo correcto para que gane la version autoritativa,
    pero significa que una sincronizacion PUEDE eliminar datos de esta PC. Con
    el respaldo, ese caso siempre es reversible.

    Usa la API de backup de SQLite en vez de copiar el archivo con shutil: la
    aplicacion tiene la base abierta y una copia cruda podria capturarla a
    mitad de una escritura. La API de backup entrega siempre una copia
    consistente.

    Un fallo al respaldar no aborta la sincronizacion: se registra y se sigue.
    Quedarse sin sincronizar por no poder escribir un respaldo seria peor que
    sincronizar sin el.
    """
    url = str(engine.url)
    if not url.startswith("sqlite"):
        return None
    ruta_base = engine.url.database
    if not ruta_base or not os.path.exists(ruta_base):
        return None

    try:
        os.makedirs(_CARPETA_RESPALDOS, exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        destino = os.path.join(_CARPETA_RESPALDOS, f"medglobal-{marca}.db")

        origen_conn = sqlite3.connect(ruta_base)
        try:
            destino_conn = sqlite3.connect(destino)
            try:
                origen_conn.backup(destino_conn)
            finally:
                destino_conn.close()
        finally:
            origen_conn.close()

        _rotar_respaldos()
        return destino
    except (OSError, sqlite3.Error) as e:
        logger.warning("No se pudo respaldar la base local antes de sincronizar: %s", e)
        return None


def _rotar_respaldos():
    """Deja solo los RESPALDOS_A_CONSERVAR mas recientes, para que la carpeta
    no crezca sin limite en una PC de la clinica."""
    respaldos = sorted(glob.glob(os.path.join(_CARPETA_RESPALDOS, "medglobal-*.db")))
    for viejo in respaldos[:-RESPALDOS_A_CONSERVAR] if RESPALDOS_A_CONSERVAR > 0 else []:
        try:
            os.remove(viejo)
        except OSError:
            pass


def esta_en_linea():
    if not SYNC_SERVER_URL:
        return False
    try:
        r = requests.get(f"{SYNC_SERVER_URL}/docs", timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _login():
    """Devuelve (token, motivo_del_fallo).

    Distingue no poder llegar al servidor de que el servidor rechace el
    usuario: para quien esta en la clinica son dos problemas completamente
    distintos ("esperá a tener internet" vs "avisá a sistemas"), y antes los
    dos casos devolvian None y se reportaban como credenciales invalidas."""
    try:
        r = requests.post(
            f"{SYNC_SERVER_URL}/auth/login",
            data={"username": SYNC_USERNAME, "password": SYNC_PASSWORD},
            timeout=10,
        )
    except requests.RequestException:
        return None, "sin_conexion"
    if r.status_code == 200:
        return r.json()["access_token"], None
    return None, "credenciales"


def _empujar_cambios(token, since_local, since_servidor, db):
    """since_local filtra la base local (se compara con updated_at, reloj de
    esta PC). since_servidor es lo que viaja en el payload para que el servidor
    detecte conflictos (se compara alla con server_updated_at, reloj del
    servidor). Son valores de relojes distintos y no se pueden intercambiar:
    ver la explicacion en _leer_cursores.

    Devuelve (subidos, conflictos) para poder mostrarle al usuario cuantos
    registros salieron de esta PC, en vez de un "listo" sin respaldo."""
    cambios = {}
    for tabla, model in SYNCABLE_MODELS.items():
        query = db.query(model)
        if since_local:
            query = query.filter(model.updated_at > _parse_iso(since_local))
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
        return 0, 0
    respuesta = requests.post(
        f"{SYNC_SERVER_URL}/sync/subir",
        headers={"Authorization": f"Bearer {token}"},
        json={"since": since_servidor, "cambios": cambios},
        timeout=PUSH_TIMEOUT_SEGUNDOS,
    )
    respuesta.raise_for_status()

    # El servidor informa por tabla cuantas filas aplico y cuantas quedaron
    # como conflicto (se guardan enteras en conflictos_sync, no se pierden).
    resultado = respuesta.json().get("resultado", {})
    subidos = sum(r.get("aplicados", 0) for r in resultado.values())
    conflictos = sum(r.get("conflictos", 0) for r in resultado.values())
    return subidos, conflictos


def _limpiar_colisiones_locales(db, model, fila):
    """Antes de insertar una fila nueva que llega por pull, borra cualquier
    fila local (con OTRO id) que choque en una columna unique (username,
    ruc, dni, codigo, nombre...). Hace falta porque este mismo dispositivo
    puede tener localmente su propia version de un registro que el
    servidor YA rechazo por chocar con la de otro dispositivo (ver el
    except IntegrityError en sync_subir, main.py) -- esa fila local nunca
    llego a existir para el servidor, asi que no tiene sentido conservarla
    bloqueando la version autoritativa que ahora llega por pull."""
    row_id = fila.get("id")
    for col in model.__table__.columns:
        if not col.unique or col.name not in fila:
            continue
        valor = fila[col.name]
        if valor is None:
            continue
        choque = db.query(model).filter(getattr(model, col.name) == valor, model.id != row_id).first()
        if choque is not None:
            db.delete(choque)
    db.flush()


def _traer_cambios(token, since, db):
    """Devuelve (server_time, bajados). Todo el pull se aplica en UNA sola
    transaccion: el commit esta al final, asi que si algo falla a mitad de
    camino la base local queda exactamente como estaba y el cursor no avanza.
    El proximo intento vuelve a pedir lo mismo."""
    params = {"since": since} if since else {}
    r = requests.get(
        f"{SYNC_SERVER_URL}/sync/cambios",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=PULL_TIMEOUT_SEGUNDOS,
    )
    r.raise_for_status()
    data = r.json()

    bajados = 0
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
                _limpiar_colisiones_locales(db, model, fila)
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
            bajados += 1

    db.commit()
    return data["server_time"], bajados


def _parse_iso(value):
    return datetime.fromisoformat(value)


def sincronizar_ahora(origen="manual"):
    """Un ciclo completo (push y despues pull) con detalle de lo que paso.

    Nunca lanza excepciones: siempre devuelve un dict con 'ok' y, cuando
    ok=False, un 'motivo' estable que la interfaz traduce a un mensaje para el
    usuario. Que no lance es importante para el hilo de fondo, que no tiene su
    propio try/except: una excepcion que se escapara de aca mataria el hilo
    para siempre y esa instalacion no volveria a sincronizar hasta reiniciar
    la app.

    Garantias para no perder informacion:

      - Un solo ciclo a la vez (_lock). Si el usuario aprieta el boton
        mientras el ciclo automatico esta corriendo, no se solapan dos push
        ni se pisa el archivo de cursores a medio escribir.
      - Antes de tocar nada se hace un respaldo de la base local, porque el
        pull puede borrar filas locales al resolver colisiones de columnas
        unique (ver _limpiar_colisiones_locales).
      - El cursor SOLO avanza si el ciclo entero termino bien. Si falla en
        cualquier punto, se deshace la transaccion y el cursor queda donde
        estaba: el proximo intento reenvia y vuelve a pedir exactamente lo
        mismo. Un fallo retrasa la sincronizacion, nunca la saltea.
    """
    if not sync_habilitado():
        return {"ok": False, "motivo": "no_configurado"}

    # blocking=False: si ya hay un ciclo en curso se avisa en el momento en
    # vez de dejar la interfaz esperando sin explicacion.
    if not _lock.acquire(blocking=False):
        return {"ok": False, "motivo": "en_curso"}

    try:
        token, motivo_login = _login()
        if not token:
            return {"ok": False, "motivo": motivo_login}

        respaldo = _respaldar_base_local()

        db = LocalSession()
        try:
            since_servidor, since_local = _leer_cursores()
            # La marca local se toma ANTES de empujar: cualquier fila que un
            # usuario guarde mientras el push esta en vuelo queda por encima de
            # este corte y entra en el ciclo siguiente, en vez de caer en el hueco
            # entre "ya la filtre" y "ya avance el cursor".
            marca_local = datetime.utcnow().isoformat()
            subidos, conflictos = _empujar_cambios(token, since_local, since_servidor, db)
            nuevo_cursor, bajados = _traer_cambios(token, since_servidor, db)
            _guardar_cursores(nuevo_cursor, marca_local)
            return {
                "ok": True,
                "subidos": subidos,
                "bajados": bajados,
                "conflictos": conflictos,
                "respaldo": respaldo,
                "origen": origen,
            }
        except requests.RequestException as e:
            db.rollback()
            logger.warning("Sincronizacion (%s): fallo de red: %s", origen, e)
            return {"ok": False, "motivo": "sin_conexion", "detalle": str(e)}
        except Exception as e:
            db.rollback()
            logger.exception("Sincronizacion (%s): error inesperado", origen)
            return {"ok": False, "motivo": "error", "detalle": str(e)}
        finally:
            db.close()
    finally:
        _lock.release()


def sincronizar_una_vez():
    """Compatibilidad: la version booleana que usa el hilo de fondo."""
    return sincronizar_ahora(origen="automatico")["ok"]


# Mensajes que ve el usuario en el indicador de la barra lateral. Las claves
# son los 'motivo' que devuelve sincronizar_ahora.
_MENSAJE_POR_MOTIVO = {
    "no_configurado": "Esta instalacion no tiene configurada la sincronizacion",
    "en_curso": "Ya hay una sincronizacion en curso",
    "credenciales": "El servidor rechazo el usuario o la contrasena de sincronizacion",
    "sin_conexion": "Sin conexion con el servidor -- los datos siguen guardados en esta PC",
    "error": "La sincronizacion fallo -- los datos siguen guardados en esta PC",
}


def _actualizar_estado(resultado):
    """Refleja el resultado de un ciclo en el indicador que lee /sync/estado.
    Lo llaman tanto el hilo de fondo como el boton manual, para que apretar el
    boton actualice el indicador en el acto."""
    if resultado.get("motivo") == "en_curso":
        return  # otro ciclo esta corriendo y ya reportara su propio resultado

    if resultado.get("ok"):
        _estado["estado"] = "en_linea"
        # +"Z": datetime.utcnow().isoformat() no incluye marca de zona
        # horaria, y new Date(...) en JS interpreta un ISO sin zona como hora
        # LOCAL, no UTC -- sin la Z el indicador del frontend mostraba la
        # ultima sync como si hubiera sido en el futuro.
        _estado["ultima_sincronizacion"] = datetime.utcnow().isoformat() + "Z"
        _estado["ultimo_error"] = None
    elif resultado.get("motivo") == "sin_conexion":
        _estado["estado"] = "fuera_de_linea"
    else:
        _estado["estado"] = "error"
        _estado["ultimo_error"] = _MENSAJE_POR_MOTIVO.get(
            resultado.get("motivo"), "La sincronizacion fallo"
        )


def iniciar_hilo_sincronizacion():
    """Arranca el ciclo de sync en segundo plano. No hace nada si SYNC_* no
    esta configurado — la app sigue 100% local sin cambio de comportamiento."""
    if not sync_habilitado():
        return

    # El cursor persistido ya es, en los hechos, la hora del ultimo pull
    # exitoso -- lo usamos para que "ultima sincronizacion" no aparezca en
    # blanco cada vez que se reinicia la app (p.ej. tras reiniciar la PC)
    # aunque haya sincronizado bien minutos antes.
    _cursor_inicial, _ = _leer_cursores()
    if _cursor_inicial:
        _estado["ultima_sincronizacion"] = _cursor_inicial + "Z"

    def loop():
        while True:
            if esta_en_linea():
                _actualizar_estado(sincronizar_ahora(origen="automatico"))
            else:
                _estado["estado"] = "fuera_de_linea"
            time.sleep(SYNC_INTERVAL_SEGUNDOS)

    threading.Thread(target=loop, daemon=True).start()
