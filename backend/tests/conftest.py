"""Configuracion comun de los tests.

Cada corrida usa una BD SQLite nueva en un directorio temporal. La variable
DATABASE_URL se define ANTES de importar database/models porque database.py la
lee al importarse, no al abrir una sesion.
"""
import os
import sys
import tempfile

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND)

_tmp = tempfile.mkdtemp(prefix="medglobal-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp, "test.db").replace("\\", "/")
os.environ["SECRET_KEY"] = "clave-solo-para-tests"
# main.py monta StaticFiles sobre ./static y lo crea si no existe: que lo haga
# en el temporal y no ensucie el arbol del repo.
os.chdir(_tmp)

import pytest

import auth  # noqa: E402
import models  # noqa: E402
from database import SessionLocal  # noqa: E402


@pytest.fixture
def db():
    sesion = SessionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


@pytest.fixture
def client():
    """TestClient autenticado contra una BD vacia."""
    from fastapi.testclient import TestClient
    import main

    sesion = SessionLocal()
    # Cada test arranca de cero: se borran las filas de la corrida anterior.
    for modelo in (models.AtencionMedicamento, models.Kardex, models.Atencion,
                   models.Trabajador, models.Medicamento, models.SistemaAtencion,
                   models.ClasificacionAtencion, models.Empresa, models.Usuario):
        sesion.query(modelo).delete()
    sesion.add(models.Usuario(
        username="tester", password_hash=auth.hash_password("secreto"),
        nombre="Tester", rol="ADMIN", estado="ACTIVO",
    ))
    sesion.commit()
    sesion.close()

    c = TestClient(main.app)
    token = c.post("/auth/login", data={"username": "tester", "password": "secreto"}).json()["access_token"]
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c
