"""Migraciones de arranque: agrega columnas que faltan en bases ya creadas.

El proyecto no usa Alembic. Cuando se agrega una columna a models.py,
create_all() no la agrega a las tablas que ya existen, asi que las
instalaciones en curso (cada .exe tiene su propio SQLite) quedarian con la
tabla vieja y cualquier consulta fallaria.

Cada ALTER va en su propia transaccion y se ignora el error: si la columna ya
esta, no hay nada que hacer. Es idempotente a proposito -- corre en cada
arranque.
"""
import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)

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
        "diagnostico_2 VARCHAR(255)", "diagnostico_3 VARCHAR(255)",
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
    "botiquin_inspecciones": ["imagenes TEXT"],
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


def aplicar(engine) -> None:
    with engine.connect() as conn:
        for tabla, columnas in COLUMNAS_POR_TABLA.items():
            for columna in columnas:
                _ejecutar_ignorando_errores(conn, f"ALTER TABLE {tabla} ADD COLUMN {columna}")
        for sentencia in AMPLIACIONES_DE_TIPO:
            _ejecutar_ignorando_errores(conn, sentencia)
