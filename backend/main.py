import os
import re
import json
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

import models, schemas
import auth
from database import engine, get_db

# Create DB tables
models.Base.metadata.create_all(bind=engine)

# Aplicar migraciones autom├â┬íticas para SQLite/PostgreSQL si las columnas no existen
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
with engine.connect() as conn:
    columnas_trabajador = [
        "codigo_trabajador VARCHAR(50)", "cargo VARCHAR(100)", "fecha_ingreso VARCHAR(20)", "fecha_cese VARCHAR(20)",
        "estado_trabajador VARCHAR(50)", "subdivision_sede VARCHAR(100)", "centro_costo VARCHAR(100)",
        "tipo_calculo_nomina VARCHAR(100)", "area VARCHAR(150)", "area_personal VARCHAR(100)", "grupo_personal VARCHAR(100)",
        "nivel_org_1 VARCHAR(100)", "nivel_org_2 VARCHAR(100)", "nivel_org_3 VARCHAR(100)", "nivel_org_4 VARCHAR(100)",
        "nivel_org_5 VARCHAR(100)", "fecha_nacimiento VARCHAR(20)", "genero VARCHAR(20)", "jefe_inmediato VARCHAR(150)",
        "telefono VARCHAR(50)", "correo_electronico VARCHAR(150)", "empresa_id INTEGER",
        "obra VARCHAR(150)"
    ]
    for col in columnas_trabajador:
        try:
            with conn.begin():
                conn.execute(text(f"ALTER TABLE trabajadores ADD COLUMN {col}"))
        except Exception:
            pass

    columnas_atencion = [
        "edad VARCHAR(10)", "residencia VARCHAR(200)", "empresa_id INTEGER", "cargo VARCHAR(100)",
        "funciones_biologicas TEXT", "signos_vitales TEXT", "examen_fisico TEXT", "examenes_auxiliares TEXT",
        "codigo_diagnostico VARCHAR(100)", "diagnostico_1 VARCHAR(255)", "diagnostico_2 VARCHAR(255)", "diagnostico_3 VARCHAR(255)"
    ]
    for col in columnas_atencion:
        try:
            with conn.begin():
                conn.execute(text(f"ALTER TABLE atenciones ADD COLUMN {col}"))
        except Exception:
            pass

    try:
        with conn.begin():
            conn.execute(text("ALTER TABLE medicamentos ADD COLUMN costo_unitario FLOAT DEFAULT 0.0"))
    except Exception:
        pass

    columnas_medicamento = [
        "tipo VARCHAR(20) DEFAULT 'MEDICAMENTO'", "lote VARCHAR(50)", "fecha_vencimiento VARCHAR(20)"
    ]
    for col in columnas_medicamento:
        try:
            with conn.begin():
                conn.execute(text(f"ALTER TABLE medicamentos ADD COLUMN {col}"))
        except Exception:
            pass

    columnas_kardex = ["lote VARCHAR(50)", "fecha_vencimiento VARCHAR(20)"]
    for col in columnas_kardex:
        try:
            with conn.begin():
                conn.execute(text(f"ALTER TABLE kardex ADD COLUMN {col}"))
        except Exception:
            pass

    columnas_botiquin = [
        "codigo VARCHAR(50)",
        "fecha_creacion TIMESTAMP",
        "tipo_botiquin_id VARCHAR(36)",
        "mapa_url VARCHAR(500)",
        "vehiculo VARCHAR(150)",
        "marca VARCHAR(100)",
        "modelo VARCHAR(100)",
    ]
    for col in columnas_botiquin:
        try:
            with conn.begin():
                conn.execute(text(f"ALTER TABLE botiquines ADD COLUMN {col}"))
        except Exception:
            pass

app = FastAPI(title="MEDGLOBAL API")

# Configure CORS
# ALLOWED_ORIGINS es una lista separada por comas (ej. "https://medglobal.erpgestapp.com").
#
# El default ya NO es "*": con allow_credentials=True, Starlette responde
# reflejando el Origin que venga en el request, asi que cualquier pagina web
# podia llamar a este API desde el navegador de un usuario logueado. Ahora el
# default es la lista de origenes que realmente usa el sistema. El .exe de
# escritorio sirve el frontend desde el mismo origen (127.0.0.1:8000), asi que
# no depende de esta lista.
#
# Si un despliegue usa otro dominio, se configura con la variable de entorno;
# ALLOWED_ORIGINS="*" sigue disponible como valvula de escape explicita.
_ORIGENES_POR_DEFECTO = [
    "https://medglobal.erpgestapp.com",
    "https://medglobal.erpgest.com.pe",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
_allowed_origins = os.getenv("ALLOWED_ORIGINS")
if _allowed_origins is None:
    _origins = _ORIGENES_POR_DEFECTO
elif _allowed_origins.strip() == "*":
    _origins = ["*"]
else:
    _origins = [o.strip() for o in _allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    # La sesion viaja en el header Authorization (token en localStorage), no en
    # cookies, asi que el navegador nunca necesita mandar credenciales de
    # origen cruzado. Dejarlo en False es lo que hace que allow_origins=["*"]
    # sea seguro cuando alguien lo configure asi a proposito.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
import pandas as pd
import io


def _next_prefixed_code(db: Session, model, field_name: str, prefix: str) -> str:
    """Siguiente c├â┬│digo secuencial tipo PREFIX-0001, buscando el m├â┬íximo existente
    (no se puede usar el id para esto desde que los ids son UUID)."""
    col = getattr(model, field_name)
    rows = db.query(col).filter(col.like(f"{prefix}-%")).all()
    max_n = 0
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    for (val,) in rows:
        if not val:
            continue
        m = pattern.match(val)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"{prefix}-{max_n + 1:04d}"


# --- Sincronizacion (Fase 2) ---
# Tablas que participan del protocolo generico de sync. atencion_medicamentos
# se sincroniza embebida dentro de cada atencion (igual que ya se expone en
# la API normal), no como tabla independiente. usuarios SI participa (a
# diferencia del dise├â┬▒o original de la Fase 2): el mismo login debe
# funcionar tanto en la web como en el instalable de escritorio. Usa
# exactamente el mismo mecanismo generico de conflicto que cualquier otra
# tabla -- no hay tratamiento especial para password_hash, porque cualquier
# dispositivo con credenciales de sync validas ya puede escribir cualquier
# otra tabla igual.
SYNCABLE_MODELS = {
    "usuarios": models.Usuario,
    "empresas": models.Empresa,
    "sistemas": models.SistemaAtencion,
    "clasificaciones": models.ClasificacionAtencion,
    "diagnosticos_cie10": models.DiagnosticoCie10,
    "medicamentos": models.Medicamento,
    "personal_salud": models.PersonalSalud,
    "trabajadores": models.Trabajador,
    "citas": models.Cita,
    "atenciones": models.Atencion,
    "kardex": models.Kardex,
    "tipos_botiquin": models.TipoBotiquin,
    "botiquines": models.Botiquin,
    "botiquin_inspecciones": models.BotiquinInspeccion,
}

# id nunca se sobreescribe via setattr, venga de donde venga.
_SYNC_ALWAYS_SKIP = {"id"}
# folio, stock_actual y server_updated_at son calculados por el servidor.
# Un dispositivo empujando cambios (push) nunca puede pisarlos directo,
# aunque los mande en su payload ├óÔé¼ÔÇØ por eso se saltan cuando
# trusted_source=False. Pero cuando el cliente de escritorio (Fase 3)
# APLICA lo que bajo del servidor (pull), s├â┬¡ necesita quedarse con esos
# valores tal cual, porque son la verdad autoritativa ├óÔé¼ÔÇØ por eso ahi se
# llama con trusted_source=True.
#
# server_updated_at existe SEPARADO de updated_at a proposito (ver el
# comentario junto a la columna en models.py): updated_at sigue siendo la
# fecha de edicion del usuario, tal cual la manda el cliente, porque de eso
# depende decidir quien gana un conflicto. server_updated_at es cuando el
# SERVIDOR escribio la fila, y es lo que se usa para el filtro "que cambio
# desde since" ├óÔé¼ÔÇØ si se usara updated_at para ambas cosas, aplicar la
# version ganadora de un conflicto con la fecha de edicion original
# (posiblemente antigua) dejaria la fila "vieja" para el filtro de sync
# aunque el servidor la acabe de tocar, y un tercer dispositivo se la
# perderia. Se excluye del copiado directo para que dispare el
# onupdate/default de la columna (hora real del servidor).
_SYNC_SERVER_COMPUTED_COLUMNS = {"folio", "server_updated_at"}
_SYNC_SERVER_COMPUTED_COLUMNS_POR_TABLA = {
    "medicamentos": {"stock_actual"},
}
_SYNC_DATETIME_COLUMNS = {"fecha", "fecha_hora", "fecha_creacion", "created_at", "updated_at", "server_updated_at", "creado_en"}


def _parse_sync_dt(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _row_to_sync_dict(row):
    d = {}
    for col in row.__table__.columns:
        value = getattr(row, col.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        d[col.name] = value
    return d


def _apply_sync_fields(row, data, tabla=None, trusted_source=False):
    """Copia los campos de 'data' a 'row' via setattr. Usa flag_modified en
    cada columna tocada porque SQLAlchemy solo incluye una columna en el
    UPDATE si la detecta 'dirty' ├óÔé¼ÔÇØ y su deteccion de cambios es por
    igualdad de valor. Cuando un dispositivo recibe de vuelta (pull) su
    propio cambio recien empujado, el valor entrante es identico al que ya
    tiene en memoria, SQLAlchemy no lo marca dirty, la columna queda fuera
    del SET del UPDATE, y entonces el onupdate=utcnow() de la columna SI se
    dispara (porque "no esta en el SET") pisando el valor con la hora
    actual. flag_modified fuerza que la columna entre al UPDATE tal cual se
    seteo, sin importar si el valor es igual al anterior."""
    skip = set(_SYNC_ALWAYS_SKIP)
    if not trusted_source:
        skip |= _SYNC_SERVER_COMPUTED_COLUMNS
        skip |= _SYNC_SERVER_COMPUTED_COLUMNS_POR_TABLA.get(tabla, set())
    for col in row.__table__.columns:
        if col.name in skip or col.name not in data:
            continue
        value = data[col.name]
        if col.name in _SYNC_DATETIME_COLUMNS:
            value = _parse_sync_dt(value)
        setattr(row, col.name, value)
        flag_modified(row, col.name)


def _procesar_atencion_nueva(db: Session, atencion_row, medicamentos):
    """Asigna folio y reconstruye la receta (atencion_medicamentos) de una
    atencion que llega por sync. Solo corre para atenciones que no existian en
    el servidor todavia ├óÔé¼ÔÇØ editar los medicamentos de una atencion ya existente
    via sync no esta soportado, igual que tampoco lo esta en el endpoint normal
    de edicion.

    A PROPOSITO no toca el stock ni escribe en kardex, aunque create_atencion
    si lo haga: cuando el dispositivo registro esta atencion, create_atencion
    ya escribio localmente su fila de kardex SALIDA, y esa fila viaja en el
    mismo push como parte de la tabla 'kardex'. Ahi la recoge
    _procesar_kardex_nuevo, que es quien descuenta el stock recalculandolo
    contra el estado actual del servidor. Si ademas se descontara aca, cada
    atencion sincronizada restaria el doble y dejaria dos movimientos SALIDA
    duplicados en el kardex ├óÔé¼ÔÇØ el inventario del servidor se degradaba de forma
    acumulativa con cada sincronizacion.

    Regla: la fila de kardex es la unica fuente de verdad de un movimiento de
    stock. Quien crea el movimiento (create_atencion, create_kardex) descuenta;
    quien lo replica por sync solo lo aplica una vez, via kardex.
    """
    max_folio = db.query(func.max(models.Atencion.folio)).scalar()
    atencion_row.folio = (max_folio or 0) + 1
    for med in medicamentos or []:
        med_id = med.get("medicamento_id")
        cantidad = med.get("cantidad", 1)
        if not med_id:
            continue
        db.add(models.AtencionMedicamento(atencion_id=atencion_row.id, medicamento_id=med_id, cantidad=cantidad))


def _procesar_botiquin_inspeccion_nueva(db: Session, insp_row, insumos):
    """Reconstruye la lista de insumos de una inspeccion recien sincronizada."""
    for item in insumos or []:
        med_id = item.get("medicamento_id")
        cantidad = int(item.get("cantidad") or 1)
        if not med_id:
            continue
        db.add(models.BotiquinInspeccionInsumo(
            inspeccion_id=insp_row.id,
            medicamento_id=med_id,
            cantidad=max(1, cantidad),
        ))


def _reemplazar_insumos_tipo_botiquin(db: Session, tipo_row, insumos):
    """Asigna o reemplaza la plantilla de insumos de un tipo de botiquin."""
    db.query(models.TipoBotiquinInsumo).filter(
        models.TipoBotiquinInsumo.tipo_botiquin_id == tipo_row.id
    ).delete(synchronize_session=False)
    for item in insumos or []:
        if hasattr(item, "dict"):
            item = item.dict()
        med_id = item.get("medicamento_id")
        cantidad = int(item.get("cantidad") or 1)
        if not med_id:
            continue
        db.add(models.TipoBotiquinInsumo(
            tipo_botiquin_id=tipo_row.id,
            medicamento_id=med_id,
            cantidad=max(1, cantidad),
        ))


def _insumos_plantilla_botiquin(db: Session, botiquin_row):
    """Devuelve la lista estandar de insumos segun el tipo del botiquin."""
    if not botiquin_row or not botiquin_row.tipo_botiquin_id:
        return []
    tipo = db.query(models.TipoBotiquin).filter(
        models.TipoBotiquin.id == botiquin_row.tipo_botiquin_id,
        models.TipoBotiquin.is_deleted == False,
    ).first()
    if not tipo:
        return []
    return list(tipo.insumos or [])


def _procesar_kardex_nuevo(db: Session, kardex_row):
    """El stock y el saldo se recalculan aqui contra el estado actual del
    servidor ├óÔé¼ÔÇØ nunca se confia en el stock_actual/saldo que traiga el
    dispositivo, porque puede estar desactualizado si otro dispositivo
    sincronizo movimientos de este mismo medicamento mientras tanto."""
    db_med = db.query(models.Medicamento).filter(models.Medicamento.id == kardex_row.medicamento_id).first()
    if not db_med:
        return
    if kardex_row.tipo_movimiento == "INGRESO":
        db_med.stock_actual += kardex_row.cantidad
    elif kardex_row.tipo_movimiento == "SALIDA":
        db_med.stock_actual -= kardex_row.cantidad
    kardex_row.saldo = db_med.stock_actual


# Import diferido y protegido: sync_client importa `requests`, que no todo
# despliegue de main.py tiene instalado (p.ej. el del VPS, que solo sirve la
# API web y nunca corre el hilo de sync). Si no esta disponible, /sync/estado
# simplemente reporta "desactivado" en vez de tumbar el arranque del server.
try:
    import sync_client
except ImportError:
    sync_client = None


@app.get("/sync/estado")
def sync_estado(current_user: models.Usuario = Depends(auth.get_current_user)):
    """Para el indicador de estado del frontend. No indica si ESTE request
    tiene conexion -- indica lo que el hilo de fondo de sync_client observo
    en su ultimo chequeo (cada SYNC_INTERVAL_SEGUNDOS)."""
    if sync_client is None:
        return {"estado": "desactivado", "ultima_sincronizacion": None, "ultimo_error": None}
    return sync_client.obtener_estado()


@app.post("/sync/ahora")
def sync_ahora(current_user: models.Usuario = Depends(auth.get_current_user)):
    """Dispara una sincronizacion completa (primero sube lo local, despues baja
    lo del servidor) y espera a que termine para devolver el resultado.

    Es el boton "Sincronizar ahora" de la aplicacion de escritorio: permite
    trabajar sin internet todo el dia y subir todo de una vez al reconectarse,
    sin esperar al ciclo automatico.

    Solo existe en el escritorio. En el servidor central sync_client no esta
    instalado (no tiene 'requests' ni tiene a quien sincronizarse), asi que ahi
    responde 400 en vez de fallar.
    """
    if sync_client is None:
        raise HTTPException(
            status_code=400,
            detail="Esta instalacion no tiene la sincronizacion disponible.",
        )
    resultado = sync_client.sincronizar_ahora(origen="manual")
    sync_client._actualizar_estado(resultado)
    return resultado


@app.get("/sync/cambios")
def sync_cambios(since: Optional[str] = None, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    """Pull: todo lo que cambio desde 'since' (ISO 8601), incluyendo
    borrados (is_deleted=true actua como tombstone). Sin 'since', devuelve
    todo ├óÔé¼ÔÇØ es la sincronizacion inicial de un dispositivo nuevo.
    server_time va en la respuesta a proposito: el cliente debe guardar ESE
    valor como su proximo cursor, no su propio reloj ├óÔé¼ÔÇØ evita que un reloj
    desincronizado en una PC cause huecos o duplicados en la sync."""
    server_time = datetime.utcnow()
    since_dt = None
    if since:
        try:
            since_dt = _parse_sync_dt(since)
        except ValueError:
            raise HTTPException(status_code=400, detail="Parametro 'since' invalido, usa formato ISO 8601")

    cambios = {}
    for tabla, model in SYNCABLE_MODELS.items():
        query = db.query(model)
        if since_dt:
            query = query.filter(model.server_updated_at > since_dt)
        rows = query.all()
        items = []
        for row in rows:
            item = _row_to_sync_dict(row)
            if tabla == "atenciones":
                item["medicamentos"] = [
                    {"medicamento_id": am.medicamento_id, "cantidad": am.cantidad}
                    for am in row.medicamentos
                ]
            if tabla == "tipos_botiquin":
                item["insumos"] = [
                    {"medicamento_id": p.medicamento_id, "cantidad": p.cantidad}
                    for p in row.insumos
                ]
            if tabla == "botiquin_inspecciones":
                item["insumos"] = [
                    {"medicamento_id": am.medicamento_id, "cantidad": am.cantidad}
                    for am in row.insumos
                ]
            items.append(item)
        cambios[tabla] = items

    return {"server_time": server_time.isoformat(), "cambios": cambios}


@app.post("/sync/subir")
def sync_subir(payload: schemas.SyncPushRequest, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    """Push: aplica los cambios locales de un dispositivo.

    Deteccion de conflicto real (no cada sync normal es un 'conflicto'):
    el payload trae el 'since' que el dispositivo uso en su ULTIMO pull
    exitoso. Para cada fila que ya existe en el servidor:
      - si el servidor NO cambio desde ese 'since' -> es una actualizacion
        limpia, un solo dispositivo la toco, se aplica sin mas.
      - si el servidor SI cambio desde ese 'since' -> otro dispositivo
        edito lo mismo mientras este estaba desconectado. Eso es un
        conflicto real: gana el updated_at mas reciente entre las dos
        versiones, y la version que pierde se guarda completa en
        conflictos_sync en vez de perderse en silencio.

    Se confirma fila por fila (no una vez por tabla) a proposito: varias
    tablas synceables tienen columnas unique (username, ruc, dni, codigo,
    nombre...), y dos dispositivos offline pueden crear el mismo valor sin
    saberlo. Con un solo commit por tabla, esa fila chocando tumbaria TODA
    la transaccion de la tabla entera -- incluidas filas anteriores ya
    aplicadas sin problema. Confirmando de a una, un choque solo pierde esa
    fila (se audita en conflictos_sync en vez de perderse en silencio), sin
    arrastrarse las demas.
    """
    since_dt = _parse_sync_dt(payload.since) if payload.since else None

    resultado = {}
    for tabla, filas in payload.cambios.items():
        model = SYNCABLE_MODELS.get(tabla)
        if model is None:
            raise HTTPException(status_code=400, detail=f"Tabla no sincronizable: {tabla}")

        aplicados = 0
        conflictos = 0
        for fila in filas:
            row_id = fila.get("id")
            if not row_id:
                continue
            try:
                incoming_updated_at = _parse_sync_dt(fila.get("updated_at")) or datetime.utcnow()
                existing = db.query(model).filter(model.id == row_id).first()

                if existing is None:
                    nuevo = model(id=row_id)
                    _apply_sync_fields(nuevo, fila, tabla)
                    db.add(nuevo)
                    db.flush()
                    if tabla == "atenciones":
                        _procesar_atencion_nueva(db, nuevo, fila.get("medicamentos", []))
                    elif tabla == "tipos_botiquin":
                        _reemplazar_insumos_tipo_botiquin(db, nuevo, fila.get("insumos", []))
                    elif tabla == "botiquin_inspecciones":
                        _procesar_botiquin_inspeccion_nueva(db, nuevo, fila.get("insumos", []))
                    elif tabla == "kardex":
                        _procesar_kardex_nuevo(db, nuevo)
                    db.commit()
                    aplicados += 1
                    continue

                servidor_cambio_despues = since_dt is None or (
                    existing.server_updated_at is not None and existing.server_updated_at > since_dt
                )

                if not servidor_cambio_despues:
                    _apply_sync_fields(existing, fila, tabla)
                    db.commit()
                    aplicados += 1
                    continue

                # Conflicto real
                conflictos += 1
                if existing.updated_at is None or incoming_updated_at >= existing.updated_at:
                    perdedora = _row_to_sync_dict(existing)
                    db.add(models.ConflictoSync(
                        tabla=tabla, registro_id=row_id,
                        version_perdedora=json.dumps(perdedora, default=str),
                        version_ganadora_id=row_id,
                    ))
                    _apply_sync_fields(existing, fila, tabla)
                else:
                    db.add(models.ConflictoSync(
                        tabla=tabla, registro_id=row_id,
                        version_perdedora=json.dumps(fila, default=str),
                        version_ganadora_id=row_id,
                    ))
                    # el servidor conserva su version, no se aplica la entrante
                db.commit()
            except IntegrityError:
                # Choco contra una columna unique (username/ruc/dni/codigo/
                # nombre repetido creado en paralelo por otro dispositivo).
                # Se descarta SOLO esta fila -- rollback aca no afecta las
                # filas anteriores de este mismo tabla porque cada una ya
                # confirmo su propio commit por separado.
                db.rollback()
                conflictos += 1
                db.add(models.ConflictoSync(
                    tabla=tabla, registro_id=row_id,
                    version_perdedora=json.dumps(fila, default=str),
                    version_ganadora_id=None,
                ))
                db.commit()

        resultado[tabla] = {"aplicados": aplicados, "conflictos": conflictos}

    return {"server_time": datetime.utcnow().isoformat(), "resultado": resultado}


# --- Autenticacion ---
@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Usuario o contrase├â┬▒a incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": auth.create_access_token(user.username), "token_type": "bearer"}

@app.get("/auth/me", response_model=schemas.Usuario)
def read_current_user(current_user: models.Usuario = Depends(auth.get_current_user)):
    return current_user

# --- Diagnosticos CIE10 ---
@app.get("/diagnosticos/", response_model=schemas.PaginatedDiagnosticos)
def read_diagnosticos(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)
):
    query = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.is_deleted == False)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (models.DiagnosticoCie10.codigo.ilike(search_term)) |
            (models.DiagnosticoCie10.descripcion.ilike(search_term))
        )

    total = query.count()
    items = query.order_by(models.DiagnosticoCie10.codigo.asc()).offset(skip).limit(limit).all()

    return {"total": total, "items": items}

@app.post("/diagnosticos/", response_model=schemas.DiagnosticoCie10)
def create_diagnostico(diag: schemas.DiagnosticoCie10Create, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_diag = models.DiagnosticoCie10(**diag.dict())
    db.add(db_diag)
    db.commit()
    db.refresh(db_diag)
    return db_diag

@app.put("/diagnosticos/{id}", response_model=schemas.DiagnosticoCie10)
def update_diagnostico(id: str, diag: schemas.DiagnosticoCie10Create, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_diag = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.id == id).first()
    if not db_diag:
        raise HTTPException(status_code=404, detail="Diagn├â┬│stico no encontrado")

    # Check if new code already exists in another record
    if diag.codigo != db_diag.codigo:
        exist = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.codigo == diag.codigo).first()
        if exist:
            raise HTTPException(status_code=400, detail="El c├â┬│digo CIE-10 ya existe")

    for key, value in diag.dict().items():
        setattr(db_diag, key, value)
    db.commit()
    db.refresh(db_diag)
    return db_diag

@app.delete("/diagnosticos/{id}")
def delete_diagnostico(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_diag = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.id == id).first()
    if not db_diag:
        raise HTTPException(status_code=404, detail="Diagn├â┬│stico no encontrado")
    db_diag.is_deleted = True
    db.commit()
    return {"detail": "Eliminado"}

@app.post("/diagnosticos/importar/")
async def import_diagnosticos(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Formato de archivo inv├â┬ílido. Usa Excel (.xlsx)")

    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents), header=None)

        count = 0
        import re

        for index, row in df.iterrows():
            if pd.isna(row.iloc[0]):
                continue

            celda = str(row.iloc[0]).strip()

            # Buscar el patron "CODIGO - DESCRIPCION" (ej. "A00 - COLERA")
            match = re.match(r"^([A-Z0-9.]{3,8})\s*-\s*(.+)$", celda)

            if match:
                codigo = match.group(1).strip()
                descripcion = match.group(2).strip()
            else:
                # Si tiene 2 columnas, plan B cl├â┬ísico
                if len(df.columns) >= 2 and not pd.isna(row.iloc[1]):
                    codigo = celda
                    descripcion = str(row.iloc[1]).strip()
                else:
                    continue

            if codigo and codigo != 'nan' and descripcion and descripcion != 'nan':
                # Evitar duplicados por c├â┬│digo
                exist = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.codigo == codigo).first()
                if not exist:
                    new_diag = models.DiagnosticoCie10(codigo=codigo, descripcion=descripcion)
                    db.add(new_diag)
                    count += 1

        db.commit()
        return {"message": f"Se importaron {count} diagn├â┬│sticos nuevos."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Empresas ---
@app.get("/empresas/", response_model=List[schemas.Empresa])
def read_empresas(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    return db.query(models.Empresa).filter(models.Empresa.is_deleted == False).all()

@app.post("/empresas/", response_model=schemas.Empresa)
def create_empresa(empresa: schemas.EmpresaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_emp = models.Empresa(**empresa.dict())
    db.add(db_emp)
    db.commit()
    db.refresh(db_emp)
    return db_emp

@app.put("/empresas/{id}", response_model=schemas.Empresa)
def update_empresa(id: str, empresa: schemas.EmpresaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_emp = db.query(models.Empresa).filter(models.Empresa.id == id).first()
    if not db_emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    for key, value in empresa.dict().items():
        setattr(db_emp, key, value)
    db.commit()
    db.refresh(db_emp)
    return db_emp

@app.delete("/empresas/{id}")
def delete_empresa(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_emp = db.query(models.Empresa).filter(models.Empresa.id == id).first()
    if not db_emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    db_emp.is_deleted = True
    db.commit()
    return {"detail": "Eliminada"}

# --- Trabajadores ---
@app.get("/trabajadores/", response_model=List[schemas.Trabajador])
def read_trabajadores(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    return (
        db.query(models.Trabajador)
        .filter(models.Trabajador.is_deleted == False)
        .order_by(models.Trabajador.codigo_trabajador.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

@app.post("/trabajadores/", response_model=schemas.Trabajador)
def create_trabajador(trabajador: schemas.TrabajadorCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    if not trabajador.codigo_trabajador:
        trabajador.codigo_trabajador = _next_prefixed_code(db, models.Trabajador, "codigo_trabajador", "TRB")

    db_trabajador = models.Trabajador(**trabajador.dict())
    db.add(db_trabajador)
    db.commit()
    db.refresh(db_trabajador)
    return db_trabajador

@app.get("/trabajadores/obras")
def get_obras(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    obras = db.query(models.Trabajador.obra).filter(
        models.Trabajador.is_deleted == False,
        models.Trabajador.obra.isnot(None),
        models.Trabajador.obra != ""
    ).distinct().order_by(models.Trabajador.obra).all()
    return [o[0] for o in obras if o[0]]

@app.put("/trabajadores/{id}", response_model=schemas.Trabajador)
def update_trabajador(id: str, trabajador: schemas.TrabajadorCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_trabajador = db.query(models.Trabajador).filter(models.Trabajador.id == id).first()
    if not db_trabajador:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    for key, value in trabajador.dict().items():
        setattr(db_trabajador, key, value)
    db.commit()
    db.refresh(db_trabajador)
    return db_trabajador

@app.delete("/trabajadores/{id}")
def delete_trabajador(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_trabajador = db.query(models.Trabajador).filter(models.Trabajador.id == id).first()
    if not db_trabajador:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    db_trabajador.is_deleted = True
    db.commit()
    return {"detail": "Eliminado"}

# --- Sistemas y Clasificaciones ---
@app.get("/sistemas/", response_model=List[schemas.Sistema])
def read_sistemas(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    return db.query(models.SistemaAtencion).filter(models.SistemaAtencion.is_deleted == False).all()

@app.post("/sistemas/", response_model=schemas.Sistema)
def create_sistema(sistema: schemas.SistemaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_sistema = models.SistemaAtencion(**sistema.dict())
    db.add(db_sistema)
    db.commit()
    db.refresh(db_sistema)
    return db_sistema

@app.put("/sistemas/{id}", response_model=schemas.Sistema)
def update_sistema(id: str, sistema: schemas.SistemaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_sistema = db.query(models.SistemaAtencion).filter(models.SistemaAtencion.id == id).first()
    if not db_sistema:
        raise HTTPException(status_code=404, detail="Sistema no encontrado")
    for key, value in sistema.dict().items():
        setattr(db_sistema, key, value)
    db.commit()
    db.refresh(db_sistema)
    return db_sistema

@app.delete("/sistemas/{id}")
def delete_sistema(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_sistema = db.query(models.SistemaAtencion).filter(models.SistemaAtencion.id == id).first()
    if not db_sistema:
        raise HTTPException(status_code=404, detail="Sistema no encontrado")
    db_sistema.is_deleted = True
    db.commit()
    return {"detail": "Eliminado"}

@app.get("/clasificaciones/", response_model=List[schemas.Clasificacion])
def read_clasificaciones(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    return db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.is_deleted == False).all()

@app.post("/clasificaciones/", response_model=schemas.Clasificacion)
def create_clasificacion(clasificacion: schemas.ClasificacionCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_clas = models.ClasificacionAtencion(**clasificacion.dict())
    db.add(db_clas)
    db.commit()
    db.refresh(db_clas)
    return db_clas

@app.put("/clasificaciones/{id}", response_model=schemas.Clasificacion)
def update_clasificacion(id: str, clasificacion: schemas.ClasificacionCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_clas = db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.id == id).first()
    if not db_clas:
        raise HTTPException(status_code=404, detail="Clasificaci├â┬│n no encontrada")
    for key, value in clasificacion.dict().items():
        setattr(db_clas, key, value)
    db.commit()
    db.refresh(db_clas)
    return db_clas

@app.delete("/clasificaciones/{id}")
def delete_clasificacion(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_clas = db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.id == id).first()
    if not db_clas:
        raise HTTPException(status_code=404, detail="Clasificaci├â┬│n no encontrada")
    db_clas.is_deleted = True
    db.commit()
    return {"detail": "Eliminado"}

# --- Atenciones ---
@app.get("/atenciones/", response_model=List[schemas.Atencion])
def read_atenciones(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    return db.query(models.Atencion).filter(models.Atencion.is_deleted == False).order_by(models.Atencion.fecha.desc()).all()

@app.post("/atenciones/", response_model=schemas.Atencion)
def create_atencion(atencion: schemas.AtencionCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    # Separar la data base de medicamentos
    atencion_data = atencion.dict(exclude={'medicamentos'})
    # Si no envian fecha, dejar que el default del modelo (utcnow) la asigne
    if not atencion_data.get("fecha"):
        atencion_data.pop("fecha", None)
    for optional_fk in ("empresa_id", "cita_id", "personal_salud_id"):
        if atencion_data.get(optional_fk) == "":
            atencion_data[optional_fk] = None
    db_atencion = models.Atencion(**atencion_data)

    # Folio correlativo humano (Ficha N├é┬░), asignado solo por el servidor
    max_folio = db.query(func.max(models.Atencion.folio)).scalar()
    db_atencion.folio = (max_folio or 0) + 1

    db.add(db_atencion)
    db.commit()
    db.refresh(db_atencion)

    # Procesar medicamentos si hay
    if atencion.medicamentos:
        for med_req in atencion.medicamentos:
            # A├â┬▒adir relaci├â┬│n
            db_am = models.AtencionMedicamento(
                atencion_id=db_atencion.id,
                medicamento_id=med_req.medicamento_id,
                cantidad=med_req.cantidad
            )
            db.add(db_am)

            # Descontar de stock
            db_med = db.query(models.Medicamento).filter(models.Medicamento.id == med_req.medicamento_id).first()
            if db_med:
                db_med.stock_actual -= med_req.cantidad
                # Registrar en Kardex
                db_kardex = models.Kardex(
                    medicamento_id=db_med.id,
                    tipo_movimiento="SALIDA",
                    cantidad=med_req.cantidad,
                    saldo=db_med.stock_actual
                )
                db.add(db_kardex)

    # Si viene con una cita programada, marcarla como ATENDIDA
    if atencion.cita_id:
        db_cita = db.query(models.Cita).filter(models.Cita.id == atencion.cita_id).first()
        if db_cita:
            db_cita.estado = "ATENDIDA"

    db.commit()
    db.refresh(db_atencion)
    return db_atencion

@app.put("/atenciones/{id}", response_model=schemas.Atencion)
def update_atencion(id: str, atencion: schemas.AtencionCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_atencion = db.query(models.Atencion).filter(models.Atencion.id == id).first()
    if not db_atencion:
        raise HTTPException(status_code=404, detail="Atenci├â┬│n no encontrada")

    atencion_data = atencion.dict(exclude={'medicamentos'})
    # Evitar FK inv├â┬ílidos por strings vac├â┬¡os enviados desde el formulario
    for optional_fk in ("empresa_id", "cita_id", "personal_salud_id"):
        if atencion_data.get(optional_fk) == "":
            atencion_data[optional_fk] = None
    # Si no mandan fecha en la edicion, conservar la existente
    if not atencion_data.get("fecha"):
        atencion_data.pop("fecha", None)

    for key, value in atencion_data.items():
        setattr(db_atencion, key, value)

    # Reemplazar medicamentos: devolver stock anterior y descontar el nuevo
    previos = db.query(models.AtencionMedicamento).filter(
        models.AtencionMedicamento.atencion_id == id
    ).all()
    for prev in previos:
        db_med = db.query(models.Medicamento).filter(models.Medicamento.id == prev.medicamento_id).first()
        if db_med:
            db_med.stock_actual += prev.cantidad
            db.add(models.Kardex(
                medicamento_id=db_med.id,
                tipo_movimiento="INGRESO",
                cantidad=prev.cantidad,
                saldo=db_med.stock_actual
            ))
        db.delete(prev)
    db.flush()

    if atencion.medicamentos:
        for med_req in atencion.medicamentos:
            if not med_req.medicamento_id:
                continue
            db.add(models.AtencionMedicamento(
                atencion_id=db_atencion.id,
                medicamento_id=med_req.medicamento_id,
                cantidad=med_req.cantidad
            ))
            db_med = db.query(models.Medicamento).filter(models.Medicamento.id == med_req.medicamento_id).first()
            if db_med:
                db_med.stock_actual -= med_req.cantidad
                db.add(models.Kardex(
                    medicamento_id=db_med.id,
                    tipo_movimiento="SALIDA",
                    cantidad=med_req.cantidad,
                    saldo=db_med.stock_actual
                ))

    db.commit()
    db.refresh(db_atencion)
    return db_atencion

@app.delete("/atenciones/{id}")
def delete_atencion(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_atencion = db.query(models.Atencion).filter(models.Atencion.id == id).first()
    if not db_atencion:
        raise HTTPException(status_code=404, detail="Atenci├â┬│n no encontrada")
    db_atencion.is_deleted = True
    db.commit()
    return {"detail": "Eliminada"}

# --- Medicamentos y Kardex ---
@app.get("/medicamentos/", response_model=List[schemas.Medicamento])
def read_medicamentos(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    return db.query(models.Medicamento).filter(models.Medicamento.is_deleted == False).all()

@app.post("/medicamentos/", response_model=schemas.Medicamento)
def create_medicamento(medicamento: schemas.MedicamentoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    if not medicamento.codigo:
        medicamento.codigo = _next_prefixed_code(db, models.Medicamento, "codigo", "MED")
    db_med = models.Medicamento(**medicamento.dict())
    db.add(db_med)
    db.commit()
    db.refresh(db_med)
    return db_med

@app.put("/medicamentos/{id}", response_model=schemas.Medicamento)
def update_medicamento(id: str, medicamento: schemas.MedicamentoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_med = db.query(models.Medicamento).filter(models.Medicamento.id == id).first()
    if not db_med:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    for key, value in medicamento.dict().items():
        setattr(db_med, key, value)
    db.commit()
    db.refresh(db_med)
    return db_med

@app.delete("/medicamentos/{id}")
def delete_medicamento(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_med = db.query(models.Medicamento).filter(models.Medicamento.id == id).first()
    if not db_med:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    db_med.is_deleted = True
    db.commit()
    return {"detail": "Eliminado"}

def _norm_header(h) -> str:
    h = str(h).strip().lower()
    for a, b in [("├â┬í", "a"), ("├â┬®", "e"), ("├â┬¡", "i"), ("├â┬│", "o"), ("├â┬║", "u"), ("├â┬▒", "n")]:
        h = h.replace(a, b)
    return re.sub(r"[\s_\-\.]+", "", h)

_MED_HEADER_ALIASES = {
    "codigo": "codigo",
    "nombre": "nombre",
    "medicamento": "nombre",
    "producto": "nombre",
    "presentacion": "presentacion",
    "tipo": "tipo",
    "descripcion": "descripcion",
    "costounitario": "costo_unitario",
    "costo": "costo_unitario",
    "precio": "costo_unitario",
    "preciounitario": "costo_unitario",
    "lote": "lote",
    "fechavencimiento": "fecha_vencimiento",
    "vencimiento": "fecha_vencimiento",
    "fecvenc": "fecha_vencimiento",
    "fecvencimiento": "fecha_vencimiento",
    "stock": "stock_inicial",
    "stockactual": "stock_inicial",
    "stockinicial": "stock_inicial",
}
_MED_TIPOS_VALIDOS = {"MEDICAMENTO", "INSUMO", "OTROS"}
_MED_MESES_ES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
}


def _parse_med_costo(val) -> float:
    """Acepta numeros tal cual o texto con simbolo de moneda ('S/ 37.20'),
    porque los excels reales de la clinica traen la columna de precio
    formateada como moneda, no como numero plano."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = re.sub(r"[^\d.,\-]", "", str(val))
    if not s:
        return 0.0
    if ',' in s and '.' in s:
        s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_med_fecha_vencimiento(val):
    """Ademas de fechas reales de Excel, acepta el formato abreviado en
    espa├â┬▒ol que usa el excel real de la clinica para la columna de
    vencimiento (ej. 'sep.-28', 'ene.-28') -- no trae dia, se asume el 01
    del mes."""
    if val is None:
        return None
    if isinstance(val, (pd.Timestamp, datetime)):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    m = re.match(r"^([a-zA-Z]{3})\.?-?(\d{2,4})$", s)
    if m:
        mes = _MED_MESES_ES.get(m.group(1).lower())
        anio = int(m.group(2))
        if anio < 100:
            anio += 2000
        if mes:
            return f"{anio:04d}-{mes:02d}-01"
    return s

@app.post("/medicamentos/importar/")
async def import_medicamentos(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    """Importa/actualiza el catalogo desde un Excel. Columnas reconocidas
    (encabezados en cualquiera de las primeras 10 filas -- por si hay una
    fila de titulo o una fila vacia arriba de la tabla -- sin importar
    mayusculas/acentos): Codigo, Nombre, Presentacion, Tipo, Descripcion,
    Costo Unitario, Lote, Fecha Vencimiento, Stock Inicial. Solo Nombre y
    Presentacion son obligatorias. Si el Codigo ya existe en el catalogo
    (o si no hay Codigo, si el Nombre ya existe), actualiza esa fila en vez
    de crear una nueva; si no trae Codigo, se genera uno (MED-000X)."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Formato de archivo inv├â┬ílido. Usa Excel (.xlsx)")

    contents = await file.read()
    try:
        # La fila de encabezados no siempre es la primera -- varios excels
        # reales traen una fila de titulo o una fila vacia arriba de la
        # tabla. Se buscan encabezados reconocibles en las primeras filas
        # en vez de asumir siempre header=0.
        muestra = pd.read_excel(io.BytesIO(contents), header=None, nrows=10)
        header_row_idx, mejor_cantidad = 0, -1
        for i in range(len(muestra)):
            cantidad = sum(1 for v in muestra.iloc[i].tolist() if _MED_HEADER_ALIASES.get(_norm_header(v)))
            if cantidad > mejor_cantidad:
                header_row_idx, mejor_cantidad = i, cantidad
        if mejor_cantidad <= 0:
            raise HTTPException(status_code=400, detail="No se encontraron encabezados reconocibles (Nombre/Medicamento, Presentaci├â┬│n, etc.) en las primeras filas del archivo.")

        df = pd.read_excel(io.BytesIO(contents), header=header_row_idx)
        encabezados_originales = [str(c) for c in df.columns]
        df.columns = [_MED_HEADER_ALIASES.get(_norm_header(c)) for c in df.columns]

        creados = 0
        actualizados = 0
        omitidos = 0

        def get(row, col):
            if col not in df.columns:
                return None
            val = row[col]
            if isinstance(val, pd.Series):
                val = val.iloc[0]
            return None if pd.isna(val) else val

        def trunc(s, n):
            return s if s is None else str(s).strip()[:n]

        for _, row in df.iterrows():
            nombre = get(row, "nombre")
            presentacion = get(row, "presentacion")
            if not nombre or not presentacion:
                omitidos += 1
                continue

            # Se recorta cada campo a su limite de columna: una celda con
            # texto mas largo de lo esperado (ej. una nota en vez de una
            # fecha) no debe tumbar el INSERT de las 200+ filas restantes,
            # que van todas en la misma transaccion.
            codigo = trunc(get(row, "codigo"), 50)

            tipo = get(row, "tipo")
            tipo = str(tipo).strip().upper() if tipo else "MEDICAMENTO"
            if tipo not in _MED_TIPOS_VALIDOS:
                tipo = "MEDICAMENTO"

            descripcion = get(row, "descripcion")
            descripcion = str(descripcion).strip() if descripcion else None

            lote = trunc(get(row, "lote"), 50)

            fecha_venc = trunc(_parse_med_fecha_vencimiento(get(row, "fecha_vencimiento")), 20)

            costo = _parse_med_costo(get(row, "costo_unitario"))

            try:
                stock_inicial = int(get(row, "stock_inicial") or 0)
            except (ValueError, TypeError):
                stock_inicial = 0

            nombre = trunc(nombre, 150)
            presentacion = trunc(presentacion, 100).upper()

            existente = None
            if codigo:
                existente = db.query(models.Medicamento).filter(models.Medicamento.codigo == codigo).first()
            if not existente:
                # Muchos excels de la clinica no traen Codigo -- sin esto,
                # cada reimportacion del mismo listado duplicaria todo el
                # catalogo en vez de actualizar precios/stock/vencimiento.
                existente = db.query(models.Medicamento).filter(
                    func.lower(models.Medicamento.nombre) == nombre.lower(),
                    models.Medicamento.is_deleted == False,
                ).first()

            if existente:
                existente.nombre = nombre
                existente.presentacion = presentacion
                existente.tipo = tipo
                existente.descripcion = descripcion
                existente.lote = lote
                existente.fecha_vencimiento = fecha_venc
                existente.costo_unitario = costo
                actualizados += 1
            else:
                if not codigo:
                    codigo = _next_prefixed_code(db, models.Medicamento, "codigo", "MED")
                nuevo = models.Medicamento(
                    codigo=codigo, nombre=nombre, presentacion=presentacion,
                    tipo=tipo, descripcion=descripcion, lote=lote, fecha_vencimiento=fecha_venc,
                    costo_unitario=costo, stock_actual=0,
                )
                db.add(nuevo)
                db.flush()
                if stock_inicial > 0:
                    nuevo.stock_actual = stock_inicial
                    db.add(models.Kardex(
                        medicamento_id=nuevo.id, tipo_movimiento="INGRESO",
                        cantidad=stock_inicial, saldo=stock_inicial,
                    ))
                creados += 1

        db.commit()
        msg = f"Importaci├â┬│n completa: {creados} nuevos, {actualizados} actualizados, {omitidos} fila(s) omitida(s) (sin nombre o presentaci├â┬│n)."
        if creados == 0 and actualizados == 0 and omitidos > 0:
            msg += f" Encabezados detectados en el archivo: {', '.join(encabezados_originales)}."
        return {"message": msg}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/kardex/todos/", response_model=List[schemas.Kardex])
def read_kardex_todos(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    """Historial global de movimientos (todos los productos), para la
    pantalla de Control de Almacen -- a diferencia de /kardex/{id}, que es
    el historial de un solo medicamento (usado en el modal de detalle)."""
    return db.query(models.Kardex).filter(
        models.Kardex.is_deleted == False
    ).order_by(models.Kardex.fecha.desc()).limit(1000).all()

@app.get("/kardex/{medicamento_id}", response_model=List[schemas.Kardex])
def read_kardex(medicamento_id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    return db.query(models.Kardex).filter(
        models.Kardex.medicamento_id == medicamento_id,
        models.Kardex.is_deleted == False
    ).order_by(models.Kardex.fecha.desc()).all()

@app.post("/kardex/", response_model=schemas.Kardex)
def create_kardex(kardex: schemas.KardexCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_med = db.query(models.Medicamento).filter(
        models.Medicamento.id == kardex.medicamento_id,
        models.Medicamento.is_deleted == False
    ).first()
    if not db_med:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")

    # Update stock
    if kardex.tipo_movimiento == "INGRESO":
        db_med.stock_actual += kardex.cantidad
    elif kardex.tipo_movimiento == "SALIDA":
        if db_med.stock_actual < kardex.cantidad:
            raise HTTPException(status_code=400, detail="Stock insuficiente")
        db_med.stock_actual -= kardex.cantidad

    db_kardex = models.Kardex(
        medicamento_id=kardex.medicamento_id,
        tipo_movimiento=kardex.tipo_movimiento,
        cantidad=kardex.cantidad,
        saldo=db_med.stock_actual,
        lote=kardex.lote,
        fecha_vencimiento=kardex.fecha_vencimiento,
    )
    db.add(db_kardex)
    db.commit()
    db.refresh(db_kardex)
    return db_kardex

# --- Personal de Salud ---
@app.get("/personal_salud/", response_model=List[schemas.PersonalSalud])
def read_personal_salud(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    return db.query(models.PersonalSalud).filter(models.PersonalSalud.is_deleted == False).all()

@app.post("/personal_salud/", response_model=schemas.PersonalSalud)
def create_personal_salud(personal: schemas.PersonalSaludCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_personal = models.PersonalSalud(**personal.dict())
    db.add(db_personal)
    db.commit()
    db.refresh(db_personal)
    return db_personal

@app.put("/personal_salud/{id}", response_model=schemas.PersonalSalud)
def update_personal_salud(id: str, personal: schemas.PersonalSaludCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_personal = db.query(models.PersonalSalud).filter(models.PersonalSalud.id == id).first()
    if not db_personal:
        raise HTTPException(status_code=404, detail="Personal no encontrado")
    for key, value in personal.dict().items():
        setattr(db_personal, key, value)
    db.commit()
    db.refresh(db_personal)
    return db_personal

@app.delete("/personal_salud/{id}")
def delete_personal_salud(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_personal = db.query(models.PersonalSalud).filter(models.PersonalSalud.id == id).first()
    if not db_personal:
        raise HTTPException(status_code=404, detail="Personal no encontrado")
    db_personal.is_deleted = True
    db.commit()
    return {"detail": "Eliminado"}

# --- Tipos de Botiquin ---
@app.get("/tipos_botiquin/", response_model=List[schemas.TipoBotiquin])
def read_tipos_botiquin(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user),
):
    q = db.query(models.TipoBotiquin).filter(models.TipoBotiquin.is_deleted == False)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (models.TipoBotiquin.codigo.ilike(like))
            | (models.TipoBotiquin.nombre.ilike(like))
        )
    return q.order_by(models.TipoBotiquin.nombre.asc()).all()


@app.post("/tipos_botiquin/", response_model=schemas.TipoBotiquin)
def create_tipo_botiquin(
    tipo: schemas.TipoBotiquinCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user),
):
    data = tipo.dict(exclude={"insumos"})
    if not (data.get("codigo") or "").strip():
        data["codigo"] = _next_prefixed_code(db, models.TipoBotiquin, "codigo", "TB")
    else:
        data["codigo"] = data["codigo"].strip()
    db_tipo = models.TipoBotiquin(**data)
    db.add(db_tipo)
    db.flush()
    _reemplazar_insumos_tipo_botiquin(db, db_tipo, tipo.insumos or [])
    db.commit()
    db.refresh(db_tipo)
    return db_tipo


@app.get("/tipos_botiquin/{id}", response_model=schemas.TipoBotiquin)
def read_tipo_botiquin(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_tipo = db.query(models.TipoBotiquin).filter(
        models.TipoBotiquin.id == id,
        models.TipoBotiquin.is_deleted == False,
    ).first()
    if not db_tipo:
        raise HTTPException(status_code=404, detail="Tipo de botiquín no encontrado")
    return db_tipo


@app.put("/tipos_botiquin/{id}", response_model=schemas.TipoBotiquin)
def update_tipo_botiquin(
    id: str,
    tipo: schemas.TipoBotiquinCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user),
):
    db_tipo = db.query(models.TipoBotiquin).filter(models.TipoBotiquin.id == id).first()
    if not db_tipo:
        raise HTTPException(status_code=404, detail="Tipo de botiquín no encontrado")
    data = tipo.dict(exclude={"insumos"})
    if data.get("codigo") is not None:
        data["codigo"] = (data["codigo"] or "").strip() or db_tipo.codigo
    for key, value in data.items():
        setattr(db_tipo, key, value)
    _reemplazar_insumos_tipo_botiquin(db, db_tipo, tipo.insumos or [])
    db.commit()
    db.refresh(db_tipo)
    return db_tipo


@app.delete("/tipos_botiquin/{id}")
def delete_tipo_botiquin(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_tipo = db.query(models.TipoBotiquin).filter(models.TipoBotiquin.id == id).first()
    if not db_tipo:
        raise HTTPException(status_code=404, detail="Tipo de botiquín no encontrado")
    en_uso = db.query(models.Botiquin).filter(
        models.Botiquin.tipo_botiquin_id == id,
        models.Botiquin.is_deleted == False,
    ).count()
    if en_uso:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {en_uso} botiquín(es) usando este tipo",
        )
    db_tipo.is_deleted = True
    db.commit()
    return {"detail": "Eliminado"}


# --- Botiquin ---
@app.get("/botiquines/", response_model=List[schemas.Botiquin])
def read_botiquines(
    tipo_equipo: Optional[str] = None,
    area: Optional[str] = None,
    empresa_id: Optional[str] = None,
    equipo: Optional[str] = None,
    estado: Optional[str] = None,
    tipo_botiquin_id: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user),
):
    q = db.query(models.Botiquin).filter(models.Botiquin.is_deleted == False)
    if tipo_equipo:
        q = q.filter(models.Botiquin.tipo_equipo == tipo_equipo)
    if area:
        q = q.filter(models.Botiquin.area == area)
    if empresa_id:
        q = q.filter(models.Botiquin.empresa_id == empresa_id)
    if equipo:
        q = q.filter(models.Botiquin.equipo == equipo)
    if estado:
        q = q.filter(models.Botiquin.estado == estado)
    if tipo_botiquin_id:
        q = q.filter(models.Botiquin.tipo_botiquin_id == tipo_botiquin_id)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (models.Botiquin.codigo.ilike(like))
            | (models.Botiquin.ubicacion.ilike(like))
            | (models.Botiquin.numero_serie_placa.ilike(like))
            | (models.Botiquin.vehiculo.ilike(like))
            | (models.Botiquin.marca.ilike(like))
            | (models.Botiquin.modelo.ilike(like))
            | (models.Botiquin.tipo_equipo.ilike(like))
            | (models.Botiquin.equipo.ilike(like))
        )
    return q.order_by(models.Botiquin.created_at.desc()).all()


@app.post("/botiquines/", response_model=schemas.Botiquin)
def create_botiquin(
    botiquin: schemas.BotiquinCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user),
):
    data = botiquin.dict()
    if not data.get("empresa_id"):
        data["empresa_id"] = None
    if not data.get("tipo_botiquin_id"):
        data["tipo_botiquin_id"] = None
    elif not db.query(models.TipoBotiquin).filter(
        models.TipoBotiquin.id == data["tipo_botiquin_id"],
        models.TipoBotiquin.is_deleted == False,
    ).first():
        raise HTTPException(status_code=400, detail="Tipo de botiquín no encontrado")
    if not (data.get("codigo") or "").strip():
        data["codigo"] = _next_prefixed_code(db, models.Botiquin, "codigo", "BOT")
    else:
        data["codigo"] = data["codigo"].strip()
    if not data.get("fecha_creacion"):
        data["fecha_creacion"] = datetime.utcnow()
    db_bot = models.Botiquin(**data)
    db.add(db_bot)
    db.commit()
    db.refresh(db_bot)
    return db_bot


@app.get("/botiquines/{id}", response_model=schemas.Botiquin)
def read_botiquin(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_bot = db.query(models.Botiquin).filter(models.Botiquin.id == id, models.Botiquin.is_deleted == False).first()
    if not db_bot:
        raise HTTPException(status_code=404, detail="Botiquín no encontrado")
    return db_bot


@app.get("/botiquines/{id}/insumos", response_model=List[schemas.TipoBotiquinInsumo])
def read_botiquin_insumos(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    """Plantilla de insumos del tipo asociado al botiquin (para inspecciones)."""
    db_bot = db.query(models.Botiquin).filter(models.Botiquin.id == id, models.Botiquin.is_deleted == False).first()
    if not db_bot:
        raise HTTPException(status_code=404, detail="Botiquín no encontrado")
    return _insumos_plantilla_botiquin(db, db_bot)


@app.put("/botiquines/{id}", response_model=schemas.Botiquin)
def update_botiquin(
    id: str,
    botiquin: schemas.BotiquinCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user),
):
    db_bot = db.query(models.Botiquin).filter(models.Botiquin.id == id).first()
    if not db_bot:
        raise HTTPException(status_code=404, detail="Botiquín no encontrado")
    data = botiquin.dict()
    if not data.get("empresa_id"):
        data["empresa_id"] = None
    if not data.get("tipo_botiquin_id"):
        data["tipo_botiquin_id"] = None
    elif not db.query(models.TipoBotiquin).filter(
        models.TipoBotiquin.id == data["tipo_botiquin_id"],
        models.TipoBotiquin.is_deleted == False,
    ).first():
        raise HTTPException(status_code=400, detail="Tipo de botiquín no encontrado")
    if data.get("codigo") is not None:
        data["codigo"] = (data["codigo"] or "").strip() or db_bot.codigo
    for key, value in data.items():
        setattr(db_bot, key, value)
    db.commit()
    db.refresh(db_bot)
    return db_bot


@app.delete("/botiquines/{id}")
def delete_botiquin(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_bot = db.query(models.Botiquin).filter(models.Botiquin.id == id).first()
    if not db_bot:
        raise HTTPException(status_code=404, detail="Botiquín no encontrado")
    db_bot.is_deleted = True
    db.commit()
    return {"detail": "Eliminado"}


@app.get("/botiquin_inspecciones/", response_model=List[schemas.BotiquinInspeccion])
def read_botiquin_inspecciones(
    botiquin_id: Optional[str] = None,
    responsable_id: Optional[str] = None,
    empresa_id: Optional[str] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user),
):
    q = (
        db.query(models.BotiquinInspeccion)
        .filter(models.BotiquinInspeccion.is_deleted == False)
        .join(models.Botiquin, models.Botiquin.id == models.BotiquinInspeccion.botiquin_id)
    )
    if botiquin_id:
        q = q.filter(models.BotiquinInspeccion.botiquin_id == botiquin_id)
    if responsable_id:
        q = q.filter(models.BotiquinInspeccion.responsable_id == responsable_id)
    if empresa_id:
        q = q.filter(models.Botiquin.empresa_id == empresa_id)
    if fecha_inicio:
        q = q.filter(func.date(models.BotiquinInspeccion.fecha) >= fecha_inicio)
    if fecha_fin:
        q = q.filter(func.date(models.BotiquinInspeccion.fecha) <= fecha_fin)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (models.Botiquin.ubicacion.ilike(like))
            | (models.Botiquin.numero_serie_placa.ilike(like))
            | (models.Botiquin.tipo_equipo.ilike(like))
        )
    return q.order_by(models.BotiquinInspeccion.fecha.desc()).all()


@app.post("/botiquin_inspecciones/", response_model=schemas.BotiquinInspeccion)
def create_botiquin_inspeccion(
    inspeccion: schemas.BotiquinInspeccionCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user),
):
    bot = db.query(models.Botiquin).filter(
        models.Botiquin.id == inspeccion.botiquin_id,
        models.Botiquin.is_deleted == False,
    ).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Botiqu├¡n no encontrado")

    data = inspeccion.dict(exclude={"insumos"})
    if not data.get("responsable_id"):
        data["responsable_id"] = None
    if not data.get("fecha"):
        data["fecha"] = datetime.utcnow()

    db_insp = models.BotiquinInspeccion(**data)
    db.add(db_insp)
    db.flush()

    for item in inspeccion.insumos or []:
        med = db.query(models.Medicamento).filter(models.Medicamento.id == item.medicamento_id).first()
        if not med:
            raise HTTPException(status_code=400, detail=f"Insumo no encontrado: {item.medicamento_id}")
        cantidad = max(1, int(item.cantidad or 1))
        db.add(models.BotiquinInspeccionInsumo(
            inspeccion_id=db_insp.id,
            medicamento_id=item.medicamento_id,
            cantidad=cantidad,
        ))

    db.commit()
    db.refresh(db_insp)
    return db_insp


@app.get("/botiquin_inspecciones/{id}", response_model=schemas.BotiquinInspeccion)
def read_botiquin_inspeccion(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_insp = db.query(models.BotiquinInspeccion).filter(
        models.BotiquinInspeccion.id == id,
        models.BotiquinInspeccion.is_deleted == False,
    ).first()
    if not db_insp:
        raise HTTPException(status_code=404, detail="Inspecci├│n no encontrada")
    return db_insp


@app.delete("/botiquin_inspecciones/{id}")
def delete_botiquin_inspeccion(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_insp = db.query(models.BotiquinInspeccion).filter(models.BotiquinInspeccion.id == id).first()
    if not db_insp:
        raise HTTPException(status_code=404, detail="Inspecci├│n no encontrada")
    db_insp.is_deleted = True
    db.commit()
    return {"detail": "Eliminado"}


@app.get("/reportes/consumo-insumos-botiquin")
def get_reporte_consumo_insumos_botiquin(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    empresa_id: Optional[str] = None,
    botiquin_id: Optional[str] = None,
    area: Optional[str] = None,
    tipo_equipo: Optional[str] = None,
    equipo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user),
):
    """Consumo de insumos registrados en inspecciones de botiquin, con costo total."""
    q = (
        db.query(models.BotiquinInspeccionInsumo, models.BotiquinInspeccion, models.Botiquin, models.Medicamento)
        .join(models.BotiquinInspeccion, models.BotiquinInspeccion.id == models.BotiquinInspeccionInsumo.inspeccion_id)
        .join(models.Botiquin, models.Botiquin.id == models.BotiquinInspeccion.botiquin_id)
        .join(models.Medicamento, models.Medicamento.id == models.BotiquinInspeccionInsumo.medicamento_id)
        .filter(models.BotiquinInspeccion.is_deleted == False)
        .filter(models.Botiquin.is_deleted == False)
    )
    if fecha_inicio:
        q = q.filter(func.date(models.BotiquinInspeccion.fecha) >= fecha_inicio)
    if fecha_fin:
        q = q.filter(func.date(models.BotiquinInspeccion.fecha) <= fecha_fin)
    if empresa_id:
        q = q.filter(models.Botiquin.empresa_id == empresa_id)
    if botiquin_id:
        q = q.filter(models.Botiquin.id == botiquin_id)
    if area:
        q = q.filter(models.Botiquin.area == area)
    if tipo_equipo:
        q = q.filter(models.Botiquin.tipo_equipo == tipo_equipo)
    if equipo:
        q = q.filter(models.Botiquin.equipo == equipo)

    resultados = q.all()
    from collections import defaultdict

    insumos_dict = {}
    fechas_set = set()
    total_general = 0.0

    for item, insp, bot, med in resultados:
        if not insp.fecha:
            continue
        fecha_str = insp.fecha.strftime("%Y-%m-%d")
        fechas_set.add(fecha_str)
        precio = float(med.costo_unitario or 0)
        if med.id not in insumos_dict:
            insumos_dict[med.id] = {
                "id": med.id,
                "codigo": med.codigo or "",
                "nombre": med.nombre or "",
                "presentacion": med.presentacion or "",
                "tipo": med.tipo or "",
                "precio_und": precio,
                "consumos": defaultdict(int),
                "sub_total_cantidad": 0,
                "total_soles": 0.0,
            }
        insumos_dict[med.id]["consumos"][fecha_str] += item.cantidad or 0
        insumos_dict[med.id]["sub_total_cantidad"] += item.cantidad or 0

    lista = []
    for m in insumos_dict.values():
        m["total_soles"] = round(m["sub_total_cantidad"] * m["precio_und"], 2)
        total_general += m["total_soles"]
        m["consumos"] = dict(m["consumos"])
        lista.append(m)

    lista.sort(key=lambda x: x["total_soles"], reverse=True)
    total_general = round(total_general, 2)
    sub_total = round(total_general / 1.18, 2) if total_general else 0.0
    igv = round(total_general - sub_total, 2) if total_general else 0.0

    return {
        "rango_fechas": sorted(list(fechas_set)),
        "insumos": lista,
        "totales": {
            "sub_total": sub_total,
            "igv": igv,
            "total": total_general,
        },
    }


# --- Citas ---
@app.get("/citas/", response_model=List[schemas.Cita])
def read_citas(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    return db.query(models.Cita).filter(models.Cita.is_deleted == False).order_by(models.Cita.fecha_hora.desc()).all()

@app.post("/citas/", response_model=schemas.Cita)
def create_cita(cita: schemas.CitaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_cita = models.Cita(**cita.dict())
    db.add(db_cita)
    db.commit()
    db.refresh(db_cita)
    return db_cita

@app.put("/citas/{id}", response_model=schemas.Cita)
def update_cita(id: str, cita: schemas.CitaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_cita = db.query(models.Cita).filter(models.Cita.id == id).first()
    if not db_cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    for key, value in cita.dict().items():
        setattr(db_cita, key, value)
    db.commit()
    db.refresh(db_cita)
    return db_cita

@app.delete("/citas/{id}")
def delete_cita(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_cita = db.query(models.Cita).filter(models.Cita.id == id).first()
    if not db_cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    db_cita.is_deleted = True
    db.commit()
    return {"detail": "Eliminada"}

# --- Dashboard ---
@app.get("/dashboard/kpis")
def get_dashboard_kpis(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    atenciones_count = db.query(models.Atencion).filter(models.Atencion.is_deleted == False).count()
    trabajadores_count = db.query(models.Trabajador).filter(models.Trabajador.is_deleted == False).count()
    medicamentos_count = db.query(models.Medicamento).filter(models.Medicamento.is_deleted == False).count()
    stock_bajo = db.query(models.Medicamento).filter(models.Medicamento.is_deleted == False, models.Medicamento.stock_actual < 10).count()

    return {
        "total_atenciones": atenciones_count,
        "total_trabajadores": trabajadores_count,
        "total_medicamentos": medicamentos_count,
        "medicamentos_stock_bajo": stock_bajo
    }

@app.get("/dashboard/stats")
def get_dashboard_stats(fecha_inicio: str = None, fecha_fin: str = None, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    # Helper to apply date filters
    def apply_date_filter(query):
        if fecha_inicio:
            query = query.filter(func.date(models.Atencion.fecha) >= fecha_inicio)
        if fecha_fin:
            query = query.filter(func.date(models.Atencion.fecha) <= fecha_fin)
        return query

    # 1. Enfermedades m├â┬ís frecuentes
    q_enf = db.query(models.Atencion.diagnostico, func.count(models.Atencion.id).label('total')) \
        .filter(models.Atencion.is_deleted == False, models.Atencion.diagnostico != None, models.Atencion.diagnostico != '')
    q_enf = apply_date_filter(q_enf)
    top_enfermedades = q_enf.group_by(models.Atencion.diagnostico) \
        .order_by(func.count(models.Atencion.id).desc()) \
        .limit(5).all()

    enfermedades = [{"name": str(e.diagnostico), "value": int(e.total)} for e in top_enfermedades]

    # 2. Pacientes m├â┬ís atendidos
    q_pac = db.query(models.Trabajador.nombre, models.Trabajador.apellidos, func.count(models.Atencion.id).label('total')) \
        .join(models.Atencion, models.Trabajador.id == models.Atencion.trabajador_id) \
        .filter(models.Atencion.is_deleted == False)
    q_pac = apply_date_filter(q_pac)
    top_pacientes = q_pac.group_by(models.Trabajador.id) \
        .order_by(func.count(models.Atencion.id).desc()) \
        .limit(5).all()

    pacientes = [{"name": f"{p.nombre} {p.apellidos}", "value": int(p.total)} for p in top_pacientes]

    # 3. Empresas m├â┬ís atendidas
    q_emp = db.query(models.Empresa.nombre, func.count(models.Atencion.id).label('total')) \
        .join(models.Atencion, models.Empresa.id == models.Atencion.empresa_id) \
        .filter(models.Atencion.is_deleted == False)
    q_emp = apply_date_filter(q_emp)
    top_empresas = q_emp.group_by(models.Empresa.id) \
        .order_by(func.count(models.Atencion.id).desc()) \
        .limit(5).all()

    empresas = [{"name": str(e.nombre), "value": int(e.total)} for e in top_empresas]

    # 4. Medicamentos m├â┬ís usados
    q_med = db.query(models.Medicamento.nombre, func.sum(models.AtencionMedicamento.cantidad).label('total')) \
        .join(models.AtencionMedicamento, models.Medicamento.id == models.AtencionMedicamento.medicamento_id) \
        .join(models.Atencion, models.Atencion.id == models.AtencionMedicamento.atencion_id) \
        .filter(models.Atencion.is_deleted == False)
    q_med = apply_date_filter(q_med)
    top_medicamentos = q_med.group_by(models.Medicamento.id) \
        .order_by(func.sum(models.AtencionMedicamento.cantidad).desc()) \
        .limit(5).all()

    medicamentos = [{"name": str(m.nombre), "value": int(m.total or 0)} for m in top_medicamentos]

    # 5. Costos por Empresa
    q_costos = db.query(models.Empresa.nombre, func.sum(models.AtencionMedicamento.cantidad * models.Medicamento.costo_unitario).label('total_costo')) \
        .join(models.Atencion, models.Empresa.id == models.Atencion.empresa_id) \
        .join(models.AtencionMedicamento, models.Atencion.id == models.AtencionMedicamento.atencion_id) \
        .join(models.Medicamento, models.AtencionMedicamento.medicamento_id == models.Medicamento.id) \
        .filter(models.Atencion.is_deleted == False)
    q_costos = apply_date_filter(q_costos)
    costos_empresa_query = q_costos.group_by(models.Empresa.id) \
        .order_by(func.sum(models.AtencionMedicamento.cantidad * models.Medicamento.costo_unitario).desc()) \
        .limit(10).all()

    costos = [{"name": str(c.nombre), "value": float(c.total_costo or 0)} for c in costos_empresa_query]

    # 6. Estado de Empresas (Activas vs Inactivas)
    q_estado = db.query(models.Empresa.estado, func.count(models.Empresa.id).label('total')) \
        .filter(models.Empresa.is_deleted == False) \
        .group_by(models.Empresa.estado).all()
    estado_empresas = [{"name": str(e.estado or 'Desconocido'), "value": int(e.total)} for e in q_estado]

    # 7. Atenciones por D├â┬¡a (├â┼íltimas Atenciones Gr├â┬ífico)
    q_dias = db.query(func.date(models.Atencion.fecha).label('dia'), func.count(models.Atencion.id).label('total')) \
        .filter(models.Atencion.is_deleted == False)
    q_dias = apply_date_filter(q_dias)
    dias_query = q_dias.group_by(func.date(models.Atencion.fecha)).order_by(func.date(models.Atencion.fecha).asc()).limit(14).all()
    atenciones_por_dia = [{"name": str(d.dia), "value": int(d.total)} for d in dias_query]

    # 8. ├â┼íltimas Atenciones Realizadas (Lista)
    q_ultimas = db.query(models.Atencion).filter(models.Atencion.is_deleted == False)
    q_ultimas = apply_date_filter(q_ultimas)
    ultimas = q_ultimas.order_by(models.Atencion.fecha.desc()).limit(10).all()
    ultimas_atenciones = []
    for a in ultimas:
        ultimas_atenciones.append({
            "id": a.id,
            "fecha": str(a.fecha.date()) if a.fecha else "",
            "paciente": f"{a.trabajador.nombre} {a.trabajador.apellidos}" if a.trabajador else "N/A",
            "diagnostico": str(a.diagnostico or ""),
            "sistema": a.sistema.nombre if a.sistema else "N/A"
        })

    # 9. Sistemas Afectados (Ranking)
    q_sist = db.query(models.SistemaAtencion.nombre, func.count(models.Atencion.id).label('total')) \
        .join(models.Atencion, models.SistemaAtencion.id == models.Atencion.sistema_id) \
        .filter(models.Atencion.is_deleted == False)
    q_sist = apply_date_filter(q_sist)
    top_sistemas = q_sist.group_by(models.SistemaAtencion.id).order_by(func.count(models.Atencion.id).desc()).limit(10).all()
    sistemas_afectados = [{"name": str(s.nombre), "value": int(s.total)} for s in top_sistemas]

    return {
        "enfermedades": enfermedades,
        "pacientes": pacientes,
        "empresas": empresas,
        "medicamentos": medicamentos,
        "costos": costos,
        "estado_empresas": estado_empresas,
        "atenciones_por_dia": atenciones_por_dia,
        "ultimas_atenciones": ultimas_atenciones,
        "sistemas_afectados": sistemas_afectados
    }

@app.get("/dashboard/reporte-sistemas")
def get_reporte_sistemas(
    fecha_inicio: str = None,
    fecha_fin: str = None,
    sistema_id: Optional[str] = None,
    empresa_id: Optional[str] = None,
    obra: str = None,
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)
):
    query = db.query(models.SistemaAtencion.nombre, func.count(models.Atencion.id).label('total')) \
        .join(models.Atencion, models.SistemaAtencion.id == models.Atencion.sistema_id) \
        .filter(models.Atencion.is_deleted == False)

    if fecha_inicio:
        query = query.filter(func.date(models.Atencion.fecha) >= fecha_inicio)
    if fecha_fin:
        query = query.filter(func.date(models.Atencion.fecha) <= fecha_fin)
    if sistema_id:
        query = query.filter(models.Atencion.sistema_id == sistema_id)
    if empresa_id:
        query = query.filter(models.Atencion.empresa_id == empresa_id)
    if obra:
        query = query.join(models.Trabajador, models.Atencion.trabajador_id == models.Trabajador.id) \
            .filter(models.Trabajador.obra == obra)

    resultados = query.group_by(models.SistemaAtencion.id).order_by(func.count(models.Atencion.id).desc()).all()
    total_general = sum([r.total for r in resultados])

    return {
        "total_general": total_general,
        "sistemas": [{"name": str(r.nombre), "value": int(r.total)} for r in resultados]
    }

# ├óÔÇØÔé¼├óÔÇØÔé¼ Detailed Report Data ├óÔÇØÔé¼├óÔÇØÔé¼
@app.get("/dashboard/report/{report_type}")
def get_report_detail(report_type: str, fecha_inicio: str = None, fecha_fin: str = None, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    def apply_date_filter(query):
        if fecha_inicio:
            query = query.filter(func.date(models.Atencion.fecha) >= fecha_inicio)
        if fecha_fin:
            query = query.filter(func.date(models.Atencion.fecha) <= fecha_fin)
        return query

    if report_type == "enfermedades":
        q = db.query(models.Atencion).filter(
            models.Atencion.is_deleted == False, models.Atencion.diagnostico != None, models.Atencion.diagnostico != ''
        )
        q = apply_date_filter(q)
        atenciones = q.all()

        # Group by diagnostico
        from collections import defaultdict
        grouped = defaultdict(list)
        for a in atenciones:
            trab = a.trabajador
            emp = a.empresa
            grouped[a.diagnostico].append({
                "fecha": a.fecha.strftime("%d/%m/%Y") if a.fecha else "",
                "paciente": f"{trab.nombre} {trab.apellidos}" if trab else "├óÔé¼ÔÇØ",
                "dni": trab.dni if trab else "├óÔé¼ÔÇØ",
                "empresa": emp.nombre if emp else "├óÔé¼ÔÇØ",
                "area": trab.area or "├óÔé¼ÔÇØ" if trab else "├óÔé¼ÔÇØ",
            })

        result = []
        for diag, items in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
            result.append({"name": diag, "total": len(items), "details": items})
        return result[:10]

    elif report_type == "pacientes":
        q = db.query(models.Atencion).filter(models.Atencion.is_deleted == False)
        q = apply_date_filter(q)
        atenciones = q.all()

        from collections import defaultdict
        grouped = defaultdict(list)
        for a in atenciones:
            trab = a.trabajador
            emp = a.empresa
            if not trab:
                continue
            key = trab.id
            grouped[key].append({
                "fecha": a.fecha.strftime("%d/%m/%Y") if a.fecha else "",
                "diagnostico": a.diagnostico or "├óÔé¼ÔÇØ",
                "empresa": emp.nombre if emp else "├óÔé¼ÔÇØ",
                "destino": a.destino or "├óÔé¼ÔÇØ",
                "_nombre": f"{trab.nombre} {trab.apellidos}",
                "_dni": trab.dni,
                "_cargo": trab.cargo or "├óÔé¼ÔÇØ",
                "_area": trab.area or "├óÔé¼ÔÇØ",
            })

        result = []
        for tid, items in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
            first = items[0]
            result.append({
                "name": first["_nombre"],
                "dni": first["_dni"],
                "cargo": first["_cargo"],
                "area": first["_area"],
                "total": len(items),
                "details": [{"fecha": i["fecha"], "diagnostico": i["diagnostico"], "empresa": i["empresa"], "destino": i["destino"]} for i in items]
            })
        return result[:10]

    elif report_type == "empresas":
        q = db.query(models.Atencion).filter(models.Atencion.is_deleted == False, models.Atencion.empresa_id != None)
        q = apply_date_filter(q)
        atenciones = q.all()

        from collections import defaultdict
        grouped = defaultdict(list)
        for a in atenciones:
            emp = a.empresa
            trab = a.trabajador
            if not emp:
                continue
            grouped[emp.id].append({
                "fecha": a.fecha.strftime("%d/%m/%Y") if a.fecha else "",
                "paciente": f"{trab.nombre} {trab.apellidos}" if trab else "├óÔé¼ÔÇØ",
                "diagnostico": a.diagnostico or "├óÔé¼ÔÇØ",
                "destino": a.destino or "├óÔé¼ÔÇØ",
                "_empresa": emp.nombre,
                "_ruc": emp.ruc,
            })

        result = []
        for eid, items in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
            first = items[0]
            result.append({
                "name": first["_empresa"],
                "ruc": first["_ruc"],
                "total": len(items),
                "details": [{"fecha": i["fecha"], "paciente": i["paciente"], "diagnostico": i["diagnostico"], "destino": i["destino"]} for i in items]
            })
        return result[:10]

    elif report_type == "medicamentos":
        q = db.query(
            models.Medicamento.nombre,
            models.Medicamento.presentacion,
            models.Medicamento.costo_unitario,
            models.Medicamento.stock_actual,
            func.sum(models.AtencionMedicamento.cantidad).label('total')
        ).join(models.AtencionMedicamento, models.Medicamento.id == models.AtencionMedicamento.medicamento_id) \
         .join(models.Atencion, models.Atencion.id == models.AtencionMedicamento.atencion_id) \
         .filter(models.Atencion.is_deleted == False)
        q = apply_date_filter(q)
        rows = q.group_by(models.Medicamento.id).order_by(func.sum(models.AtencionMedicamento.cantidad).desc()).limit(10).all()

        result = []
        for r in rows:
            result.append({
                "name": str(r.nombre),
                "presentacion": str(r.presentacion or "├óÔé¼ÔÇØ"),
                "costo_unitario": float(r.costo_unitario or 0),
                "stock_actual": int(r.stock_actual or 0),
                "total": int(r.total or 0),
                "costo_total": round(float(r.costo_unitario or 0) * int(r.total or 0), 2)
            })
        return result

    elif report_type == "costos":
        q = db.query(models.Atencion).filter(models.Atencion.is_deleted == False, models.Atencion.empresa_id != None)
        q = apply_date_filter(q)
        atenciones = q.all()

        from collections import defaultdict
        empresas_data = defaultdict(lambda: {"nombre": "", "ruc": "", "meds": defaultdict(lambda: {"nombre": "", "presentacion": "", "cantidad": 0, "costo_unitario": 0.0})})

        for a in atenciones:
            emp = a.empresa
            if not emp:
                continue
            ed = empresas_data[emp.id]
            ed["nombre"] = emp.nombre
            ed["ruc"] = emp.ruc or "├óÔé¼ÔÇØ"
            for am in a.medicamentos:
                med = am.medicamento
                if med:
                    md = ed["meds"][med.id]
                    md["nombre"] = med.nombre
                    md["presentacion"] = med.presentacion or ""
                    md["cantidad"] += am.cantidad
                    md["costo_unitario"] = float(med.costo_unitario or 0)

        result = []
        for eid, ed in empresas_data.items():
            details = []
            total_cost = 0
            for mid, md in ed["meds"].items():
                subtotal = md["cantidad"] * md["costo_unitario"]
                total_cost += subtotal
                details.append({
                    "medicamento": md["nombre"],
                    "presentacion": md["presentacion"],
                    "cantidad": md["cantidad"],
                    "costo_unitario": md["costo_unitario"],
                    "subtotal": round(subtotal, 2)
                })
            result.append({
                "name": ed["nombre"],
                "ruc": ed["ruc"],
                "total": round(total_cost, 2),
                "details": sorted(details, key=lambda x: x["subtotal"], reverse=True)
            })

        result.sort(key=lambda x: x["total"], reverse=True)
        return result[:10]

    return []

@app.get("/reportes/consumo-medicamentos")
def get_reporte_consumo_medicamentos(
    fecha_inicio: str = None,
    fecha_fin: str = None,
    empresa_id: Optional[str] = None,
    obra: str = None,
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)
):
    query = db.query(models.AtencionMedicamento, models.Atencion, models.Medicamento) \
        .join(models.Atencion, models.Atencion.id == models.AtencionMedicamento.atencion_id) \
        .join(models.Medicamento, models.Medicamento.id == models.AtencionMedicamento.medicamento_id) \
        .filter(models.Atencion.is_deleted == False)

    if fecha_inicio:
        query = query.filter(func.date(models.Atencion.fecha) >= fecha_inicio)
    if fecha_fin:
        query = query.filter(func.date(models.Atencion.fecha) <= fecha_fin)
    if empresa_id:
        query = query.filter(models.Atencion.empresa_id == empresa_id)
    if obra:
        query = query.join(models.Trabajador, models.Atencion.trabajador_id == models.Trabajador.id) \
            .filter(models.Trabajador.obra == obra)

    resultados = query.all()

    from collections import defaultdict
    medicamentos_dict = {}
    fechas_set = set()

    for am, atencion, med in resultados:
        if not atencion.fecha: continue
        fecha_str = atencion.fecha.strftime("%Y-%m-%d")
        fechas_set.add(fecha_str)

        med = am.medicamento
        if med.id not in medicamentos_dict:
            medicamentos_dict[med.id] = {
                "id": med.id,
                "codigo": med.codigo or "",
                "nombre": med.nombre or "",
                "presentacion": med.presentacion or "",
                "precio_und": float(med.costo_unitario or 0),
                "consumos": defaultdict(int),
                "sub_total_cantidad": 0,
                "total_soles": 0.0
            }

        medicamentos_dict[med.id]["consumos"][fecha_str] += am.cantidad
        medicamentos_dict[med.id]["sub_total_cantidad"] += am.cantidad

    lista_medicamentos = []
    total_general = 0.0

    for med_id, m in medicamentos_dict.items():
        m["total_soles"] = round(m["sub_total_cantidad"] * m["precio_und"], 2)
        total_general += m["total_soles"]
        m["consumos"] = dict(m["consumos"])
        lista_medicamentos.append(m)

    total_general = round(total_general, 2)
    sub_total = round(total_general / 1.18, 2)
    igv = round(total_general - sub_total, 2)

    rango_fechas = sorted(list(fechas_set))

    return {
        "rango_fechas": rango_fechas,
        "medicamentos": lista_medicamentos,
        "totales": {
            "sub_total": sub_total,
            "igv": igv,
            "total": total_general
        }
    }



# --- Administracion de cuentas (la usa el panel del ERP) ---------------------
#
# Hasta ahora los usuarios de MEDGLOBAL se creaban con scripts sueltos en el
# servidor (crear_admin.py, cambiar_password.py) y no habia forma de verlos ni
# bloquearlos a distancia. Estos endpoints existen para que el panel de
# plataforma pueda hacerlo, y todos exigen rol ADMIN.
#
# Bloquear surte efecto de inmediato: authenticate_user rechaza a quien no
# este ACTIVO y get_current_user lo revalida en cada peticion, asi que ademas
# corta las sesiones que ya estuvieran abiertas.

def _registrar_evento(db: Session, request: Request, actor, accion: str,
                      objetivo: str = "", objetivo_id: str = "", detalle: str = ""):
    db.add(models.EventoAdmin(
        actor=getattr(actor, "username", None) or "sistema",
        accion=accion,
        objetivo=objetivo,
        objetivo_id=objetivo_id,
        detalle=detalle,
        ip=(request.client.host if request and request.client else ""),
    ))


@app.get("/admin/usuarios", response_model=List[schemas.Usuario])
def admin_listar_usuarios(
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(auth.require_admin),
):
    return db.query(models.Usuario).order_by(models.Usuario.username).all()


@app.post("/admin/usuarios", response_model=schemas.Usuario, status_code=201)
def admin_crear_usuario(
    datos: schemas.UsuarioAdminCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: models.Usuario = Depends(auth.require_admin),
):
    if db.query(models.Usuario).filter(models.Usuario.username == datos.username).first():
        raise HTTPException(status_code=400, detail="Ese nombre de usuario ya existe.")
    if len(datos.password or "") < 8:
        raise HTTPException(status_code=400, detail="La contrase├â┬▒a debe tener al menos 8 caracteres.")

    usuario = models.Usuario(
        username=datos.username,
        nombre=datos.nombre,
        rol=(datos.rol or "ESTANDAR").upper(),
        estado=(datos.estado or "ACTIVO").upper(),
        password_hash=auth.hash_password(datos.password),
    )
    db.add(usuario)
    _registrar_evento(db, request, actor, "crear_usuario",
                      objetivo=usuario.username, objetivo_id=usuario.id,
                      detalle=f"rol={usuario.rol} estado={usuario.estado}")
    db.commit()
    db.refresh(usuario)
    return usuario


@app.patch("/admin/usuarios/{usuario_id}", response_model=schemas.Usuario)
def admin_editar_usuario(
    usuario_id: str,
    datos: schemas.UsuarioAdminUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: models.Usuario = Depends(auth.require_admin),
):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    # Candado contra dejarse fuera: un administrador no puede bloquearse ni
    # quitarse el rol a si mismo. Si es el ultimo ADMIN activo, ademas nadie
    # podria volver a entrar a administrar.
    if usuario.id == actor.id:
        if datos.estado and datos.estado.upper() != "ACTIVO":
            raise HTTPException(status_code=400, detail="No puede bloquear su propia cuenta.")
        if datos.rol and datos.rol.upper() != "ADMIN":
            raise HTTPException(status_code=400, detail="No puede quitarse el rol de administrador.")

    cambios = []
    if datos.nombre is not None and datos.nombre != usuario.nombre:
        usuario.nombre = datos.nombre
        cambios.append("nombre")
    if datos.rol is not None and datos.rol.upper() != usuario.rol:
        usuario.rol = datos.rol.upper()
        cambios.append(f"rol={usuario.rol}")
    if datos.estado is not None and datos.estado.upper() != usuario.estado:
        usuario.estado = datos.estado.upper()
        cambios.append(f"estado={usuario.estado}")
    # Vacio o ausente = no tocar la contrasena.
    if datos.password:
        if len(datos.password) < 8:
            raise HTTPException(status_code=400, detail="La contrase├â┬▒a debe tener al menos 8 caracteres.")
        usuario.password_hash = auth.hash_password(datos.password)
        cambios.append("contrase├â┬▒a")

    if not cambios:
        return usuario

    # Si se queda sin ningun ADMIN activo, nadie podria volver a administrar.
    admins_activos = db.query(models.Usuario).filter(
        models.Usuario.rol == "ADMIN", models.Usuario.estado == "ACTIVO"
    ).count()
    if admins_activos == 0:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="No puede dejar el sistema sin ning├â┬║n administrador activo.",
        )

    _registrar_evento(db, request, actor, "editar_usuario",
                      objetivo=usuario.username, objetivo_id=usuario.id,
                      detalle=", ".join(cambios))
    db.commit()
    db.refresh(usuario)
    return usuario


@app.get("/admin/actividad", response_model=List[schemas.EventoAdmin])
def admin_actividad(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(auth.require_admin),
):
    return (
        db.query(models.EventoAdmin)
        .order_by(models.EventoAdmin.creado_en.desc())
        .limit(min(max(limit, 1), 500))
        .all()
    )

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# index.html NUNCA se cachea; los assets, para siempre.
#
# Vite le pone un hash al nombre de cada asset (index-DC3vAq3r.js), asi que un
# archivo con ese nombre no cambia jamas y se puede cachear indefinidamente.
# index.html es lo contrario: es el unico que dice cual es el hash vigente, y
# si el navegador se lo queda cacheado sigue pidiendo el bundle anterior.
#
# Eso convertia cada actualizacion del .exe en un problema por PC: la
# aplicacion quedaba actualizada en disco pero el navegador seguia mostrando
# la version vieja hasta que alguien hiciera Ctrl+Shift+R, sin ninguna pista
# de que eso hacia falta.
_CACHE_INDEX = "no-store, no-cache, must-revalidate"
_CACHE_ASSETS = "public, max-age=31536000, immutable"


class ArchivosEstaticos(StaticFiles):
    def file_response(self, full_path, stat_result, scope, status_code=200):
        respuesta = super().file_response(full_path, stat_result, scope, status_code)
        es_index = str(full_path).replace("\\", "/").endswith("/index.html")
        respuesta.headers["Cache-Control"] = _CACHE_INDEX if es_index else _CACHE_ASSETS
        return respuesta


os.makedirs('static', exist_ok=True)
app.mount('/', ArchivosEstaticos(directory='static', html=True), name='static')


# Prefijos que son API pura y nunca rutas del navegador. No se puede
# generalizar a ├é┬½todo lo que sea una ruta declarada├é┬╗: /atenciones, /empresas y
# casi todas las demas son a la vez endpoint del API y pantalla del frontend,
# asi que ahi el 404 tiene que seguir cayendo en index.html.
#
# (Queda pendiente, y es anterior a esto: un 404 de esos endpoints compartidos
# devuelve la pagina web en vez de un JSON. No se toca aqui para no cambiar un
# comportamiento que las pruebas existentes dan por bueno.)
_PREFIJOS_SOLO_API = ("/api", "/admin/")


@app.exception_handler(404)
async def custom_404_handler(request, exc):
    # Las rutas del API que no existen devuelven un 404 normal; el resto cae en
    # index.html porque el ruteo del frontend es del lado del navegador.
    #
    # Antes esta rama hacia `return exc`, devolviendo la excepcion misma donde
    # Starlette espera una Response: cualquier /api/... inexistente terminaba
    # en "TypeError: 'HTTPException' object is not callable" en vez de un 404.
    if request.url.path.startswith(_PREFIJOS_SOLO_API):
        return JSONResponse({"detail": getattr(exc, "detail", "Not Found")}, status_code=404)
    return FileResponse('static/index.html', headers={"Cache-Control": _CACHE_INDEX})
