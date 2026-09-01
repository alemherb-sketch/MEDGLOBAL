import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base
from servicios.tiempo import ahora_utc


def gen_uuid():
    return str(uuid.uuid4())


def Id():
    """Clave primaria de todas las tablas.

    Es un UUID y no un entero autoincremental porque cada instalacion de
    escritorio crea filas sin ver a las demas: con enteros, dos PCs generarian
    el id 47 para registros distintos y la sincronizacion los fusionaria."""
    return Column(String(36), primary_key=True, default=gen_uuid, index=True)


class MarcasDeSincronizacion:
    """Columnas que necesita toda tabla que viaja entre dispositivos.

    `updated_at` y `server_updated_at` son distintas A PROPOSITO:

      - updated_at es cuando el USUARIO edito la fila, tal cual la manda el
        cliente. De eso depende quien gana un conflicto.
      - server_updated_at es cuando el SERVIDOR escribio la fila. De eso
        depende el filtro «que cambio desde `since`» al sincronizar.

    Si fueran una sola columna, aplicar la version ganadora de un conflicto
    con su fecha de edicion original (posiblemente antigua) dejaria la fila
    «vieja» para el filtro de sync aunque el servidor la acabe de tocar, y un
    tercer dispositivo se la perderia.

    `is_deleted` es borrado logico: un registro medico no se elimina, y ademas
    la marca es lo que propaga la baja al resto de los dispositivos (sin ella,
    borrar en una PC seria invisible para las otras).
    """

    updated_at = Column(DateTime, default=ahora_utc, onupdate=ahora_utc)
    server_updated_at = Column(DateTime, default=ahora_utc, onupdate=ahora_utc)
    is_deleted = Column(Boolean, default=False, index=True)


class MarcasDeAuditoria(MarcasDeSincronizacion):
    """Lo anterior mas la fecha de alta."""

    created_at = Column(DateTime, default=ahora_utc)


class Usuario(MarcasDeSincronizacion, Base):
    # Usa `creado_en` y `estado` en vez de created_at/is_deleted: son columnas
    # anteriores a la sincronizacion y renombrarlas romperia las bases en uso.
    __tablename__ = "usuarios"
    id = Id()
    username = Column(String(50), unique=True, index=True)
    password_hash = Column(String(255))
    nombre = Column(String(150))
    rol = Column(String(50), default="ESTANDAR")  # ADMIN, ESTANDAR
    estado = Column(String(20), default="ACTIVO")
    creado_en = Column(DateTime, default=ahora_utc)


class Empresa(MarcasDeAuditoria, Base):
    __tablename__ = "empresas"
    id = Id()
    nombre = Column(String(150), index=True)
    ruc = Column(String(20), unique=True, index=True)
    direccion = Column(String(250), nullable=True)
    telefono = Column(String(50), nullable=True)
    correo_electronico = Column(Text, nullable=True)  # puede traer varios separados por coma
    estado = Column(String(50), default="ACTIVO")

    trabajadores = relationship("Trabajador", back_populates="empresa")


class Trabajador(MarcasDeAuditoria, Base):
    __tablename__ = "trabajadores"
    id = Id()
    nombre = Column(String(100), index=True)
    apellidos = Column(String(150), index=True)
    dni = Column(String(20), unique=True, index=True)
    tipo_contrato = Column(String(100))
    afp_onp = Column(String(100))
    rol = Column(String(100))  # Medico, Enfermera, etc.

    codigo_trabajador = Column(String(50), unique=True, index=True, nullable=True)
    cargo = Column(String(100), nullable=True)
    fecha_ingreso = Column(String(20), nullable=True)
    fecha_cese = Column(String(20), nullable=True)
    estado_trabajador = Column(String(50), nullable=True)
    subdivision_sede = Column(String(100), nullable=True)
    centro_costo = Column(String(100), nullable=True)
    tipo_calculo_nomina = Column(String(100), nullable=True)
    area = Column(String(150), nullable=True)
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


class SistemaAtencion(MarcasDeAuditoria, Base):
    __tablename__ = "sistemas"
    id = Id()
    nombre = Column(String(100), unique=True, index=True)


class ClasificacionAtencion(MarcasDeAuditoria, Base):
    __tablename__ = "clasificaciones"
    id = Id()
    nombre = Column(String(100))


class Obra(MarcasDeAuditoria, Base):
    """Catalogo de obras / proyectos. Independiente de sistemas y contingencias."""
    __tablename__ = "obras"
    id = Id()
    nombre = Column(String(150), unique=True, index=True)


class DiagnosticoCie10(MarcasDeAuditoria, Base):
    __tablename__ = "diagnosticos_cie10"
    id = Id()
    codigo = Column(String(50), unique=True, index=True)
    descripcion = Column(String(255))
    estado = Column(String(20), default="ACTIVO")


class AtencionMedicamento(Base):
    """Un renglon de la receta de una atencion.

    No lleva las marcas de sincronizacion: viaja embebido dentro de su
    atencion, no como tabla independiente."""
    __tablename__ = "atencion_medicamentos"
    id = Id()
    atencion_id = Column(String(36), ForeignKey("atenciones.id"))
    medicamento_id = Column(String(36), ForeignKey("medicamentos.id"))
    cantidad = Column(Integer, default=1)

    medicamento = relationship("Medicamento")


class Atencion(MarcasDeAuditoria, Base):
    __tablename__ = "atenciones"
    id = Id()
    folio = Column(Integer, unique=True, index=True, nullable=True)  # Ficha N.o, lo asigna el servidor
    fecha = Column(DateTime, default=ahora_utc)

    hora_ingreso = Column(String(10), nullable=True)
    hora_salida = Column(String(10), nullable=True)
    tiempo_topico = Column(String(50), nullable=True)

    edad = Column(String(10), nullable=True)
    residencia = Column(String(200), nullable=True)
    empresa_id = Column(String(36), ForeignKey("empresas.id"), nullable=True)
    cargo = Column(String(100), nullable=True)

    descripcion = Column(Text)  # malestar / anamnesis

    funciones_biologicas = Column(Text, nullable=True)  # JSON
    signos_vitales = Column(Text, nullable=True)        # JSON
    examen_fisico = Column(Text, nullable=True)
    examenes_auxiliares = Column(Text, nullable=True)

    # Los dos siguientes se mantienen por retrocompatibilidad con fichas
    # anteriores a los tres diagnosticos separados.
    codigo_diagnostico = Column(String(100), nullable=True)
    diagnostico = Column(Text, nullable=True)

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

    trabajador = relationship("Trabajador", back_populates="atenciones")
    empresa = relationship("Empresa")
    sistema = relationship("SistemaAtencion")
    clasificacion = relationship("ClasificacionAtencion")
    cita = relationship("Cita")
    personal_salud = relationship("PersonalSalud")
    medicamentos = relationship("AtencionMedicamento", cascade="all, delete-orphan")


class Medicamento(MarcasDeAuditoria, Base):
    __tablename__ = "medicamentos"
    id = Id()
    codigo = Column(String(50), unique=True, index=True)
    nombre = Column(String(150), index=True)
    presentacion = Column(String(100))
    descripcion = Column(Text)
    tipo = Column(String(20), default="MEDICAMENTO")  # MEDICAMENTO, INSUMO, OTROS
    lote = Column(String(50), nullable=True)
    fecha_vencimiento = Column(String(20), nullable=True)
    # Solo lo cambian los movimientos de kardex (ver servicios/stock.py).
    stock_actual = Column(Integer, default=0)
    costo_unitario = Column(Float, default=0.0)


class Kardex(MarcasDeAuditoria, Base):
    """Un movimiento de inventario. Es la unica fuente de verdad del stock:
    cada cambio de `Medicamento.stock_actual` tiene su fila aca."""
    __tablename__ = "kardex"
    id = Id()
    medicamento_id = Column(String(36), ForeignKey("medicamentos.id"))
    fecha = Column(DateTime, default=ahora_utc)
    tipo_movimiento = Column(String(10))  # INGRESO, SALIDA
    cantidad = Column(Integer)
    saldo = Column(Integer)
    lote = Column(String(50), nullable=True)
    fecha_vencimiento = Column(String(20), nullable=True)
    observacion = Column(Text, nullable=True)

    medicamento = relationship("Medicamento")


class PersonalSalud(MarcasDeAuditoria, Base):
    __tablename__ = "personal_salud"
    id = Id()
    nombre = Column(String(100), index=True)
    apellidos = Column(String(150), index=True)
    especialidad = Column(String(100))
    cmp = Column(String(50), unique=True, nullable=True)  # Colegio Medico / de Enfermeria
    telefono = Column(String(50), nullable=True)
    correo = Column(String(150), nullable=True)
    estado = Column(String(50), default="ACTIVO")


class ConflictoSync(Base):
    """Auditoria de sincronizacion: cuando dos dispositivos editan el mismo
    registro sin haberse visto, gana el mas reciente y la version que pierde se
    guarda aqui completa, en vez de desaparecer en silencio."""
    __tablename__ = "conflictos_sync"
    id = Id()
    tabla = Column(String(50), index=True)
    registro_id = Column(String(36), index=True)
    version_perdedora = Column(Text)  # JSON con todos los campos descartados
    version_ganadora_id = Column(String(36), nullable=True)
    dispositivo_origen = Column(String(100), nullable=True)
    resuelto_en = Column(DateTime, default=ahora_utc)


class Cita(MarcasDeAuditoria, Base):
    __tablename__ = "citas"
    id = Id()
    fecha_hora = Column(DateTime)
    motivo = Column(Text, nullable=True)
    estado = Column(String(50), default="PENDIENTE")  # PENDIENTE, CONFIRMADA, ATENDIDA, CANCELADA

    paciente_id = Column(String(36), ForeignKey("trabajadores.id"))  # el paciente es el trabajador
    personal_salud_id = Column(String(36), ForeignKey("personal_salud.id"))

    paciente = relationship("Trabajador")
    personal_salud = relationship("PersonalSalud")


class TipoBotiquin(MarcasDeAuditoria, Base):
    """Plantilla de botiquin: el conjunto estandar de insumos que deberia tener."""
    __tablename__ = "tipos_botiquin"
    id = Id()
    codigo = Column(String(50), unique=True, nullable=True, index=True)
    nombre = Column(String(150), index=True)

    insumos = relationship("TipoBotiquinInsumo", cascade="all, delete-orphan")


class TipoBotiquinInsumo(Base):
    __tablename__ = "tipo_botiquin_insumos"
    id = Id()
    tipo_botiquin_id = Column(String(36), ForeignKey("tipos_botiquin.id"), index=True)
    medicamento_id = Column(String(36), ForeignKey("medicamentos.id"), index=True)
    cantidad = Column(Integer, default=1)

    medicamento = relationship("Medicamento")


class Botiquin(MarcasDeAuditoria, Base):
    """Equipo de emergencia o botiquin, en un area, un vehiculo o una instalacion."""
    __tablename__ = "botiquines"
    id = Id()
    # Sin unique= a proposito, y es el unico codigo del sistema que no lo lleva.
    # La columna se agrego a una tabla que ya existia (migraciones.py), y un
    # ALTER TABLE ADD COLUMN no crea el indice: la base en produccion nunca
    # tuvo esa restriccion. Declararla aqui hacia que una instalacion NUEVA
    # naciera con un esquema mas estricto que el del servidor, y al sincronizar
    # los botiquines que comparten codigo (uno borrado y otro vivo, de dar de
    # baja y volver a crear) chocaban contra el indice: la fila se descartaba
    # como conflicto y el equipo se quedaba sin ese botiquin. La unicidad entre
    # los botiquines VIGENTES la exige el endpoint, que es donde esta la regla.
    codigo = Column(String(50), nullable=True, index=True)
    tipo_botiquin_id = Column(String(36), ForeignKey("tipos_botiquin.id"), nullable=True, index=True)
    tipo_equipo = Column(String(120), index=True)  # botiquin de area, de vehiculo, etc.
    area = Column(String(150), index=True)
    empresa_id = Column(String(36), ForeignKey("empresas.id"), nullable=True, index=True)
    ubicacion = Column(String(250), nullable=True)
    mapa_url = Column(String(500), nullable=True)
    numero_serie_placa = Column(String(100), nullable=True, index=True)  # legado
    vehiculo = Column(String(200), nullable=True, index=True)  # resumen de marca/modelo/serie/placa
    marca = Column(String(100), nullable=True)
    modelo = Column(String(100), nullable=True)
    serie = Column(String(100), nullable=True, index=True)
    placa = Column(String(50), nullable=True, index=True)
    equipo = Column(String(100), index=True)  # botiquin de emergencia, polvorines, refugios
    estado = Column(String(50), default="ACTIVO")
    fecha_creacion = Column(DateTime, default=ahora_utc, index=True)

    empresa = relationship("Empresa")
    tipo_botiquin = relationship("TipoBotiquin")
    productos = relationship("BotiquinProducto", cascade="all, delete-orphan")
    inspecciones = relationship("BotiquinInspeccion", back_populates="botiquin")


class BotiquinProducto(Base):
    """Legado: contenido cargado por botiquin. El estandar actual es
    TipoBotiquin + sus insumos."""
    __tablename__ = "botiquin_productos"
    id = Id()
    botiquin_id = Column(String(36), ForeignKey("botiquines.id"), index=True)
    medicamento_id = Column(String(36), ForeignKey("medicamentos.id"), index=True)
    cantidad = Column(Integer, default=1)

    medicamento = relationship("Medicamento")


class BotiquinInspeccion(MarcasDeAuditoria, Base):
    """Inspeccion de un botiquin, con responsable e insumos registrados."""
    __tablename__ = "botiquin_inspecciones"
    id = Id()
    botiquin_id = Column(String(36), ForeignKey("botiquines.id"), index=True)
    fecha = Column(DateTime, default=ahora_utc, index=True)
    responsable_id = Column(String(36), ForeignKey("personal_salud.id"), nullable=True, index=True)
    observaciones = Column(Text, nullable=True)
    # JSON serializado: lista de rutas relativas (/media/inspecciones/...)
    imagenes = Column(Text, nullable=True)

    botiquin = relationship("Botiquin", back_populates="inspecciones")
    responsable = relationship("PersonalSalud")
    insumos = relationship("BotiquinInspeccionInsumo", cascade="all, delete-orphan")


class BotiquinInspeccionInsumo(Base):
    __tablename__ = "botiquin_inspeccion_insumos"
    id = Id()
    inspeccion_id = Column(String(36), ForeignKey("botiquin_inspecciones.id"), index=True)
    medicamento_id = Column(String(36), ForeignKey("medicamentos.id"), index=True)
    cantidad = Column(Integer, default=1)
    estado = Column(String(50), default="BUENO")  # BUENO, REGULAR, MALO, VENCIDO, FALTANTE
    reposicion = Column(String(10), default="NO")  # SI | NO

    medicamento = relationship("Medicamento")


class EventoAdmin(Base):
    """Traza de lo que hacen los administradores sobre las cuentas.

    NO entra en SYNCABLE_MODELS a proposito: es del servidor. Repartirla a cada
    PC expondria en todas partes quien administra que, y no aporta nada al
    trabajo offline.
    """
    __tablename__ = "eventos_admin"
    id = Id()
    # Se guarda el nombre y no una clave foranea: si algun dia se borra al
    # usuario, la traza de lo que hizo debe sobrevivir.
    actor = Column(String(150))
    accion = Column(String(60), index=True)
    objetivo = Column(String(150))
    objetivo_id = Column(String(36))
    detalle = Column(Text, default="")
    ip = Column(String(60), default="")
    creado_en = Column(DateTime, default=ahora_utc, index=True)
