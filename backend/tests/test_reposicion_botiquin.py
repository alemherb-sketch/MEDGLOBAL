def _crear_botiquin_y_medicamento(client, stock=10):
    medicamento = client.post("/medicamentos/", json={
        "nombre": "GASA ESTERIL",
        "presentacion": "SOBRE",
        "tipo": "INSUMO",
    }).json()
    client.post("/kardex/", json={
        "medicamento_id": medicamento["id"],
        "tipo_movimiento": "INGRESO",
        "cantidad": stock,
    })
    botiquin = client.post("/botiquines/", json={
        "codigo": f"BOT-PRUEBA-{stock}",
        "tipo_equipo": "BOTIQUÍN",
        "area": "MINA",
        "equipo": "EMERGENCIA",
    }).json()
    return botiquin, medicamento


def test_reponer_botiquin_descuenta_stock_y_rotula_kardex(client):
    botiquin, medicamento = _crear_botiquin_y_medicamento(client)

    respuesta = client.post(f"/botiquines/{botiquin['id']}/reponer", json={
        "medicamento_id": medicamento["id"],
        "cantidad": 3,
    })

    assert respuesta.status_code == 200
    movimiento = respuesta.json()
    assert movimiento["tipo_movimiento"] == "SALIDA"
    assert movimiento["cantidad"] == 3
    assert movimiento["saldo"] == 7
    assert movimiento["observacion"] == "Reposición botiquín BOT-PRUEBA-10"
    assert client.get("/medicamentos/").json()[0]["stock_actual"] == 7


def test_reponer_botiquin_rechaza_stock_insuficiente(client):
    botiquin, medicamento = _crear_botiquin_y_medicamento(client, stock=2)

    respuesta = client.post(f"/botiquines/{botiquin['id']}/reponer", json={
        "medicamento_id": medicamento["id"],
        "cantidad": 3,
    })

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Stock insuficiente. Disponible: 2"
    assert client.get("/medicamentos/").json()[0]["stock_actual"] == 2
