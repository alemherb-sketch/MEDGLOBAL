"""El correlativo visible de una inspeccion es INS0001, no el UUID interno."""
import re


def _botiquin(client, codigo):
    return client.post("/botiquines/", json={
        "codigo": codigo,
        "tipo_equipo": "Botiquín de área de trabajo",
        "area": "MINA",
        "equipo": "Botiquín de emergencia",
    }).json()


def test_crear_inspeccion_asigna_ins0001(client):
    bot = _botiquin(client, "BOT-INSP-CREATE")
    primera = client.post("/botiquin_inspecciones/", json={
        "botiquin_id": bot["id"],
        "observaciones": "primera",
        "insumos": [],
    })
    assert primera.status_code == 200, primera.text
    codigo1 = primera.json()["codigo"]
    assert re.fullmatch(r"INS\d{4,}", codigo1)
    assert primera.json()["id"] != codigo1

    segunda = client.post("/botiquin_inspecciones/", json={
        "botiquin_id": bot["id"],
        "observaciones": "segunda",
        "insumos": [],
    })
    assert segunda.status_code == 200, segunda.text
    codigo2 = segunda.json()["codigo"]
    assert codigo2 == f"INS{int(codigo1[3:]) + 1:04d}"


def test_editar_inspeccion_conserva_el_codigo(client):
    bot = _botiquin(client, "BOT-INSP-EDIT")
    creada = client.post("/botiquin_inspecciones/", json={
        "botiquin_id": bot["id"],
        "observaciones": "orig",
        "insumos": [],
    }).json()
    codigo = creada["codigo"]
    assert codigo and codigo.startswith("INS")

    editada = client.put(f"/botiquin_inspecciones/{creada['id']}", json={
        "observaciones": "cambiada",
    })
    assert editada.status_code == 200, editada.text
    assert editada.json()["codigo"] == codigo
    assert editada.json()["observaciones"] == "cambiada"


def test_sembrar_corrige_correlativos_disparados_por_doble_arranque(client, db):
    """Si dos workers numeraron a la vez (INS0001 y luego INS0144), se reescribe."""
    import migraciones
    import models
    from database import engine

    bot = _botiquin(client, "BOT-INSP-SEED")
    primera = client.post("/botiquin_inspecciones/", json={
        "botiquin_id": bot["id"],
        "observaciones": "a",
        "insumos": [],
    }).json()
    segunda = client.post("/botiquin_inspecciones/", json={
        "botiquin_id": bot["id"],
        "observaciones": "b",
        "insumos": [],
    }).json()

    fila_b = db.get(models.BotiquinInspeccion, segunda["id"])
    fila_b.codigo = "INS0144"
    db.commit()

    migraciones.sembrar_codigos_inspeccion(engine)
    db.expire_all()

    filas = (
        db.query(models.BotiquinInspeccion)
        .order_by(models.BotiquinInspeccion.created_at.asc(), models.BotiquinInspeccion.id.asc())
        .all()
    )
    numeros = [int(f.codigo[3:]) for f in filas]
    assert numeros == list(range(1, len(filas) + 1))
    assert db.get(models.BotiquinInspeccion, primera["id"]).codigo.startswith("INS")
    assert db.get(models.BotiquinInspeccion, segunda["id"]).codigo != "INS0144"
