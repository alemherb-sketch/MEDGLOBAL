"""Inicio de sesion y datos del usuario en curso."""
from fastapi import APIRouter, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends

import auth
import schemas
from dependencias import SesionDB, UsuarioActual

router = APIRouter(prefix="/auth", tags=["autenticacion"])


@router.post("/login", response_model=schemas.Token)
def login(db: SesionDB, form_data: OAuth2PasswordRequestForm = Depends()):
    usuario = auth.authenticate_user(db, form_data.username, form_data.password)
    if not usuario:
        raise HTTPException(
            status_code=401,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": auth.create_access_token(usuario.username), "token_type": "bearer"}


@router.get("/me", response_model=schemas.Usuario)
def usuario_en_sesion(current_user: UsuarioActual):
    return current_user
