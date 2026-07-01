from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Trabajador ---
class TrabajadorBase(BaseModel):
    nombre: str
    apellidos: str
    dni: str
    tipo_contrato: Optional[str] = None
    afp_onp: Optional[str] = None
    rol: str
    
    codigo_trabajador: Optional[str] = None
    cargo: Optional[str] = None
    fecha_ingreso: Optional[str] = None
    fecha_cese: Optional[str] = None
    estado_trabajador: Optional[str] = None
    subdivision_sede: Optional[str] = None
    centro_costo: Optional[str] = None
    tipo_calculo_nomina: Optional[str] = None
    area_personal: Optional[str] = None
    grupo_personal: Optional[str] = None
    nivel_org_1: Optional[str] = None
    nivel_org_2: Optional[str] = None
    nivel_org_3: Optional[str] = None
    nivel_org_4: Optional[str] = None
    nivel_org_5: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    genero: Optional[str] = None
    jefe_inmediato: Optional[str] = None
    telefono: Optional[str] = None
    correo_electronico: Optional[str] = None

class TrabajadorCreate(TrabajadorBase):
    pass

class Trabajador(TrabajadorBase):
    id: int

    class Config:
        orm_mode = True
        from_attributes = True

# --- Sistemas de Atencion ---
class ClasificacionBase(BaseModel):
    nombre: str

class ClasificacionCreate(ClasificacionBase):
    sistema_id: int

class Clasificacion(ClasificacionBase):
    id: int
    sistema_id: int

    class Config:
        orm_mode = True
        from_attributes = True

class SistemaBase(BaseModel):
    nombre: str

class SistemaCreate(SistemaBase):
    pass

class Sistema(SistemaBase):
    id: int
    clasificaciones: List[Clasificacion] = []

    class Config:
        orm_mode = True
        from_attributes = True

# --- Medicamento ---
class MedicamentoBase(BaseModel):
    codigo: Optional[str] = None
    nombre: str
    presentacion: str
    descripcion: Optional[str] = None

class MedicamentoCreate(MedicamentoBase):
    pass

class Medicamento(MedicamentoBase):
    id: int
    stock_actual: int

    class Config:
        orm_mode = True
        from_attributes = True

# --- Kardex ---
class KardexBase(BaseModel):
    medicamento_id: int
    tipo_movimiento: str
    cantidad: int

class KardexCreate(KardexBase):
    pass

class Kardex(KardexBase):
    id: int
    fecha: datetime
    saldo: int
    medicamento: Optional[Medicamento] = None

    class Config:
        orm_mode = True
        from_attributes = True

# --- Personal de Salud ---
class PersonalSaludBase(BaseModel):
    nombre: str
    apellidos: str
    especialidad: str
    cmp: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    estado: Optional[str] = "ACTIVO"

class PersonalSaludCreate(PersonalSaludBase):
    pass

class PersonalSalud(PersonalSaludBase):
    id: int
    
    class Config:
        orm_mode = True
        from_attributes = True

# --- Atencion ---
class AtencionMedicamentoBase(BaseModel):
    medicamento_id: int
    cantidad: int = 1

class AtencionMedicamentoCreate(AtencionMedicamentoBase):
    pass

class AtencionMedicamento(AtencionMedicamentoBase):
    id: int
    medicamento: Medicamento
    class Config:
        from_attributes = True

class AtencionBase(BaseModel):
    hora_ingreso: Optional[str] = None
    hora_salida: Optional[str] = None
    tiempo_topico: Optional[str] = None
    
    descripcion: str
    diagnostico: Optional[str] = None
    tratamiento: Optional[str] = None
    destino: Optional[str] = None
    sede_atencion: Optional[str] = None
    jefe_inmediato: Optional[str] = None
    observaciones: Optional[str] = None

    trabajador_id: int
    sistema_id: int
    clasificacion_id: int
    cita_id: Optional[int] = None
    personal_salud_id: Optional[int] = None

class AtencionCreate(AtencionBase):
    medicamentos: List[AtencionMedicamentoCreate] = []

class Atencion(AtencionBase):
    id: int
    fecha: datetime
    trabajador: Trabajador
    sistema: Sistema
    clasificacion: Clasificacion
    personal_salud: Optional[PersonalSalud] = None
    medicamentos: List[AtencionMedicamento] = []
    
    class Config:
        from_attributes = True

# --- Citas ---
class CitaBase(BaseModel):
    fecha_hora: datetime
    motivo: Optional[str] = None
    estado: Optional[str] = "PENDIENTE"
    paciente_id: int
    personal_salud_id: int

class CitaCreate(CitaBase):
    pass

class Cita(CitaBase):
    id: int
    paciente: Trabajador
    personal_salud: PersonalSalud
    
    class Config:
        orm_mode = True
        from_attributes = True
