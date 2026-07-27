"""Regresiones de seguridad del arranque: clave de firma y CORS."""
import datetime
import importlib

from jose import jwt

CLAVE_VIEJA_DEL_REPOSITORIO = "medglobal-dev-secret-cambiar-en-produccion"


def _token_admin(clave):
    return jwt.encode(
        {"sub": "tester", "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
        clave,
        algorithm="HS256",
    )


def test_no_se_acepta_un_token_firmado_con_la_clave_vieja(client):
    """Esa constante estaba escrita en auth.py y ningun despliegue definia
    SECRET_KEY, asi que cualquiera que leyera el repositorio podia firmarse un
    token de administrador valido contra el servidor de la clinica."""
    respuesta = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {_token_admin(CLAVE_VIEJA_DEL_REPOSITORIO)}"},
    )
    assert respuesta.status_code == 401


def test_sin_variable_de_entorno_se_genera_una_clave_y_se_reutiliza(tmp_path, monkeypatch):
    """El .exe de escritorio no recibe variables de entorno. Tiene que
    arrancar solo, pero con una clave propia e impredecible, y conservarla
    entre reinicios para no cerrar las sesiones abiertas."""
    import auth

    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    primera = auth._obtener_secret_key()
    assert primera != CLAVE_VIEJA_DEL_REPOSITORIO
    assert len(primera) >= 40
    assert (tmp_path / "secret_key.txt").exists()

    # Un reinicio de la app reutiliza la clave guardada.
    assert auth._obtener_secret_key() == primera


def test_la_variable_de_entorno_tiene_prioridad(tmp_path, monkeypatch):
    import auth

    monkeypatch.setenv("SECRET_KEY", "la-del-servidor")
    monkeypatch.chdir(tmp_path)
    assert auth._obtener_secret_key() == "la-del-servidor"
    assert not (tmp_path / "secret_key.txt").exists()


def test_cors_no_refleja_un_origen_desconocido(client):
    """Con allow_origins=["*"] y allow_credentials=True, Starlette responde
    reflejando el Origin recibido: cualquier pagina web podia llamar al API
    desde el navegador de un usuario logueado."""
    respuesta = client.get("/medicamentos/", headers={"Origin": "https://sitio-cualquiera.com"})
    assert respuesta.headers.get("access-control-allow-origin") != "https://sitio-cualquiera.com"
    assert respuesta.headers.get("access-control-allow-credentials") != "true"


def test_cors_permite_el_dominio_de_produccion(client):
    respuesta = client.get("/medicamentos/", headers={"Origin": "https://medglobal.erpgest.com.pe"})
    assert respuesta.headers.get("access-control-allow-origin") == "https://medglobal.erpgest.com.pe"
