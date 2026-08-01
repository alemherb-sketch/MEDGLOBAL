import logging
import os
import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import models
from database import get_db

logger = logging.getLogger(__name__)

# Archivo donde se guarda la clave generada automaticamente cuando no hay
# SECRET_KEY en el entorno. Va junto a la BD (mismo directorio de trabajo que
# medglobal.db y sync_cursor.json) y NO se versiona.
_SECRET_KEY_FILE = "secret_key.txt"


def _obtener_secret_key() -> str:
    """La clave con la que se firman los tokens de sesion.

    Antes esta funcion no existia y habia un valor por defecto fijo escrito en
    el codigo. Como ese valor esta en el repositorio, cualquiera que lo leyera
    podia firmarse un token de administrador valido contra cualquier
    despliegue que no definiera SECRET_KEY -- y ningun despliegue la definia.

    Orden de resolucion:
      1. SECRET_KEY del entorno (lo correcto en el VPS y en Render).
      2. Una clave aleatoria persistida en disco junto a la BD. Esto es para
         el .exe de escritorio, que no tiene forma comoda de recibir variables
         de entorno: la primera vez se genera sola y despues se reutiliza, asi
         que las sesiones sobreviven a los reinicios de la app.
    Ya no hay un tercer caso: nunca se cae a una constante conocida.
    """
    del_entorno = os.getenv("SECRET_KEY")
    if del_entorno:
        return del_entorno

    if os.path.exists(_SECRET_KEY_FILE):
        with open(_SECRET_KEY_FILE, encoding="utf-8") as f:
            guardada = f.read().strip()
        if guardada:
            return guardada

    nueva = secrets.token_urlsafe(64)
    try:
        with open(_SECRET_KEY_FILE, "w", encoding="utf-8") as f:
            f.write(nueva)
        logger.warning(
            "SECRET_KEY no esta definida: se genero una clave nueva en %s. "
            "En el servidor define SECRET_KEY como variable de entorno.",
            os.path.abspath(_SECRET_KEY_FILE),
        )
    except OSError:
        # Filesystem de solo lectura: la app arranca igual, pero cada
        # reinicio invalida las sesiones abiertas. Preferible a firmar con
        # una clave que este publicada en el repositorio.
        logger.warning(
            "SECRET_KEY no esta definida y no se pudo guardar una clave en disco. "
            "Se usara una clave temporal: las sesiones se cerraran al reiniciar. "
            "Define SECRET_KEY como variable de entorno."
        )
    return nueva


SECRET_KEY = _obtener_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 horas

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models.Usuario).filter(models.Usuario.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    if user.estado != "ACTIVO":
        return None
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesión",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.Usuario).filter(models.Usuario.username == username).first()
    if user is None or user.estado != "ACTIVO":
        raise credentials_exception
    return user


def require_admin(current_user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
    """Exige rol ADMIN.

    Hasta ahora ningun endpoint distinguia el rol: bastaba una sesion valida
    para hacer cualquier cosa. Para administrar cuentas ajenas eso no sirve,
    porque cualquier usuario ESTANDAR podria bloquear al resto o darse ADMIN
    a si mismo.
    """
    if (current_user.rol or "").upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador.",
        )
    return current_user
