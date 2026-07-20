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

# Aplicar migraciones automáticas para SQLite/PostgreSQL si las columnas no existen
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

app = FastAPI(title="MEDGLOBAL API")

# Configure CORS
# ALLOWED_ORIGINS es una lista separada por comas (ej. "https://medglobal.erpgest.com.pe").
# Por defecto "*" para no romper el desarrollo local ni el .exe de escritorio.
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allowed_origins == "*" else [o.strip() for o in _allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
import pandas as pd
import io


def _next_prefixed_code(db: Session, model, field_name: str, prefix: str) -> str:
    """Siguiente código secuencial tipo PREFIX-0001, buscando el máximo existente
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
# diferencia del diseño original de la Fase 2): el mismo login debe
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
}

# id nunca se sobreescribe via setattr, venga de donde venga.
_SYNC_ALWAYS_SKIP = {"id"}
# folio, stock_actual y server_updated_at son calculados por el servidor.
# Un dispositivo empujando cambios (push) nunca puede pisarlos directo,
# aunque los mande en su payload — por eso se saltan cuando
# trusted_source=False. Pero cuando el cliente de escritorio (Fase 3)
# APLICA lo que bajo del servidor (pull), sí necesita quedarse con esos
# valores tal cual, porque son la verdad autoritativa — por eso ahi se
# llama con trusted_source=True.
#
# server_updated_at existe SEPARADO de updated_at a proposito (ver el
# comentario junto a la columna en models.py): updated_at sigue siendo la
# fecha de edicion del usuario, tal cual la manda el cliente, porque de eso
# depende decidir quien gana un conflicto. server_updated_at es cuando el
# SERVIDOR escribio la fila, y es lo que se usa para el filtro "que cambio
# desde since" — si se usara updated_at para ambas cosas, aplicar la
# version ganadora de un conflicto con la fecha de edicion original
# (posiblemente antigua) dejaria la fila "vieja" para el filtro de sync
# aunque el servidor la acabe de tocar, y un tercer dispositivo se la
# perderia. Se excluye del copiado directo para que dispare el
# onupdate/default de la columna (hora real del servidor).
_SYNC_SERVER_COMPUTED_COLUMNS = {"folio", "server_updated_at"}
_SYNC_SERVER_COMPUTED_COLUMNS_POR_TABLA = {
    "medicamentos": {"stock_actual"},
}
_SYNC_DATETIME_COLUMNS = {"fecha", "fecha_hora", "created_at", "updated_at", "server_updated_at", "creado_en"}


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
    UPDATE si la detecta 'dirty' — y su deteccion de cambios es por
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
    """Igual que create_atencion: asigna folio y descuenta stock/kardex.
    Solo corre para atenciones que no existian en el servidor todavia —
    editar los medicamentos de una atencion ya existente via sync no esta
    soportado, igual que tampoco lo esta en el endpoint normal de edicion."""
    max_folio = db.query(func.max(models.Atencion.folio)).scalar()
    atencion_row.folio = (max_folio or 0) + 1
    for med in medicamentos or []:
        med_id = med.get("medicamento_id")
        cantidad = med.get("cantidad", 1)
        if not med_id:
            continue
        db.add(models.AtencionMedicamento(atencion_id=atencion_row.id, medicamento_id=med_id, cantidad=cantidad))
        db_med = db.query(models.Medicamento).filter(models.Medicamento.id == med_id).first()
        if db_med:
            db_med.stock_actual -= cantidad
            db.add(models.Kardex(
                medicamento_id=db_med.id, tipo_movimiento="SALIDA",
                cantidad=cantidad, saldo=db_med.stock_actual,
            ))


def _procesar_kardex_nuevo(db: Session, kardex_row):
    """El stock y el saldo se recalculan aqui contra el estado actual del
    servidor — nunca se confia en el stock_actual/saldo que traiga el
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


@app.get("/sync/cambios")
def sync_cambios(since: Optional[str] = None, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    """Pull: todo lo que cambio desde 'since' (ISO 8601), incluyendo
    borrados (is_deleted=true actua como tombstone). Sin 'since', devuelve
    todo — es la sincronizacion inicial de un dispositivo nuevo.
    server_time va en la respuesta a proposito: el cliente debe guardar ESE
    valor como su proximo cursor, no su propio reloj — evita que un reloj
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
            detail="Usuario o contraseña incorrectos",
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
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")

    # Check if new code already exists in another record
    if diag.codigo != db_diag.codigo:
        exist = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.codigo == diag.codigo).first()
        if exist:
            raise HTTPException(status_code=400, detail="El código CIE-10 ya existe")

    for key, value in diag.dict().items():
        setattr(db_diag, key, value)
    db.commit()
    db.refresh(db_diag)
    return db_diag

@app.delete("/diagnosticos/{id}")
def delete_diagnostico(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_diag = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.id == id).first()
    if not db_diag:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    db_diag.is_deleted = True
    db.commit()
    return {"detail": "Eliminado"}

@app.post("/diagnosticos/importar/")
async def import_diagnosticos(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido. Usa Excel (.xlsx)")

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
                # Si tiene 2 columnas, plan B clásico
                if len(df.columns) >= 2 and not pd.isna(row.iloc[1]):
                    codigo = celda
                    descripcion = str(row.iloc[1]).strip()
                else:
                    continue

            if codigo and codigo != 'nan' and descripcion and descripcion != 'nan':
                # Evitar duplicados por código
                exist = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.codigo == codigo).first()
                if not exist:
                    new_diag = models.DiagnosticoCie10(codigo=codigo, descripcion=descripcion)
                    db.add(new_diag)
                    count += 1

        db.commit()
        return {"message": f"Se importaron {count} diagnósticos nuevos."}
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
def read_trabajadores(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    return db.query(models.Trabajador).filter(models.Trabajador.is_deleted == False).offset(skip).limit(limit).all()

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
        raise HTTPException(status_code=404, detail="Clasificación no encontrada")
    for key, value in clasificacion.dict().items():
        setattr(db_clas, key, value)
    db.commit()
    db.refresh(db_clas)
    return db_clas

@app.delete("/clasificaciones/{id}")
def delete_clasificacion(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_clas = db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.id == id).first()
    if not db_clas:
        raise HTTPException(status_code=404, detail="Clasificación no encontrada")
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
    db_atencion = models.Atencion(**atencion_data)

    # Folio correlativo humano (Ficha N°), asignado solo por el servidor
    max_folio = db.query(func.max(models.Atencion.folio)).scalar()
    db_atencion.folio = (max_folio or 0) + 1

    db.add(db_atencion)
    db.commit()
    db.refresh(db_atencion)

    # Procesar medicamentos si hay
    if atencion.medicamentos:
        for med_req in atencion.medicamentos:
            # Añadir relación
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
        raise HTTPException(status_code=404, detail="Atención no encontrada")

    atencion_data = atencion.dict(exclude={'medicamentos'})
    for key, value in atencion_data.items():
        setattr(db_atencion, key, value)

    db.commit()
    db.refresh(db_atencion)
    return db_atencion

@app.delete("/atenciones/{id}")
def delete_atencion(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    db_atencion = db.query(models.Atencion).filter(models.Atencion.id == id).first()
    if not db_atencion:
        raise HTTPException(status_code=404, detail="Atención no encontrada")
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
        saldo=db_med.stock_actual
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

    # 1. Enfermedades más frecuentes
    q_enf = db.query(models.Atencion.diagnostico, func.count(models.Atencion.id).label('total')) \
        .filter(models.Atencion.is_deleted == False, models.Atencion.diagnostico != None, models.Atencion.diagnostico != '')
    q_enf = apply_date_filter(q_enf)
    top_enfermedades = q_enf.group_by(models.Atencion.diagnostico) \
        .order_by(func.count(models.Atencion.id).desc()) \
        .limit(5).all()

    enfermedades = [{"name": str(e.diagnostico), "value": int(e.total)} for e in top_enfermedades]

    # 2. Pacientes más atendidos
    q_pac = db.query(models.Trabajador.nombre, models.Trabajador.apellidos, func.count(models.Atencion.id).label('total')) \
        .join(models.Atencion, models.Trabajador.id == models.Atencion.trabajador_id) \
        .filter(models.Atencion.is_deleted == False)
    q_pac = apply_date_filter(q_pac)
    top_pacientes = q_pac.group_by(models.Trabajador.id) \
        .order_by(func.count(models.Atencion.id).desc()) \
        .limit(5).all()

    pacientes = [{"name": f"{p.nombre} {p.apellidos}", "value": int(p.total)} for p in top_pacientes]

    # 3. Empresas más atendidas
    q_emp = db.query(models.Empresa.nombre, func.count(models.Atencion.id).label('total')) \
        .join(models.Atencion, models.Empresa.id == models.Atencion.empresa_id) \
        .filter(models.Atencion.is_deleted == False)
    q_emp = apply_date_filter(q_emp)
    top_empresas = q_emp.group_by(models.Empresa.id) \
        .order_by(func.count(models.Atencion.id).desc()) \
        .limit(5).all()

    empresas = [{"name": str(e.nombre), "value": int(e.total)} for e in top_empresas]

    # 4. Medicamentos más usados
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

    # 7. Atenciones por Día (Últimas Atenciones Gráfico)
    q_dias = db.query(func.date(models.Atencion.fecha).label('dia'), func.count(models.Atencion.id).label('total')) \
        .filter(models.Atencion.is_deleted == False)
    q_dias = apply_date_filter(q_dias)
    dias_query = q_dias.group_by(func.date(models.Atencion.fecha)).order_by(func.date(models.Atencion.fecha).asc()).limit(14).all()
    atenciones_por_dia = [{"name": str(d.dia), "value": int(d.total)} for d in dias_query]

    # 8. Últimas Atenciones Realizadas (Lista)
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

# ── Detailed Report Data ──
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
                "paciente": f"{trab.nombre} {trab.apellidos}" if trab else "—",
                "dni": trab.dni if trab else "—",
                "empresa": emp.nombre if emp else "—",
                "area": trab.area or "—" if trab else "—",
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
                "diagnostico": a.diagnostico or "—",
                "empresa": emp.nombre if emp else "—",
                "destino": a.destino or "—",
                "_nombre": f"{trab.nombre} {trab.apellidos}",
                "_dni": trab.dni,
                "_cargo": trab.cargo or "—",
                "_area": trab.area or "—",
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
                "paciente": f"{trab.nombre} {trab.apellidos}" if trab else "—",
                "diagnostico": a.diagnostico or "—",
                "destino": a.destino or "—",
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
                "presentacion": str(r.presentacion or "—"),
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
            ed["ruc"] = emp.ruc or "—"
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

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
os.makedirs('static', exist_ok=True)
app.mount('/', StaticFiles(directory='static', html=True), name='static')
@app.exception_handler(404)
async def custom_404_handler(request, exc):
    if request.url.path.startswith('/api'): return exc
    return FileResponse('static/index.html')
