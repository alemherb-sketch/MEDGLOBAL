from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

import models, schemas
from database import engine, get_db

# Create DB tables
models.Base.metadata.create_all(bind=engine)

# Aplicar migraciones automáticas para SQLite/PostgreSQL si las columnas no existen
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
with engine.connect() as conn:
    columnas_trabajador = [
        "codigo_trabajador VARCHAR(50)", "cargo VARCHAR(100)", "fecha_ingreso VARCHAR(20)", "fecha_cese VARCHAR(20)",
        "estado_trabajador VARCHAR(50)", "subdivision_sede VARCHAR(100)", "centro_costo VARCHAR(100)",
        "tipo_calculo_nomina VARCHAR(100)", "area VARCHAR(150)", "area_personal VARCHAR(100)", "grupo_personal VARCHAR(100)",
        "nivel_org_1 VARCHAR(100)", "nivel_org_2 VARCHAR(100)", "nivel_org_3 VARCHAR(100)", "nivel_org_4 VARCHAR(100)",
        "nivel_org_5 VARCHAR(100)", "fecha_nacimiento VARCHAR(20)", "genero VARCHAR(20)", "jefe_inmediato VARCHAR(150)",
        "telefono VARCHAR(50)", "correo_electronico VARCHAR(150)", "empresa_id INTEGER"
    ]
    for col in columnas_trabajador:
        try:
            with conn.begin():
                conn.execute(text(f"ALTER TABLE trabajadores ADD COLUMN {col}"))
        except Exception:
            pass
            
    columnas_atencion = [
        "edad VARCHAR(10)", "residencia VARCHAR(200)", "empresa_id INTEGER", "cargo VARCHAR(100)",
        "funciones_biologicas TEXT", "signos_vitales TEXT", "examen_fisico TEXT", "examenes_auxiliares TEXT"
    ]
    for col in columnas_atencion:
        try:
            with conn.begin():
                conn.execute(text(f"ALTER TABLE atenciones ADD COLUMN {col}"))
        except Exception:
            pass

app = FastAPI(title="MEDGLOBAL API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Empresas ---
@app.get("/empresas/", response_model=List[schemas.Empresa])
def read_empresas(db: Session = Depends(get_db)):
    return db.query(models.Empresa).all()

@app.post("/empresas/", response_model=schemas.Empresa)
def create_empresa(empresa: schemas.EmpresaCreate, db: Session = Depends(get_db)):
    db_emp = models.Empresa(**empresa.dict())
    db.add(db_emp)
    db.commit()
    db.refresh(db_emp)
    return db_emp

@app.put("/empresas/{id}", response_model=schemas.Empresa)
def update_empresa(id: int, empresa: schemas.EmpresaCreate, db: Session = Depends(get_db)):
    db_emp = db.query(models.Empresa).filter(models.Empresa.id == id).first()
    if not db_emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    for key, value in empresa.dict().items():
        setattr(db_emp, key, value)
    db.commit()
    db.refresh(db_emp)
    return db_emp

@app.delete("/empresas/{id}")
def delete_empresa(id: int, db: Session = Depends(get_db)):
    db_emp = db.query(models.Empresa).filter(models.Empresa.id == id).first()
    if not db_emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    db.delete(db_emp)
    db.commit()
    return {"detail": "Eliminada"}

# --- Trabajadores ---
@app.get("/trabajadores/", response_model=List[schemas.Trabajador])
def read_trabajadores(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Trabajador).offset(skip).limit(limit).all()

@app.post("/trabajadores/", response_model=schemas.Trabajador)
def create_trabajador(trabajador: schemas.TrabajadorCreate, db: Session = Depends(get_db)):
    if not trabajador.codigo_trabajador:
        last_t = db.query(models.Trabajador).order_by(models.Trabajador.id.desc()).first()
        next_id = (last_t.id + 1) if last_t else 1
        trabajador.codigo_trabajador = f"TRB-{next_id:04d}"
        
    db_trabajador = models.Trabajador(**trabajador.dict())
    db.add(db_trabajador)
    db.commit()
    db.refresh(db_trabajador)
    return db_trabajador

@app.put("/trabajadores/{id}", response_model=schemas.Trabajador)
def update_trabajador(id: int, trabajador: schemas.TrabajadorCreate, db: Session = Depends(get_db)):
    db_trabajador = db.query(models.Trabajador).filter(models.Trabajador.id == id).first()
    if not db_trabajador:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    for key, value in trabajador.dict().items():
        setattr(db_trabajador, key, value)
    db.commit()
    db.refresh(db_trabajador)
    return db_trabajador

@app.delete("/trabajadores/{id}")
def delete_trabajador(id: int, db: Session = Depends(get_db)):
    db_trabajador = db.query(models.Trabajador).filter(models.Trabajador.id == id).first()
    if not db_trabajador:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    db.delete(db_trabajador)
    db.commit()
    return {"detail": "Eliminado"}

# --- Sistemas y Clasificaciones ---
@app.get("/sistemas/", response_model=List[schemas.Sistema])
def read_sistemas(db: Session = Depends(get_db)):
    return db.query(models.SistemaAtencion).all()

@app.post("/sistemas/", response_model=schemas.Sistema)
def create_sistema(sistema: schemas.SistemaCreate, db: Session = Depends(get_db)):
    db_sistema = models.SistemaAtencion(**sistema.dict())
    db.add(db_sistema)
    db.commit()
    db.refresh(db_sistema)
    return db_sistema

@app.put("/sistemas/{id}", response_model=schemas.Sistema)
def update_sistema(id: int, sistema: schemas.SistemaCreate, db: Session = Depends(get_db)):
    db_sistema = db.query(models.SistemaAtencion).filter(models.SistemaAtencion.id == id).first()
    if not db_sistema:
        raise HTTPException(status_code=404, detail="Sistema no encontrado")
    for key, value in sistema.dict().items():
        setattr(db_sistema, key, value)
    db.commit()
    db.refresh(db_sistema)
    return db_sistema

@app.delete("/sistemas/{id}")
def delete_sistema(id: int, db: Session = Depends(get_db)):
    db_sistema = db.query(models.SistemaAtencion).filter(models.SistemaAtencion.id == id).first()
    if not db_sistema:
        raise HTTPException(status_code=404, detail="Sistema no encontrado")
    db.delete(db_sistema)
    db.commit()
    return {"detail": "Eliminado"}

@app.post("/clasificaciones/", response_model=schemas.Clasificacion)
def create_clasificacion(clasificacion: schemas.ClasificacionCreate, db: Session = Depends(get_db)):
    db_clas = models.ClasificacionAtencion(**clasificacion.dict())
    db.add(db_clas)
    db.commit()
    db.refresh(db_clas)
    return db_clas

@app.put("/clasificaciones/{id}", response_model=schemas.Clasificacion)
def update_clasificacion(id: int, clasificacion: schemas.ClasificacionCreate, db: Session = Depends(get_db)):
    db_clas = db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.id == id).first()
    if not db_clas:
        raise HTTPException(status_code=404, detail="Clasificación no encontrada")
    for key, value in clasificacion.dict().items():
        setattr(db_clas, key, value)
    db.commit()
    db.refresh(db_clas)
    return db_clas

@app.delete("/clasificaciones/{id}")
def delete_clasificacion(id: int, db: Session = Depends(get_db)):
    db_clas = db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.id == id).first()
    if not db_clas:
        raise HTTPException(status_code=404, detail="Clasificación no encontrada")
    db.delete(db_clas)
    db.commit()
    return {"detail": "Eliminado"}

# --- Atenciones ---
@app.get("/atenciones/", response_model=List[schemas.Atencion])
def read_atenciones(db: Session = Depends(get_db)):
    return db.query(models.Atencion).order_by(models.Atencion.fecha.desc()).all()

@app.post("/atenciones/", response_model=schemas.Atencion)
def create_atencion(atencion: schemas.AtencionCreate, db: Session = Depends(get_db)):
    # Separar la data base de medicamentos
    atencion_data = atencion.dict(exclude={'medicamentos'})
    db_atencion = models.Atencion(**atencion_data)
    db.add(db_atencion)
    db.commit()
    db.refresh(db_atencion)
    
    # Procesar medicamentos si hay
    if atencion.medicamentos:
        for med_req in atencion.medicamentos:
            # Añadir relación
            db_am = models.AtencionMedicamento(
                atencion_id=db_atencion.id,
                medicamento_id=med_req.medicamento_id,
                cantidad=med_req.cantidad
            )
            db.add(db_am)
            
            # Descontar de stock
            db_med = db.query(models.Medicamento).filter(models.Medicamento.id == med_req.medicamento_id).first()
            if db_med:
                db_med.stock_actual -= med_req.cantidad
                # Registrar en Kardex
                db_kardex = models.Kardex(
                    medicamento_id=db_med.id,
                    tipo_movimiento="SALIDA",
                    cantidad=med_req.cantidad,
                    saldo=db_med.stock_actual
                )
                db.add(db_kardex)
    
    # Si viene con una cita programada, marcarla como ATENDIDA
    if atencion.cita_id:
        db_cita = db.query(models.Cita).filter(models.Cita.id == atencion.cita_id).first()
        if db_cita:
            db_cita.estado = "ATENDIDA"
            
    db.commit()
    db.refresh(db_atencion)
    return db_atencion

@app.put("/atenciones/{id}", response_model=schemas.Atencion)
def update_atencion(id: int, atencion: schemas.AtencionCreate, db: Session = Depends(get_db)):
    db_atencion = db.query(models.Atencion).filter(models.Atencion.id == id).first()
    if not db_atencion:
        raise HTTPException(status_code=404, detail="Atención no encontrada")
    
    atencion_data = atencion.dict(exclude={'medicamentos'})
    for key, value in atencion_data.items():
        setattr(db_atencion, key, value)
        
    db.commit()
    db.refresh(db_atencion)
    return db_atencion

@app.delete("/atenciones/{id}")
def delete_atencion(id: int, db: Session = Depends(get_db)):
    db_atencion = db.query(models.Atencion).filter(models.Atencion.id == id).first()
    if not db_atencion:
        raise HTTPException(status_code=404, detail="Atención no encontrada")
    db.delete(db_atencion)
    db.commit()
    return {"detail": "Eliminada"}

# --- Medicamentos y Kardex ---
@app.get("/medicamentos/", response_model=List[schemas.Medicamento])
def read_medicamentos(db: Session = Depends(get_db)):
    return db.query(models.Medicamento).all()

@app.post("/medicamentos/", response_model=schemas.Medicamento)
def create_medicamento(medicamento: schemas.MedicamentoCreate, db: Session = Depends(get_db)):
    if not medicamento.codigo:
        last_med = db.query(models.Medicamento).order_by(models.Medicamento.id.desc()).first()
        next_id = (last_med.id + 1) if last_med else 1
        medicamento.codigo = f"MED-{next_id:04d}"
    db_med = models.Medicamento(**medicamento.dict())
    db.add(db_med)
    db.commit()
    db.refresh(db_med)
    return db_med

@app.put("/medicamentos/{id}", response_model=schemas.Medicamento)
def update_medicamento(id: int, medicamento: schemas.MedicamentoCreate, db: Session = Depends(get_db)):
    db_med = db.query(models.Medicamento).filter(models.Medicamento.id == id).first()
    if not db_med:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    for key, value in medicamento.dict().items():
        setattr(db_med, key, value)
    db.commit()
    db.refresh(db_med)
    return db_med

@app.delete("/medicamentos/{id}")
def delete_medicamento(id: int, db: Session = Depends(get_db)):
    db_med = db.query(models.Medicamento).filter(models.Medicamento.id == id).first()
    if not db_med:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    db.delete(db_med)
    db.commit()
    return {"detail": "Eliminado"}

@app.get("/kardex/{medicamento_id}", response_model=List[schemas.Kardex])
def read_kardex(medicamento_id: int, db: Session = Depends(get_db)):
    return db.query(models.Kardex).filter(models.Kardex.medicamento_id == medicamento_id).order_by(models.Kardex.fecha.desc()).all()

@app.post("/kardex/", response_model=schemas.Kardex)
def create_kardex(kardex: schemas.KardexCreate, db: Session = Depends(get_db)):
    db_med = db.query(models.Medicamento).filter(models.Medicamento.id == kardex.medicamento_id).first()
    if not db_med:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    
    # Update stock
    if kardex.tipo_movimiento == "INGRESO":
        db_med.stock_actual += kardex.cantidad
    elif kardex.tipo_movimiento == "SALIDA":
        if db_med.stock_actual < kardex.cantidad:
            raise HTTPException(status_code=400, detail="Stock insuficiente")
        db_med.stock_actual -= kardex.cantidad
        
    db_kardex = models.Kardex(
        medicamento_id=kardex.medicamento_id,
        tipo_movimiento=kardex.tipo_movimiento,
        cantidad=kardex.cantidad,
        saldo=db_med.stock_actual
    )
    db.add(db_kardex)
    db.commit()
    db.refresh(db_kardex)
    return db_kardex

# --- Personal de Salud ---
@app.get("/personal_salud/", response_model=List[schemas.PersonalSalud])
def read_personal_salud(db: Session = Depends(get_db)):
    return db.query(models.PersonalSalud).all()

@app.post("/personal_salud/", response_model=schemas.PersonalSalud)
def create_personal_salud(personal: schemas.PersonalSaludCreate, db: Session = Depends(get_db)):
    db_personal = models.PersonalSalud(**personal.dict())
    db.add(db_personal)
    db.commit()
    db.refresh(db_personal)
    return db_personal

@app.put("/personal_salud/{id}", response_model=schemas.PersonalSalud)
def update_personal_salud(id: int, personal: schemas.PersonalSaludCreate, db: Session = Depends(get_db)):
    db_personal = db.query(models.PersonalSalud).filter(models.PersonalSalud.id == id).first()
    if not db_personal:
        raise HTTPException(status_code=404, detail="Personal no encontrado")
    for key, value in personal.dict().items():
        setattr(db_personal, key, value)
    db.commit()
    db.refresh(db_personal)
    return db_personal

@app.delete("/personal_salud/{id}")
def delete_personal_salud(id: int, db: Session = Depends(get_db)):
    db_personal = db.query(models.PersonalSalud).filter(models.PersonalSalud.id == id).first()
    if not db_personal:
        raise HTTPException(status_code=404, detail="Personal no encontrado")
    db.delete(db_personal)
    db.commit()
    return {"detail": "Eliminado"}

# --- Citas ---
@app.get("/citas/", response_model=List[schemas.Cita])
def read_citas(db: Session = Depends(get_db)):
    return db.query(models.Cita).order_by(models.Cita.fecha_hora.desc()).all()

@app.post("/citas/", response_model=schemas.Cita)
def create_cita(cita: schemas.CitaCreate, db: Session = Depends(get_db)):
    db_cita = models.Cita(**cita.dict())
    db.add(db_cita)
    db.commit()
    db.refresh(db_cita)
    return db_cita

@app.put("/citas/{id}", response_model=schemas.Cita)
def update_cita(id: int, cita: schemas.CitaCreate, db: Session = Depends(get_db)):
    db_cita = db.query(models.Cita).filter(models.Cita.id == id).first()
    if not db_cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    for key, value in cita.dict().items():
        setattr(db_cita, key, value)
    db.commit()
    db.refresh(db_cita)
    return db_cita

@app.delete("/citas/{id}")
def delete_cita(id: int, db: Session = Depends(get_db)):
    db_cita = db.query(models.Cita).filter(models.Cita.id == id).first()
    if not db_cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    db.delete(db_cita)
    db.commit()
    return {"detail": "Eliminada"}

# --- Dashboard ---
@app.get("/dashboard/kpis")
def get_dashboard_kpis(db: Session = Depends(get_db)):
    atenciones_count = db.query(models.Atencion).count()
    trabajadores_count = db.query(models.Trabajador).count()
    medicamentos_count = db.query(models.Medicamento).count()
    stock_bajo = db.query(models.Medicamento).filter(models.Medicamento.stock_actual < 10).count()
    
    return {
        "total_atenciones": atenciones_count,
        "total_trabajadores": trabajadores_count,
        "total_medicamentos": medicamentos_count,
        "medicamentos_stock_bajo": stock_bajo
    }
