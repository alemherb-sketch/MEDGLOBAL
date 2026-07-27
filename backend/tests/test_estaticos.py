"""Cabeceras de cache de los archivos que sirve la aplicacion.

Sin esto, actualizar el .exe no alcanzaba: el navegador seguia mostrando la
version anterior de la interfaz hasta que alguien hiciera Ctrl+Shift+R, y no
habia ninguna senal de que hiciera falta.
"""
import os


def _preparar_static():
    """main.py sirve ./static; los tests corren en un directorio temporal."""
    os.makedirs("static/assets", exist_ok=True)
    with open("static/index.html", "w", encoding="utf-8") as f:
        f.write('<!doctype html><script src="/assets/index-abc123.js"></script>')
    with open("static/assets/index-abc123.js", "w", encoding="utf-8") as f:
        f.write("console.log('bundle')")


def test_index_no_se_cachea(client):
    """index.html es el unico archivo que dice cual es el bundle vigente. Si
    el navegador se lo queda, sigue pidiendo el bundle viejo para siempre."""
    _preparar_static()
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    assert "no-store" in respuesta.headers.get("cache-control", "")


def test_los_assets_si_se_cachean(client):
    """Vite les pone un hash en el nombre, asi que el contenido de un asset
    con ese nombre no cambia nunca y conviene cachearlo."""
    _preparar_static()
    respuesta = client.get("/assets/index-abc123.js")
    assert respuesta.status_code == 200
    assert "max-age=31536000" in respuesta.headers.get("cache-control", "")


def test_una_ruta_del_frontend_devuelve_el_index_sin_cache(client):
    """El ruteo es del lado del navegador: /atenciones lo resuelve React, el
    servidor devuelve index.html."""
    _preparar_static()
    respuesta = client.get("/atenciones")
    assert respuesta.status_code == 200
    assert "no-store" in respuesta.headers.get("cache-control", "")


def test_una_ruta_de_api_inexistente_devuelve_404_y_no_revienta(client):
    """El handler hacia `return exc` en vez de `raise exc`, y Starlette
    esperaba una Response: cualquier /api/... inexistente lanzaba
    TypeError: 'HTTPException' object is not callable."""
    _preparar_static()
    respuesta = client.get("/api/lo-que-sea")
    assert respuesta.status_code == 404
