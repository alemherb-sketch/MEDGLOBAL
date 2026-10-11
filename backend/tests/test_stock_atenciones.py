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


def _movimientos(client, medicamento):
    """Kardex del medicamento, del mas viejo al mas nuevo."""
    return list(reversed(client.get(f"/kardex/{medicamento['id']}").json()))


def test_editar_una_atencion_sin_cambiar_la_receta_no_mueve_stock(client):
    """Antes guardar una ficha (aunque solo se corrigiera el diagnostico)
    devolvia toda la receta como INGRESO y la volvia a sacar como SALIDA: el
    kardex se llenaba de ingresos que nunca existieron."""
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
    tipos = [k["tipo_movimiento"] for k in _movimientos(client, medicamento)]
    assert tipos == ["INGRESO", "SALIDA"]  # stock inicial + la atencion, nada mas


def test_editar_una_atencion_solo_mueve_la_diferencia(client):
    sistema, clasificacion, trabajador, medicamento = _catalogo_minimo(client, stock=10)
    atencion = client.post("/atenciones/", json=_atencion(
        sistema, clasificacion, trabajador,
        [{"medicamento_id": medicamento["id"], "cantidad": 3}],
    )).json()

    client.put(f"/atenciones/{atencion['id']}", json=_atencion(
        sistema, clasificacion, trabajador,
        [{"medicamento_id": medicamento["id"], "cantidad": 5}],
    ))
    assert _stock(client, medicamento) == 5
    ultimo = _movimientos(client, medicamento)[-1]
    assert (ultimo["tipo_movimiento"], ultimo["cantidad"]) == ("SALIDA", 2)
    assert ultimo["observacion"] == f"Edición de atención N.º {atencion['folio']}"

    client.put(f"/atenciones/{atencion['id']}", json=_atencion(
        sistema, clasificacion, trabajador, [],
    ))
    assert _stock(client, medicamento) == 10
    ultimo = _movimientos(client, medicamento)[-1]
    assert (ultimo["tipo_movimiento"], ultimo["cantidad"]) == ("INGRESO", 5)
    assert ultimo["observacion"] == f"Devolución por edición de atención N.º {atencion['folio']}"


def test_editar_no_exige_stock_extra_por_lo_ya_dispensado(client):
    """Subir de 4 a 5 necesita 1 unidad disponible, no 5."""
    sistema, clasificacion, trabajador, medicamento = _catalogo_minimo(client, stock=5)
    atencion = client.post("/atenciones/", json=_atencion(
        sistema, clasificacion, trabajador,
        [{"medicamento_id": medicamento["id"], "cantidad": 4}],
    )).json()

    respuesta = client.put(f"/atenciones/{atencion['id']}", json=_atencion(
        sistema, clasificacion, trabajador,
        [{"medicamento_id": medicamento["id"], "cantidad": 5}],
    ))

    assert respuesta.status_code == 200
    assert _stock(client, medicamento) == 0


def test_la_salida_de_una_atencion_dice_de_que_ficha_y_usuario_viene(client):
    sistema, clasificacion, trabajador, medicamento = _catalogo_minimo(client, stock=10)
    atencion = client.post("/atenciones/", json=_atencion(
        sistema, clasificacion, trabajador,
        [{"medicamento_id": medicamento["id"], "cantidad": 3}],
    )).json()

    salida = _movimientos(client, medicamento)[-1]
    assert salida["observacion"] == f"Atención N.º {atencion['folio']}"
    assert salida["atencion_id"] == atencion["id"]
    assert salida["usuario"] == "tester"


def test_un_movimiento_manual_registra_el_usuario(client):
    _, _, _, medicamento = _catalogo_minimo(client, stock=0)

    fila = client.post("/kardex/", json={
        "medicamento_id": medicamento["id"], "tipo_movimiento": "INGRESO", "cantidad": 7,
        "observacion": "Compra factura F001-1",
    }).json()

    assert fila["usuario"] == "tester"
    assert fila["observacion"] == "Compra factura F001-1"
    assert fila["atencion_id"] is None


def test_eliminar_una_atencion_devuelve_lo_recetado_una_sola_vez(client):
    """Antes el borrado era solo la marca: lo dispensado quedaba descontado
    aunque la ficha ya no existiera.

    No se compara el status de la segunda llamada: /atenciones es tambien una
    pantalla del frontend y main.manejar_404 responde index.html en vez del 404."""
    sistema, clasificacion, trabajador, medicamento = _catalogo_minimo(client, stock=10)
    atencion = client.post("/atenciones/", json=_atencion(
        sistema, clasificacion, trabajador,
        [{"medicamento_id": medicamento["id"], "cantidad": 3}],
    )).json()
    assert _stock(client, medicamento) == 7

    assert client.delete(f"/atenciones/{atencion['id']}").status_code == 200
    assert _stock(client, medicamento) == 10
    devolucion = _movimientos(client, medicamento)[-1]
    assert devolucion["tipo_movimiento"] == "INGRESO"
    assert devolucion["observacion"] == f"Anulación de atención N.º {atencion['folio']}"

    # Anular otra vez una ficha ya anulada no puede devolver de nuevo.
    movimientos = len(_movimientos(client, medicamento))
    client.delete(f"/atenciones/{atencion['id']}")
    assert _stock(client, medicamento) == 10
    assert len(_movimientos(client, medicamento)) == movimientos


def test_la_fecha_del_kardex_sale_con_zona_utc(client):
    """Sin la marca de zona el browser leia la hora UTC como local y el kardex
    mostraba las 11:59 de Peru como 16:59."""
    _, _, _, medicamento = _catalogo_minimo(client, stock=1)

    fecha = _movimientos(client, medicamento)[0]["fecha"]

    assert fecha.endswith("+00:00")


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
