"""Dependencias compartidas por todos los routers.

`SesionDB` y `RequiereSesion` existen para que la firma de cada endpoint diga
lo que hace el endpoint y no repita el cableado de FastAPI. Antes cada una de
las ~70 funciones arrastraba

    db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)

y `current_user` casi nunca se usaba: su unico efecto era exigir sesion. Eso
se declara ahora una sola vez por router (`dependencies=[RequiereSesion]`), lo
que ademas evita el fallo silencioso de agregar un endpoint nuevo y olvidarse
de pedir autenticacion.
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

import auth
import models
from database import get_db

# Sesion de base de datos.
SesionDB = Annotated[Session, Depends(get_db)]

# Para los routers: exige sesion valida sin agregar parametros al endpoint.
RequiereSesion = Depends(auth.get_current_user)
RequiereAdmin = Depends(auth.require_admin)

# Para los pocos endpoints que SI necesitan saber quien es el usuario.
UsuarioActual = Annotated[models.Usuario, Depends(auth.get_current_user)]
AdminActual = Annotated[models.Usuario, Depends(auth.require_admin)]
