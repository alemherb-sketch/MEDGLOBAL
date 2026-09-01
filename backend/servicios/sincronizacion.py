"""Protocolo de sincronizacion: que tablas viajan y como se copia una fila.

Vive aparte de los endpoints y del cliente a proposito. Antes estas
definiciones estaban dentro de main.py y sync_client.py hacia
`from main import SYNCABLE_MODELS, ...`, mientras main.py importaba a
sync_client: un ciclo que solo funcionaba por el orden exacto de las lineas.
Peor todavia, main.py atrapaba ese import con `except ImportError`, asi que si
el ciclo se rompia la sincronizacion desaparecia del ejecutable sin ningun
error visible. Ahora los dos dependen de este modulo, que no depende de
ninguno.
"""
from datetime import datetime

import models

# Tablas que participan del protocolo generico.
#
# atencion_medicamentos NO esta: viaja embebida dentro de cada atencion, igual
# que en la API normal. usuarios SI participa, para que el mismo login sirva en
# la web y en el instalable; usa el mismo mecanismo de conflicto que cualquier
# otra tabla, sin trato especial para password_hash -- un dispositivo con
# credenciales de sync validas ya puede escribir cualquier otra tabla.
SYNCABLE_MODELS = {
    "usuarios": models.Usuario,
    "empresas": models.Empresa,
    "sistemas": models.SistemaAtencion,
    "clasificaciones": models.ClasificacionAtencion,
    "obras": models.Obra,
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

# El id nunca se sobreescribe, venga de donde venga.
COLUMNAS_NUNCA_COPIADAS = {"id"}

# folio, stock_actual y server_updated_at los calcula el servidor. Un
# dispositivo que empuja cambios (push) no puede pisarlos aunque los mande;
# cuando el cliente APLICA lo que bajo del servidor (pull) si se queda con
# ellos tal cual, porque ahi el servidor es la verdad -- de eso se encarga
# `trusted_source=True`.
#
# server_updated_at existe SEPARADO de updated_at a proposito: updated_at es la
# fecha de edicion del usuario (decide quien gana un conflicto) y
# server_updated_at es cuando el servidor escribio la fila (decide que entra en
# el filtro "cambios desde since"). Si fueran la misma columna, aplicar la
# version ganadora de un conflicto con su fecha original dejaria la fila
# "vieja" para el filtro aunque el servidor la acabe de tocar, y un tercer
# dispositivo se la perderia. Se excluye del copiado para que dispare el
# onupdate de la columna (hora real del servidor).
COLUMNAS_DEL_SERVIDOR = {"folio", "server_updated_at"}
COLUMNAS_DEL_SERVIDOR_POR_TABLA = {
    "medicamentos": {"stock_actual"},
}

COLUMNAS_DE_FECHA = {
    "fecha", "fecha_hora", "fecha_creacion", "created_at", "updated_at",
    "server_updated_at", "creado_en",
}


def parsear_fecha(valor):
    if valor is None or isinstance(valor, datetime):
        return valor
    return datetime.fromisoformat(valor)


def fila_a_dict(fila) -> dict:
    """Serializa una fila completa (todas sus columnas) para mandarla por red."""
    datos = {}
    for columna in fila.__table__.columns:
        valor = getattr(fila, columna.name)
        datos[columna.name] = valor.isoformat() if isinstance(valor, datetime) else valor
    return datos


def aplicar_campos(fila, datos: dict, tabla: str = None, trusted_source: bool = False) -> None:
    """Copia los campos de `datos` sobre `fila`.

    Se marca cada columna tocada con flag_modified porque SQLAlchemy solo
    incluye una columna en el UPDATE si la detecta 'sucia', y esa deteccion es
    por igualdad de valor. Cuando un dispositivo recibe de vuelta su propio
    cambio recien empujado, el valor entrante es identico al que ya tiene: la
    columna queda fuera del SET y entonces el onupdate=utcnow() SI se dispara,
    pisando el valor con la hora actual. flag_modified fuerza que la columna
    entre al UPDATE tal cual se seteo.
    """
    from sqlalchemy.orm.attributes import flag_modified

    omitir = set(COLUMNAS_NUNCA_COPIADAS)
    if not trusted_source:
        omitir |= COLUMNAS_DEL_SERVIDOR
        omitir |= COLUMNAS_DEL_SERVIDOR_POR_TABLA.get(tabla, set())

    for columna in fila.__table__.columns:
        if columna.name in omitir or columna.name not in datos:
            continue
        valor = datos[columna.name]
        if columna.name in COLUMNAS_DE_FECHA:
            valor = parsear_fecha(valor)
        setattr(fila, columna.name, valor)
        flag_modified(fila, columna.name)
