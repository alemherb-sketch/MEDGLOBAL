"""Donde termina cada archivo segun como se ejecute la aplicacion.

Estas reglas deciden si la informacion de una PC sobrevive o no. El caso que
importa es el ejecutable unico: PyInstaller descomprime el programa en una
carpeta temporal que borra al cerrar, asi que escribir la base ahi seria
perderla entera en cada cierre.
"""
import os
import sys
import tempfile

import rutas


def _recargar(monkeypatch, frozen=False, meipass=None, exe=None, datos_env=None,
              local_appdata=None):
    """rutas.py resuelve las carpetas al importarse; para probar los distintos
    escenarios hay que recalcularlas con sys y el entorno preparados.

    local_appdata se redirige siempre a un temporal: la rama del ejecutable
    unico termina en %LOCALAPPDATA%\\MEDGLOBAL y rutas.datos() crea la carpeta,
    asi que sin esto correr las pruebas dejaba una carpeta en el perfil real
    del usuario."""
    monkeypatch.setenv("LOCALAPPDATA", local_appdata or str(tempfile.mkdtemp()))
    monkeypatch.setattr(sys, "frozen", frozen, raising=False)
    if meipass is None:
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    else:
        monkeypatch.setattr(sys, "_MEIPASS", meipass, raising=False)
    if exe:
        monkeypatch.setattr(sys, "executable", exe)
    if datos_env is None:
        monkeypatch.delenv("MEDGLOBAL_DATOS", raising=False)
    else:
        monkeypatch.setenv("MEDGLOBAL_DATOS", datos_env)
    monkeypatch.setattr(rutas, "CARPETA_RECURSOS", rutas._elegir_carpeta_recursos())
    monkeypatch.setattr(rutas, "CARPETA_DATOS", rutas._elegir_carpeta_datos())


def test_sin_congelar_todo_queda_relativo(monkeypatch):
    """En desarrollo y en las pruebas no cambia nada: rutas relativas al
    directorio actual, igual que antes de que existiera este modulo."""
    _recargar(monkeypatch)
    assert rutas.datos("medglobal.db") == "medglobal.db"
    assert rutas.recurso("static") == "static"


def test_el_ejecutable_unico_no_escribe_donde_descomprime(monkeypatch, tmp_path):
    """Lo que se escribe NO puede ir a _MEIPASS: esa carpeta se borra al
    cerrar el programa."""
    temporal = str(tmp_path / "_MEI12345")
    _recargar(monkeypatch, frozen=True, meipass=temporal,
              exe=str(tmp_path / "Escritorio" / "MEDGLOBAL.exe"))

    base = rutas.datos("medglobal.db")
    assert not base.startswith(temporal), "la base terminaria en la carpeta temporal"
    assert rutas.recurso("static").startswith(temporal), "los recursos SI vienen de ahi"


def test_el_ejecutable_unico_tampoco_ensucia_donde_esta_el_exe(monkeypatch, tmp_path):
    """Un solo archivo se abre desde el Escritorio o desde Descargas. Dejar
    ahi la base, la clave y los respaldos seria un desastre para el usuario:
    van a una carpeta estable suya."""
    escritorio = tmp_path / "Escritorio"
    escritorio.mkdir()
    perfil = tmp_path / "AppData" / "Local"
    _recargar(monkeypatch, frozen=True, meipass=str(tmp_path / "_MEI"),
              exe=str(escritorio / "MEDGLOBAL.exe"), local_appdata=str(perfil))

    base = rutas.datos("medglobal.db")
    assert not base.startswith(str(escritorio))
    assert base == str(perfil / "MEDGLOBAL" / "medglobal.db")


def test_una_instalacion_existente_manda(monkeypatch, tmp_path):
    """Si hay un medglobal.db al lado del ejecutable, esa es la instalacion en
    uso: hay que seguir usandola. Es lo que permite actualizar una PC con
    datos copiando solo el .exe nuevo dentro de su carpeta."""
    instalacion = tmp_path / "MEDGLOBAL_Local_App"
    instalacion.mkdir()
    (instalacion / "medglobal.db").write_text("base con datos")

    _recargar(monkeypatch, frozen=True, meipass=str(tmp_path / "_MEI"),
              exe=str(instalacion / "MEDGLOBAL.exe"))

    assert rutas.datos("medglobal.db") == str(instalacion / "medglobal.db")
    assert rutas.datos("sync_cursor.json") == str(instalacion / "sync_cursor.json")


def test_se_puede_forzar_la_carpeta_de_datos(monkeypatch, tmp_path):
    """Valvula de escape para revisar una instalacion sin tocarla."""
    aparte = tmp_path / "prueba"
    _recargar(monkeypatch, frozen=True, meipass=str(tmp_path / "_MEI"),
              exe=str(tmp_path / "MEDGLOBAL.exe"), datos_env=str(aparte))

    assert rutas.datos("medglobal.db") == str(aparte / "medglobal.db")
    assert os.path.isdir(aparte), "la carpeta se crea sola en el primer uso"
