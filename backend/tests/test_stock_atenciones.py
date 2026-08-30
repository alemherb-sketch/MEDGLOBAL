"""El stock no puede quedar en negativo ni moverse con cantidades invalidas.

/kardex/ y la reposicion de botiquines ya rechazaban sacar mas de lo
disponible, pero registrar una atencion no: dispensar medicamentos restaba
directo de stock_actual sin comprobar nada. Una clinica terminaba con
inventario negativo y sin ninguna senal de cuando habia pasado.
"""


def _catalogo_minimo(client, stock=5):
    """Lo minimo para poder registrar una atencion."""
    sistema = client.post("/sistemas/", json={"nombre": "RESPIRATORIO"}).json()
    clasificacion = client.post("/clasificaciones/", json={"nombre": "COMUN"}).json()
    trabajador = client.post("/trabajadores/", json={
        "nombre": "Ana", "apellidos": "Quispe", "dni": "40404040", "rol": "Operario",
    }).json()
    medicamento = client.post("/medicamentos/", json={
        "nombre": "PARACETAMOL", "presentacion": "TAB 500MG",
    }).json()
    if stock:
        client.post("/kardex/", json={
            "medicamento_id": medicamento["id"], "tipo_movimiento": "INGRESO", "cantidad": stock,
        })
    return sistema, clasificacion, trabajador, medicamento


def _atencion(sistema, clasificacion, trabajador, medicamentos):
    return {
        "descripcion": "Dolor de cabeza",
        "trabajador_id": trabajador["id"],
        "sistema_id": sistema["id"],
        "clasificacion_id": clasificacion["id"],
        "medicamentos": medicamentos,
    }


def _stock(client, medicamento):
    fichas = client.get("/medicamentos/").json()
    return next(m["stock_actual"] for m in fichas if m["id"] == medicamento["id"])


def test_una_atencion_no_puede_dispensar_mas_de_lo_que_hay(client):
    sistema, clasificacion, trabajador, medicamento = _catalogo_minimo(client, stock=2)

    respuesta = client.post("/atenciones/", json=_atencion(
        sistema, clasificacion, trabajador,
        [{"medicamento_id": medicamento["id"], "cantidad": 5}],
    ))

    assert respuesta.status_code == 400
    assert "Stock insuficiente" in respuesta.json()["detail"]
    assert _stock(client, medicamento) == 2


def test_si_la_receta_se_rechaza_no_queda_la_atencion_a_medias(client):
    """La atencion y su receta se confirman juntas. Antes la atencion se
    guardaba primero, asi que un fallo posterior dejaba una ficha sin la
    receta que la justifica."""
    sistema, clasificacion, trabajador, medicamento = _catalogo_minimo(client, stock=1)

    client.post("/atenciones/", json=_atencion(
        sistema, clasificacion, trabajador,
        [{"medicamento_id": medicamento["id"], "cantidad": 9}],
    ))

    assert client.get("/atenciones/").json() == []


def test_una_atencion_normal_si_descuenta_el_stock(client):
    sistema, clasificacion, trabajador, medicamento = _catalogo_minimo(client, stock=10)

    respuesta = client.post("/atenciones/", json=_atencion(
        sistema, clasificacion, trabajador,
        [{"medicamento_id": medicamento["id"], "cantidad": 3}],
    ))

    assert respuesta.status_code == 200
    assert _stock(client, medicamento) == 7


def test_editar_una_atencion_devuelve_lo_anterior_antes_de_descontar(client):
    """Reeditar la misma cantidad no debe exigir stock extra: primero vuelve al
    almacen lo que estaba recetado y recien despues sale lo nuevo."""
    sistema, clasificacion, trabajador, medicamento = _catalogo_minimo(client, stock=4)

    atencion = client.post("/atenciones/", json=_atencion(
        sistema, clasificacion, trabajador,
        [{"medicamento_id": medicamento["id"], "cantidad": 4}],
    )).json()
    assert _stock(client, medicamento) == 0

    respuesta = client.put(f"/atenciones/{atencion['id']}", json=_atencion(
        sistema, clasificacion, trabajador,
        [{"medicamento_id": medicamento["id"], "cantidad": 4}],
    ))

    assert respuesta.status_code == 200
    assert _stock(client, medicamento) == 0


def test_una_salida_negativa_no_puede_aumentar_el_stock(client):
    """Una cantidad negativa invertia el movimiento: `stock < -5` es falso, asi
    que pasaba la comprobacion y despues SUMABA al inventario."""
    _, _, _, medicamento = _catalogo_minimo(client, stock=3)

    respuesta = client.post("/kardex/", json={
        "medicamento_id": medicamento["id"], "tipo_movimiento": "SALIDA", "cantidad": -5,
    })

    assert respuesta.status_code == 400
    assert _stock(client, medicamento) == 3


def test_un_movimiento_de_cantidad_cero_se_rechaza(client):
    _, _, _, medicamento = _catalogo_minimo(client, stock=3)

    respuesta = client.post("/kardex/", json={
        "medicamento_id": medicamento["id"], "tipo_movimiento": "INGRESO", "cantidad": 0,
    })

    assert respuesta.status_code == 400
    assert _stock(client, medicamento) == 3


def test_un_tipo_de_movimiento_desconocido_se_rechaza(client):
    """Antes cualquier valor distinto de INGRESO/SALIDA no tocaba el stock pero
    igual dejaba una fila de kardex, que despues no cuadraba con el saldo."""
    _, _, _, medicamento = _catalogo_minimo(client, stock=3)

    respuesta = client.post("/kardex/", json={
        "medicamento_id": medicamento["id"], "tipo_movimiento": "AJUSTE", "cantidad": 1,
    })

    assert respuesta.status_code == 400
    assert client.get(f"/kardex/{medicamento['id']}").json().__len__() == 1  # solo el INGRESO inicial
