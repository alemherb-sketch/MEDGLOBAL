"""Reporte de consumo de insumos de botiquin: filtro por producto."""
from uuid import uuid4


def _inspeccion_con_dos_insumos(client):
    gasa = client.post("/medicamentos/", json={
        "nombre": "GASA ESTERIL", "presentacion": "SOBRE", "tipo": "INSUMO",
    }).json()
    tijera = client.post("/medicamentos/", json={
        "nombre": "TIJERA DE TRAUMA", "presentacion": "UNIDAD", "tipo": "INSUMO",
    }).json()
    # La tabla de botiquines no se limpia entre tests y el codigo no puede repetirse.
    botiquin = client.post("/botiquines/", json={
        "codigo": f"BOT-REPORTE-{uuid4().hex[:8]}",
        "tipo_equipo": "BOTIQUÍN",
        "area": "MINA",
        "equipo": "EMERGENCIA",
    }).json()
    inspeccion = client.post("/botiquin_inspecciones/", json={
        "botiquin_id": botiquin["id"],
        "insumos": [
            {"medicamento_id": gasa["id"], "cantidad": 4},
            {"medicamento_id": tijera["id"], "cantidad": 1},
        ],
    })
    assert inspeccion.status_code == 200, inspeccion.text
    return gasa, tijera


def _nombres(reporte):
    return sorted(i["nombre"] for i in reporte["insumos"])


def test_reporte_sin_filtro_de_producto_trae_todos(client):
    _inspeccion_con_dos_insumos(client)

    reporte = client.get("/reportes/consumo-insumos-botiquin").json()

    assert _nombres(reporte) == ["GASA ESTERIL", "TIJERA DE TRAUMA"]


def test_reporte_filtra_por_un_producto(client):
    _, tijera = _inspeccion_con_dos_insumos(client)

    reporte = client.get(
        "/reportes/consumo-insumos-botiquin", params={"medicamento_id": tijera["id"]}
    ).json()

    assert _nombres(reporte) == ["TIJERA DE TRAUMA"]
    assert reporte["insumos"][0]["sub_total_cantidad"] == 1


def test_reporte_filtra_por_varios_productos(client):
    gasa, tijera = _inspeccion_con_dos_insumos(client)

    reporte = client.get(
        "/reportes/consumo-insumos-botiquin",
        params={"medicamento_id": f"{gasa['id']},{tijera['id']}"},
    ).json()

    assert _nombres(reporte) == ["GASA ESTERIL", "TIJERA DE TRAUMA"]


def test_reporte_con_producto_inexistente_queda_vacio(client):
    _inspeccion_con_dos_insumos(client)

    reporte = client.get(
        "/reportes/consumo-insumos-botiquin", params={"medicamento_id": "no-existe"}
    ).json()

    assert reporte["insumos"] == []
