"""API de administracion de cuentas.

Antes MEDGLOBAL solo exponia /auth/login y /auth/me: los usuarios se creaban
con scripts sueltos en el servidor y no habia forma de verlos ni bloquearlos a
distancia. Estas pruebas cubren lo que se acaba de anadir, y sobre todo los
candados: que un usuario ESTANDAR no pueda administrar, que nadie se bloquee a
si mismo y que el sistema no se quede sin ningun administrador.
"""
import auth
import models
from database import SessionLocal


def _crear_usuario(username, rol="ESTANDAR", estado="ACTIVO", password="secreto8"):
    sesion = SessionLocal()
    usuario = models.Usuario(
        username=username, password_hash=auth.hash_password(password),
        nombre=username.title(), rol=rol, estado=estado,
    )
    sesion.add(usuario)
    sesion.commit()
    uid = usuario.id
    sesion.close()
    return uid


def _token(client, username, password):
    return client.post(
        "/auth/login", data={"username": username, "password": password}
    ).json().get("access_token")


# --- Permisos ---------------------------------------------------------------

def test_un_usuario_estandar_no_puede_administrar(client):
    """Sin esto, cualquiera podria bloquear al resto o darse rol ADMIN."""
    _crear_usuario("juan", rol="ESTANDAR")
    token = _token(client, "juan", "secreto8")
    respuesta = client.get("/admin/usuarios", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 403
    assert "administrador" in respuesta.json()["detail"].lower()


def test_sin_sesion_no_se_entra(client):
    respuesta = client.get("/admin/usuarios", headers={"Authorization": "Bearer no-vale"})
    assert respuesta.status_code == 401


def test_un_admin_lista_los_usuarios(client):
    _crear_usuario("juan")
    respuesta = client.get("/admin/usuarios")
    assert respuesta.status_code == 200
    nombres = {u["username"] for u in respuesta.json()}
    assert {"tester", "juan"} <= nombres


def test_la_api_nunca_devuelve_la_contrasena(client):
    _crear_usuario("juan")
    cuerpo = str(client.get("/admin/usuarios").json()).lower()
    assert "password" not in cuerpo
    assert "hash" not in cuerpo


# --- Alta -------------------------------------------------------------------

def test_se_crea_una_cuenta_y_puede_iniciar_sesion(client):
    respuesta = client.post("/admin/usuarios", json={
        "username": "nueva", "nombre": "Cuenta Nueva",
        "rol": "ESTANDAR", "password": "claveLarga1",
    })
    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "ACTIVO"
    assert _token(client, "nueva", "claveLarga1")


def test_no_se_repite_el_nombre_de_usuario(client):
    _crear_usuario("juan")
    respuesta = client.post("/admin/usuarios", json={
        "username": "juan", "nombre": "Otro", "password": "claveLarga1",
    })
    assert respuesta.status_code == 400


def test_se_exige_una_contrasena_minima(client):
    respuesta = client.post("/admin/usuarios", json={
        "username": "corta", "nombre": "Corta", "password": "1234",
    })
    assert respuesta.status_code == 400


# --- Bloqueo ----------------------------------------------------------------

def test_bloquear_impide_iniciar_sesion(client):
    """Es lo que da sentido al boton: si tras bloquear se pudiera seguir
    entrando, el estado seria decorativo."""
    uid = _crear_usuario("juan")
    assert _token(client, "juan", "secreto8")

    respuesta = client.patch(f"/admin/usuarios/{uid}", json={"estado": "BLOQUEADO"})
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "BLOQUEADO"
    assert _token(client, "juan", "secreto8") is None


def test_bloquear_corta_tambien_la_sesion_ya_abierta(client):
    """No basta con impedir el proximo inicio de sesion: quien ya tenia el
    token seguiria trabajando hasta que caducara."""
    uid = _crear_usuario("juan")
    token = _token(client, "juan", "secreto8")
    cabecera = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=cabecera).status_code == 200

    client.patch(f"/admin/usuarios/{uid}", json={"estado": "BLOQUEADO"})
    assert client.get("/auth/me", headers=cabecera).status_code == 401


def test_reactivar_devuelve_el_acceso(client):
    uid = _crear_usuario("juan", estado="BLOQUEADO")
    assert _token(client, "juan", "secreto8") is None
    client.patch(f"/admin/usuarios/{uid}", json={"estado": "ACTIVO"})
    assert _token(client, "juan", "secreto8")


# --- Edicion ----------------------------------------------------------------

def test_se_cambia_el_rol(client):
    uid = _crear_usuario("juan")
    respuesta = client.patch(f"/admin/usuarios/{uid}", json={"rol": "admin"})
    assert respuesta.status_code == 200
    assert respuesta.json()["rol"] == "ADMIN"


def test_editar_el_nombre_no_borra_la_contrasena(client):
    """`password` ausente significa «no tocar»: si no, cada cambio de nombre
    obligaria a reescribirla."""
    uid = _crear_usuario("juan")
    client.patch(f"/admin/usuarios/{uid}", json={"nombre": "Juan Perez"})
    assert _token(client, "juan", "secreto8")


def test_se_cambia_la_contrasena(client):
    uid = _crear_usuario("juan")
    client.patch(f"/admin/usuarios/{uid}", json={"password": "otraClave12"})
    assert _token(client, "juan", "secreto8") is None
    assert _token(client, "juan", "otraClave12")


def test_editar_a_alguien_que_no_existe_da_404(client):
    assert client.patch("/admin/usuarios/no-existe", json={"nombre": "x"}).status_code == 404


# --- Candados contra dejarse fuera -----------------------------------------

def test_un_admin_no_puede_bloquearse_a_si_mismo(client):
    sesion = SessionLocal()
    uid = sesion.query(models.Usuario).filter_by(username="tester").first().id
    sesion.close()
    respuesta = client.patch(f"/admin/usuarios/{uid}", json={"estado": "BLOQUEADO"})
    assert respuesta.status_code == 400
    assert _token(client, "tester", "secreto")


def test_un_admin_no_puede_quitarse_el_rol(client):
    sesion = SessionLocal()
    uid = sesion.query(models.Usuario).filter_by(username="tester").first().id
    sesion.close()
    respuesta = client.patch(f"/admin/usuarios/{uid}", json={"rol": "ESTANDAR"})
    assert respuesta.status_code == 400


def test_no_se_puede_dejar_el_sistema_sin_administradores(client):
    """Bloquear al ultimo ADMIN dejaria el sistema sin nadie que pueda
    administrar, y ya no habria forma de deshacerlo."""
    otro = _crear_usuario("otroadmin", rol="ADMIN")
    respuesta = client.patch(f"/admin/usuarios/{otro}", json={"estado": "BLOQUEADO"})
    # Queda 'tester', asi que este si se permite.
    assert respuesta.status_code == 200

    sesion = SessionLocal()
    activos = sesion.query(models.Usuario).filter_by(rol="ADMIN", estado="ACTIVO").count()
    sesion.close()
    assert activos >= 1


# --- Registro de actividad --------------------------------------------------

def test_las_acciones_quedan_registradas(client):
    """MEDGLOBAL no tenia ninguna traza de quien administraba que."""
    client.post("/admin/usuarios", json={
        "username": "auditada", "nombre": "Auditada", "password": "claveLarga1",
    })
    respuesta = client.get("/admin/actividad")
    assert respuesta.status_code == 200
    eventos = respuesta.json()
    assert any(e["accion"] == "crear_usuario" and e["objetivo"] == "auditada" for e in eventos)
    assert eventos[0]["actor"] == "tester"


def test_la_actividad_registra_el_detalle_del_cambio(client):
    uid = _crear_usuario("juan")
    client.patch(f"/admin/usuarios/{uid}", json={"estado": "BLOQUEADO"})
    eventos = client.get("/admin/actividad").json()
    edicion = next(e for e in eventos if e["accion"] == "editar_usuario")
    assert "BLOQUEADO" in edicion["detalle"]


def test_un_estandar_no_ve_la_actividad(client):
    _crear_usuario("juan")
    token = _token(client, "juan", "secreto8")
    respuesta = client.get("/admin/actividad", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 403
