"""Regresiones del protocolo de sincronizacion.

Los dos casos de aca son bugs que ya ocurrieron en produccion y que no dan la
cara solos: no lanzan ningun error, simplemente dejan el inventario mal o los
datos sin subir.
"""
import datetime

import models


def _catalogo_basico(client, stock=100):
    """Deja el servidor con un medicamento con stock y los catalogos minimos
    que una atencion necesita. Devuelve (medicamento, sistema, clasificacion,
    trabajador)."""
    med = client.post("/medicamentos/", json={"nombre": "PARACETAMOL", "presentacion": "TABLETA"}).json()
    client.post("/kardex/", json={
        "medicamento_id": med["id"], "tipo_movimiento": "INGRESO", "cantidad": stock,
    })
    sistema = client.post("/sistemas/", json={"nombre": "RESPIRATORIO"}).json()
    clasificacion = client.post("/clasificaciones/", json={"nombre": "COMUN"}).json()
    trabajador = client.post("/trabajadores/", json={
        "nombre": "Juan", "apellidos": "Perez", "dni": "12345678", "rol": "OBRERO",
    }).json()
    return med, sistema, clasificacion, trabajador


def test_atencion_sincronizada_descuenta_stock_una_sola_vez(client):
    """Una atencion que llega por sync trae su receta embebida Y, por separado,
    la fila de kardex que create_atencion ya habia escrito en el dispositivo.
    El servidor debe aplicar el movimiento una sola vez.

    Antes descontaba dos veces (una en _procesar_atencion_nueva y otra en
    _procesar_kardex_nuevo), asi que el stock del servidor se degradaba de
    forma acumulativa con cada sincronizacion de cada instalacion offline.
    """
    med, sistema, clasificacion, trabajador = _catalogo_basico(client, stock=100)
    ahora = datetime.datetime.utcnow().isoformat()

    respuesta = client.post("/sync/subir", json={
        "since": None,
        "cambios": {
            "atenciones": [{
                "id": "11111111-1111-1111-1111-111111111111",
                "fecha": ahora, "descripcion": "dolor de cabeza",
                "trabajador_id": trabajador["id"], "sistema_id": sistema["id"],
                "clasificacion_id": clasificacion["id"],
                "updated_at": ahora, "is_deleted": False,
                "medicamentos": [{"medicamento_id": med["id"], "cantidad": 10}],
            }],
            "kardex": [{
                "id": "22222222-2222-2222-2222-222222222222",
                "medicamento_id": med["id"], "fecha": ahora,
                "tipo_movimiento": "SALIDA", "cantidad": 10, "saldo": 90,
                "updated_at": ahora, "is_deleted": False,
            }],
        },
    })
    assert respuesta.status_code == 200

    assert client.get("/medicamentos/").json()[0]["stock_actual"] == 90

    salidas = [m for m in client.get("/kardex/todos/").json() if m["tipo_movimiento"] == "SALIDA"]
    assert len(salidas) == 1, "el movimiento de salida se duplico"

    # La receta si tiene que quedar reconstruida en el servidor.
    atencion = client.get("/atenciones/").json()[0]
    assert [(m["medicamento_id"], m["cantidad"]) for m in atencion["medicamentos"]] == [(med["id"], 10)]
    assert atencion["folio"] == 1


def test_push_filtra_por_reloj_local_no_por_el_del_servidor(db, monkeypatch):
    """El filtro del push compara updated_at (reloj de esta PC) y el 'since'
    del payload usa el reloj del servidor.

    Antes se usaba un unico cursor para las dos cosas. En una PC con el reloj
    atrasado respecto al servidor, las filas nacian con updated_at menor que el
    cursor y no se subian nunca — el cursor solo avanza, asi que la perdida era
    permanente y silenciosa.
    """
    import sync_client

    monkeypatch.setattr(sync_client, "SYNC_SERVER_URL", "https://servidor-de-prueba")

    enviados = {}

    class RespuestaFalsa:
        def raise_for_status(self):
            pass

        def json(self):
            return {"server_time": "2026-01-01T00:00:00", "resultado": {}}

    def post_falso(url, headers=None, json=None, timeout=None):
        enviados.update(json)
        return RespuestaFalsa()

    monkeypatch.setattr(sync_client.requests, "post", post_falso)

    # Reloj de la PC atrasado 2 horas respecto al del servidor.
    hora_local = datetime.datetime.utcnow()
    hora_servidor = hora_local + datetime.timedelta(hours=2)

    empresa = models.Empresa(
        nombre="ACME", ruc="20999999999",
        updated_at=hora_local, server_updated_at=hora_local,
    )
    db.add(empresa)
    db.commit()

    sync_client._empujar_cambios(
        token="t",
        since_local=(hora_local - datetime.timedelta(minutes=5)).isoformat(),
        since_servidor=hora_servidor.isoformat(),
        db=db,
    )

    rucs = [fila["ruc"] for fila in enviados.get("cambios", {}).get("empresas", [])]
    assert "20999999999" in rucs, "una fila editada localmente quedo sin subir"
    # El 'since' que viaja al servidor sigue siendo el del reloj del servidor,
    # que es contra el que alla se comparan los server_updated_at.
    assert enviados["since"] == hora_servidor.isoformat()


def test_cursores_leen_el_formato_viejo(tmp_path, monkeypatch):
    """Un sync_cursor.json escrito por la version anterior tiene que seguir
    siendo valido tras actualizar: se respeta el punto de pull y el push se
    reenvia entero una vez, que es lo que recupera lo que el bug no habia
    subido."""
    import json

    import sync_client

    monkeypatch.chdir(tmp_path)
    (tmp_path / "sync_cursor.json").write_text(json.dumps({"last_synced_at": "2026-01-01T10:00:00"}))

    last_pulled, last_pushed = sync_client._leer_cursores()
    assert last_pulled == "2026-01-01T10:00:00"
    assert last_pushed is None

    sync_client._guardar_cursores("2026-01-02T10:00:00", "2026-01-02T09:59:00")
    guardado = json.loads((tmp_path / "sync_cursor.json").read_text())
    assert guardado["last_pulled_at"] == "2026-01-02T10:00:00"
    assert guardado["last_pushed_at"] == "2026-01-02T09:59:00"
    # La clave vieja se mantiene por si se vuelve a una version anterior.
    assert guardado["last_synced_at"] == "2026-01-02T10:00:00"
