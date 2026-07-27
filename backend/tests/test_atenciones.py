"""Listado de atenciones."""
import models


def _catalogos(client):
    sistema = client.post("/sistemas/", json={"nombre": "RESPIRATORIO"}).json()
    clasificacion = client.post("/clasificaciones/", json={"nombre": "COMUN"}).json()
    trabajador = client.post("/trabajadores/", json={
        "nombre": "Juan", "apellidos": "Perez", "dni": "12345678", "rol": "OBRERO",
    }).json()
    return sistema, clasificacion, trabajador


def test_una_atencion_incompleta_no_tumba_todo_el_listado(client, db):
    """FastAPI valida la respuesta entera: cuando trabajador/sistema/
    clasificacion eran obligatorios en el schema de salida, UNA fila con esos
    campos en NULL hacia fallar GET /atenciones/ con 500 y la pantalla de
    Atenciones quedaba vacia, sin mostrar ninguna de las demas atenciones ni
    ningun mensaje de error."""
    sistema, clasificacion, trabajador = _catalogos(client)
    client.post("/atenciones/", json={
        "descripcion": "consulta normal", "trabajador_id": trabajador["id"],
        "sistema_id": sistema["id"], "clasificacion_id": clasificacion["id"],
    })

    # Fila incompleta, como las que dejan los registros viejos o los datos que
    # llegaron a medias.
    db.add(models.Atencion(descripcion="incompleta", trabajador_id=None,
                           sistema_id=None, clasificacion_id=None, folio=999))
    db.commit()

    respuesta = client.get("/atenciones/")
    assert respuesta.status_code == 200

    datos = respuesta.json()
    assert len(datos) == 2, "la atencion valida tiene que seguir apareciendo"
    incompleta = next(a for a in datos if a["descripcion"] == "incompleta")
    assert incompleta["trabajador"] is None
    assert incompleta["sistema"] is None


def test_el_listado_devuelve_las_atenciones_completas(client):
    sistema, clasificacion, trabajador = _catalogos(client)
    for i in range(3):
        client.post("/atenciones/", json={
            "descripcion": f"consulta {i}", "trabajador_id": trabajador["id"],
            "sistema_id": sistema["id"], "clasificacion_id": clasificacion["id"],
        })

    datos = client.get("/atenciones/").json()
    assert len(datos) == 3
    assert all(a["trabajador"]["dni"] == "12345678" for a in datos)
    assert sorted(a["folio"] for a in datos) == [1, 2, 3]
