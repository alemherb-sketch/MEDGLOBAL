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
