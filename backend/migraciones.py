"""Migraciones de arranque: agrega columnas que faltan en bases ya creadas
y mantiene catalogos alineados con el negocio.

El proyecto no usa Alembic. Cuando se agrega una columna a models.py,
create_all() no la agrega a las tablas que ya existen, asi que las
instalaciones en curso (cada .exe tiene su propio SQLite) quedarian con la
tabla vieja y cualquier consulta fallaria.

Cada ALTER va en su propia transaccion y se ignora el error: si la columna ya
esta, no hay nada que hacer. Es idempotente a proposito -- corre en cada
arranque.
"""
import logging
import re

from sqlalchemy import func, text
from sqlalchemy.orm import Session

import models
from servicios.tiempo import ahora_utc

logger = logging.getLogger(__name__)

# Nombre que se sembró por error en sistemas/clasificaciones. Ya no es un
# item de esos catalogos: las obras viven en su propia tabla.
NOMBRE_OBRA_ERRONEO = "OBRA"

# tabla -> columnas a garantizar (definicion SQL tal cual va en el ALTER).
COLUMNAS_POR_TABLA = {
    "trabajadores": [
        "codigo_trabajador VARCHAR(50)", "cargo VARCHAR(100)", "fecha_ingreso VARCHAR(20)",
        "fecha_cese VARCHAR(20)", "estado_trabajador VARCHAR(50)", "subdivision_sede VARCHAR(100)",
        "centro_costo VARCHAR(100)", "tipo_calculo_nomina VARCHAR(100)", "area VARCHAR(150)",
        "area_personal VARCHAR(100)", "grupo_personal VARCHAR(100)", "nivel_org_1 VARCHAR(100)",
        "nivel_org_2 VARCHAR(100)", "nivel_org_3 VARCHAR(100)", "nivel_org_4 VARCHAR(100)",
        "nivel_org_5 VARCHAR(100)", "fecha_nacimiento VARCHAR(20)", "genero VARCHAR(20)",
        "jefe_inmediato VARCHAR(150)", "telefono VARCHAR(50)", "correo_electronico VARCHAR(150)",
        "empresa_id INTEGER", "obra VARCHAR(150)",
    ],
    "atenciones": [
        "edad VARCHAR(10)", "residencia VARCHAR(200)", "empresa_id INTEGER", "cargo VARCHAR(100)",
        "funciones_biologicas TEXT", "signos_vitales TEXT", "examen_fisico TEXT",
        "examenes_auxiliares TEXT", "codigo_diagnostico VARCHAR(100)", "diagnostico_1 VARCHAR(255)",
        "diagnostico_2 VARCHAR(255)", "diagnostico_3 VARCHAR(255)", "sede_atencion VARCHAR(100)",
    ],
    "medicamentos": [
        "costo_unitario FLOAT DEFAULT 0.0", "tipo VARCHAR(20) DEFAULT 'MEDICAMENTO'",
        "lote VARCHAR(50)", "fecha_vencimiento VARCHAR(20)",
    ],
    "kardex": ["lote VARCHAR(50)", "fecha_vencimiento VARCHAR(20)", "observacion TEXT"],
    "botiquines": [
        "codigo VARCHAR(50)", "fecha_creacion TIMESTAMP", "tipo_botiquin_id VARCHAR(36)",
        "mapa_url VARCHAR(500)", "vehiculo VARCHAR(200)", "marca VARCHAR(100)",
        "modelo VARCHAR(100)", "serie VARCHAR(100)", "placa VARCHAR(50)",
    ],
    "botiquin_inspeccion_insumos": [
        "estado VARCHAR(50) DEFAULT 'BUENO'", "reposicion VARCHAR(10) DEFAULT 'NO'",
    ],
    "botiquin_inspecciones": ["imagenes TEXT", "codigo VARCHAR(20)"],
}

# Cambios de tipo que solo entiende PostgreSQL; en SQLite fallan y se ignoran.
AMPLIACIONES_DE_TIPO = [
    "ALTER TABLE botiquines ALTER COLUMN area TYPE VARCHAR(150)",
]


def _ejecutar_ignorando_errores(conn, sentencia: str) -> None:
    """Cada sentencia en su propia transaccion: si una falla porque el cambio
    ya estaba aplicado, las siguientes tienen que poder seguir."""
    try:
        with conn.begin():
            conn.execute(text(sentencia))
    except Exception:
        logger.debug("Migracion omitida (probablemente ya aplicada): %s", sentencia)


def _asegurar_nombre(sesion, modelo, nombre: str) -> None:
    """Si ya hay una fila con ese nombre (cualquier capitalizacion), no
    duplica. Si solo esta borrada en logico, la reactiva para que vuelva a
    los desplegables. Prefiere la vigente cuando hay varias."""
    existente = (
        sesion.query(modelo)
        .filter(func.lower(modelo.nombre) == nombre.lower())
        .order_by(modelo.is_deleted.asc())
        .first()
    )
    if existente is None:
        sesion.add(modelo(nombre=nombre))
        return
    if existente.is_deleted:
        existente.is_deleted = False
        ahora = ahora_utc()
        existente.updated_at = ahora
        existente.server_updated_at = ahora


def _soft_delete_por_nombre(sesion, modelo, nombre: str) -> None:
    """Baja logica de filas vigentes cuyo nombre coincide (sin importar mayusculas)."""
    filas = (
        sesion.query(modelo)
        .filter(func.lower(modelo.nombre) == nombre.lower())
        .filter(modelo.is_deleted == False)  # noqa: E712
        .all()
    )
    ahora = ahora_utc()
    for fila in filas:
        fila.is_deleted = True
        fila.updated_at = ahora
        fila.server_updated_at = ahora


def limpiar_obra_de_catalogos_clinicos(engine) -> None:
    """Quita el item OBRA de sistemas y clasificaciones si se sembró ahi.

    No toca trabajadores.obra ni la tabla obras. Es idempotente: si ya
    esta borrado en logico, no hace nada.
    """
    sesion = Session(bind=engine)
    try:
        _soft_delete_por_nombre(sesion, models.SistemaAtencion, NOMBRE_OBRA_ERRONEO)
        _soft_delete_por_nombre(sesion, models.ClasificacionAtencion, NOMBRE_OBRA_ERRONEO)
        sesion.commit()
    except Exception:
        sesion.rollback()
        logger.debug("Limpieza de OBRA en catalogos clinicos omitida", exc_info=True)
    finally:
        sesion.close()


def sembrar_obras_desde_planilla(engine) -> None:
    """Copia al catalogo los nombres de obra ya usados en planilla, sin duplicar.

    Asi los desplegables no quedan vacios en instalaciones que ya tenian
    obras cargadas como texto libre. No inventa el item OBRA.
    """
    sesion = Session(bind=engine)
    try:
        nombres = (
            sesion.query(models.Trabajador.obra)
            .filter(
                models.Trabajador.is_deleted == False,  # noqa: E712
                models.Trabajador.obra.isnot(None),
                models.Trabajador.obra != "",
            )
            .distinct()
            .all()
        )
        for (nombre,) in nombres:
            nombre = (nombre or "").strip()
            if not nombre:
                continue
            _asegurar_nombre(sesion, models.Obra, nombre)
        sesion.commit()
    except Exception:
        sesion.rollback()
        logger.debug("Semilla de obras desde planilla omitida", exc_info=True)
    finally:
        sesion.close()


def _numero_codigo_ins(codigo) -> int:
    encontrado = re.match(r"^INS(\d+)$", (codigo or "").strip())
    return int(encontrado.group(1)) if encontrado else 0


def sembrar_codigos_inspeccion(engine) -> None:
    """Asigna INS0001, INS0002... a inspecciones que todavia no tienen codigo.

    Orden: las mas antiguas primero. En PostgreSQL un advisory lock evita que
    dos workers de uvicorn numeren a la vez (si no, el segundo pisa los
    correlativos y queda INS0001 + INS0144...). Si el maximo ya asignado es
    mayor que la cantidad de filas, se reescriben todos: es esa corrida
    doble, no un hueco legitimo.

    No pisa un codigo valido cuando la secuencia esta sana.
    """
    from servicios.codigos import siguiente_codigo

    sesion = Session(bind=engine)
    try:
        if engine.dialect.name == "postgresql":
            sesion.execute(text("SELECT pg_advisory_xact_lock(87233401)"))

        sesion.query(models.BotiquinInspeccion).filter(
            models.BotiquinInspeccion.codigo == ""
        ).update({models.BotiquinInspeccion.codigo: None}, synchronize_session=False)
        sesion.flush()

        filas = (
            sesion.query(models.BotiquinInspeccion)
            .order_by(
                models.BotiquinInspeccion.created_at.asc(),
                models.BotiquinInspeccion.fecha.asc(),
                models.BotiquinInspeccion.id.asc(),
            )
            .all()
        )
        if not filas:
            sesion.commit()
            return

        n = len(filas)
        maximo = max(_numero_codigo_ins(fila.codigo) for fila in filas)
        if maximo > n:
            logger.warning(
                "Correlativos de inspeccion inconsistentes (max INS%04d con %s filas); se reescriben",
                maximo, n,
            )
            for fila in filas:
                fila.codigo = None
            sesion.flush()

        for fila in filas:
            if fila.codigo:
                continue
            fila.codigo = siguiente_codigo(
                sesion, models.BotiquinInspeccion, "codigo", "INS", separador=""
            )
            sesion.flush()
        sesion.commit()
    except Exception:
        sesion.rollback()
        logger.exception("No se pudieron sembrar los codigos de inspeccion")
    finally:
        sesion.close()


def aplicar(engine) -> None:
    with engine.connect() as conn:
        for tabla, columnas in COLUMNAS_POR_TABLA.items():
            for columna in columnas:
                _ejecutar_ignorando_errores(conn, f"ALTER TABLE {tabla} ADD COLUMN {columna}")
        for sentencia in AMPLIACIONES_DE_TIPO:
            _ejecutar_ignorando_errores(conn, sentencia)
        _ejecutar_ignorando_errores(
            conn,
            "UPDATE botiquin_inspecciones SET codigo = NULL WHERE codigo = ''",
        )
        # El indice unico va ANTES de sembrar: dos workers no pueden grabar el
        # mismo INS0001. Varios NULL siguen permitidos.
        _ejecutar_ignorando_errores(
            conn,
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_botiquin_inspecciones_codigo "
            "ON botiquin_inspecciones (codigo)",
        )
    try:
        models.Obra.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        logger.debug("Creacion de tabla obras omitida", exc_info=True)
    limpiar_obra_de_catalogos_clinicos(engine)
    sembrar_obras_desde_planilla(engine)
    sembrar_codigos_inspeccion(engine)
