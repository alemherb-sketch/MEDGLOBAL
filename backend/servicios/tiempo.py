"""Reloj de la aplicacion.

`datetime.utcnow()` esta deprecado desde Python 3.12 y se elimina en una
version futura. Su reemplazo directo, `datetime.now(timezone.utc)`, devuelve
un datetime CON tzinfo, y eso no es intercambiable: toda la base guarda
datetimes ingenuos (sin zona) y el protocolo de sincronizacion los compara
entre si (`existing.server_updated_at > since_dt`). Mezclar ingenuos con
conscientes lanza TypeError en tiempo de ejecucion.

Por eso esta funcion produce lo mismo que producia utcnow() -- UTC sin
tzinfo -- pero por la via que no esta deprecada.
"""
from datetime import datetime, timezone


def ahora_utc() -> datetime:
    """Hora UTC actual, sin tzinfo (igual que el viejo datetime.utcnow())."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
