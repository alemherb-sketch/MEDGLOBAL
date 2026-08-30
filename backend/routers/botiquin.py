"""Botiquines: tipos (plantillas de insumos), equipos e inspecciones."""
import json
import os
import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

import models
import rutas
import schemas
from dependencias import RequiereSesion, SesionDB
from servicios import crud, stock
from servicios.codigos import siguiente_codigo
from servicios.tiempo import ahora_utc

router = APIRouter(dependencies=[RequiereSesion])

# Las imagenes de evidencia se guardan aca, dentro de la carpeta de datos (la
# que sobrevive a una actualizacion del programa).
CARPETA_IMAGENES = "uploads/inspecciones"
EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
EXTENSION_POR_TIPO = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp", "image/bmp": ".bmp",
}
TAMANO_MAXIMO_IMAGEN = 8 * 1024 * 1024


# --- Ayudas -----------------------------------------------------------------

def _resumen_vehiculo(marca=None, modelo=None, serie=None, placa=None) -> Optional[str]:
    """Nombre legible del vehiculo a partir de sus componentes."""
    partes = []
    marca, modelo = (marca or "").strip(), (modelo or "").strip()
    serie, placa = (serie or "").strip(), (placa or "").strip()
    if marca or modelo:
        partes.append(" ".join(p for p in (marca, modelo) if p))
    if serie:
        partes.append(f"Serie {serie}")
    if placa:
        partes.append(f"Placa {placa}")
    return " · ".join(partes) if partes else None


def _aplicar_resumen_vehiculo(datos: dict) -> dict:
    """Si vienen marca/modelo/serie/placa arma el resumen; si no, respeta el
    texto libre que haya cargado el usuario en `vehiculo`."""
    serie, placa = datos.get("serie"), datos.get("placa")
    resumen = _resumen_vehiculo(datos.get("marca"), datos.get("modelo"), serie, placa)
    if resumen:
        datos["vehiculo"] = resumen
    else:
        datos["vehiculo"] = (datos.get("vehiculo") or "").strip() or None
    if serie or placa:
        datos["numero_serie_placa"] = " / ".join(p for p in (serie, placa) if p)
    return datos


def _orden_por_codigo(botiquin):
    """Mayor a menor por el numero del codigo (BS-10 antes que BS-07).

    Se ordena en Python porque el orden alfabetico de la base pondria BS-9
    despues de BS-10."""
    codigo = (getattr(botiquin, "codigo", None) or "").strip()
    encontrado = re.search(r"(\d+)$", codigo)
    return (int(encontrado.group(1)) if encontrado else -1, codigo.lower())


def _reemplazar_insumos_de_tipo(db, tipo, insumos) -> None:
    """Asigna o reemplaza entera la plantilla de insumos de un tipo."""
    db.query(models.TipoBotiquinInsumo).filter(
        models.TipoBotiquinInsumo.tipo_botiquin_id == tipo.id
    ).delete(synchronize_session=False)
    for item in insumos or []:
        if hasattr(item, "model_dump"):
            item = item.model_dump()
        elif hasattr(item, "dict"):
            item = item.dict()
        medicamento_id = item.get("medicamento_id")
        if not medicamento_id:
            continue
        db.add(models.TipoBotiquinInsumo(
            tipo_botiquin_id=tipo.id,
            medicamento_id=medicamento_id,
            cantidad=max(1, int(item.get("cantidad") or 1)),
        ))


def _serializar_imagenes(lista) -> str:
    try:
        return json.dumps(list(lista or []), ensure_ascii=False)
    except (TypeError, ValueError):
        return "[]"


def _campo(item, nombre, por_defecto=None):
    """Los insumos llegan como esquema Pydantic (API) o como dict (sync)."""
    if hasattr(item, nombre):
        return getattr(item, nombre)
    return item.get(nombre, por_defecto)


def _agregar_insumos_a_inspeccion(db, inspeccion_id: str, insumos) -> None:
    items = list(insumos or [])
    if not items:
        return

    # Una sola consulta para validar todos los insumos. Antes se consultaba la
    # base una vez por insumo: una inspeccion de 40 items eran 40 consultas.
    solicitados = {_campo(i, "medicamento_id") for i in items}
    solicitados.discard(None)
    existentes = {
        med_id for (med_id,) in db.query(models.Medicamento.id).filter(
            models.Medicamento.id.in_(solicitados)
        ).all()
    }

    for item in items:
        medicamento_id = _campo(item, "medicamento_id")
        if medicamento_id not in existentes:
            raise HTTPException(status_code=400, detail=f"Insumo no encontrado: {medicamento_id}")

        estado = (_campo(item, "estado", "BUENO") or "BUENO").upper().strip()
        reposicion = (_campo(item, "reposicion", "NO") or "NO").upper().strip()
        if reposicion not in ("SI", "NO"):
            reposicion = "NO"

        db.add(models.BotiquinInspeccionInsumo(
            inspeccion_id=inspeccion_id,
            medicamento_id=medicamento_id,
            cantidad=max(1, int(_campo(item, "cantidad", 1) or 1)),
            estado=estado,
            reposicion=reposicion,
        ))


def _insumos_de_plantilla(db, botiquin):
    """Lista estandar de insumos segun el tipo del botiquin."""
    if not botiquin or not botiquin.tipo_botiquin_id:
        return []
    tipo = db.query(models.TipoBotiquin).filter(
        models.TipoBotiquin.id == botiquin.tipo_botiquin_id,
        models.TipoBotiquin.is_deleted == False,  # noqa: E712
    ).first()
    return list(tipo.insumos or []) if tipo else []


# --- Tipos de botiquin ------------------------------------------------------

@router.get("/tipos_botiquin/", response_model=List[schemas.TipoBotiquin], tags=["botiquin"])
def listar_tipos_botiquin(db: SesionDB, search: Optional[str] = None):
    consulta = (
        db.query(models.TipoBotiquin)
        .options(selectinload(models.TipoBotiquin.insumos).joinedload(models.TipoBotiquinInsumo.medicamento))
        .filter(models.TipoBotiquin.is_deleted == False)  # noqa: E712
    )
    if search:
        patron = f"%{search}%"
        consulta = consulta.filter(
            models.TipoBotiquin.codigo.ilike(patron) | models.TipoBotiquin.nombre.ilike(patron)
        )
    return consulta.order_by(models.TipoBotiquin.nombre.asc()).all()


@router.post("/tipos_botiquin/", response_model=schemas.TipoBotiquin, tags=["botiquin"])
def crear_tipo_botiquin(tipo: schemas.TipoBotiquinCreate, db: SesionDB):
    datos = tipo.model_dump(exclude={"insumos"})
    codigo = (datos.get("codigo") or "").strip()
    datos["codigo"] = codigo or siguiente_codigo(db, models.TipoBotiquin, "codigo", "TB")
    crud.rechazar_duplicado(db, models.TipoBotiquin, models.TipoBotiquin.codigo, datos["codigo"],
                            "Ya existe un tipo de botiquín con ese código")

    fila = models.TipoBotiquin(**datos)
    db.add(fila)
    db.flush()
    _reemplazar_insumos_de_tipo(db, fila, tipo.insumos)
    db.commit()
    db.refresh(fila)
    return fila


@router.get("/tipos_botiquin/{id}", response_model=schemas.TipoBotiquin, tags=["botiquin"])
def ver_tipo_botiquin(id: str, db: SesionDB):
    return crud.obtener_o_404(db, models.TipoBotiquin, id, "Tipo de botiquín no encontrado",
                              solo_vigentes=True)


@router.put("/tipos_botiquin/{id}", response_model=schemas.TipoBotiquin, tags=["botiquin"])
def editar_tipo_botiquin(id: str, tipo: schemas.TipoBotiquinCreate, db: SesionDB):
    fila = crud.obtener_o_404(db, models.TipoBotiquin, id, "Tipo de botiquín no encontrado")
    datos = tipo.model_dump(exclude={"insumos"})
    if datos.get("codigo") is not None:
        datos["codigo"] = (datos["codigo"] or "").strip() or fila.codigo
        crud.rechazar_duplicado(db, models.TipoBotiquin, models.TipoBotiquin.codigo, datos["codigo"],
                                "Ya existe un tipo de botiquín con ese código", excluir_id=id)
    crud.aplicar_campos(fila, datos)
    _reemplazar_insumos_de_tipo(db, fila, tipo.insumos)
    db.commit()
    db.refresh(fila)
    return fila


@router.delete("/tipos_botiquin/{id}", tags=["botiquin"])
def borrar_tipo_botiquin(id: str, db: SesionDB):
    fila = crud.obtener_o_404(db, models.TipoBotiquin, id, "Tipo de botiquín no encontrado")
    en_uso = db.query(models.Botiquin).filter(
        models.Botiquin.tipo_botiquin_id == id,
        models.Botiquin.is_deleted == False,  # noqa: E712
    ).count()
    if en_uso:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {en_uso} botiquín(es) usando este tipo",
        )
    fila.is_deleted = True
    db.commit()
    return {"detail": "Eliminado"}


# --- Botiquines -------------------------------------------------------------

@router.get("/botiquines/", response_model=List[schemas.Botiquin], tags=["botiquin"])
def listar_botiquines(
    db: SesionDB,
    tipo_equipo: Optional[str] = None,
    area: Optional[str] = None,
    ubicacion: Optional[str] = None,
    empresa_id: Optional[str] = None,
    equipo: Optional[str] = None,
    estado: Optional[str] = None,
    tipo_botiquin_id: Optional[str] = None,
    search: Optional[str] = None,
):
    consulta = (
        db.query(models.Botiquin)
        .options(
            joinedload(models.Botiquin.empresa),
            selectinload(models.Botiquin.tipo_botiquin)
            .selectinload(models.TipoBotiquin.insumos)
            .joinedload(models.TipoBotiquinInsumo.medicamento),
        )
        .filter(models.Botiquin.is_deleted == False)  # noqa: E712
    )

    exactos = {
        models.Botiquin.tipo_equipo: tipo_equipo,
        models.Botiquin.ubicacion: ubicacion,
        models.Botiquin.empresa_id: empresa_id,
        models.Botiquin.equipo: equipo,
        models.Botiquin.estado: estado,
        models.Botiquin.tipo_botiquin_id: tipo_botiquin_id,
    }
    for columna, valor in exactos.items():
        if valor:
            consulta = consulta.filter(columna == valor)
    if area:
        consulta = consulta.filter(models.Botiquin.area.ilike(f"%{area}%"))
    if search:
        patron = f"%{search}%"
        campos = (
            models.Botiquin.codigo, models.Botiquin.ubicacion, models.Botiquin.numero_serie_placa,
            models.Botiquin.vehiculo, models.Botiquin.marca, models.Botiquin.modelo,
            models.Botiquin.serie, models.Botiquin.placa, models.Botiquin.tipo_equipo,
            models.Botiquin.equipo,
        )
        condicion = campos[0].ilike(patron)
        for campo in campos[1:]:
            condicion = condicion | campo.ilike(patron)
        consulta = consulta.filter(condicion)

    botiquines = consulta.all()
    botiquines.sort(key=_orden_por_codigo, reverse=True)

    if botiquines:
        # Fecha de la ultima inspeccion de cada botiquin en UNA consulta
        # agrupada (no es columna de la tabla; el esquema la expone calculada).
        ultimas = dict(
            db.query(
                models.BotiquinInspeccion.botiquin_id,
                func.max(models.BotiquinInspeccion.fecha),
            )
            .filter(
                models.BotiquinInspeccion.botiquin_id.in_([b.id for b in botiquines]),
                models.BotiquinInspeccion.is_deleted == False,  # noqa: E712
            )
            .group_by(models.BotiquinInspeccion.botiquin_id)
            .all()
        )
        for botiquin in botiquines:
            botiquin.ultima_inspeccion = ultimas.get(botiquin.id)
    return botiquines


def _validar_tipo(db, datos: dict) -> dict:
    if not datos.get("empresa_id"):
        datos["empresa_id"] = None
    if not datos.get("tipo_botiquin_id"):
        datos["tipo_botiquin_id"] = None
    elif not db.query(models.TipoBotiquin).filter(
        models.TipoBotiquin.id == datos["tipo_botiquin_id"],
        models.TipoBotiquin.is_deleted == False,  # noqa: E712
    ).first():
        raise HTTPException(status_code=400, detail="Tipo de botiquín no encontrado")
    return datos


@router.post("/botiquines/", response_model=schemas.Botiquin, tags=["botiquin"])
def crear_botiquin(botiquin: schemas.BotiquinCreate, db: SesionDB):
    datos = _validar_tipo(db, botiquin.model_dump())
    codigo = (datos.get("codigo") or "").strip()
    datos["codigo"] = codigo or siguiente_codigo(db, models.Botiquin, "codigo", "BOT")
    # solo_vigentes: a diferencia del resto de codigos del sistema, este NO
    # tiene indice UNIQUE en la base (la columna se agrego con ALTER TABLE ADD
    # COLUMN, que no lo crea). Borrar un botiquin y volver a darlo de alta con
    # el mismo codigo es un uso normal y hay varios casos asi en produccion:
    # mirar tambien las filas borradas rechazaria esa alta.
    crud.rechazar_duplicado(db, models.Botiquin, models.Botiquin.codigo, datos["codigo"],
                            "Ya existe un botiquín activo con ese código",
                            solo_vigentes=True)
    if not datos.get("fecha_creacion"):
        datos["fecha_creacion"] = ahora_utc()
    datos = _aplicar_resumen_vehiculo(datos)

    fila = models.Botiquin(**datos)
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


@router.get("/botiquines/{id}", response_model=schemas.Botiquin, tags=["botiquin"])
def ver_botiquin(id: str, db: SesionDB):
    return crud.obtener_o_404(db, models.Botiquin, id, "Botiquín no encontrado", solo_vigentes=True)


@router.get("/botiquines/{id}/insumos", response_model=List[schemas.TipoBotiquinInsumo], tags=["botiquin"])
def listar_insumos_de_botiquin(id: str, db: SesionDB):
    """Plantilla de insumos del tipo asociado (es la base de una inspeccion)."""
    botiquin = crud.obtener_o_404(db, models.Botiquin, id, "Botiquín no encontrado", solo_vigentes=True)
    return _insumos_de_plantilla(db, botiquin)


@router.post("/botiquines/{id}/reponer", response_model=schemas.Kardex, tags=["botiquin"])
def reponer_insumo(id: str, reposicion: schemas.BotiquinReposicionCreate, db: SesionDB):
    """Descuenta del almacen una reposicion destinada a un botiquin."""
    botiquin = crud.obtener_o_404(db, models.Botiquin, id, "Botiquín no encontrado", solo_vigentes=True)
    medicamento = stock.buscar_medicamento(db, reposicion.medicamento_id)
    fila = stock.registrar_movimiento(
        db, medicamento, "SALIDA", reposicion.cantidad,
        observacion=f"Reposición botiquín {botiquin.codigo or botiquin.id}",
    )
    db.commit()
    db.refresh(fila)
    return fila


@router.put("/botiquines/{id}", response_model=schemas.Botiquin, tags=["botiquin"])
def editar_botiquin(id: str, botiquin: schemas.BotiquinCreate, db: SesionDB):
    fila = crud.obtener_o_404(db, models.Botiquin, id, "Botiquín no encontrado")
    datos = _validar_tipo(db, botiquin.model_dump())
    if datos.get("codigo") is not None:
        datos["codigo"] = (datos["codigo"] or "").strip() or fila.codigo
        crud.rechazar_duplicado(db, models.Botiquin, models.Botiquin.codigo, datos["codigo"],
                                "Ya existe un botiquín activo con ese código",
                                excluir_id=id, solo_vigentes=True)
    crud.aplicar_campos(fila, _aplicar_resumen_vehiculo(datos))
    db.commit()
    db.refresh(fila)
    return fila


@router.delete("/botiquines/{id}", tags=["botiquin"])
def borrar_botiquin(id: str, db: SesionDB):
    return crud.borrado_logico(db, models.Botiquin, id, "Botiquín no encontrado")


# --- Inspecciones -----------------------------------------------------------

def _cargar_inspeccion(consulta):
    """El esquema de respuesta anida el botiquin (con su empresa y su tipo), el
    responsable y cada insumo con su medicamento."""
    return consulta.options(
        joinedload(models.BotiquinInspeccion.botiquin).joinedload(models.Botiquin.empresa),
        joinedload(models.BotiquinInspeccion.botiquin)
        .selectinload(models.Botiquin.tipo_botiquin)
        .selectinload(models.TipoBotiquin.insumos)
        .joinedload(models.TipoBotiquinInsumo.medicamento),
        joinedload(models.BotiquinInspeccion.responsable),
        selectinload(models.BotiquinInspeccion.insumos)
        .joinedload(models.BotiquinInspeccionInsumo.medicamento),
    )


@router.get("/botiquin_inspecciones/", response_model=List[schemas.BotiquinInspeccion], tags=["inspecciones"])
def listar_inspecciones(
    db: SesionDB,
    botiquin_id: Optional[str] = None,
    responsable_id: Optional[str] = None,
    empresa_id: Optional[str] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    search: Optional[str] = None,
):
    consulta = _cargar_inspeccion(
        db.query(models.BotiquinInspeccion)
        .filter(models.BotiquinInspeccion.is_deleted == False)  # noqa: E712
        .join(models.Botiquin, models.Botiquin.id == models.BotiquinInspeccion.botiquin_id)
    )
    if botiquin_id:
        consulta = consulta.filter(models.BotiquinInspeccion.botiquin_id == botiquin_id)
    if responsable_id:
        consulta = consulta.filter(models.BotiquinInspeccion.responsable_id == responsable_id)
    if empresa_id:
        consulta = consulta.filter(models.Botiquin.empresa_id == empresa_id)
    if fecha_inicio:
        consulta = consulta.filter(func.date(models.BotiquinInspeccion.fecha) >= fecha_inicio)
    if fecha_fin:
        consulta = consulta.filter(func.date(models.BotiquinInspeccion.fecha) <= fecha_fin)
    if search:
        patron = f"%{search}%"
        consulta = consulta.filter(
            models.Botiquin.ubicacion.ilike(patron)
            | models.Botiquin.numero_serie_placa.ilike(patron)
            | models.Botiquin.tipo_equipo.ilike(patron)
        )
    return consulta.order_by(models.BotiquinInspeccion.fecha.desc()).all()


@router.post("/botiquin_inspecciones/upload-imagen", tags=["inspecciones"])
async def subir_imagen_inspeccion(file: UploadFile = File(...)):
    """Guarda una imagen de evidencia bajo la carpeta de datos."""
    tipo_contenido = (file.content_type or "").lower()
    if not tipo_contenido.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos de imagen")

    contenido = await file.read()
    if not contenido:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    if len(contenido) > TAMANO_MAXIMO_IMAGEN:
        raise HTTPException(status_code=400, detail="La imagen no puede superar 8 MB")

    extension = os.path.splitext((file.filename or "imagen").lower())[1]
    if extension not in EXTENSIONES_IMAGEN:
        extension = EXTENSION_POR_TIPO.get(tipo_contenido, ".jpg")

    carpeta = rutas.datos(CARPETA_IMAGENES)
    os.makedirs(carpeta, exist_ok=True)
    # El nombre lo genera el servidor: el del archivo subido nunca toca el
    # disco, asi que no hay forma de escribir fuera de esta carpeta.
    nombre = f"{uuid.uuid4().hex}{extension}"
    with open(os.path.join(carpeta, nombre), "wb") as destino:
        destino.write(contenido)

    return {"url": f"/media/inspecciones/{nombre}", "nombre": nombre}


@router.post("/botiquin_inspecciones/", response_model=schemas.BotiquinInspeccion, tags=["inspecciones"])
def crear_inspeccion(inspeccion: schemas.BotiquinInspeccionCreate, db: SesionDB):
    crud.obtener_o_404(db, models.Botiquin, inspeccion.botiquin_id, "Botiquín no encontrado",
                       solo_vigentes=True)

    datos = inspeccion.model_dump(exclude={"insumos", "imagenes"})
    if not datos.get("responsable_id"):
        datos["responsable_id"] = None
    if not datos.get("fecha"):
        datos["fecha"] = ahora_utc()
    datos["imagenes"] = _serializar_imagenes(inspeccion.imagenes)

    fila = models.BotiquinInspeccion(**datos)
    db.add(fila)
    db.flush()
    _agregar_insumos_a_inspeccion(db, fila.id, inspeccion.insumos)
    db.commit()
    db.refresh(fila)
    return fila


@router.put("/botiquin_inspecciones/{id}", response_model=schemas.BotiquinInspeccion, tags=["inspecciones"])
def editar_inspeccion(id: str, inspeccion: schemas.BotiquinInspeccionUpdate, db: SesionDB):
    fila = crud.obtener_o_404(db, models.BotiquinInspeccion, id, "Inspección no encontrada",
                              solo_vigentes=True)

    cambios = inspeccion.model_dump(exclude_unset=True, exclude={"insumos", "imagenes"})
    if cambios.get("botiquin_id"):
        crud.obtener_o_404(db, models.Botiquin, cambios["botiquin_id"], "Botiquín no encontrado",
                           solo_vigentes=True)
    if "responsable_id" in cambios and not cambios["responsable_id"]:
        cambios["responsable_id"] = None
    crud.aplicar_campos(fila, cambios)

    if inspeccion.imagenes is not None:
        fila.imagenes = _serializar_imagenes(inspeccion.imagenes)

    if inspeccion.insumos is not None:
        db.query(models.BotiquinInspeccionInsumo).filter(
            models.BotiquinInspeccionInsumo.inspeccion_id == fila.id
        ).delete(synchronize_session=False)
        _agregar_insumos_a_inspeccion(db, fila.id, inspeccion.insumos)

    fila.updated_at = ahora_utc()
    db.commit()
    db.refresh(fila)
    return fila


@router.get("/botiquin_inspecciones/{id}", response_model=schemas.BotiquinInspeccion, tags=["inspecciones"])
def ver_inspeccion(id: str, db: SesionDB):
    return crud.obtener_o_404(db, models.BotiquinInspeccion, id, "Inspección no encontrada",
                              solo_vigentes=True)


@router.delete("/botiquin_inspecciones/{id}", tags=["inspecciones"])
def borrar_inspeccion(id: str, db: SesionDB):
    return crud.borrado_logico(db, models.BotiquinInspeccion, id, "Inspección no encontrada")


# --- Imagenes servidas ------------------------------------------------------
# Router aparte y SIN sesion: el navegador pide estas URLs con <img src="...">,
# que no manda la cabecera Authorization. El acceso se apoya en que el nombre
# es un UUID que solo conoce quien ya vio la inspeccion, y en que la carpeta no
# se puede listar.

router_publico = APIRouter(tags=["inspecciones"])


@router_publico.get("/media/inspecciones/{nombre}")
def servir_imagen_inspeccion(nombre: str):
    seguro = os.path.basename(nombre or "")
    if not seguro or seguro != nombre or ".." in nombre:
        raise HTTPException(status_code=400, detail="Nombre inválido")
    ruta = os.path.join(rutas.datos(CARPETA_IMAGENES), seguro)
    if not os.path.isfile(ruta):
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return FileResponse(ruta)
