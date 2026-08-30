"""Catalogo de medicamentos e insumos, y el kardex de movimientos."""
import io
from typing import List

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import joinedload

import models
import schemas
from dependencias import RequiereSesion, SesionDB
from servicios import crud, excel, stock
from servicios.codigos import siguiente_codigo

router = APIRouter(dependencies=[RequiereSesion])


# --- Catalogo ---------------------------------------------------------------

@router.get("/medicamentos/", response_model=List[schemas.Medicamento], tags=["medicamentos"])
def listar_medicamentos(db: SesionDB):
    return crud.listar_vigentes(db, models.Medicamento)


@router.post("/medicamentos/", response_model=schemas.Medicamento, tags=["medicamentos"])
def crear_medicamento(medicamento: schemas.MedicamentoCreate, db: SesionDB):
    datos = medicamento.model_dump()
    if not datos.get("codigo"):
        datos["codigo"] = siguiente_codigo(db, models.Medicamento, "codigo", "MED")
    crud.rechazar_duplicado(db, models.Medicamento, models.Medicamento.codigo, datos["codigo"],
                            "Ya existe un producto con ese código")
    fila = models.Medicamento(**datos)
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


@router.put("/medicamentos/{id}", response_model=schemas.Medicamento, tags=["medicamentos"])
def editar_medicamento(id: str, medicamento: schemas.MedicamentoCreate, db: SesionDB):
    fila = crud.obtener_o_404(db, models.Medicamento, id, "Medicamento no encontrado")
    crud.rechazar_duplicado(db, models.Medicamento, models.Medicamento.codigo, medicamento.codigo,
                            "Ya existe un producto con ese código", excluir_id=id)
    # `MedicamentoCreate` no incluye stock_actual a proposito: el stock solo se
    # cambia con un movimiento de kardex, nunca editando la ficha.
    crud.aplicar_campos(fila, medicamento.model_dump())
    db.commit()
    db.refresh(fila)
    return fila


@router.delete("/medicamentos/{id}", tags=["medicamentos"])
def borrar_medicamento(id: str, db: SesionDB):
    return crud.borrado_logico(db, models.Medicamento, id, "Medicamento no encontrado")


@router.post("/medicamentos/importar/", tags=["medicamentos"])
async def importar_medicamentos(db: SesionDB, file: UploadFile = File(...)):
    """Importa o actualiza el catalogo desde un Excel.

    Columnas reconocidas (en cualquiera de las primeras 10 filas, sin importar
    mayusculas ni acentos): Codigo, Nombre, Presentacion, Tipo, Descripcion,
    Costo Unitario, Lote, Fecha Vencimiento, Stock Inicial. Solo Nombre y
    Presentacion son obligatorias.

    Si el codigo ya existe se actualiza esa ficha; si no viene codigo, se
    busca por nombre antes de crear, para que reimportar el mismo listado
    actualice precios y vencimientos en vez de duplicar el catalogo.
    """
    if not (file.filename or "").lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido. Usa Excel (.xlsx)")

    contenido = await file.read()
    try:
        fila_encabezados = excel.fila_de_encabezados(contenido)
        if fila_encabezados < 0:
            raise HTTPException(
                status_code=400,
                detail="No se encontraron encabezados reconocibles (Nombre/Medicamento, Presentación, etc.) "
                       "en las primeras filas del archivo.",
            )
        df = pd.read_excel(io.BytesIO(contenido), header=fila_encabezados)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el archivo: ¿es un Excel válido?")

    encabezados_originales = [str(c) for c in df.columns]
    df.columns = [excel.ALIAS_ENCABEZADOS.get(excel.normalizar_encabezado(c)) for c in df.columns]
    columnas = set(df.columns)

    creados = actualizados = omitidos = 0
    try:
        for _, fila in df.iterrows():
            nombre = excel.valor_de_celda(fila, "nombre", columnas)
            presentacion = excel.valor_de_celda(fila, "presentacion", columnas)
            if not nombre or not presentacion:
                omitidos += 1
                continue

            nombre = excel.recortar(nombre, 150)
            presentacion = excel.recortar(presentacion, 100).upper()
            codigo = excel.recortar(excel.valor_de_celda(fila, "codigo", columnas), 50)

            tipo = excel.valor_de_celda(fila, "tipo", columnas)
            tipo = str(tipo).strip().upper() if tipo else "MEDICAMENTO"
            if tipo not in excel.TIPOS_VALIDOS:
                tipo = "MEDICAMENTO"

            descripcion = excel.valor_de_celda(fila, "descripcion", columnas)
            descripcion = str(descripcion).strip() if descripcion else None

            lote = excel.recortar(excel.valor_de_celda(fila, "lote", columnas), 50)
            vencimiento = excel.recortar(
                excel.parsear_vencimiento(excel.valor_de_celda(fila, "fecha_vencimiento", columnas)), 20
            )
            costo = excel.parsear_costo(excel.valor_de_celda(fila, "costo_unitario", columnas))

            try:
                stock_inicial = int(excel.valor_de_celda(fila, "stock_inicial", columnas) or 0)
            except (ValueError, TypeError):
                stock_inicial = 0

            existente = None
            if codigo:
                existente = db.query(models.Medicamento).filter(
                    models.Medicamento.codigo == codigo
                ).first()
            if not existente:
                existente = db.query(models.Medicamento).filter(
                    func.lower(models.Medicamento.nombre) == nombre.lower(),
                    models.Medicamento.is_deleted == False,  # noqa: E712
                ).first()

            if existente:
                existente.nombre = nombre
                existente.presentacion = presentacion
                existente.tipo = tipo
                existente.descripcion = descripcion
                existente.lote = lote
                existente.fecha_vencimiento = vencimiento
                existente.costo_unitario = costo
                actualizados += 1
                continue

            if not codigo:
                codigo = siguiente_codigo(db, models.Medicamento, "codigo", "MED")
            nuevo = models.Medicamento(
                codigo=codigo, nombre=nombre, presentacion=presentacion, tipo=tipo,
                descripcion=descripcion, lote=lote, fecha_vencimiento=vencimiento,
                costo_unitario=costo, stock_actual=0,
            )
            db.add(nuevo)
            db.flush()
            if stock_inicial > 0:
                # El stock inicial entra como movimiento, no como valor suelto:
                # asi el kardex explica de donde salio cada unidad.
                stock.registrar_movimiento(
                    db, nuevo, "INGRESO", stock_inicial,
                    lote=lote, fecha_vencimiento=vencimiento,
                    observacion="Stock inicial (importación de catálogo)",
                )
            creados += 1

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se pudo importar el archivo: revise que los datos de cada fila sean válidos.",
        )

    mensaje = (f"Importación completa: {creados} nuevos, {actualizados} actualizados, "
               f"{omitidos} fila(s) omitida(s) (sin nombre o presentación).")
    if creados == 0 and actualizados == 0 and omitidos > 0:
        mensaje += f" Encabezados detectados en el archivo: {', '.join(encabezados_originales)}."
    return {"message": mensaje}


# --- Kardex -----------------------------------------------------------------
# /kardex/todos/ va ANTES que /kardex/{medicamento_id}: si no, "todos" se
# interpretaria como un id de medicamento.

@router.get("/kardex/todos/", response_model=List[schemas.Kardex], tags=["kardex"])
def listar_kardex_completo(db: SesionDB):
    """Historial global de movimientos, para la pantalla de Control de Almacen."""
    return (
        db.query(models.Kardex)
        # El esquema de respuesta anida el medicamento de cada movimiento: sin
        # esto son 1000 consultas extra, una por fila devuelta.
        .options(joinedload(models.Kardex.medicamento))
        .filter(models.Kardex.is_deleted == False)  # noqa: E712
        .order_by(models.Kardex.fecha.desc())
        .limit(1000)
        .all()
    )


@router.get("/kardex/{medicamento_id}", response_model=List[schemas.Kardex], tags=["kardex"])
def listar_kardex_de_medicamento(medicamento_id: str, db: SesionDB):
    return (
        db.query(models.Kardex)
        .options(joinedload(models.Kardex.medicamento))
        .filter(
            models.Kardex.medicamento_id == medicamento_id,
            models.Kardex.is_deleted == False,  # noqa: E712
        )
        .order_by(models.Kardex.fecha.desc())
        .all()
    )


@router.post("/kardex/", response_model=schemas.Kardex, tags=["kardex"])
def crear_movimiento_kardex(kardex: schemas.KardexCreate, db: SesionDB):
    medicamento = stock.buscar_medicamento(db, kardex.medicamento_id)
    fila = stock.registrar_movimiento(
        db, medicamento, kardex.tipo_movimiento, kardex.cantidad,
        lote=kardex.lote,
        fecha_vencimiento=kardex.fecha_vencimiento,
        observacion=kardex.observacion,
    )
    db.commit()
    db.refresh(fila)
    return fila
