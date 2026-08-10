from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
import datetime
import uuid
from database import Base

def gen_uuid():
    return str(uuid.uuid4())

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    username = Column(String(50), unique=True, index=True)
    password_hash = Column(String(255))
    nombre = Column(String(150))
    rol = Column(String(50), default="ESTANDAR")  # ADMIN, ESTANDAR
    estado = Column(String(20), default="ACTIVO")
    creado_en = Column(DateTime, default=datetime.datetime.utcnow)
    # creado_en/estado se dejan tal cual estaban (no son lo mismo que
    # created_at/is_deleted de las demas tablas) -- estas tres son nuevas,
    # necesarias para que usuarios entre al protocolo generico de sync igual
    # que cualquier otra tabla.
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)

class Empresa(Base):
    __tablename__ = "empresas"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    nombre = Column(String(150), index=True)
    ruc = Column(String(20), unique=True, index=True)
    direccion = Column(String(250), nullable=True)
    telefono = Column(String(50), nullable=True)
    correo_electronico = Column(Text, nullable=True) # Puede contener multiples separados por coma
    estado = Column(String(50), default="ACTIVO")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Distinto de updated_at a proposito: updated_at es cuando el USUARIO
    # edito (se usa para decidir quien gana un conflicto de sync), esta
    # columna es cuando el SERVIDOR escribio la fila por ultima vez (se usa
    # para el filtro "que cambio desde since" al sincronizar). Si fueran la
    # misma columna, aplicar la version ganadora de un conflicto con la
    # fecha de edicion original del usuario podria dejarla "vieja" para el
    # filtro de sync aunque el servidor la acabe de tocar — un tercer
    # dispositivo se la perderia. Ver _SYNC_SERVER_COMPUTED_COLUMNS en main.py.
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)

    trabajadores = relationship("Trabajador", back_populates="empresa")

class Trabajador(Base):
    __tablename__ = "trabajadores"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
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
    obra = Column(String(150), nullable=True)
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

    empresa_id = Column(String(36), ForeignKey("empresas.id"), nullable=True)
    empresa = relationship("Empresa", back_populates="trabajadores")

    atenciones = relationship("Atencion", back_populates="trabajador")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Distinto de updated_at a proposito: updated_at es cuando el USUARIO
    # edito (se usa para decidir quien gana un conflicto de sync), esta
    # columna es cuando el SERVIDOR escribio la fila por ultima vez (se usa
    # para el filtro "que cambio desde since" al sincronizar). Si fueran la
    # misma columna, aplicar la version ganadora de un conflicto con la
    # fecha de edicion original del usuario podria dejarla "vieja" para el
    # filtro de sync aunque el servidor la acabe de tocar — un tercer
    # dispositivo se la perderia. Ver _SYNC_SERVER_COMPUTED_COLUMNS en main.py.
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)

class SistemaAtencion(Base):
    __tablename__ = "sistemas"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    nombre = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Distinto de updated_at a proposito: updated_at es cuando el USUARIO
    # edito (se usa para decidir quien gana un conflicto de sync), esta
    # columna es cuando el SERVIDOR escribio la fila por ultima vez (se usa
    # para el filtro "que cambio desde since" al sincronizar). Si fueran la
    # misma columna, aplicar la version ganadora de un conflicto con la
    # fecha de edicion original del usuario podria dejarla "vieja" para el
    # filtro de sync aunque el servidor la acabe de tocar — un tercer
    # dispositivo se la perderia. Ver _SYNC_SERVER_COMPUTED_COLUMNS en main.py.
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)

class ClasificacionAtencion(Base):
    __tablename__ = "clasificaciones"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    nombre = Column(String(100))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Distinto de updated_at a proposito: updated_at es cuando el USUARIO
    # edito (se usa para decidir quien gana un conflicto de sync), esta
    # columna es cuando el SERVIDOR escribio la fila por ultima vez (se usa
    # para el filtro "que cambio desde since" al sincronizar). Si fueran la
    # misma columna, aplicar la version ganadora de un conflicto con la
    # fecha de edicion original del usuario podria dejarla "vieja" para el
    # filtro de sync aunque el servidor la acabe de tocar — un tercer
    # dispositivo se la perderia. Ver _SYNC_SERVER_COMPUTED_COLUMNS en main.py.
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)

class DiagnosticoCie10(Base):
    __tablename__ = "diagnosticos_cie10"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    codigo = Column(String(50), unique=True, index=True)
    descripcion = Column(String(255))
    estado = Column(String(20), default="ACTIVO")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Distinto de updated_at a proposito: updated_at es cuando el USUARIO
    # edito (se usa para decidir quien gana un conflicto de sync), esta
    # columna es cuando el SERVIDOR escribio la fila por ultima vez (se usa
    # para el filtro "que cambio desde since" al sincronizar). Si fueran la
    # misma columna, aplicar la version ganadora de un conflicto con la
    # fecha de edicion original del usuario podria dejarla "vieja" para el
    # filtro de sync aunque el servidor la acabe de tocar — un tercer
    # dispositivo se la perderia. Ver _SYNC_SERVER_COMPUTED_COLUMNS en main.py.
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)

class AtencionMedicamento(Base):
    __tablename__ = "atencion_medicamentos"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    atencion_id = Column(String(36), ForeignKey("atenciones.id"))
    medicamento_id = Column(String(36), ForeignKey("medicamentos.id"))
    cantidad = Column(Integer, default=1)

    medicamento = relationship("Medicamento")

class Atencion(Base):
    __tablename__ = "atenciones"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    folio = Column(Integer, unique=True, index=True, nullable=True)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)

    hora_ingreso = Column(String(10), nullable=True)
    hora_salida = Column(String(10), nullable=True)
    tiempo_topico = Column(String(50), nullable=True)

    # Nuevos datos derivados
    edad = Column(String(10), nullable=True)
    residencia = Column(String(200), nullable=True)
    empresa_id = Column(String(36), ForeignKey("empresas.id"), nullable=True)
    cargo = Column(String(100), nullable=True)

    descripcion = Column(Text) # Malestar/Anamnesis

    # Nuevos campos Evaluacion Medica
    funciones_biologicas = Column(Text, nullable=True) # JSON
    signos_vitales = Column(Text, nullable=True) # JSON
    examen_fisico = Column(Text, nullable=True)
    examenes_auxiliares = Column(Text, nullable=True)

    codigo_diagnostico = Column(String(100), nullable=True) # Mantenido por retrocompatibilidad
    diagnostico = Column(Text, nullable=True) # Mantenido por retrocompatibilidad

    # Nuevos campos para los 3 diagnosticos (guardaremos el string seleccionado)
    diagnostico_1 = Column(String(255), nullable=True)
    diagnostico_2 = Column(String(255), nullable=True)
    diagnostico_3 = Column(String(255), nullable=True)

    tratamiento = Column(Text, nullable=True)
    destino = Column(String(100), nullable=True)
    sede_atencion = Column(String(100), nullable=True)
    jefe_inmediato = Column(String(150), nullable=True)
    observaciones = Column(Text, nullable=True)

    trabajador_id = Column(String(36), ForeignKey("trabajadores.id"))
    sistema_id = Column(String(36), ForeignKey("sistemas.id"))
    clasificacion_id = Column(String(36), ForeignKey("clasificaciones.id"))
    cita_id = Column(String(36), ForeignKey("citas.id"), nullable=True)
    personal_salud_id = Column(String(36), ForeignKey("personal_salud.id"), nullable=True)

    trabajador = relationship("Trabajador")
    empresa = relationship("Empresa")
    sistema = relationship("SistemaAtencion")
    clasificacion = relationship("ClasificacionAtencion")
    cita = relationship("Cita")
    personal_salud = relationship("PersonalSalud")

    medicamentos = relationship("AtencionMedicamento", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Distinto de updated_at a proposito: updated_at es cuando el USUARIO
    # edito (se usa para decidir quien gana un conflicto de sync), esta
    # columna es cuando el SERVIDOR escribio la fila por ultima vez (se usa
    # para el filtro "que cambio desde since" al sincronizar). Si fueran la
    # misma columna, aplicar la version ganadora de un conflicto con la
    # fecha de edicion original del usuario podria dejarla "vieja" para el
    # filtro de sync aunque el servidor la acabe de tocar — un tercer
    # dispositivo se la perderia. Ver _SYNC_SERVER_COMPUTED_COLUMNS en main.py.
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)

class Medicamento(Base):
    __tablename__ = "medicamentos"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    codigo = Column(String(50), unique=True, index=True)
    nombre = Column(String(150), index=True)
    presentacion = Column(String(100))
    descripcion = Column(Text)
    tipo = Column(String(20), default="MEDICAMENTO")  # MEDICAMENTO, INSUMO, OTROS
    lote = Column(String(50), nullable=True)
    fecha_vencimiento = Column(String(20), nullable=True)
    stock_actual = Column(Integer, default=0)
    costo_unitario = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Distinto de updated_at a proposito: updated_at es cuando el USUARIO
    # edito (se usa para decidir quien gana un conflicto de sync), esta
    # columna es cuando el SERVIDOR escribio la fila por ultima vez (se usa
    # para el filtro "que cambio desde since" al sincronizar). Si fueran la
    # misma columna, aplicar la version ganadora de un conflicto con la
    # fecha de edicion original del usuario podria dejarla "vieja" para el
    # filtro de sync aunque el servidor la acabe de tocar — un tercer
    # dispositivo se la perderia. Ver _SYNC_SERVER_COMPUTED_COLUMNS en main.py.
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)

class Kardex(Base):
    __tablename__ = "kardex"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    medicamento_id = Column(String(36), ForeignKey("medicamentos.id"))
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    tipo_movimiento = Column(String(10)) # INGRESO, SALIDA
    cantidad = Column(Integer)
    saldo = Column(Integer)
    lote = Column(String(50), nullable=True)
    fecha_vencimiento = Column(String(20), nullable=True)

    medicamento = relationship("Medicamento")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Distinto de updated_at a proposito: updated_at es cuando el USUARIO
    # edito (se usa para decidir quien gana un conflicto de sync), esta
    # columna es cuando el SERVIDOR escribio la fila por ultima vez (se usa
    # para el filtro "que cambio desde since" al sincronizar). Si fueran la
    # misma columna, aplicar la version ganadora de un conflicto con la
    # fecha de edicion original del usuario podria dejarla "vieja" para el
    # filtro de sync aunque el servidor la acabe de tocar — un tercer
    # dispositivo se la perderia. Ver _SYNC_SERVER_COMPUTED_COLUMNS en main.py.
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)

class PersonalSalud(Base):
    __tablename__ = "personal_salud"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    nombre = Column(String(100), index=True)
    apellidos = Column(String(150), index=True)
    especialidad = Column(String(100))
    cmp = Column(String(50), unique=True, nullable=True) # Colegio Médico / Enfermería
    telefono = Column(String(50), nullable=True)
    correo = Column(String(150), nullable=True)
    estado = Column(String(50), default="ACTIVO")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Distinto de updated_at a proposito: updated_at es cuando el USUARIO
    # edito (se usa para decidir quien gana un conflicto de sync), esta
    # columna es cuando el SERVIDOR escribio la fila por ultima vez (se usa
    # para el filtro "que cambio desde since" al sincronizar). Si fueran la
    # misma columna, aplicar la version ganadora de un conflicto con la
    # fecha de edicion original del usuario podria dejarla "vieja" para el
    # filtro de sync aunque el servidor la acabe de tocar — un tercer
    # dispositivo se la perderia. Ver _SYNC_SERVER_COMPUTED_COLUMNS en main.py.
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)

class ConflictoSync(Base):
    """Auditoria de sincronizacion: cuando dos dispositivos editan el mismo
    registro sin haberse visto entre si, gana el mas reciente y la version
    que pierde se guarda aqui completa, en vez de perderse en silencio."""
    __tablename__ = "conflictos_sync"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    tabla = Column(String(50), index=True)
    registro_id = Column(String(36), index=True)
    version_perdedora = Column(Text)  # JSON con todos los campos de la version descartada
    version_ganadora_id = Column(String(36), nullable=True)
    dispositivo_origen = Column(String(100), nullable=True)  # se completa desde la Fase 5 (identidad por instalacion)
    resuelto_en = Column(DateTime, default=datetime.datetime.utcnow)

class Cita(Base):
    __tablename__ = "citas"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    fecha_hora = Column(DateTime)
    motivo = Column(Text, nullable=True)
    estado = Column(String(50), default="PENDIENTE") # PENDIENTE, CONFIRMADA, ATENDIDA, CANCELADA

    paciente_id = Column(String(36), ForeignKey("trabajadores.id")) # El paciente es el trabajador
    personal_salud_id = Column(String(36), ForeignKey("personal_salud.id"))

    paciente = relationship("Trabajador")
    personal_salud = relationship("PersonalSalud")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Distinto de updated_at a proposito: updated_at es cuando el USUARIO
    # edito (se usa para decidir quien gana un conflicto de sync), esta
    # columna es cuando el SERVIDOR escribio la fila por ultima vez (se usa
    # para el filtro "que cambio desde since" al sincronizar). Si fueran la
    # misma columna, aplicar la version ganadora de un conflicto con la
    # fecha de edicion original del usuario podria dejarla "vieja" para el
    # filtro de sync aunque el servidor la acabe de tocar — un tercer
    # dispositivo se la perderia. Ver _SYNC_SERVER_COMPUTED_COLUMNS en main.py.
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)


class TipoBotiquin(Base):
    """Plantilla de botiquin: define el conjunto estandar de insumos/medicamentos."""
    __tablename__ = "tipos_botiquin"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    codigo = Column(String(50), unique=True, nullable=True, index=True)
    nombre = Column(String(150), index=True)

    insumos = relationship("TipoBotiquinInsumo", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)


class TipoBotiquinInsumo(Base):
    __tablename__ = "tipo_botiquin_insumos"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    tipo_botiquin_id = Column(String(36), ForeignKey("tipos_botiquin.id"), index=True)
    medicamento_id = Column(String(36), ForeignKey("medicamentos.id"), index=True)
    cantidad = Column(Integer, default=1)

    medicamento = relationship("Medicamento")


class Botiquin(Base):
    """Equipo de emergencia / botiquin en area, vehiculo o instalacion."""
    __tablename__ = "botiquines"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    codigo = Column(String(50), unique=True, nullable=True, index=True)
    tipo_botiquin_id = Column(String(36), ForeignKey("tipos_botiquin.id"), nullable=True, index=True)
    tipo_equipo = Column(String(120), index=True)  # Botiquin area, vehiculo, etc.
    area = Column(String(50), index=True)  # Mina, Planta
    empresa_id = Column(String(36), ForeignKey("empresas.id"), nullable=True, index=True)
    ubicacion = Column(String(250), nullable=True)
    mapa_url = Column(String(500), nullable=True)  # Enlace Google Maps u otro mapa
    numero_serie_placa = Column(String(100), nullable=True, index=True)  # legacy
    vehiculo = Column(String(150), nullable=True, index=True)
    marca = Column(String(100), nullable=True)
    modelo = Column(String(100), nullable=True)
    equipo = Column(String(100), index=True)  # Botiquin emergencia, Polvorines, Refugios
    estado = Column(String(50), default="ACTIVO")
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    empresa = relationship("Empresa")
    tipo_botiquin = relationship("TipoBotiquin")
    productos = relationship("BotiquinProducto", cascade="all, delete-orphan")
    inspecciones = relationship("BotiquinInspeccion", back_populates="botiquin")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)


class BotiquinProducto(Base):
    """Legacy: contenido por botiquin. El estandar actual es TipoBotiquin + insumos."""
    __tablename__ = "botiquin_productos"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    botiquin_id = Column(String(36), ForeignKey("botiquines.id"), index=True)
    medicamento_id = Column(String(36), ForeignKey("medicamentos.id"), index=True)
    cantidad = Column(Integer, default=1)

    medicamento = relationship("Medicamento")


class BotiquinInspeccion(Base):
    """Inspeccion de un botiquin con responsable e insumos registrados (uso)."""
    __tablename__ = "botiquin_inspecciones"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    botiquin_id = Column(String(36), ForeignKey("botiquines.id"), index=True)
    fecha = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    responsable_id = Column(String(36), ForeignKey("personal_salud.id"), nullable=True, index=True)
    observaciones = Column(Text, nullable=True)

    botiquin = relationship("Botiquin", back_populates="inspecciones")
    responsable = relationship("PersonalSalud")
    insumos = relationship("BotiquinInspeccionInsumo", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    server_updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_deleted = Column(Boolean, default=False, index=True)


class BotiquinInspeccionInsumo(Base):
    __tablename__ = "botiquin_inspeccion_insumos"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    inspeccion_id = Column(String(36), ForeignKey("botiquin_inspecciones.id"), index=True)
    medicamento_id = Column(String(36), ForeignKey("medicamentos.id"), index=True)
    cantidad = Column(Integer, default=1)

    medicamento = relationship("Medicamento")


class EventoAdmin(Base):
    """Registro de lo que hacen los administradores sobre las cuentas.

    MEDGLOBAL no tenia ninguna traza: se sabia quien era usuario, pero no
    quien lo habia creado, bloqueado ni cambiado de rol. El panel del ERP
    necesita mostrar esa actividad, y sin esta tabla no habria nada que
    mostrar.

    NO entra en SYNCABLE_MODELS a proposito: es del servidor. Repartirla a
    cada PC local expondria en todas partes quien administra que, y no aporta
    nada al trabajo offline.
    """

    __tablename__ = "eventos_admin"
    id = Column(String(36), primary_key=True, default=gen_uuid, index=True)
    # Se guarda el nombre, no una clave foranea: si algun dia se borra al
    # usuario, la traza de lo que hizo debe sobrevivir.
    actor = Column(String(150))
    accion = Column(String(60), index=True)
    objetivo = Column(String(150))
    objetivo_id = Column(String(36))
    detalle = Column(Text, default="")
    ip = Column(String(60), default="")
    creado_en = Column(DateTime, default=datetime.datetime.utcnow, index=True)
