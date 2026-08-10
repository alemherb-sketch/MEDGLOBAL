"""Donde vive cada archivo de la aplicacion.

Hay dos clases de archivos y mezclarlas hace perder datos:

  - RECURSOS: lo que viene DENTRO del programa y nunca cambia -- el frontend
    compilado (static/), la base inicial y el .env de fabrica. En el ejecutable
    unico esto se descomprime en una carpeta temporal en cada arranque y se
    borra al cerrar: escribir ahi es tirar la informacion a la basura.

  - DATOS: lo que la PC va escribiendo y no se puede perder -- medglobal.db,
    secret_key.txt, sync_cursor.json y respaldos/.

Hasta ahora los dos eran "el directorio actual", y funcionaba porque el .exe
viajaba con su carpeta al lado y siempre se ejecutaba desde ahi. Con un
ejecutable unico eso deja de ser cierto por partida doble: los recursos estan
en el temporal y el directorio actual es aquel desde donde se hizo doble clic
(el Escritorio, tipicamente), que no es lugar para dejar la base de datos.

Fuera del ejecutable congelado -- en desarrollo y en las pruebas -- las dos
funciones devuelven la ruta relativa tal cual, o sea exactamente el
comportamiento anterior: todo relativo al directorio actual.
"""
import os
import sys


def _es_ejecutable_unico():
    """PyInstaller en modo un-solo-archivo: _MEIPASS es la carpeta temporal
    donde quedo descomprimido el contenido del .exe."""
    return hasattr(sys, "_MEIPASS")


def _elegir_carpeta_recursos():
    if _es_ejecutable_unico():
        return sys._MEIPASS
    if getattr(sys, "frozen", False):
        # Congelado en carpeta (cx_Freeze): los recursos estan junto al .exe.
        return os.path.dirname(sys.executable)
    return ""


def _elegir_carpeta_datos():
    # Valvula de escape explicita, util para revisar una instalacion sin
    # tocarla: MEDGLOBAL_DATOS=C:\prueba MEDGLOBAL.exe
    del_entorno = os.getenv("MEDGLOBAL_DATOS")
    if del_entorno:
        return del_entorno

    if not getattr(sys, "frozen", False):
        return ""

    junto_al_exe = os.path.dirname(sys.executable)
    # Una instalacion que ya existe manda siempre. Asi el ejecutable nuevo
    # sigue usando la base que esa PC ya tiene al lado, sin migrar nada, y
    # tambien alcanza con poner el .exe junto a un medglobal.db para llevarse
    # una instalacion entera en un pendrive.
    if os.path.exists(os.path.join(junto_al_exe, "medglobal.db")):
        return junto_al_exe

    if _es_ejecutable_unico():
        # Un solo archivo y sin base al lado: la informacion va a una carpeta
        # estable del usuario. No puede quedar donde este el .exe, porque ese
        # sitio puede ser el Escritorio o una carpeta de descargas.
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "MEDGLOBAL")

    return junto_al_exe


CARPETA_RECURSOS = _elegir_carpeta_recursos()
CARPETA_DATOS = _elegir_carpeta_datos()


def recurso(nombre):
    """Ruta de un archivo que viene empaquetado (solo lectura)."""
    return os.path.join(CARPETA_RECURSOS, nombre) if CARPETA_RECURSOS else nombre


def datos(nombre):
    """Ruta de un archivo que la aplicacion escribe. Crea la carpeta si hace
    falta: en el primer arranque del ejecutable unico todavia no existe."""
    if not CARPETA_DATOS:
        return nombre
    os.makedirs(CARPETA_DATOS, exist_ok=True)
    return os.path.join(CARPETA_DATOS, nombre)
