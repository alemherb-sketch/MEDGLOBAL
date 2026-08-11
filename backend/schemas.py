from pydantic import BaseModel, field_validator
from typing import List, Optional, Any, Dict
from datetime import datetime
import json

# --- Autenticacion ---
class UsuarioBase(BaseModel):
    username: str
    nombre: str
    rol: Optional[str] = "ESTANDAR"

class UsuarioCreate(UsuarioBase):
    password: str

class Usuario(UsuarioBase):
    id: str
    estado: str

    class Config:
        from_attributes = True

class UsuarioAdminCreate(UsuarioBase):
    """Alta de cuenta desde el panel de administracion."""
    password: str
    estado: Optional[str] = "ACTIVO"


class UsuarioAdminUpdate(BaseModel):
    """Todos opcionales: se envia solo lo que cambia.

    `password` vacio o ausente significa "no tocar la contrasena"; si no,
    editar el nombre obligaria a reescribirla en cada cambio.
    """
    nombre: Optional[str] = None
    rol: Optional[str] = None
    estado: Optional[str] = None
    password: Optional[str] = None


class EventoAdmin(BaseModel):
    id: str
    actor: Optional[str] = None
    accion: str
    objetivo: Optional[str] = None
    objetivo_id: Optional[str] = None
    detalle: Optional[str] = ""
    ip: Optional[str] = ""
    creado_en: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# --- Empresa ---
class EmpresaBase(BaseModel):
    nombre: str
    ruc: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    correo_electronico: Optional[str] = None
    estado: Optional[str] = "ACTIVO"

class EmpresaCreate(EmpresaBase):
    pass

class Empresa(EmpresaBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True
        orm_mode = True
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
    area: Optional[str] = None
    obra: Optional[str] = None
    empresa_id: Optional[str] = None
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
    id: str
    empresa: Optional[Empresa] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True

# --- Sistemas de Atencion ---
class ClasificacionBase(BaseModel):
    nombre: str

class ClasificacionCreate(ClasificacionBase):
    pass

class Clasificacion(ClasificacionBase):
    id: str

    class Config:
        orm_mode = True
        from_attributes = True

# --- Diagnosticos CIE10 ---
class DiagnosticoCie10Base(BaseModel):
    codigo: str
    descripcion: str
    estado: Optional[str] = "ACTIVO"

class DiagnosticoCie10Create(DiagnosticoCie10Base):
    pass

class DiagnosticoCie10(DiagnosticoCie10Base):
    id: str
    class Config:
        orm_mode = True
        from_attributes = True

class PaginatedDiagnosticos(BaseModel):
    total: int
    items: List[DiagnosticoCie10]

class SistemaBase(BaseModel):
    nombre: str

class SistemaCreate(SistemaBase):
    pass

class Sistema(SistemaBase):
    id: str

    class Config:
        orm_mode = True
        from_attributes = True

# --- Medicamento ---
class MedicamentoBase(BaseModel):
    codigo: Optional[str] = None
    nombre: str
    presentacion: str
    descripcion: Optional[str] = None
    tipo: Optional[str] = "MEDICAMENTO"
    lote: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    costo_unitario: Optional[float] = 0.0

class MedicamentoCreate(MedicamentoBase):
    pass

class Medicamento(MedicamentoBase):
    id: str
    stock_actual: int

    class Config:
        orm_mode = True
        from_attributes = True

# --- Kardex ---
class KardexBase(BaseModel):
    medicamento_id: str
    tipo_movimiento: str
    cantidad: int
    lote: Optional[str] = None
    fecha_vencimiento: Optional[str] = None

class KardexCreate(KardexBase):
    pass

class Kardex(KardexBase):
    id: str
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
    id: str

    class Config:
        orm_mode = True
        from_attributes = True

# --- Atencion ---
class AtencionMedicamentoBase(BaseModel):
    medicamento_id: str
    cantidad: int = 1

class AtencionMedicamentoCreate(AtencionMedicamentoBase):
    pass

class AtencionMedicamento(AtencionMedicamentoBase):
    id: str
    medicamento: Medicamento
    class Config:
        from_attributes = True

class AtencionBase(BaseModel):
    fecha: Optional[datetime] = None
    hora_ingreso: Optional[str] = None
    hora_salida: Optional[str] = None
    tiempo_topico: Optional[str] = None

    edad: Optional[str] = None
    residencia: Optional[str] = None
    empresa_id: Optional[str] = None
    cargo: Optional[str] = None

    descripcion: str
    funciones_biologicas: Optional[str] = None
    signos_vitales: Optional[str] = None
    examen_fisico: Optional[str] = None
    examenes_auxiliares: Optional[str] = None

    codigo_diagnostico: Optional[str] = None
    diagnostico: Optional[str] = None
    diagnostico_1: Optional[str] = None
    diagnostico_2: Optional[str] = None
    diagnostico_3: Optional[str] = None
    tratamiento: Optional[str] = None
    destino: Optional[str] = None
    sede_atencion: Optional[str] = None
    jefe_inmediato: Optional[str] = None
    observaciones: Optional[str] = None

    trabajador_id: str
    sistema_id: str
    clasificacion_id: str
    cita_id: Optional[str] = None
    personal_salud_id: Optional[str] = None

class AtencionCreate(AtencionBase):
    medicamentos: List[AtencionMedicamentoCreate] = []

class Atencion(AtencionBase):
    id: str
    folio: Optional[int] = None
    fecha: datetime

    # Al CREAR una atencion estos campos son obligatorios (asi quedan en
    # AtencionBase, que es lo que valida la entrada), pero al DEVOLVERLOS son
    # opcionales a proposito.
    #
    # Antes eran obligatorios tambien en la respuesta, y como FastAPI valida la
    # lista entera, una sola fila con el trabajador o el sistema en NULL hacia
    # fallar GET /atenciones/ con un 500: la pantalla de Atenciones quedaba
    # completamente vacia, sin mostrar ninguna de las demas atenciones y sin
    # ningun mensaje de error. Filas asi aparecen por registros viejos
    # anteriores a una migracion o por datos que llegaron incompletos.
    # La interfaz ya sabe mostrar "N/A" cuando falta alguno.
    trabajador_id: Optional[str] = None
    sistema_id: Optional[str] = None
    clasificacion_id: Optional[str] = None
    trabajador: Optional[Trabajador] = None
    empresa: Optional[Empresa] = None
    sistema: Optional[Sistema] = None
    clasificacion: Optional[Clasificacion] = None
    personal_salud: Optional[PersonalSalud] = None
    medicamentos: List[AtencionMedicamento] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Botiquin ---
class TipoBotiquinInsumoBase(BaseModel):
    medicamento_id: str
    cantidad: int = 1


class TipoBotiquinInsumoCreate(TipoBotiquinInsumoBase):
    pass


class TipoBotiquinInsumo(TipoBotiquinInsumoBase):
    id: str
    medicamento: Optional[Medicamento] = None

    class Config:
        orm_mode = True
        from_attributes = True


class TipoBotiquinBase(BaseModel):
    codigo: Optional[str] = None
    nombre: str
    insumos: List[TipoBotiquinInsumoCreate] = []


class TipoBotiquinCreate(TipoBotiquinBase):
    pass


class TipoBotiquin(TipoBotiquinBase):
    id: str
    insumos: List[TipoBotiquinInsumo] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True


class BotiquinBase(BaseModel):
    codigo: Optional[str] = None
    tipo_botiquin_id: Optional[str] = None
    tipo_equipo: str
    area: str
    empresa_id: Optional[str] = None
    ubicacion: Optional[str] = None
    mapa_url: Optional[str] = None
    numero_serie_placa: Optional[str] = None
    vehiculo: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    serie: Optional[str] = None
    placa: Optional[str] = None
    equipo: str
    estado: Optional[str] = "ACTIVO"
    fecha_creacion: Optional[datetime] = None


class BotiquinCreate(BotiquinBase):
    pass


class Botiquin(BotiquinBase):
    id: str
    empresa: Optional[Empresa] = None
    tipo_botiquin: Optional[TipoBotiquin] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Fecha de la última inspección no eliminada (calculada, no es columna de BD)
    ultima_inspeccion: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True


class BotiquinInspeccionInsumoBase(BaseModel):
    medicamento_id: str
    cantidad: int = 1
    estado: Optional[str] = "BUENO"
    reposicion: Optional[str] = "NO"

class BotiquinInspeccionInsumoCreate(BotiquinInspeccionInsumoBase):
    pass

class BotiquinInspeccionInsumo(BotiquinInspeccionInsumoBase):
    id: str
    medicamento: Optional[Medicamento] = None

    class Config:
        orm_mode = True
        from_attributes = True


def _parse_imagenes(v):
    if v is None or v == '':
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x]
    if isinstance(v, str):
        try:
            data = json.loads(v)
            if isinstance(data, list):
                return [str(x) for x in data if x]
        except Exception:
            return []
    return []


class BotiquinInspeccionBase(BaseModel):
    botiquin_id: str
    fecha: Optional[datetime] = None
    responsable_id: Optional[str] = None
    observaciones: Optional[str] = None
    imagenes: Optional[List[str]] = []
    insumos: List[BotiquinInspeccionInsumoCreate] = []

    @field_validator('imagenes', mode='before')
    @classmethod
    def _imgs(cls, v):
        return _parse_imagenes(v)

class BotiquinInspeccionCreate(BotiquinInspeccionBase):
    pass

class BotiquinInspeccionUpdate(BaseModel):
    botiquin_id: Optional[str] = None
    fecha: Optional[datetime] = None
    responsable_id: Optional[str] = None
    observaciones: Optional[str] = None
    imagenes: Optional[List[str]] = None
    insumos: Optional[List[BotiquinInspeccionInsumoCreate]] = None

    @field_validator('imagenes', mode='before')
    @classmethod
    def _imgs(cls, v):
        if v is None:
            return None
        return _parse_imagenes(v)

class BotiquinInspeccion(BaseModel):
    id: str
    botiquin_id: str
    fecha: Optional[datetime] = None
    responsable_id: Optional[str] = None
    observaciones: Optional[str] = None
    imagenes: Optional[List[str]] = []
    botiquin: Optional[Botiquin] = None
    responsable: Optional[PersonalSalud] = None
    insumos: List[BotiquinInspeccionInsumo] = []
    created_at: Optional[datetime] = None

    @field_validator('imagenes', mode='before')
    @classmethod
    def _imgs(cls, v):
        return _parse_imagenes(v)

    class Config:
        orm_mode = True
        from_attributes = True


# --- Citas ---
class CitaBase(BaseModel):
    fecha_hora: datetime
    motivo: Optional[str] = None
    estado: Optional[str] = "PENDIENTE"
    paciente_id: str
    personal_salud_id: str

class CitaCreate(CitaBase):
    pass

class Cita(CitaBase):
    id: str
    paciente: Trabajador
    personal_salud: PersonalSalud

    class Config:
        orm_mode = True
        from_attributes = True

# --- Sincronizacion ---
class SyncPushRequest(BaseModel):
    since: Optional[str] = None
    cambios: Dict[str, List[Dict[str, Any]]] = {}
