"""Sincronizacion manual (el boton "Sincronizar ahora" del escritorio).

El foco de estos tests es la garantia que se le promete al usuario: apretar el
boton nunca puede perder informacion, ni la que esta en esta PC ni la que ya
esta en el servidor.
"""
import json
import threading

import pytest
import requests

import sync_client


@pytest.fixture
def sync_configurado(monkeypatch, tmp_path):
    """Deja sync_client como si la instalacion tuviera credenciales validas y
    trabajando sobre un directorio limpio (cursor y respaldos aparte)."""
    monkeypatch.setattr(sync_client, "SYNC_SERVER_URL", "https://servidor-de-prueba")
    monkeypatch.setattr(sync_client, "SYNC_USERNAME", "equipo")
    monkeypatch.setattr(sync_client, "SYNC_PASSWORD", "clave")
    monkeypatch.setattr(sync_client, "_login", lambda: ("token-valido", None, None))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_login_distingue_falta_de_internet_de_password_incorrecta(monkeypatch):
    """El caso mas comun en la clinica es quedarse sin internet, no tener mal
    la contrasena. Antes los dos casos devolvian None y se reportaban igual,
    mandando al usuario a buscar un problema de configuracion inexistente."""
    monkeypatch.setattr(sync_client, "SYNC_SERVER_URL", "https://servidor-de-prueba")

    def sin_red(*a, **kw):
        raise requests.ConnectionError("no hay ruta al servidor")

    monkeypatch.setattr(sync_client.requests, "post", sin_red)
    token, motivo, detalle = sync_client._login()
    assert (token, motivo) == (None, "sin_conexion")
    # El detalle dice QUE fallo: sin el, "no se pudo conectar" podia ser un
    # DNS, un certificado, un proxy o falta de internet, sin forma de saberlo.
    assert "ConnectionError" in detalle and "no hay ruta" in detalle

    class Respuesta401:
        status_code = 401

    monkeypatch.setattr(sync_client.requests, "post", lambda *a, **kw: Respuesta401())
    token, motivo, detalle = sync_client._login()
    assert (token, motivo) == (None, "credenciales")
    assert "401" in detalle

    class Respuesta200:
        status_code = 200

        def json(self):
            return {"access_token": "abc"}

    monkeypatch.setattr(sync_client.requests, "post", lambda *a, **kw: Respuesta200())
    assert sync_client._login() == ("abc", None, None)


def test_el_detalle_del_fallo_llega_al_resultado(sync_configurado, monkeypatch):
    """Lo que se ve en pantalla tiene que alcanzar para diagnosticar sin tener
    que abrir la consola de la aplicacion."""
    def sin_red(*a, **kw):
        raise requests.exceptions.SSLError("certificate verify failed")

    monkeypatch.setattr(sync_client, "_login", lambda: (None, "sin_conexion", "SSLError: certificate verify failed"))

    resultado = sync_client.sincronizar_ahora(origen="manual")
    assert resultado["motivo"] == "sin_conexion"
    assert "certificate verify failed" in resultado["detalle"]


def test_el_push_se_parte_en_lotes(sync_configurado, monkeypatch, db):
    """Una instalacion real tiene ~16.000 filas (el catalogo CIE-10 solo trae
    15.040). Mandarlas en un unico POST hacia que el servidor, que confirma
    fila por fila, quedara ocupado varios minutos; el ciclo siguiente cortaba
    por timeout y, como el cursor no avanza ante un fallo, volvia a intentar
    las mismas 16.000 filas para siempre."""
    import models

    for i in range(750):
        db.add(models.DiagnosticoCie10(codigo=f"Z{i:04d}", descripcion=f"Diagnostico {i}"))
    db.commit()

    monkeypatch.setattr(sync_client, "LOTE_FILAS", 300)

    peticiones = []

    class RespuestaFalsa:
        def raise_for_status(self):
            pass

        def json(self):
            return {"resultado": {"diagnosticos_cie10": {"aplicados": 300, "conflictos": 0}}}

    def post_falso(url, headers=None, json=None, timeout=None):
        peticiones.append(sum(len(filas) for filas in json["cambios"].values()))
        return RespuestaFalsa()

    monkeypatch.setattr(sync_client.requests, "post", post_falso)

    sync_client._empujar_cambios(token="t", since_local=None, since_servidor=None, db=db)

    assert len(peticiones) >= 3, "se mando todo en una sola peticion"
    assert max(peticiones) <= 300, f"un lote supero el maximo: {max(peticiones)}"
    assert sum(peticiones) >= 750, "se perdieron filas al partir en lotes"


def test_los_lotes_no_pierden_ninguna_fila(sync_configurado, monkeypatch, db):
    """Cortar en lotes no puede saltearse registros: lo que se sube tiene que
    ser exactamente lo que hay en la base."""
    import models

    esperados = set()
    for i in range(120):
        codigo = f"Y{i:04d}"
        esperados.add(codigo)
        db.add(models.DiagnosticoCie10(codigo=codigo, descripcion=f"D{i}"))
    db.commit()

    monkeypatch.setattr(sync_client, "LOTE_FILAS", 25)
    enviados = set()

    class RespuestaFalsa:
        def raise_for_status(self):
            pass

        def json(self):
            return {"resultado": {}}

    def post_falso(url, headers=None, json=None, timeout=None):
        for fila in json["cambios"].get("diagnosticos_cie10", []):
            enviados.add(fila["codigo"])
        return RespuestaFalsa()

    monkeypatch.setattr(sync_client.requests, "post", post_falso)
    sync_client._empujar_cambios(token="t", since_local=None, since_servidor=None, db=db)

    assert esperados <= enviados, f"faltaron {len(esperados - enviados)} filas"


def test_el_pull_puede_reordenar_valores_unicos_entre_filas(sync_configurado, db):
    """El servidor le asigna a cada atencion que recibe el siguiente folio
    libre EN EL SERVIDOR, que no tiene por que ser el que tenia en la PC. Al
    bajar la respuesta, el folio 1 puede tener que pasar de la atencion A a la
    B mientras A pasa al 2. Aplicandolas de a una, la primera choca contra la
    segunda, que todavia tiene el valor viejo: la sincronizacion entera se
    caia con "UNIQUE constraint failed: atenciones.folio" y, como el cursor no
    avanza ante un fallo, el error se repetia en cada intento."""
    import models

    db.query(models.AtencionMedicamento).delete()
    db.query(models.Atencion).delete()
    db.commit()

    a = models.Atencion(id="aaaaaaaa-0000-0000-0000-000000000001", descripcion="A", folio=1)
    b = models.Atencion(id="bbbbbbbb-0000-0000-0000-000000000002", descripcion="B", folio=2)
    db.add_all([a, b])
    db.commit()

    # El servidor devuelve los folios intercambiados.
    filas = [
        {"id": a.id, "folio": 2, "descripcion": "A"},
        {"id": b.id, "folio": 1, "descripcion": "B"},
    ]

    sync_client._liberar_valores_unicos(db, models.Atencion, filas)
    for fila in filas:
        existente = db.query(models.Atencion).filter(models.Atencion.id == fila["id"]).first()
        sync_client._apply_sync_fields(existente, fila, "atenciones", trusted_source=True)
    db.commit()

    assert db.query(models.Atencion).filter(models.Atencion.id == a.id).first().folio == 2
    assert db.query(models.Atencion).filter(models.Atencion.id == b.id).first().folio == 1


def test_no_deja_correr_dos_sincronizaciones_a_la_vez(sync_configurado, monkeypatch):
    """El ciclo automatico corre cada 30 segundos; si el usuario aprieta el
    boton justo en ese momento, los dos ciclos empujarian las mismas filas y
    escribirian el archivo de cursores uno encima del otro."""
    empezo = threading.Event()
    puede_terminar = threading.Event()

    def push_lento(*a, **kw):
        empezo.set()
        puede_terminar.wait(timeout=5)
        return 0, 0

    monkeypatch.setattr(sync_client, "_empujar_cambios", push_lento)
    monkeypatch.setattr(sync_client, "_traer_cambios", lambda *a, **kw: ("2026-01-01T00:00:00", 0))

    hilo = threading.Thread(target=sync_client.sincronizar_ahora, args=("automatico",))
    hilo.start()
    assert empezo.wait(timeout=5), "el primer ciclo no arranco"

    # Con un ciclo en curso, el boton avisa en vez de solaparse.
    assert sync_client.sincronizar_ahora(origen="manual") == {"ok": False, "motivo": "en_curso"}

    puede_terminar.set()
    hilo.join(timeout=5)

    # Y una vez libre, vuelve a funcionar.
    assert sync_client.sincronizar_ahora(origen="manual")["ok"] is True


def test_un_fallo_de_red_no_mueve_el_cursor(sync_configurado, monkeypatch):
    """Si se corta internet a mitad del ciclo, el punto de sincronizacion tiene
    que quedar donde estaba para que el proximo intento reenvie exactamente lo
    mismo. Si el cursor avanzara igual, esos registros no se subirian nunca."""
    sync_client._guardar_cursores("2026-01-01T10:00:00", "2026-01-01T09:59:00")
    antes = (sync_configurado / "sync_cursor.json").read_text()

    def push_que_falla(*a, **kw):
        raise requests.ConnectionError("se corto internet")

    monkeypatch.setattr(sync_client, "_empujar_cambios", push_que_falla)

    resultado = sync_client.sincronizar_ahora(origen="manual")

    assert resultado["ok"] is False
    assert resultado["motivo"] == "sin_conexion"
    assert (sync_configurado / "sync_cursor.json").read_text() == antes, "el cursor avanzo pese al fallo"


def test_un_fallo_en_el_pull_tampoco_mueve_el_cursor(sync_configurado, monkeypatch):
    sync_client._guardar_cursores("2026-01-01T10:00:00", "2026-01-01T09:59:00")
    antes = (sync_configurado / "sync_cursor.json").read_text()

    monkeypatch.setattr(sync_client, "_empujar_cambios", lambda *a, **kw: (5, 0))
    monkeypatch.setattr(sync_client, "_traer_cambios", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))

    resultado = sync_client.sincronizar_ahora(origen="manual")

    assert resultado["ok"] is False
    assert resultado["motivo"] == "error"
    assert (sync_configurado / "sync_cursor.json").read_text() == antes


def test_respalda_la_base_antes_de_sincronizar(sync_configurado, monkeypatch):
    """El pull puede borrar filas locales al resolver colisiones de columnas
    unique (_limpiar_colisiones_locales), asi que una sincronizacion puede
    eliminar datos de esta PC. El respaldo hace que eso sea reversible."""
    monkeypatch.setattr(sync_client, "_empujar_cambios", lambda *a, **kw: (0, 0))
    monkeypatch.setattr(sync_client, "_traer_cambios", lambda *a, **kw: ("2026-01-01T00:00:00", 0))

    resultado = sync_client.sincronizar_ahora(origen="manual")

    assert resultado["ok"] is True
    respaldos = list((sync_configurado / "respaldos").glob("medglobal-*.db"))
    assert len(respaldos) == 1
    assert respaldos[0].stat().st_size > 0


def test_los_respaldos_se_rotan(sync_configurado, monkeypatch):
    """La carpeta no puede crecer sin limite en una PC de la clinica."""
    monkeypatch.setattr(sync_client, "RESPALDOS_A_CONSERVAR", 3)
    carpeta = sync_configurado / "respaldos"
    carpeta.mkdir()
    for i in range(6):
        (carpeta / f"medglobal-2026010{i}-000000.db").write_text("x")

    sync_client._rotar_respaldos()

    assert len(list(carpeta.glob("medglobal-*.db"))) == 3
    # Se conservan los mas recientes.
    assert (carpeta / "medglobal-20260105-000000.db").exists()
    assert not (carpeta / "medglobal-20260100-000000.db").exists()


def test_informa_cuantos_registros_se_movieron(sync_configurado, monkeypatch):
    """El usuario necesita ver que efectivamente subio algo, no un 'listo' sin
    respaldo."""
    monkeypatch.setattr(sync_client, "_empujar_cambios", lambda *a, **kw: (12, 2))
    monkeypatch.setattr(sync_client, "_traer_cambios", lambda *a, **kw: ("2026-01-01T00:00:00", 7))

    resultado = sync_client.sincronizar_ahora(origen="manual")

    assert resultado["ok"] is True
    assert resultado["subidos"] == 12
    assert resultado["bajados"] == 7
    assert resultado["conflictos"] == 2


def test_sin_credenciales_no_se_intenta_sincronizar(monkeypatch, tmp_path):
    monkeypatch.setattr(sync_client, "SYNC_SERVER_URL", None)
    monkeypatch.chdir(tmp_path)
    assert sync_client.sincronizar_ahora(origen="manual") == {"ok": False, "motivo": "no_configurado"}


def test_endpoint_sync_ahora_responde_el_detalle(client, monkeypatch):
    import main

    monkeypatch.setattr(
        sync_client, "sincronizar_ahora",
        lambda origen="manual": {"ok": True, "subidos": 3, "bajados": 1, "conflictos": 0},
    )
    monkeypatch.setattr(main, "sync_client", sync_client)

    respuesta = client.post("/sync/ahora")
    assert respuesta.status_code == 200
    assert respuesta.json()["subidos"] == 3


def test_endpoint_sync_ahora_no_existe_en_el_servidor_web(client, monkeypatch):
    """En el VPS sync_client no esta instalado: el endpoint tiene que responder
    un error claro, no reventar."""
    import main

    monkeypatch.setattr(main, "sync_client", None)
    assert client.post("/sync/ahora").status_code == 400


def test_sync_ahora_requiere_sesion(client):
    sin_token = {"Authorization": ""}
    assert client.post("/sync/ahora", headers=sin_token).status_code == 401
