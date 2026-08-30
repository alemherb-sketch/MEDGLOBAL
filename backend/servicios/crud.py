"""Piezas comunes de los CRUD.

Casi todas las entidades del sistema comparten la misma forma: listar las no
borradas, crear, editar campo por campo y borrar en logico. Estas funciones
son ese esqueleto; cada endpoint agrega solo lo suyo (validaciones, codigos
correlativos, efectos sobre el stock).
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session


def listar_vigentes(db: Session, model, orden=None):
    """Las filas no borradas. El borrado del sistema es logico (is_deleted):
    un registro medico no se elimina, y ademas la sincronizacion necesita la
    marca para propagar la baja a los demas dispositivos."""
    consulta = db.query(model).filter(model.is_deleted == False)  # noqa: E712
    return consulta.order_by(orden).all() if orden is not None else consulta.all()


def obtener_o_404(db: Session, model, id_: str, mensaje: str, solo_vigentes: bool = False):
    consulta = db.query(model).filter(model.id == id_)
    if solo_vigentes:
        consulta = consulta.filter(model.is_deleted == False)  # noqa: E712
    fila = consulta.first()
    if not fila:
        raise HTTPException(status_code=404, detail=mensaje)
    return fila


def aplicar_campos(fila, datos: dict) -> None:
    for campo, valor in datos.items():
        setattr(fila, campo, valor)


def borrado_logico(db: Session, model, id_: str, mensaje: str, respuesta: str = "Eliminado"):
    fila = obtener_o_404(db, model, id_, mensaje)
    fila.is_deleted = True
    db.commit()
    return {"detail": respuesta}


def rechazar_duplicado(db: Session, model, columna, valor, mensaje: str, excluir_id: str = None):
    """Devuelve 400 en vez de dejar que choque la restriccion UNIQUE.

    Sin esto el conflicto sale como IntegrityError -> 500, con la sesion de
    SQLAlchemy en estado invalido y un mensaje de base de datos en pantalla."""
    if valor in (None, ""):
        return
    consulta = db.query(model).filter(columna == valor)
    if excluir_id is not None:
        consulta = consulta.filter(model.id != excluir_id)
    if consulta.first():
        raise HTTPException(status_code=400, detail=mensaje)
