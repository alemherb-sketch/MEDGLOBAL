import uvicorn
import webbrowser
import threading
import time
from main import app
import sync_client

def open_browser():
    # Esperar un poco a que arranque FastAPI
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    # Iniciar hilo para abrir el navegador
    threading.Thread(target=open_browser, daemon=True).start()

    # Fase 3: sincronizacion en segundo plano con el servidor central.
    # No hace nada si SYNC_SERVER_URL/SYNC_USERNAME/SYNC_PASSWORD no estan
    # configurados (variables de entorno) — sin eso la app sigue siendo
    # 100% local, igual que siempre.
    sync_client.iniciar_hilo_sincronizacion()

    # Iniciar servidor FastAPI
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
