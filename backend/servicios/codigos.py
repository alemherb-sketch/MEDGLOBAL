"""Codigos correlativos legibles (MED-0001, BOT-0007, TRB-0123...).

No se pueden derivar del id: los ids son UUID desde la migracion a
sincronizacion multi-dispositivo.
"""
import re

from sqlalchemy.orm import Session


def siguiente_codigo(db: Session, model, campo: str, prefijo: str, separador: str = "-") -> str:
    """Siguiente codigo tipo PREFIJO-0001 (o PREFIJO0001 si separador='').

    Se leen los codigos existentes y se compara la parte numerica en Python en
    vez de pedirle el maximo a la base: el orden alfabetico daria mal
    ('PREF-9' > 'PREF-10') y hay datos historicos con distinta cantidad de
    ceros a la izquierda.

    No es atomico: dos altas simultaneas pueden calcular el mismo numero. La
    columna es UNIQUE, asi que la segunda choca con IntegrityError en vez de
    duplicar el codigo -- ver `crear_con_codigo_unico`, que reintenta.
    """
    columna = getattr(model, campo)
    patron = re.compile(rf"^{re.escape(prefijo)}{re.escape(separador)}(\d+)$")
    maximo = 0
    like = f"{prefijo}{separador}%" if separador else f"{prefijo}%"
    for (valor,) in db.query(columna).filter(columna.like(like)).all():
        if not valor:
            continue
        encontrado = patron.match(valor)
        if encontrado:
            maximo = max(maximo, int(encontrado.group(1)))
    return f"{prefijo}{separador}{maximo + 1:04d}"
