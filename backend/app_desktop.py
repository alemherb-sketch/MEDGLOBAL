import os


def _cargar_env_local():
    """Carga un .env junto al ejecutable a variables de entorno, sin pisar
    las que ya esten seteadas (asi las pruebas locales con variables reales
    del sistema operativo siguen funcionando igual). Existe porque
    sync_client.py lee SYNC_SERVER_URL/USERNAME/PASSWORD de os.environ al
    importarse, y un .exe de cx_Freeze no carga nada de un .env por su
    cuenta -- este es el unico mecanismo para configurar la sync sin pedirle
    a cada PC de la clinica que edite variables de entorno de Windows."""
    if not os.path.exists(".env"):
        return
    with open(".env", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


_cargar_env_local()

import logging

import uvicorn
import webbrowser
import threading
import time
from main import app
import sync_client

# Configurable para poder levantar una segunda instancia (por ejemplo, para
# revisar un problema de sincronizacion) sin cerrar la que esta en uso.
PUERTO = int(os.getenv("MEDGLOBAL_PORT", "8000"))


def open_browser():
    # Esperar un poco a que arranque FastAPI
    time.sleep(2)
    webbrowser.open(f"http://127.0.0.1:{PUERTO}")

if __name__ == "__main__":
    # Los avisos de sync_client (por que fallo una conexion, por ejemplo) se
    # escriben con logging: sin esta configuracion no aparecian en la consola
    # de la aplicacion y no habia forma de diagnosticar nada desde la PC.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    # Iniciar hilo para abrir el navegador
    threading.Thread(target=open_browser, daemon=True).start()

    # Fase 3: sincronizacion en segundo plano con el servidor central.
    # No hace nada si SYNC_SERVER_URL/SYNC_USERNAME/SYNC_PASSWORD no estan
    # configurados (variables de entorno) — sin eso la app sigue siendo
    # 100% local, igual que siempre.
    sync_client.iniciar_hilo_sincronizacion()

    # Iniciar servidor FastAPI
    uvicorn.run(app, host="127.0.0.1", port=PUERTO, log_level="warning")
