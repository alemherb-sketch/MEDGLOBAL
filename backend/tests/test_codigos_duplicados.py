"""Que la comprobacion de codigos repetidos diga lo mismo que la base.

Si el endpoint es MAS estricto que el indice de la base, rechaza altas que la
base aceptaria (y que la gente usa). Si es MENOS estricto, el choque sale como
error 500 con la sesion rota en vez de un mensaje. Las dos mitades tienen que
coincidir, y no coinciden para todas las tablas: `botiquines.codigo` es el
unico codigo sin indice UNIQUE, porque su columna se agrego con ALTER TABLE
ADD COLUMN sobre una tabla que ya existia.
"""


def _botiquin(codigo, area="ALMACEN"):
    return {
        "codigo": codigo,
        "tipo_equipo": "Botiquín de área de trabajo",
        "area": area,
        "equipo": "Botiquín de emergencia",
    }


def test_se_puede_reusar_el_codigo_de_un_botiquin_dado_de_baja(client):
    """Dar de baja un botiquin y volver a crearlo con el mismo codigo es un uso
    normal: en produccion hay cuatro codigos asi. Mirar tambien las filas
    borradas rechazaba la segunda alta."""
    primero = client.post("/botiquines/", json=_botiquin("B-EE-P-02", "Lixiviación")).json()
    assert client.delete(f"/botiquines/{primero['id']}").status_code == 200

    segundo = client.post("/botiquines/", json=_botiquin("B-EE-P-02", "Preparación de Reactivos"))

    assert segundo.status_code == 200, segundo.text
    assert segundo.json()["codigo"] == "B-EE-P-02"
    # Y en el listado queda uno solo: el vigente.
    vigentes = [b for b in client.get("/botiquines/").json() if b["codigo"] == "B-EE-P-02"]
    assert len(vigentes) == 1
    assert vigentes[0]["area"] == "Preparación de Reactivos"


def test_dos_botiquines_vigentes_no_pueden_compartir_codigo(client):
    """La unicidad entre los que estan en uso si se exige, y es el endpoint
    quien la aplica porque la base no tiene el indice."""
    client.post("/botiquines/", json=_botiquin("B-S-M-01"))

    repetido = client.post("/botiquines/", json=_botiquin("B-S-M-01", "OTRA AREA"))

    assert repetido.status_code == 400
    assert "código" in repetido.json()["detail"]


def test_un_codigo_de_medicamento_repetido_da_400_y_no_500(client):
    """Aca la base SI tiene indice UNIQUE, asi que la comprobacion mira todas
    las filas: sin ella el conflicto llegaba como IntegrityError -> 500 y
    dejaba la sesion inutilizable para las peticiones siguientes."""
    client.post("/medicamentos/", json={
        "codigo": "MED-9001", "nombre": "IBUPROFENO", "presentacion": "TAB 400MG",
    })

    repetido = client.post("/medicamentos/", json={
        "codigo": "MED-9001", "nombre": "OTRO", "presentacion": "TAB",
    })

    assert repetido.status_code == 400
    assert "código" in repetido.json()["detail"]


def test_el_codigo_de_un_medicamento_borrado_sigue_ocupado(client):
    """Coherente con el indice UNIQUE de la base, que no distingue borrados:
    si aca se permitiera, el INSERT reventaria al confirmar."""
    creado = client.post("/medicamentos/", json={
        "codigo": "MED-9002", "nombre": "AMOXICILINA", "presentacion": "CAP 500MG",
    }).json()
    client.delete(f"/medicamentos/{creado['id']}")

    repetido = client.post("/medicamentos/", json={
        "codigo": "MED-9002", "nombre": "OTRO", "presentacion": "CAP",
    })

    assert repetido.status_code == 400
