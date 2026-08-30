"""Catalogos maestros: CIE-10, empresas, trabajadores, sistemas,
clasificaciones y personal de salud.

Todos comparten el mismo esqueleto (ver servicios/crud.py); aca queda solo lo
propio de cada uno: paginacion y busqueda del CIE-10, codigo correlativo del
trabajador y la lista de obras.
"""
import io
import re
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

import models
import schemas
from dependencias import RequiereSesion, SesionDB
from servicios import crud
from servicios.codigos import siguiente_codigo

router = APIRouter(dependencies=[RequiereSesion])


# --- Diagnosticos CIE-10 ----------------------------------------------------

@router.get("/diagnosticos/", response_model=schemas.PaginatedDiagnosticos, tags=["cie10"])
def listar_diagnosticos(db: SesionDB, search: Optional[str] = None, skip: int = 0, limit: int = 50):
    consulta = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.is_deleted == False)  # noqa: E712
    if search:
        patron = f"%{search}%"
        consulta = consulta.filter(
            models.DiagnosticoCie10.codigo.ilike(patron)
            | models.DiagnosticoCie10.descripcion.ilike(patron)
        )
    return {
        "total": consulta.count(),
        "items": consulta.order_by(models.DiagnosticoCie10.codigo.asc()).offset(skip).limit(limit).all(),
    }


@router.post("/diagnosticos/", response_model=schemas.DiagnosticoCie10, tags=["cie10"])
def crear_diagnostico(diag: schemas.DiagnosticoCie10Create, db: SesionDB):
    crud.rechazar_duplicado(
        db, models.DiagnosticoCie10, models.DiagnosticoCie10.codigo, diag.codigo,
        "El código CIE-10 ya existe",
    )
    fila = models.DiagnosticoCie10(**diag.model_dump())
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


@router.put("/diagnosticos/{id}", response_model=schemas.DiagnosticoCie10, tags=["cie10"])
def editar_diagnostico(id: str, diag: schemas.DiagnosticoCie10Create, db: SesionDB):
    fila = crud.obtener_o_404(db, models.DiagnosticoCie10, id, "Diagnóstico no encontrado")
    # El codigo es UNIQUE incluso para filas borradas en logico, asi que la
    # busqueda de duplicados NO filtra por is_deleted: si lo hiciera, el choque
    # saldria como error de base de datos en vez de este mensaje.
    if diag.codigo != fila.codigo:
        crud.rechazar_duplicado(
            db, models.DiagnosticoCie10, models.DiagnosticoCie10.codigo, diag.codigo,
            "El código CIE-10 ya existe", excluir_id=id,
        )
    crud.aplicar_campos(fila, diag.model_dump())
    db.commit()
    db.refresh(fila)
    return fila


@router.delete("/diagnosticos/{id}", tags=["cie10"])
def borrar_diagnostico(id: str, db: SesionDB):
    return crud.borrado_logico(db, models.DiagnosticoCie10, id, "Diagnóstico no encontrado")


_PATRON_CIE10 = re.compile(r"^([A-Z0-9.]{3,8})\s*-\s*(.+)$")


@router.post("/diagnosticos/importar/", tags=["cie10"])
async def importar_diagnosticos(db: SesionDB, file: UploadFile = File(...)):
    """Importa un Excel de CIE-10, ya sea con una sola columna
    «CODIGO - DESCRIPCION» o con codigo y descripcion en columnas separadas."""
    if not (file.filename or "").lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido. Usa Excel (.xlsx)")

    contenido = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contenido), header=None)
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el archivo: ¿es un Excel válido?")

    # Los codigos existentes se leen UNA vez. Antes se consultaba la base por
    # cada fila del archivo (miles de consultas en un CIE-10 completo) y ademas
    # dos filas repetidas dentro del MISMO archivo pasaban las dos: ninguna
    # estaba confirmada todavia, chocaban al hacer commit y la importacion
    # entera terminaba en error 500.
    existentes = {codigo for (codigo,) in db.query(models.DiagnosticoCie10.codigo).all() if codigo}

    nuevos = 0
    try:
        for _, fila in df.iterrows():
            if pd.isna(fila.iloc[0]):
                continue
            celda = str(fila.iloc[0]).strip()

            encontrado = _PATRON_CIE10.match(celda)
            if encontrado:
                codigo, descripcion = encontrado.group(1).strip(), encontrado.group(2).strip()
            elif len(df.columns) >= 2 and not pd.isna(fila.iloc[1]):
                codigo, descripcion = celda, str(fila.iloc[1]).strip()
            else:
                continue

            if not codigo or codigo == "nan" or not descripcion or descripcion == "nan":
                continue
            if codigo in existentes:
                continue

            db.add(models.DiagnosticoCie10(codigo=codigo, descripcion=descripcion))
            existentes.add(codigo)
            nuevos += 1

        db.commit()
    except Exception:
        # Sin este rollback la sesion queda inutilizable y las peticiones
        # siguientes atendidas por el mismo worker fallan tambien.
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se pudo importar el archivo: revise el formato de las filas.",
        )

    return {"message": f"Se importaron {nuevos} diagnósticos nuevos."}


# --- Empresas ---------------------------------------------------------------

@router.get("/empresas/", response_model=List[schemas.Empresa], tags=["empresas"])
def listar_empresas(db: SesionDB):
    return crud.listar_vigentes(db, models.Empresa)


@router.post("/empresas/", response_model=schemas.Empresa, tags=["empresas"])
def crear_empresa(empresa: schemas.EmpresaCreate, db: SesionDB):
    crud.rechazar_duplicado(db, models.Empresa, models.Empresa.ruc, empresa.ruc,
                            "Ya existe una empresa con ese RUC")
    fila = models.Empresa(**empresa.model_dump())
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


@router.put("/empresas/{id}", response_model=schemas.Empresa, tags=["empresas"])
def editar_empresa(id: str, empresa: schemas.EmpresaCreate, db: SesionDB):
    fila = crud.obtener_o_404(db, models.Empresa, id, "Empresa no encontrada")
    crud.rechazar_duplicado(db, models.Empresa, models.Empresa.ruc, empresa.ruc,
                            "Ya existe una empresa con ese RUC", excluir_id=id)
    crud.aplicar_campos(fila, empresa.model_dump())
    db.commit()
    db.refresh(fila)
    return fila


@router.delete("/empresas/{id}", tags=["empresas"])
def borrar_empresa(id: str, db: SesionDB):
    return crud.borrado_logico(db, models.Empresa, id, "Empresa no encontrada", "Eliminada")


# --- Trabajadores -----------------------------------------------------------

@router.get("/trabajadores/", response_model=List[schemas.Trabajador], tags=["trabajadores"])
def listar_trabajadores(db: SesionDB, skip: int = 0, limit: int = 1000):
    return (
        db.query(models.Trabajador)
        .filter(models.Trabajador.is_deleted == False)  # noqa: E712
        .order_by(models.Trabajador.codigo_trabajador.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/trabajadores/obras", tags=["trabajadores"])
def listar_obras(db: SesionDB):
    filas = (
        db.query(models.Trabajador.obra)
        .filter(
            models.Trabajador.is_deleted == False,  # noqa: E712
            models.Trabajador.obra.isnot(None),
            models.Trabajador.obra != "",
        )
        .distinct()
        .order_by(models.Trabajador.obra)
        .all()
    )
    return [obra for (obra,) in filas if obra]


@router.post("/trabajadores/", response_model=schemas.Trabajador, tags=["trabajadores"])
def crear_trabajador(trabajador: schemas.TrabajadorCreate, db: SesionDB):
    datos = trabajador.model_dump()
    if not datos.get("codigo_trabajador"):
        datos["codigo_trabajador"] = siguiente_codigo(db, models.Trabajador, "codigo_trabajador", "TRB")
    crud.rechazar_duplicado(db, models.Trabajador, models.Trabajador.dni, datos.get("dni"),
                            "Ya existe un trabajador con ese DNI")
    fila = models.Trabajador(**datos)
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


@router.put("/trabajadores/{id}", response_model=schemas.Trabajador, tags=["trabajadores"])
def editar_trabajador(id: str, trabajador: schemas.TrabajadorCreate, db: SesionDB):
    fila = crud.obtener_o_404(db, models.Trabajador, id, "Trabajador no encontrado")
    crud.rechazar_duplicado(db, models.Trabajador, models.Trabajador.dni, trabajador.dni,
                            "Ya existe un trabajador con ese DNI", excluir_id=id)
    crud.aplicar_campos(fila, trabajador.model_dump())
    db.commit()
    db.refresh(fila)
    return fila


@router.delete("/trabajadores/{id}", tags=["trabajadores"])
def borrar_trabajador(id: str, db: SesionDB):
    return crud.borrado_logico(db, models.Trabajador, id, "Trabajador no encontrado")


# --- Sistemas clinicos y clasificaciones ------------------------------------

@router.get("/sistemas/", response_model=List[schemas.Sistema], tags=["sistemas"])
def listar_sistemas(db: SesionDB):
    return crud.listar_vigentes(db, models.SistemaAtencion)


@router.post("/sistemas/", response_model=schemas.Sistema, tags=["sistemas"])
def crear_sistema(sistema: schemas.SistemaCreate, db: SesionDB):
    crud.rechazar_duplicado(db, models.SistemaAtencion, models.SistemaAtencion.nombre,
                            sistema.nombre, "Ya existe un sistema con ese nombre")
    fila = models.SistemaAtencion(**sistema.model_dump())
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


@router.put("/sistemas/{id}", response_model=schemas.Sistema, tags=["sistemas"])
def editar_sistema(id: str, sistema: schemas.SistemaCreate, db: SesionDB):
    fila = crud.obtener_o_404(db, models.SistemaAtencion, id, "Sistema no encontrado")
    crud.rechazar_duplicado(db, models.SistemaAtencion, models.SistemaAtencion.nombre,
                            sistema.nombre, "Ya existe un sistema con ese nombre", excluir_id=id)
    crud.aplicar_campos(fila, sistema.model_dump())
    db.commit()
    db.refresh(fila)
    return fila


@router.delete("/sistemas/{id}", tags=["sistemas"])
def borrar_sistema(id: str, db: SesionDB):
    return crud.borrado_logico(db, models.SistemaAtencion, id, "Sistema no encontrado")


@router.get("/clasificaciones/", response_model=List[schemas.Clasificacion], tags=["clasificaciones"])
def listar_clasificaciones(db: SesionDB):
    return crud.listar_vigentes(db, models.ClasificacionAtencion)


@router.post("/clasificaciones/", response_model=schemas.Clasificacion, tags=["clasificaciones"])
def crear_clasificacion(clasificacion: schemas.ClasificacionCreate, db: SesionDB):
    fila = models.ClasificacionAtencion(**clasificacion.model_dump())
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


@router.put("/clasificaciones/{id}", response_model=schemas.Clasificacion, tags=["clasificaciones"])
def editar_clasificacion(id: str, clasificacion: schemas.ClasificacionCreate, db: SesionDB):
    fila = crud.obtener_o_404(db, models.ClasificacionAtencion, id, "Clasificación no encontrada")
    crud.aplicar_campos(fila, clasificacion.model_dump())
    db.commit()
    db.refresh(fila)
    return fila


@router.delete("/clasificaciones/{id}", tags=["clasificaciones"])
def borrar_clasificacion(id: str, db: SesionDB):
    return crud.borrado_logico(db, models.ClasificacionAtencion, id, "Clasificación no encontrada")


# --- Personal de salud ------------------------------------------------------

@router.get("/personal_salud/", response_model=List[schemas.PersonalSalud], tags=["personal-salud"])
def listar_personal_salud(db: SesionDB):
    return crud.listar_vigentes(db, models.PersonalSalud)


@router.post("/personal_salud/", response_model=schemas.PersonalSalud, tags=["personal-salud"])
def crear_personal_salud(personal: schemas.PersonalSaludCreate, db: SesionDB):
    crud.rechazar_duplicado(db, models.PersonalSalud, models.PersonalSalud.cmp, personal.cmp,
                            "Ya existe personal con ese CMP")
    fila = models.PersonalSalud(**personal.model_dump())
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


@router.put("/personal_salud/{id}", response_model=schemas.PersonalSalud, tags=["personal-salud"])
def editar_personal_salud(id: str, personal: schemas.PersonalSaludCreate, db: SesionDB):
    fila = crud.obtener_o_404(db, models.PersonalSalud, id, "Personal no encontrado")
    crud.rechazar_duplicado(db, models.PersonalSalud, models.PersonalSalud.cmp, personal.cmp,
                            "Ya existe personal con ese CMP", excluir_id=id)
    crud.aplicar_campos(fila, personal.model_dump())
    db.commit()
    db.refresh(fila)
    return fila


@router.delete("/personal_salud/{id}", tags=["personal-salud"])
def borrar_personal_salud(id: str, db: SesionDB):
    return crud.borrado_logico(db, models.PersonalSalud, id, "Personal no encontrado")
