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


def test_listar_inspecciones_filtra_por_tipo_y_ubicacion(client):
    tipo = client.post("/tipos_botiquin/", json={
        "nombre": "Tipo filtro inspección",
        "insumos": [],
    }).json()
    bot = client.post("/botiquines/", json={
        "codigo": "BOT-FILTRO-INSP",
        "tipo_botiquin_id": tipo["id"],
        "tipo_equipo": tipo["nombre"],
        "area": "MINA",
        "ubicacion": "Mina",
        "equipo": "Botiquín de emergencia",
    }).json()
    otro = client.post("/botiquines/", json={
        "codigo": "BOT-FILTRO-INSP-2",
        "tipo_equipo": "Otro",
        "area": "PLANTA",
        "ubicacion": "Planta",
        "equipo": "Botiquín de emergencia",
    }).json()
    ins = client.post("/botiquin_inspecciones/", json={
        "botiquin_id": bot["id"], "insumos": [],
    }).json()
    client.post("/botiquin_inspecciones/", json={
        "botiquin_id": otro["id"], "insumos": [],
    })

    por_tipo = client.get("/botiquin_inspecciones/", params={"tipo_botiquin_id": tipo["id"]})
    assert por_tipo.status_code == 200, por_tipo.text
    ids_tipo = [x["id"] for x in por_tipo.json()]
    assert ins["id"] in ids_tipo
    assert all(x["botiquin_id"] == bot["id"] for x in por_tipo.json())

    por_ubi = client.get("/botiquin_inspecciones/", params={"ubicacion": "Mina"})
    assert por_ubi.status_code == 200, por_ubi.text
    assert ins["id"] in [x["id"] for x in por_ubi.json()]


def test_listar_botiquines_filtra_por_botiquin_id(client):
    propio = client.post("/botiquines/", json={
        "codigo": "BOT-ID-PROPIO",
        "tipo_equipo": "Botiquín de área de trabajo",
        "area": "MINA",
        "equipo": "Botiquín de emergencia",
    }).json()
    otro = client.post("/botiquines/", json={
        "codigo": "BOT-ID-OTRO",
        "tipo_equipo": "Botiquín de área de trabajo",
        "area": "PLANTA",
        "equipo": "Botiquín de emergencia",
    }).json()

    lista = client.get("/botiquines/", params={"botiquin_id": propio["id"]})
    assert lista.status_code == 200, lista.text
    ids = [b["id"] for b in lista.json()]
    assert propio["id"] in ids
    assert otro["id"] not in ids


def test_listar_inspecciones_filtra_por_tipo_area_equipo(client):
    tipo = client.post("/tipos_botiquin/", json={
        "nombre": "Tipo area equipo",
        "insumos": [],
    }).json()
    bot = client.post("/botiquines/", json={
        "codigo": "BOT-AREA-EQ",
        "tipo_botiquin_id": tipo["id"],
        "tipo_equipo": tipo["nombre"],
        "area": "CISTERNA G.LESSER",
        "ubicacion": "Planta",
        "equipo": "Botiquín de emergencia",
        "estado": "ACTIVO",
    }).json()
    otro = client.post("/botiquines/", json={
        "codigo": "BOT-AREA-EQ-2",
        "tipo_equipo": "Otro tipo",
        "area": "MINA NORTE",
        "ubicacion": "Mina",
        "equipo": "Polvorines",
        "estado": "INACTIVO",
    }).json()
    ins = client.post("/botiquin_inspecciones/", json={
        "botiquin_id": bot["id"], "insumos": [],
    }).json()
    client.post("/botiquin_inspecciones/", json={
        "botiquin_id": otro["id"], "insumos": [],
    })

    por_tipo = client.get("/botiquin_inspecciones/", params={"tipo_equipo": tipo["nombre"]})
    assert por_tipo.status_code == 200, por_tipo.text
    assert ins["id"] in [x["id"] for x in por_tipo.json()]
    assert all(x["botiquin_id"] == bot["id"] for x in por_tipo.json())

    por_area = client.get("/botiquin_inspecciones/", params={"area": "CISTERNA"})
    assert por_area.status_code == 200, por_area.text
    assert ins["id"] in [x["id"] for x in por_area.json()]

    por_equipo = client.get("/botiquin_inspecciones/", params={"equipo": "Botiquín de emergencia"})
    assert por_equipo.status_code == 200, por_equipo.text
    assert ins["id"] in [x["id"] for x in por_equipo.json()]

    por_estado = client.get("/botiquin_inspecciones/", params={"estado": "ACTIVO"})
    assert por_estado.status_code == 200, por_estado.text
    assert ins["id"] in [x["id"] for x in por_estado.json()]
