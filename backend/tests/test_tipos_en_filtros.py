"""Los tipos de botiquin creados se pueden filtrar aunque tipo_equipo sea otro."""


def test_listar_botiquines_filtra_por_nombre_del_tipo(client):
    tipo = client.post("/tipos_botiquin/", json={
        "nombre": "Botiquín Vehículo pesado",
        "insumos": [],
    })
    assert tipo.status_code == 200, tipo.text
    tipo = tipo.json()

    creado = client.post("/botiquines/", json={
        "codigo": "BOT-TIPO-PESADO",
        "tipo_botiquin_id": tipo["id"],
        "tipo_equipo": "Botiquín de área de trabajo",
        "area": "MINA",
        "equipo": "Botiquín de emergencia",
    })
    assert creado.status_code == 200, creado.text

    lista = client.get("/botiquines/", params={"tipo_equipo": "Botiquín Vehículo pesado"})
    assert lista.status_code == 200, lista.text
    ids = [b["id"] for b in lista.json()]
    assert creado.json()["id"] in ids
