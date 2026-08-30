"""Licencias de la app de escritorio. No afectan al API web del VPS."""
from fastapi import APIRouter
from pydantic import BaseModel

import licencias
from dependencias import RequiereAdmin

router = APIRouter(prefix="/licencias", tags=["licencias"])


class ActivacionBody(BaseModel):
    codigo: str


@router.get("/estado")
def estado():
    """Estado de la licencia en esta instalacion.

    Publico: la pantalla de activacion lo consulta ANTES del login, porque sin
    licencia no se puede iniciar sesion."""
    return licencias.estado_licencia()


@router.post("/activar")
def activar(body: ActivacionBody):
    """Activa un codigo en esta PC. Sin autenticacion de usuario por la misma
    razon: sin licencia no hay login posible."""
    return licencias.activar(body.codigo)


@router.post("/desactivar", dependencies=[RequiereAdmin])
def desactivar():
    """Quita la licencia local (solo ADMIN, para mover la instalacion de PC)."""
    licencias.borrar_licencia()
    return {"ok": True, "detalle": "Licencia desactivada en esta PC."}
