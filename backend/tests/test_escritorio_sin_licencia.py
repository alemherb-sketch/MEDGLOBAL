"""Una PC de campo sin licencia tiene que poder activarse.

Este camino ya se rompio una vez y no se noto: la pantalla de activacion
existia (`ActivarLicencia.jsx`) pero nadie la enrutaba en App.jsx, asi que el
403 del middleware llegaba al login y la interfaz lo mostraba como «usuario o
contraseña incorrectos». El instalable quedaba inservible en cualquier PC
nueva y el sintoma no apuntaba a la licencia por ningun lado.

Lo que se comprueba aca es el lado del servidor de ese camino: que sin
licencia siga entrando lo justo para pedirla (la pantalla, sus assets y los
endpoints de activacion) y nada mas.
"""
import pytest


@pytest.fixture
def escritorio_sin_licencia(monkeypatch, tmp_path):
    """Modo instalable, sin licencia instalada y sin valvula de escape."""
    import rutas

    monkeypatch.setenv("MEDGLOBAL_ESCRITORIO", "1")
    monkeypatch.delenv("MEDGLOBAL_LICENCIA_BYPASS", raising=False)
    monkeypatch.setattr(rutas, "CARPETA_DATOS", str(tmp_path))


def _preparar_static():
    import os

    os.makedirs("static/assets", exist_ok=True)
    with open("static/index.html", "w", encoding="utf-8") as f:
        f.write('<!doctype html><script src="/assets/app.js"></script>')
    with open("static/assets/app.js", "w", encoding="utf-8") as f:
        f.write("console.log('bundle')")


def test_sin_licencia_el_login_dice_que_falta_la_licencia(client, escritorio_sin_licencia):
    """El 403 tiene que traer el motivo y el ID del equipo. Sin el motivo, el
    frontend no puede distinguirlo de una contraseña equivocada; sin el ID, el
    usuario no tiene que mandarle al administrador para pedir su codigo."""
    respuesta = client.post("/auth/login", data={"username": "tester", "password": "secreto"})

    assert respuesta.status_code == 403
    cuerpo = respuesta.json()
    assert cuerpo["motivo"] == "sin_licencia"
    assert cuerpo["machine_id"]


def test_sin_licencia_la_pantalla_de_activacion_igual_carga(client, escritorio_sin_licencia):
    """Si el middleware bloqueara tambien el index y los assets, no habria
    interfaz donde escribir el codigo: la PC quedaria sin salida."""
    _preparar_static()

    assert client.get("/").status_code == 200
    assert client.get("/assets/app.js").status_code == 200


def test_sin_licencia_se_puede_consultar_el_estado_y_activar(client, escritorio_sin_licencia):
    """Los dos endpoints que usa la pantalla de activacion son publicos a
    proposito: sin licencia no se puede iniciar sesion, asi que exigir sesion
    para activarla seria un circulo cerrado."""
    estado = client.get("/licencias/estado")
    assert estado.status_code == 200
    assert estado.json()["requerido"] is True
    assert estado.json()["valida"] is False

    # El codigo es invalido, pero lo que importa es que el middleware la deja
    # pasar en vez de responder 403 por falta de licencia.
    activacion = client.post("/licencias/activar", json={"codigo": "no-es-un-codigo"})
    assert activacion.json().get("motivo") != "sin_licencia"


def test_sin_licencia_el_resto_del_api_sigue_cerrado(client, escritorio_sin_licencia):
    """Lo que se abre es solo lo necesario para activar."""
    for ruta in ("/atenciones/", "/medicamentos/", "/dashboard/kpis", "/admin/usuarios"):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 403, ruta
        assert respuesta.json()["motivo"] == "sin_licencia", ruta


def test_en_la_web_del_vps_no_se_exige_ninguna_licencia(client):
    """Sin MEDGLOBAL_ESCRITORIO el middleware no bloquea nada: el mismo codigo
    sirve los dos productos y la web no debe enterarse de que existen
    licencias."""
    assert client.get("/licencias/estado").json()["requerido"] is False
    assert client.get("/medicamentos/").status_code == 200
