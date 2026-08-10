import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

import rutas

# Obtener URL de la variable de entorno, si no existe usa sqlite.
# rutas.datos() decide donde: junto al .exe en la instalacion de carpeta, o la
# carpeta de datos del usuario cuando es el ejecutable unico. Fuera del
# ejecutable congelado devuelve "medglobal.db" a secas, o sea el directorio
# actual, igual que siempre.
DATABASE_URL = os.getenv("DATABASE_URL") or ("sqlite:///" + rutas.datos("medglobal.db"))

# Si la URL es de render postgres://, SQLAlchemy necesita postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
