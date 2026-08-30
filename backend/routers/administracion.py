"""Administracion de cuentas (la usa el panel del ERP).

Antes los usuarios se creaban con scripts sueltos en el servidor
(crear_admin.py, cambiar_password.py) y no habia forma de verlos ni
bloquearlos a distancia.

Bloquear surte efecto de inmediato: authenticate_user rechaza a quien no este
ACTIVO y get_current_user lo revalida en cada peticion, asi que ademas corta
las sesiones que ya estuvieran abiertas.
"""
from typing import List

from fastapi import APIRouter, HTTPException, Request

import auth
import models
import schemas
from dependencias import AdminActual, RequiereAdmin, SesionDB

router = APIRouter(prefix="/admin", tags=["administracion"], dependencies=[RequiereAdmin])

LARGO_MINIMO_PASSWORD = 8


def _registrar_evento(db, request: Request, actor, accion: str,
                      objetivo: str = "", objetivo_id: str = "", detalle: str = "") -> None:
    db.add(models.EventoAdmin(
        actor=getattr(actor, "username", None) or "sistema",
        accion=accion,
        objetivo=objetivo,
        objetivo_id=objetivo_id,
        detalle=detalle,
        ip=(request.client.host if request and request.client else ""),
    ))


def _validar_password(password: str) -> None:
    if len(password or "") < LARGO_MINIMO_PASSWORD:
        raise HTTPException(
            status_code=400,
            detail=f"La contraseña debe tener al menos {LARGO_MINIMO_PASSWORD} caracteres.",
        )


@router.get("/usuarios", response_model=List[schemas.Usuario])
def listar_usuarios(db: SesionDB):
    return db.query(models.Usuario).order_by(models.Usuario.username).all()


@router.post("/usuarios", response_model=schemas.Usuario, status_code=201)
def crear_usuario(datos: schemas.UsuarioAdminCreate, request: Request, db: SesionDB, actor: AdminActual):
    if db.query(models.Usuario).filter(models.Usuario.username == datos.username).first():
        raise HTTPException(status_code=400, detail="Ese nombre de usuario ya existe.")
    _validar_password(datos.password)

    usuario = models.Usuario(
        username=datos.username,
        nombre=datos.nombre,
        rol=(datos.rol or "ESTANDAR").upper(),
        estado=(datos.estado or "ACTIVO").upper(),
        password_hash=auth.hash_password(datos.password),
    )
    db.add(usuario)
    _registrar_evento(db, request, actor, "crear_usuario",
                      objetivo=usuario.username, objetivo_id=usuario.id,
                      detalle=f"rol={usuario.rol} estado={usuario.estado}")
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/usuarios/{usuario_id}", response_model=schemas.Usuario)
def editar_usuario(usuario_id: str, datos: schemas.UsuarioAdminUpdate, request: Request,
                   db: SesionDB, actor: AdminActual):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    # Candado contra dejarse fuera: un administrador no puede bloquearse ni
    # quitarse el rol a si mismo.
    if usuario.id == actor.id:
        if datos.estado and datos.estado.upper() != "ACTIVO":
            raise HTTPException(status_code=400, detail="No puede bloquear su propia cuenta.")
        if datos.rol and datos.rol.upper() != "ADMIN":
            raise HTTPException(status_code=400, detail="No puede quitarse el rol de administrador.")

    cambios = []
    if datos.nombre is not None and datos.nombre != usuario.nombre:
        usuario.nombre = datos.nombre
        cambios.append("nombre")
    if datos.rol is not None and datos.rol.upper() != usuario.rol:
        usuario.rol = datos.rol.upper()
        cambios.append(f"rol={usuario.rol}")
    if datos.estado is not None and datos.estado.upper() != usuario.estado:
        usuario.estado = datos.estado.upper()
        cambios.append(f"estado={usuario.estado}")
    # Vacio o ausente = no tocar la contrasena; si no, editar el nombre
    # obligaria a reescribirla en cada cambio.
    if datos.password:
        _validar_password(datos.password)
        usuario.password_hash = auth.hash_password(datos.password)
        cambios.append("contraseña")

    if not cambios:
        return usuario

    # El conteo corre con los cambios ya pendientes en la sesion (autoflush):
    # si esta edicion deja el sistema sin ADMIN activo, nadie podria volver a
    # administrarlo.
    admins_activos = db.query(models.Usuario).filter(
        models.Usuario.rol == "ADMIN", models.Usuario.estado == "ACTIVO"
    ).count()
    if admins_activos == 0:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="No puede dejar el sistema sin ningún administrador activo.",
        )

    _registrar_evento(db, request, actor, "editar_usuario",
                      objetivo=usuario.username, objetivo_id=usuario.id,
                      detalle=", ".join(cambios))
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/actividad", response_model=List[schemas.EventoAdmin])
def actividad(db: SesionDB, limit: int = 100):
    return (
        db.query(models.EventoAdmin)
        .order_by(models.EventoAdmin.creado_en.desc())
        .limit(min(max(limit, 1), 500))
        .all()
    )
