"""Atenciones medicas y citas.

Una atencion puede dispensar medicamentos, y eso mueve inventario. Todo
movimiento de stock pasa por servicios/stock.py: aca no se toca
`stock_actual` directamente ni se arma un Kardex a mano.
"""
from collections import Counter
from typing import List

from fastapi import APIRouter
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

import models
import schemas
from dependencias import RequiereSesion, SesionDB, UsuarioActual
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


def _registrar_receta(db, atencion_id: str, recetados) -> Counter:
    """Guarda los renglones de la receta y devuelve cuanto se receta de cada
    medicamento. No mueve stock: eso lo hace `_mover_stock`."""
    totales = Counter()
    for item in recetados or []:
        if not item.medicamento_id:
            continue
        medicamento = stock.buscar_medicamento(db, item.medicamento_id)
        cantidad = stock.validar_cantidad(item.cantidad)
        db.add(models.AtencionMedicamento(
            atencion_id=atencion_id, medicamento_id=medicamento.id, cantidad=cantidad,
        ))
        totales[medicamento.id] += cantidad
    return totales


def _receta_guardada(db, atencion_id: str) -> List[models.AtencionMedicamento]:
    return db.query(models.AtencionMedicamento).filter(
        models.AtencionMedicamento.atencion_id == atencion_id
    ).all()


def _totales(renglones) -> Counter:
    totales = Counter()
    for renglon in renglones:
        totales[renglon.medicamento_id] += renglon.cantidad or 0
    return totales


def _numero(atencion) -> str:
    return f"N.º {atencion.folio}" if atencion.folio else "sin N.º"


def _mover_stock(db, atencion, antes: Counter, despues: Counter, usuario: str,
                 salida: str = None, ingreso: str = None) -> None:
    """Deja en el kardex solo la DIFERENCIA entre la receta anterior y la nueva.

    Antes editar una atencion devolvia al almacen la receta entera (INGRESO) y
    la volvia a descontar entera (SALIDA), aunque solo se corrigiera el
    diagnostico. El kardex se llenaba de ingresos que nunca existieron y sin
    referencia a la atencion: no habia forma de saber de donde venian.

    Cada movimiento sale por registrar_movimiento, que valida cantidad y
    disponibilidad, y lleva el numero de ficha, el usuario y el id de la
    atencion."""
    for medicamento_id in dict.fromkeys([*antes, *despues]):
        diferencia = despues[medicamento_id] - antes[medicamento_id]
        if diferencia == 0:
            continue
        # Sin filtrar los borrados: lo que se devuelve puede ser de un
        # medicamento que ya salio del catalogo.
        medicamento = db.query(models.Medicamento).filter(
            models.Medicamento.id == medicamento_id
        ).first()
        if not medicamento:
            continue
        tipo, motivo = ("SALIDA", salida) if diferencia > 0 else ("INGRESO", ingreso)
        stock.registrar_movimiento(
            db, medicamento, tipo, abs(diferencia),
            observacion=f"{motivo} {_numero(atencion)}",
            usuario=usuario,
            atencion_id=atencion.id,
        )


@router.get("/atenciones/", response_model=List[schemas.Atencion], tags=["atenciones"])
def listar_atenciones(db: SesionDB):
    consulta = _cargar_relaciones(
        db.query(models.Atencion).filter(models.Atencion.is_deleted == False)  # noqa: E712
    )
    return consulta.order_by(models.Atencion.fecha.desc()).all()


@router.post("/atenciones/", response_model=schemas.Atencion, tags=["atenciones"])
def crear_atencion(atencion: schemas.AtencionCreate, db: SesionDB, usuario: UsuarioActual):
    datos = _normalizar(atencion.model_dump(exclude={"medicamentos"}))

    fila = models.Atencion(**datos)
    fila.folio = _siguiente_folio(db)
    db.add(fila)
    # flush y no commit: la atencion, su receta y el descuento de stock tienen
    # que confirmarse juntos. Antes la atencion se confirmaba primero y si
    # despues fallaba algo (por ejemplo, un medicamento inexistente) quedaba
    # una atencion guardada sin la receta que la justifica.
    db.flush()

    recetado = _registrar_receta(db, fila.id, atencion.medicamentos)
    _mover_stock(db, fila, Counter(), recetado, usuario.username, salida="Atención")

    if atencion.cita_id:
        cita = db.query(models.Cita).filter(models.Cita.id == atencion.cita_id).first()
        if cita:
            cita.estado = "ATENDIDA"

    db.commit()
    db.refresh(fila)
    return fila


@router.put("/atenciones/{id}", response_model=schemas.Atencion, tags=["atenciones"])
def editar_atencion(id: str, atencion: schemas.AtencionCreate, db: SesionDB, usuario: UsuarioActual):
    fila = crud.obtener_o_404(db, models.Atencion, id, "Atención no encontrada", solo_vigentes=True)

    crud.aplicar_campos(fila, _normalizar(atencion.model_dump(exclude={"medicamentos"})))

    # Los renglones se reemplazan, pero el stock solo se mueve por lo que
    # cambio: reeditar la misma receta no deja nada en el kardex.
    previos = _receta_guardada(db, id)
    antes = _totales(previos)
    for previo in previos:
        db.delete(previo)
    db.flush()

    despues = _registrar_receta(db, fila.id, atencion.medicamentos)
    _mover_stock(db, fila, antes, despues, usuario.username,
                 salida="Edición de atención", ingreso="Devolución por edición de atención")

    db.commit()
    db.refresh(fila)
    return fila


@router.delete("/atenciones/{id}", tags=["atenciones"])
def borrar_atencion(id: str, db: SesionDB, usuario: UsuarioActual):
    """Anula la atencion y devuelve al almacen lo que se habia recetado.

    Antes solo se marcaba como borrada: lo dispensado quedaba descontado para
    siempre aunque la ficha ya no existiera. La receta se conserva como
    registro de lo que se habia recetado. `solo_vigentes` evita devolver dos
    veces si se anula una ficha ya anulada."""
    fila = crud.obtener_o_404(db, models.Atencion, id, "Atención no encontrada", solo_vigentes=True)
    antes = _totales(_receta_guardada(db, id))
    _mover_stock(db, fila, antes, Counter(), usuario.username, ingreso="Anulación de atención")
    fila.is_deleted = True
    db.commit()
    return {"detail": "Eliminada"}


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
