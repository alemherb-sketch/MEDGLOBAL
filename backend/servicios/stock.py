"""Movimientos de inventario: unica fuente de verdad del stock.

Regla del sistema: **cada cambio de stock_actual va acompanado de una fila de
kardex**, y esta funcion es la unica que hace las dos cosas juntas. Antes cada
endpoint repetia el par "restar del stock + crear el kardex" por su cuenta, y
no todos validaban lo mismo: /kardex/ y /botiquines/{id}/reponer rechazaban
sacar mas de lo disponible, pero registrar una atencion no -- dispensar
medicamentos en una atencion dejaba el stock en negativo sin avisar.
"""
from fastapi import HTTPException

import models


class StockInsuficiente(HTTPException):
    def __init__(self, medicamento, solicitado: int):
        super().__init__(
            status_code=400,
            detail=(
                f"Stock insuficiente de «{medicamento.nombre}»: "
                f"se piden {solicitado} y hay {medicamento.stock_actual or 0}."
            ),
        )


def _validar_cantidad(cantidad) -> int:
    """La cantidad de un movimiento siempre es un entero positivo.

    Sin esto una cantidad negativa invertia el movimiento: una SALIDA de -5
    pasaba la comprobacion de stock (`stock < -5` es falso) y despues SUMABA 5
    al inventario. Los formularios ya ponen min=1, pero al API tambien le
    entran datos por sincronizacion e importaciones."""
    try:
        cantidad = int(cantidad)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="La cantidad debe ser un numero entero.")
    if cantidad <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a cero.")
    return cantidad


def registrar_movimiento(
    db,
    medicamento: "models.Medicamento",
    tipo_movimiento: str,
    cantidad,
    *,
    lote=None,
    fecha_vencimiento=None,
    observacion=None,
) -> "models.Kardex":
    """Aplica un movimiento al stock y deja su fila de kardex.

    Devuelve la fila creada (todavia sin commit: el commit es del endpoint,
    para que un error posterior no deje el movimiento a medias)."""
    cantidad = _validar_cantidad(cantidad)
    tipo_movimiento = (tipo_movimiento or "").upper()

    actual = medicamento.stock_actual or 0
    if tipo_movimiento == "INGRESO":
        medicamento.stock_actual = actual + cantidad
    elif tipo_movimiento == "SALIDA":
        if actual < cantidad:
            raise StockInsuficiente(medicamento, cantidad)
        medicamento.stock_actual = actual - cantidad
    else:
        raise HTTPException(
            status_code=400,
            detail="Tipo de movimiento invalido: use INGRESO o SALIDA.",
        )

    fila = models.Kardex(
        medicamento_id=medicamento.id,
        tipo_movimiento=tipo_movimiento,
        cantidad=cantidad,
        saldo=medicamento.stock_actual,
        lote=lote,
        fecha_vencimiento=fecha_vencimiento,
        observacion=observacion,
    )
    db.add(fila)
    return fila


def buscar_medicamento(db, medicamento_id: str) -> "models.Medicamento":
    medicamento = db.query(models.Medicamento).filter(
        models.Medicamento.id == medicamento_id,
        models.Medicamento.is_deleted == False,  # noqa: E712
    ).first()
    if not medicamento:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    return medicamento
