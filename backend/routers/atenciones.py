"""Atenciones medicas y citas.

Una atencion puede dispensar medicamentos, y eso mueve inventario. Todo
movimiento de stock pasa por servicios/stock.py: aca no se toca
`stock_actual` directamente ni se arma un Kardex a mano.
"""
from typing import List

from fastapi import APIRouter
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

import models
import schemas
from dependencias import RequiereSesion, SesionDB
from servicios import crud, stock

router = APIRouter(dependencies=[RequiereSesion])

# Claves foraneas opcionales: el formulario manda "" cuando el usuario no
# eligio nada, y "" no es un id valido -> violacion de FK al guardar.
_FK_OPCIONALES = ("empresa_id", "cita_id", "personal_salud_id")


def _cargar_relaciones(consulta):
    """Trae de una vez todo lo que el esquema de respuesta va a leer.

    `schemas.Atencion` anida trabajador (y su empresa), empresa, sistema,
    clasificacion, personal de salud y la receta con cada medicamento. Sin
    esto SQLAlchemy los resuelve de a uno al serializar: listar 1000
    atenciones disparaba varios miles de consultas y era lo que hacia lenta la
    pantalla de Atenciones."""
    return consulta.options(
        joinedload(models.Atencion.trabajador).joinedload(models.Trabajador.empresa),
        joinedload(models.Atencion.empresa),
        joinedload(models.Atencion.sistema),
        joinedload(models.Atencion.clasificacion),
        joinedload(models.Atencion.personal_salud),
        selectinload(models.Atencion.medicamentos).joinedload(models.AtencionMedicamento.medicamento),
    )


def _normalizar(datos: dict) -> dict:
    for campo in _FK_OPCIONALES:
        if datos.get(campo) == "":
            datos[campo] = None
    # Sin fecha: al crear la asigna el default del modelo; al editar se
    # conserva la que ya tenia.
    if not datos.get("fecha"):
        datos.pop("fecha", None)
    # El formulario CIE-10 escribe en diagnostico_1; diagnostico es el campo
    # legado que leen el listado y los reportes.
    principal = (datos.get("diagnostico_1") or datos.get("diagnostico") or "").strip()
    if principal:
        datos["diagnostico"] = principal
        if not (datos.get("diagnostico_1") or "").strip():
            datos["diagnostico_1"] = principal
    return datos


def _siguiente_folio(db) -> int:
    """Numero de ficha correlativo. Lo asigna solo el servidor.

    No es atomico: dos altas simultaneas pueden calcular el mismo numero y la
    segunda choca contra el UNIQUE de la columna en vez de duplicarlo."""
    return (db.query(func.max(models.Atencion.folio)).scalar() or 0) + 1


def _dispensar(db, atencion_id: str, recetados) -> None:
    """Registra la receta y descuenta el almacen.

    Cada medicamento sale por registrar_movimiento, que valida cantidad y
    disponibilidad. Antes esto restaba directo de `stock_actual` sin ninguna
    comprobacion: recetar mas unidades de las que habia dejaba el inventario
    en negativo en silencio, aunque /kardex/ y la reposicion de botiquines si
    lo rechazaban."""
    for item in recetados or []:
        if not item.medicamento_id:
            continue
        medicamento = stock.buscar_medicamento(db, item.medicamento_id)
        db.add(models.AtencionMedicamento(
            atencion_id=atencion_id, medicamento_id=medicamento.id, cantidad=item.cantidad,
        ))
        stock.registrar_movimiento(db, medicamento, "SALIDA", item.cantidad)


@router.get("/atenciones/", response_model=List[schemas.Atencion], tags=["atenciones"])
def listar_atenciones(db: SesionDB):
    consulta = _cargar_relaciones(
        db.query(models.Atencion).filter(models.Atencion.is_deleted == False)  # noqa: E712
    )
    return consulta.order_by(models.Atencion.fecha.desc()).all()


@router.post("/atenciones/", response_model=schemas.Atencion, tags=["atenciones"])
def crear_atencion(atencion: schemas.AtencionCreate, db: SesionDB):
    datos = _normalizar(atencion.model_dump(exclude={"medicamentos"}))

    fila = models.Atencion(**datos)
    fila.folio = _siguiente_folio(db)
    db.add(fila)
    # flush y no commit: la atencion, su receta y el descuento de stock tienen
    # que confirmarse juntos. Antes la atencion se confirmaba primero y si
    # despues fallaba algo (por ejemplo, un medicamento inexistente) quedaba
    # una atencion guardada sin la receta que la justifica.
    db.flush()

    _dispensar(db, fila.id, atencion.medicamentos)

    if atencion.cita_id:
        cita = db.query(models.Cita).filter(models.Cita.id == atencion.cita_id).first()
        if cita:
            cita.estado = "ATENDIDA"

    db.commit()
    db.refresh(fila)
    return fila


@router.put("/atenciones/{id}", response_model=schemas.Atencion, tags=["atenciones"])
def editar_atencion(id: str, atencion: schemas.AtencionCreate, db: SesionDB):
    fila = crud.obtener_o_404(db, models.Atencion, id, "Atención no encontrada")

    crud.aplicar_campos(fila, _normalizar(atencion.model_dump(exclude={"medicamentos"})))

    # La receta se reemplaza entera: primero se devuelve al almacen lo que
    # estaba recetado antes (INGRESO) y recien despues se descuenta lo nuevo,
    # para que reeditar la misma cantidad no requiera stock extra.
    previos = db.query(models.AtencionMedicamento).filter(
        models.AtencionMedicamento.atencion_id == id
    ).all()
    for previo in previos:
        medicamento = db.query(models.Medicamento).filter(
            models.Medicamento.id == previo.medicamento_id
        ).first()
        if medicamento:
            stock.registrar_movimiento(db, medicamento, "INGRESO", previo.cantidad)
        db.delete(previo)
    db.flush()

    _dispensar(db, fila.id, atencion.medicamentos)

    db.commit()
    db.refresh(fila)
    return fila


@router.delete("/atenciones/{id}", tags=["atenciones"])
def borrar_atencion(id: str, db: SesionDB):
    return crud.borrado_logico(db, models.Atencion, id, "Atención no encontrada", "Eliminada")


# --- Citas ------------------------------------------------------------------

@router.get("/citas/", response_model=List[schemas.Cita], tags=["citas"])
def listar_citas(db: SesionDB):
    return (
        db.query(models.Cita)
        .options(
            joinedload(models.Cita.paciente).joinedload(models.Trabajador.empresa),
            joinedload(models.Cita.personal_salud),
        )
        .filter(models.Cita.is_deleted == False)  # noqa: E712
        .order_by(models.Cita.fecha_hora.desc())
        .all()
    )


@router.post("/citas/", response_model=schemas.Cita, tags=["citas"])
def crear_cita(cita: schemas.CitaCreate, db: SesionDB):
    fila = models.Cita(**cita.model_dump())
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


@router.put("/citas/{id}", response_model=schemas.Cita, tags=["citas"])
def editar_cita(id: str, cita: schemas.CitaCreate, db: SesionDB):
    fila = crud.obtener_o_404(db, models.Cita, id, "Cita no encontrada")
    crud.aplicar_campos(fila, cita.model_dump())
    db.commit()
    db.refresh(fila)
    return fila


@router.delete("/citas/{id}", tags=["citas"])
def borrar_cita(id: str, db: SesionDB):
    return crud.borrado_logico(db, models.Cita, id, "Cita no encontrada", "Eliminada")
