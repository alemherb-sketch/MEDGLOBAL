from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
import datetime
from database import Base

class Empresa(Base):
    __tablename__ = "empresas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), index=True)
    ruc = Column(String(20), unique=True, index=True)
    direccion = Column(String(250), nullable=True)
    telefono = Column(String(50), nullable=True)
    correo_electronico = Column(Text, nullable=True) # Puede contener multiples separados por coma
    estado = Column(String(50), default="ACTIVO")
    
    trabajadores = relationship("Trabajador", back_populates="empresa")

class Trabajador(Base):
    __tablename__ = "trabajadores"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), index=True)
    apellidos = Column(String(150), index=True)
    dni = Column(String(20), unique=True, index=True)
    tipo_contrato = Column(String(100))
    afp_onp = Column(String(100))
    rol = Column(String(100)) # Medico, Enfermera, etc.
    
    # Nuevos campos
    codigo_trabajador = Column(String(50), unique=True, index=True, nullable=True)
    cargo = Column(String(100), nullable=True)
    fecha_ingreso = Column(String(20), nullable=True)
    fecha_cese = Column(String(20), nullable=True)
    estado_trabajador = Column(String(50), nullable=True)
    subdivision_sede = Column(String(100), nullable=True)
    centro_costo = Column(String(100), nullable=True)
    tipo_calculo_nomina = Column(String(100), nullable=True)
    area = Column(String(150), nullable=True) # Added Area
    area_personal = Column(String(100), nullable=True)
    grupo_personal = Column(String(100), nullable=True)
    nivel_org_1 = Column(String(100), nullable=True)
    nivel_org_2 = Column(String(100), nullable=True)
    nivel_org_3 = Column(String(100), nullable=True)
    nivel_org_4 = Column(String(100), nullable=True)
    nivel_org_5 = Column(String(100), nullable=True)
    fecha_nacimiento = Column(String(20), nullable=True)
    genero = Column(String(20), nullable=True)
    jefe_inmediato = Column(String(150), nullable=True)
    telefono = Column(String(50), nullable=True)
    correo_electronico = Column(String(150), nullable=True)

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    empresa = relationship("Empresa", back_populates="trabajadores")

    atenciones = relationship("Atencion", back_populates="trabajador")

class SistemaAtencion(Base):
    __tablename__ = "sistemas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, index=True)
    clasificaciones = relationship("ClasificacionAtencion", back_populates="sistema")

class ClasificacionAtencion(Base):
    __tablename__ = "clasificaciones"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100))
    sistema_id = Column(Integer, ForeignKey("sistemas.id"))
    sistema = relationship("SistemaAtencion", back_populates="clasificaciones")

class AtencionMedicamento(Base):
    __tablename__ = "atencion_medicamentos"
    id = Column(Integer, primary_key=True, index=True)
    atencion_id = Column(Integer, ForeignKey("atenciones.id"))
    medicamento_id = Column(Integer, ForeignKey("medicamentos.id"))
    cantidad = Column(Integer, default=1)
    
    medicamento = relationship("Medicamento")

class Atencion(Base):
    __tablename__ = "atenciones"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    
    hora_ingreso = Column(String(10), nullable=True)
    hora_salida = Column(String(10), nullable=True)
    tiempo_topico = Column(String(50), nullable=True)
    
    # Nuevos datos derivados
    edad = Column(String(10), nullable=True)
    residencia = Column(String(200), nullable=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    cargo = Column(String(100), nullable=True)

    descripcion = Column(Text) # Malestar/Anamnesis
    
    # Nuevos campos Evaluacion Medica
    funciones_biologicas = Column(Text, nullable=True) # JSON
    signos_vitales = Column(Text, nullable=True) # JSON
    examen_fisico = Column(Text, nullable=True)
    examenes_auxiliares = Column(Text, nullable=True)

    codigo_diagnostico = Column(String(100), nullable=True)
    diagnostico = Column(Text, nullable=True)
    tratamiento = Column(Text, nullable=True)
    destino = Column(String(100), nullable=True)
    sede_atencion = Column(String(100), nullable=True)
    jefe_inmediato = Column(String(150), nullable=True)
    observaciones = Column(Text, nullable=True)
    
    trabajador_id = Column(Integer, ForeignKey("trabajadores.id"))
    sistema_id = Column(Integer, ForeignKey("sistemas.id"))
    clasificacion_id = Column(Integer, ForeignKey("clasificaciones.id"))
    cita_id = Column(Integer, ForeignKey("citas.id"), nullable=True)
    personal_salud_id = Column(Integer, ForeignKey("personal_salud.id"), nullable=True)
    
    trabajador = relationship("Trabajador")
    empresa = relationship("Empresa")
    sistema = relationship("SistemaAtencion")
    clasificacion = relationship("ClasificacionAtencion")
    cita = relationship("Cita")
    personal_salud = relationship("PersonalSalud")
    
    medicamentos = relationship("AtencionMedicamento", cascade="all, delete-orphan")

class Medicamento(Base):
    __tablename__ = "medicamentos"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, index=True)
    nombre = Column(String(150), index=True)
    presentacion = Column(String(100))
    descripcion = Column(Text)
    stock_actual = Column(Integer, default=0)

class Kardex(Base):
    __tablename__ = "kardex"
    id = Column(Integer, primary_key=True, index=True)
    medicamento_id = Column(Integer, ForeignKey("medicamentos.id"))
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    tipo_movimiento = Column(String(10)) # INGRESO, SALIDA
    cantidad = Column(Integer)
    saldo = Column(Integer)
    
    medicamento = relationship("Medicamento")

class PersonalSalud(Base):
    __tablename__ = "personal_salud"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), index=True)
    apellidos = Column(String(150), index=True)
    especialidad = Column(String(100))
    cmp = Column(String(50), unique=True, nullable=True) # Colegio Médico / Enfermería
    telefono = Column(String(50), nullable=True)
    correo = Column(String(150), nullable=True)
    estado = Column(String(50), default="ACTIVO")

class Cita(Base):
    __tablename__ = "citas"
    id = Column(Integer, primary_key=True, index=True)
    fecha_hora = Column(DateTime)
    motivo = Column(Text, nullable=True)
    estado = Column(String(50), default="PENDIENTE") # PENDIENTE, CONFIRMADA, ATENDIDA, CANCELADA
    
    paciente_id = Column(Integer, ForeignKey("trabajadores.id")) # El paciente es el trabajador
    personal_salud_id = Column(Integer, ForeignKey("personal_salud.id"))
    
    paciente = relationship("Trabajador")
    personal_salud = relationship("PersonalSalud")
