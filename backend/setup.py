"""Empaqueta la aplicacion de escritorio (MEDGLOBAL.exe) con cx_Freeze.

Antes de correr esto hay que compilar el frontend con la URL del API VACIA y
copiar el resultado a backend/static, para que el .exe hable con su propio
servidor local en vez de con el de internet:

    cd frontend && VITE_API_URL='' npm run build
    rm -rf backend/static && cp -r frontend/dist backend/static

Despues:

    cd backend && python setup.py build
"""
from cx_Freeze import setup, Executable

build_exe_options = {
    # cx_Freeze detecta la mayoria de las dependencias solo, pero estas hay que
    # nombrarlas: se cargan de forma indirecta y si faltan el .exe compila bien
    # y recien falla al usarlo.
    #   requests -> sync_client (sincronizacion con el servidor)
    #   bcrypt, jose -> login
    #   pandas, openpyxl -> importacion de medicamentos y CIE-10 desde Excel
    "packages": [
        "uvicorn", "fastapi", "sqlalchemy", "pydantic", "starlette",
        "webbrowser", "threading", "sqlite3", "logging",
        "requests", "bcrypt", "jose", "pandas", "openpyxl",
    ],
    # medglobal.db es la base inicial que se lleva la instalacion nueva.
    # .env lleva la configuracion de sincronizacion (SYNC_SERVER_URL, usuario
    # y contrasena); app_desktop.py lo lee al arrancar.
    "include_files": ["static/", "medglobal.db", ".env"],
    "excludes": ["tkinter", "test", "unittest"],
}

# base=None deja la consola visible a proposito: es la forma que tiene el
# personal de cerrar el servidor local, y ahi se ven los mensajes de error si
# algo falla al arrancar.
setup(
    name="MEDGLOBAL",
    version="1.1",
    description="Sistema Medglobal Local",
    options={"build_exe": build_exe_options},
    executables=[Executable("app_desktop.py", base=None, target_name="MEDGLOBAL.exe", icon=None)],
)
