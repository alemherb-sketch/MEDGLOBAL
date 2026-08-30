"""Aplicacion MEDGLOBAL: armado del servidor.

Aca solo se construye la aplicacion -- base de datos, CORS, licencia de
escritorio, routers y frontend compilado. La logica de cada dominio vive en
routers/ y servicios/.

El mismo `app` sirve los dos productos:
  - la web del VPS (Postgres, varios usuarios, sin licencia)
  - el instalable de escritorio (SQLite local, licencia por PC, sincronizacion
    manual con el VPS)
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

import licencias
import migraciones
import models
import rutas
from database import engine
from routers import (
    administracion,
    atenciones,
    autenticacion,
    botiquin,
    catalogos,
    inventario,
    licencias_api,
    reportes,
    sincronizacion,
)

# --- Base de datos ----------------------------------------------------------
models.Base.metadata.create_all(bind=engine)
# create_all no toca las tablas que ya existen: las columnas agregadas despues
# se aplican aparte, en cada arranque (ver migraciones.py).
migraciones.aplicar(engine)

app = FastAPI(title="MEDGLOBAL API")


# --- Licencia de escritorio -------------------------------------------------
# En el VPS (sin MEDGLOBAL_ESCRITORIO) no bloquea nada. En el instalable, sin
# licencia valida solo pasan las rutas de activacion y los assets del frontend.

class MiddlewareLicenciaEscritorio(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not licencias.licencia_permite_request(request.url.path):
            return JSONResponse(
                {
                    "detail": "Licencia de escritorio no activa en esta PC.",
                    "motivo": "sin_licencia",
                    "machine_id": licencias.machine_id(),
                },
                status_code=403,
            )
        return await call_next(request)


app.add_middleware(MiddlewareLicenciaEscritorio)


# --- CORS -------------------------------------------------------------------
# ALLOWED_ORIGINS es una lista separada por comas.
#
# El default NO es "*": con allow_credentials=True Starlette refleja el Origin
# que venga, asi que cualquier pagina podria llamar a este API desde el
# navegador de un usuario logueado. El default es la lista de origenes que el
# sistema realmente usa; el .exe sirve el frontend desde su propio origen
# (127.0.0.1:8000) y no depende de esta lista.
_ORIGENES_POR_DEFECTO = [
    "https://medglobal.erpgestapp.com",
    "https://medglobal.erpgest.com.pe",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
_configurado = os.getenv("ALLOWED_ORIGINS")
if _configurado is None:
    _origenes = _ORIGENES_POR_DEFECTO
elif _configurado.strip() == "*":
    _origenes = ["*"]
else:
    _origenes = [o.strip() for o in _configurado.split(",") if o.strip()]

# Se agrega DESPUES del middleware de licencia para quedar por fuera de el: el
# ultimo middleware agregado es el mas externo. Asi hasta un 403 por licencia
# sale con las cabeceras CORS y el navegador puede leer el motivo, en vez de
# mostrar un error de CORS que no explica nada.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origenes,
    # La sesion viaja en la cabecera Authorization (token en localStorage), no
    # en cookies: el navegador nunca necesita mandar credenciales de origen
    # cruzado. Dejarlo en False es lo que hace seguro un allow_origins=["*"]
    # configurado a proposito.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints --------------------------------------------------------------
app.include_router(licencias_api.router)
app.include_router(autenticacion.router)
app.include_router(sincronizacion.router)
app.include_router(catalogos.router)
app.include_router(atenciones.router)
app.include_router(inventario.router)
app.include_router(botiquin.router)
app.include_router(botiquin.router_publico)
app.include_router(reportes.router)
app.include_router(administracion.router)


# --- Frontend compilado -----------------------------------------------------
# index.html NUNCA se cachea; los assets, para siempre.
#
# Vite le pone un hash al nombre de cada asset (index-DC3vAq3r.js): ese archivo
# no cambia jamas y se puede cachear indefinidamente. index.html es lo
# contrario: es el unico que dice cual es el hash vigente, y si el navegador se
# lo queda cacheado sigue pidiendo el bundle anterior. Eso convertia cada
# actualizacion del .exe en un problema por PC: la aplicacion quedaba
# actualizada en disco pero la pantalla seguia mostrando la version vieja hasta
# que alguien hiciera Ctrl+Shift+R, sin ninguna pista de que hacia falta.
CACHE_INDEX = "no-store, no-cache, must-revalidate"
CACHE_ASSETS = "public, max-age=31536000, immutable"


class ArchivosEstaticos(StaticFiles):
    def file_response(self, full_path, stat_result, scope, status_code=200):
        respuesta = super().file_response(full_path, stat_result, scope, status_code)
        es_index = str(full_path).replace("\\", "/").endswith("/index.html")
        respuesta.headers["Cache-Control"] = CACHE_INDEX if es_index else CACHE_ASSETS
        return respuesta


# El frontend compilado viaja DENTRO del programa: en el ejecutable unico esta
# en la carpeta temporal que arma PyInstaller, no junto al .exe. Ver rutas.py.
CARPETA_STATIC = rutas.recurso("static")
os.makedirs(CARPETA_STATIC, exist_ok=True)
# El montaje en "/" va ULTIMO: si no, se traga las rutas de los routers.
app.mount("/", ArchivosEstaticos(directory=CARPETA_STATIC, html=True), name="static")


# Prefijos que son API pura y nunca rutas del navegador. No se puede
# generalizar a «toda ruta declarada»: /atenciones, /empresas y casi todas las
# demas son a la vez endpoint del API y pantalla del frontend, asi que ahi el
# 404 tiene que seguir cayendo en index.html.
PREFIJOS_SOLO_API = ("/api", "/admin/", "/sync/", "/licencias/", "/auth/", "/media/")


@app.exception_handler(404)
async def manejar_404(request, exc):
    """Un 404 del API responde JSON; cualquier otra ruta cae en index.html,
    porque el ruteo del frontend es del lado del navegador."""
    if request.url.path.startswith(PREFIJOS_SOLO_API):
        return JSONResponse({"detail": getattr(exc, "detail", "Not Found")}, status_code=404)
    return FileResponse(
        os.path.join(CARPETA_STATIC, "index.html"),
        headers={"Cache-Control": CACHE_INDEX},
    )
