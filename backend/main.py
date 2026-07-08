from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
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
        "funciones_biologicas TEXT", "signos_vitales TEXT", "examen_fisico TEXT", "examenes_auxiliares TEXT",
        "codigo_diagnostico VARCHAR(100)", "diagnostico_1 VARCHAR(255)", "diagnostico_2 VARCHAR(255)", "diagnostico_3 VARCHAR(255)"
    ]
    for col in columnas_atencion:
        try:
            with conn.begin():
                conn.execute(text(f"ALTER TABLE atenciones ADD COLUMN {col}"))
        except Exception:
            pass
            
    try:
        with conn.begin():
            conn.execute(text("ALTER TABLE medicamentos ADD COLUMN costo_unitario FLOAT DEFAULT 0.0"))
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

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

# --- Diagnosticos CIE10 ---
@app.get("/diagnosticos/", response_model=List[schemas.DiagnosticoCie10])
def read_diagnosticos(db: Session = Depends(get_db)):
    return db.query(models.DiagnosticoCie10).all()

@app.post("/diagnosticos/", response_model=schemas.DiagnosticoCie10)
def create_diagnostico(diag: schemas.DiagnosticoCie10Create, db: Session = Depends(get_db)):
    db_diag = models.DiagnosticoCie10(**diag.dict())
    db.add(db_diag)
    db.commit()
    db.refresh(db_diag)
    return db_diag

@app.put("/diagnosticos/{id}", response_model=schemas.DiagnosticoCie10)
def update_diagnostico(id: int, diag: schemas.DiagnosticoCie10Create, db: Session = Depends(get_db)):
    db_diag = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.id == id).first()
    if not db_diag:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    
    # Check if new code already exists in another record
    if diag.codigo != db_diag.codigo:
        exist = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.codigo == diag.codigo).first()
        if exist:
            raise HTTPException(status_code=400, detail="El código CIE-10 ya existe")
            
    for key, value in diag.dict().items():
        setattr(db_diag, key, value)
    db.commit()
    db.refresh(db_diag)
    return db_diag

@app.delete("/diagnosticos/{id}")
def delete_diagnostico(id: int, db: Session = Depends(get_db)):
    db_diag = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.id == id).first()
    if not db_diag:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    db.delete(db_diag)
    db.commit()
    return {"detail": "Eliminado"}

@app.post("/diagnosticos/importar/")
async def import_diagnosticos(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido. Usa Excel (.xlsx)")
    
    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents), header=None)
        
        count = 0
        import re
        
        for index, row in df.iterrows():
            if pd.isna(row.iloc[0]):
                continue
                
            celda = str(row.iloc[0]).strip()
            
            # Buscar el patron "CODIGO - DESCRIPCION" (ej. "A00 - COLERA")
            match = re.match(r"^([A-Z0-9.]{3,8})\s*-\s*(.+)$", celda)
            
            if match:
                codigo = match.group(1).strip()
                descripcion = match.group(2).strip()
            else:
                # Si tiene 2 columnas, plan B clásico
                if len(df.columns) >= 2 and not pd.isna(row.iloc[1]):
                    codigo = celda
                    descripcion = str(row.iloc[1]).strip()
                else:
                    continue
            
            if codigo and codigo != 'nan' and descripcion and descripcion != 'nan':
                # Evitar duplicados por código
                exist = db.query(models.DiagnosticoCie10).filter(models.DiagnosticoCie10.codigo == codigo).first()
                if not exist:
                    new_diag = models.DiagnosticoCie10(codigo=codigo, descripcion=descripcion)
                    db.add(new_diag)
                    count += 1
        
        db.commit()
        return {"message": f"Se importaron {count} diagnósticos nuevos."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/dashboard/stats")
def get_dashboard_stats(fecha_inicio: str = None, fecha_fin: str = None, db: Session = Depends(get_db)):
    # Helper to apply date filters
    def apply_date_filter(query):
        if fecha_inicio:
            query = query.filter(func.date(models.Atencion.fecha) >= fecha_inicio)
        if fecha_fin:
            query = query.filter(func.date(models.Atencion.fecha) <= fecha_fin)
        return query

    # 1. Enfermedades más frecuentes
    q_enf = db.query(models.Atencion.diagnostico, func.count(models.Atencion.id).label('total')) \
        .filter(models.Atencion.diagnostico != None, models.Atencion.diagnostico != '')
    q_enf = apply_date_filter(q_enf)
    top_enfermedades = q_enf.group_by(models.Atencion.diagnostico) \
        .order_by(func.count(models.Atencion.id).desc()) \
        .limit(5).all()
        
    enfermedades = [{"name": str(e.diagnostico), "value": int(e.total)} for e in top_enfermedades]

    # 2. Pacientes más atendidos
    q_pac = db.query(models.Trabajador.nombre, models.Trabajador.apellidos, func.count(models.Atencion.id).label('total')) \
        .join(models.Atencion, models.Trabajador.id == models.Atencion.trabajador_id)
    q_pac = apply_date_filter(q_pac)
    top_pacientes = q_pac.group_by(models.Trabajador.id) \
        .order_by(func.count(models.Atencion.id).desc()) \
        .limit(5).all()
        
    pacientes = [{"name": f"{p.nombre} {p.apellidos}", "value": int(p.total)} for p in top_pacientes]

    # 3. Empresas más atendidas
    q_emp = db.query(models.Empresa.nombre, func.count(models.Atencion.id).label('total')) \
        .join(models.Atencion, models.Empresa.id == models.Atencion.empresa_id)
    q_emp = apply_date_filter(q_emp)
    top_empresas = q_emp.group_by(models.Empresa.id) \
        .order_by(func.count(models.Atencion.id).desc()) \
        .limit(5).all()
        
    empresas = [{"name": str(e.nombre), "value": int(e.total)} for e in top_empresas]

    # 4. Medicamentos más usados
    q_med = db.query(models.Medicamento.nombre, func.sum(models.AtencionMedicamento.cantidad).label('total')) \
        .join(models.AtencionMedicamento, models.Medicamento.id == models.AtencionMedicamento.medicamento_id) \
        .join(models.Atencion, models.Atencion.id == models.AtencionMedicamento.atencion_id)
    q_med = apply_date_filter(q_med)
    top_medicamentos = q_med.group_by(models.Medicamento.id) \
        .order_by(func.sum(models.AtencionMedicamento.cantidad).desc()) \
        .limit(5).all()
        
    medicamentos = [{"name": str(m.nombre), "value": int(m.total or 0)} for m in top_medicamentos]

    # 5. Costos por Empresa
    q_costos = db.query(models.Empresa.nombre, func.sum(models.AtencionMedicamento.cantidad * models.Medicamento.costo_unitario).label('total_costo')) \
        .join(models.Atencion, models.Empresa.id == models.Atencion.empresa_id) \
        .join(models.AtencionMedicamento, models.Atencion.id == models.AtencionMedicamento.atencion_id) \
        .join(models.Medicamento, models.AtencionMedicamento.medicamento_id == models.Medicamento.id)
    q_costos = apply_date_filter(q_costos)
    costos_empresa_query = q_costos.group_by(models.Empresa.id) \
        .order_by(func.sum(models.AtencionMedicamento.cantidad * models.Medicamento.costo_unitario).desc()) \
        .limit(10).all()
        
    costos = [{"name": str(c.nombre), "value": float(c.total_costo or 0)} for c in costos_empresa_query]

    return {
        "enfermedades": enfermedades,
        "pacientes": pacientes,
        "empresas": empresas,
        "medicamentos": medicamentos,
        "costos": costos
    }

# ── Detailed Report Data ──
@app.get("/dashboard/report/{report_type}")
def get_report_detail(report_type: str, fecha_inicio: str = None, fecha_fin: str = None, db: Session = Depends(get_db)):
    def apply_date_filter(query):
        if fecha_inicio:
            query = query.filter(func.date(models.Atencion.fecha) >= fecha_inicio)
        if fecha_fin:
            query = query.filter(func.date(models.Atencion.fecha) <= fecha_fin)
        return query

    if report_type == "enfermedades":
        q = db.query(models.Atencion).filter(
            models.Atencion.diagnostico != None, models.Atencion.diagnostico != ''
        )
        q = apply_date_filter(q)
        atenciones = q.all()
        
        # Group by diagnostico
        from collections import defaultdict
        grouped = defaultdict(list)
        for a in atenciones:
            trab = a.trabajador
            emp = a.empresa
            grouped[a.diagnostico].append({
                "fecha": a.fecha.strftime("%d/%m/%Y") if a.fecha else "",
                "paciente": f"{trab.nombre} {trab.apellidos}" if trab else "—",
                "dni": trab.dni if trab else "—",
                "empresa": emp.nombre if emp else "—",
                "area": trab.area or "—" if trab else "—",
            })
        
        result = []
        for diag, items in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
            result.append({"name": diag, "total": len(items), "details": items})
        return result[:10]

    elif report_type == "pacientes":
        q = db.query(models.Atencion)
        q = apply_date_filter(q)
        atenciones = q.all()

        from collections import defaultdict
        grouped = defaultdict(list)
        for a in atenciones:
            trab = a.trabajador
            emp = a.empresa
            if not trab:
                continue
            key = trab.id
            grouped[key].append({
                "fecha": a.fecha.strftime("%d/%m/%Y") if a.fecha else "",
                "diagnostico": a.diagnostico or "—",
                "empresa": emp.nombre if emp else "—",
                "destino": a.destino or "—",
                "_nombre": f"{trab.nombre} {trab.apellidos}",
                "_dni": trab.dni,
                "_cargo": trab.cargo or "—",
                "_area": trab.area or "—",
            })

        result = []
        for tid, items in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
            first = items[0]
            result.append({
                "name": first["_nombre"],
                "dni": first["_dni"],
                "cargo": first["_cargo"],
                "area": first["_area"],
                "total": len(items),
                "details": [{"fecha": i["fecha"], "diagnostico": i["diagnostico"], "empresa": i["empresa"], "destino": i["destino"]} for i in items]
            })
        return result[:10]

    elif report_type == "empresas":
        q = db.query(models.Atencion).filter(models.Atencion.empresa_id != None)
        q = apply_date_filter(q)
        atenciones = q.all()

        from collections import defaultdict
        grouped = defaultdict(list)
        for a in atenciones:
            emp = a.empresa
            trab = a.trabajador
            if not emp:
                continue
            grouped[emp.id].append({
                "fecha": a.fecha.strftime("%d/%m/%Y") if a.fecha else "",
                "paciente": f"{trab.nombre} {trab.apellidos}" if trab else "—",
                "diagnostico": a.diagnostico or "—",
                "destino": a.destino or "—",
                "_empresa": emp.nombre,
                "_ruc": emp.ruc,
            })

        result = []
        for eid, items in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
            first = items[0]
            result.append({
                "name": first["_empresa"],
                "ruc": first["_ruc"],
                "total": len(items),
                "details": [{"fecha": i["fecha"], "paciente": i["paciente"], "diagnostico": i["diagnostico"], "destino": i["destino"]} for i in items]
            })
        return result[:10]

    elif report_type == "medicamentos":
        q = db.query(
            models.Medicamento.nombre,
            models.Medicamento.presentacion,
            models.Medicamento.costo_unitario,
            models.Medicamento.stock_actual,
            func.sum(models.AtencionMedicamento.cantidad).label('total')
        ).join(models.AtencionMedicamento, models.Medicamento.id == models.AtencionMedicamento.medicamento_id) \
         .join(models.Atencion, models.Atencion.id == models.AtencionMedicamento.atencion_id)
        q = apply_date_filter(q)
        rows = q.group_by(models.Medicamento.id).order_by(func.sum(models.AtencionMedicamento.cantidad).desc()).limit(10).all()
        
        result = []
        for r in rows:
            result.append({
                "name": str(r.nombre),
                "presentacion": str(r.presentacion or "—"),
                "costo_unitario": float(r.costo_unitario or 0),
                "stock_actual": int(r.stock_actual or 0),
                "total": int(r.total or 0),
                "costo_total": round(float(r.costo_unitario or 0) * int(r.total or 0), 2)
            })
        return result

    elif report_type == "costos":
        q = db.query(models.Atencion).filter(models.Atencion.empresa_id != None)
        q = apply_date_filter(q)
        atenciones = q.all()

        from collections import defaultdict
        empresas_data = defaultdict(lambda: {"nombre": "", "ruc": "", "meds": defaultdict(lambda: {"nombre": "", "presentacion": "", "cantidad": 0, "costo_unitario": 0.0})})
        
        for a in atenciones:
            emp = a.empresa
            if not emp:
                continue
            ed = empresas_data[emp.id]
            ed["nombre"] = emp.nombre
            ed["ruc"] = emp.ruc or "—"
            for am in a.medicamentos:
                med = am.medicamento
                if med:
                    md = ed["meds"][med.id]
                    md["nombre"] = med.nombre
                    md["presentacion"] = med.presentacion or ""
                    md["cantidad"] += am.cantidad
                    md["costo_unitario"] = float(med.costo_unitario or 0)

        result = []
        for eid, ed in empresas_data.items():
            details = []
            total_cost = 0
            for mid, md in ed["meds"].items():
                subtotal = md["cantidad"] * md["costo_unitario"]
                total_cost += subtotal
                details.append({
                    "medicamento": md["nombre"],
                    "presentacion": md["presentacion"],
                    "cantidad": md["cantidad"],
                    "costo_unitario": md["costo_unitario"],
                    "subtotal": round(subtotal, 2)
                })
            result.append({
                "name": ed["nombre"],
                "ruc": ed["ruc"],
                "total": round(total_cost, 2),
                "details": sorted(details, key=lambda x: x["subtotal"], reverse=True)
            })
        
        result.sort(key=lambda x: x["total"], reverse=True)
        return result[:10]

    return []
