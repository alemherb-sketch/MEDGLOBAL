"""Entrada de la aplicacion de ESCRITORIO MEDGLOBAL.

No abre el navegador: muestra una ventana nativa de Windows (WebView2 /
Edge embebido) con la misma interfaz y logica de la version web.

Arquitectura:
  - Servidor local solo en 127.0.0.1 (API + UI compilada + SQLite offline)
  - Ventana de escritorio (pywebview) que consume ese servidor local
  - Sincronizacion manual con el VPS (mismo protocolo que la web)
  - Licencias por PC

No se usa Flask: reescribir toda la API en Flask duplicaria el trabajo y
perderia funcionalidad. FastAPI ya expone todas las rutas de la web; la
ventana embebida es lo que convierte el producto en app de escritorio
instalable (.exe).
"""
from __future__ import annotations

import logging
import os
import shutil
import socket
import sys
import threading
import time

import rutas


def _leer_env(ruta):
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def _cargar_env_local():
    """Sync y opciones de escritorio desde .env de datos y/o empaquetado."""
    _leer_env(rutas.datos(".env"))
    _leer_env(rutas.recurso(".env"))


def _preparar_base_inicial():
    destino = rutas.datos("medglobal.db")
    if os.path.exists(destino):
        return
    semilla = rutas.recurso("medglobal-inicial.db")
    if not os.path.exists(semilla):
        return
    parcial = destino + ".parcial"
    shutil.copyfile(semilla, parcial)
    os.replace(parcial, destino)


def _configurar_log():
    log_path = rutas.datos("medglobal_escritorio.log")
    handlers = [logging.FileHandler(log_path, encoding="utf-8")]
    # Consola solo si se pidio modo debug o si no estamos congelados.
    if os.getenv("MEDGLOBAL_CONSOLA", "").strip() in ("1", "true", "True") or not getattr(sys, "frozen", False):
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    return log_path


def _puerto_libre(preferido: int) -> int:
    """Usa el puerto preferido si esta libre; si no, elige uno automatico."""
    for puerto in (preferido, *range(preferido + 1, preferido + 20)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", puerto))
                return puerto
            except OSError:
                continue
    raise RuntimeError(f"No hay puertos libres cerca de {preferido}")


def _esperar_servidor(host: str, port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def _url_inicial(puerto: int) -> str:
    import licencias

    estado = licencias.estado_licencia()
    if estado.get("requerido") and not estado.get("valida"):
        return f"http://127.0.0.1:{puerto}/#/activar-licencia"
    return f"http://127.0.0.1:{puerto}/"


def _mostrar_error(titulo: str, mensaje: str):
    """Cuadro de error nativo de Windows; fallback a print."""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, mensaje, titulo, 0x10)
    except Exception:
        print(f"{titulo}: {mensaje}", file=sys.stderr)


def _bloquear_segunda_instancia():
    """Evita dos ventanas / dos servidores locales a la vez (Windows)."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetLastError(0)
        handle = kernel32.CreateMutexW(None, False, "Local\\MEDGLOBAL_Escritorio_Mutex")
        # ERROR_ALREADY_EXISTS = 183
        if kernel32.GetLastError() == 183:
            return False
        return handle
    except Exception:
        return None


# --- Arranque: entorno y recursos antes de importar main/database ---
os.environ.setdefault("MEDGLOBAL_ESCRITORIO", "1")
_cargar_env_local()
_preparar_base_inicial()

import licencias  # noqa: E402
import sync_client  # noqa: E402
from main import app  # noqa: E402


def _iniciar_servidor(host: str, port: int):
    import traceback
    import uvicorn

    logger = logging.getLogger("medglobal.escritorio")
    try:
        # En .exe sin consola (windowed) sys.stdout/stderr son None. Uvicorn
        # configura un formatter con ColorFormatter que llama isatty() y cae:
        #   AttributeError: 'NoneType' object has no attribute 'isatty'
        # Resultado: el motor no arranca y el usuario ve el MessageBox de error.
        if sys.stdout is None or not hasattr(sys.stdout, "isatty"):
            sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")
        if sys.stderr is None or not hasattr(sys.stderr, "isatty"):
            sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="replace")

        # log_config=None: no usar el dictConfig de uvicorn (ColorFormatter).
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="warning",
            access_log=False,
            log_config=None,
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        # Hilo secundario: no instalar signal handlers (solo el hilo principal puede).
        server.install_signal_handlers = False
        _iniciar_servidor.server = server  # type: ignore[attr-defined]
        logger.info("uvicorn: escuchando en %s:%s", host, port)
        server.run()
        logger.info("uvicorn: termino")
    except Exception:
        logger.exception("uvicorn: fallo al arrancar el motor local")
        try:
            with open(rutas.datos("medglobal_crash.txt"), "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except OSError:
            pass


def _abrir_ventana_escritorio(url: str) -> int:
    """Ventana nativa de escritorio (WebView2 embebido). No abre Chrome/Edge del usuario."""
    try:
        import webview
    except ImportError:
        _mostrar_error(
            "MEDGLOBAL",
            "Falta el componente de ventana de escritorio (pywebview).\n"
            "Instale con: pip install pywebview\n"
            "o reconstruya el instalable con desktop\\build_escritorio.ps1",
        )
        return 2

    ancho = int(os.getenv("MEDGLOBAL_ANCHO", "1280"))
    alto = int(os.getenv("MEDGLOBAL_ALTO", "800"))

    window = webview.create_window(
        title="MEDGLOBAL",
        url=url,
        width=ancho,
        height=alto,
        min_size=(960, 600),
        confirm_close=False,
        text_select=True,
    )

    def _al_cerrar():
        server = getattr(_iniciar_servidor, "server", None)
        if server is not None:
            server.should_exit = True

    try:
        window.events.closed += _al_cerrar
    except Exception:
        pass

    # Edge Chromium (WebView2) en Windows; si no hay runtime, pywebview avisa.
    webview.start(gui="edgechromium", debug=os.getenv("MEDGLOBAL_DEBUG") == "1")
    _al_cerrar()
    return 0


def main() -> int:
    # Necesario en ejecutables PyInstaller en Windows (hilos / multiproceso).
    import multiprocessing

    multiprocessing.freeze_support()

    # En Python 3.8+ Windows, el loop Proactor a veces rompe uvicorn empaquetado.
    if sys.platform == "win32":
        try:
            import asyncio

            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

    log_path = _configurar_log()
    logger = logging.getLogger("medglobal.escritorio")

    mutex = _bloquear_segunda_instancia()
    if mutex is False:
        _mostrar_error(
            "MEDGLOBAL",
            "MEDGLOBAL ya se esta ejecutando en esta PC.\n"
            "Cierre la ventana anterior antes de abrir otra.",
        )
        return 1

    preferido = int(os.getenv("MEDGLOBAL_PORT", "8000"))
    try:
        puerto = _puerto_libre(preferido)
    except RuntimeError as e:
        _mostrar_error("MEDGLOBAL", str(e))
        return 1

    os.environ["MEDGLOBAL_PORT"] = str(puerto)
    host = "127.0.0.1"

    logger.info("Iniciando MEDGLOBAL Escritorio")
    logger.info("Datos: %s", rutas.CARPETA_DATOS or os.getcwd())
    logger.info("Log: %s", log_path)
    logger.info("Machine ID: %s", licencias.machine_id())
    logger.info("Puerto local: %s", puerto)

    sync_client.preparar_sincronizacion_manual()

    hilo = threading.Thread(
        target=_iniciar_servidor,
        args=(host, puerto),
        name="medglobal-uvicorn",
        daemon=True,
    )
    hilo.start()

    if not _esperar_servidor(host, puerto, timeout=45.0):
        crash = rutas.datos("medglobal_crash.txt")
        extra = ""
        if os.path.exists(crash):
            try:
                with open(crash, encoding="utf-8") as f:
                    extra = "\n\n" + f.read()[:800]
            except OSError:
                pass
        _mostrar_error(
            "MEDGLOBAL",
            "No se pudo iniciar el motor local de la aplicacion.\n"
            f"Revise el log: {log_path}"
            + (f"\n\nDetalle:{extra}" if extra else ""),
        )
        return 1

    url = _url_inicial(puerto)
    logger.info("Abriendo ventana de escritorio: %s", url)

    # Valvula: MEDGLOBAL_MODO=navegador fuerza el comportamiento viejo (solo
    # diagnostico). Por defecto es siempre ventana de escritorio.
    if os.getenv("MEDGLOBAL_MODO", "escritorio").strip().lower() in ("navegador", "browser"):
        import webbrowser

        webbrowser.open(url)
        try:
            while hilo.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        return 0

    return _abrir_ventana_escritorio(url)


if __name__ == "__main__":
    raise SystemExit(main())
