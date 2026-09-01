"""OBRA ya no es un item de sistemas ni contingencias: es un catalogo propio.

Las obras se cargan en GET/POST/PUT/DELETE /obras/ y se eligen en Planilla,
Atenciones y los filtros de Consumo/Dashboard. El arranque quita el item
OBRA que se sembró por error en sistemas/clasificaciones, sin borrar
trabajadores.obra.
"""
import models
from database import engine
from migraciones import aplicar, limpiar_obra_de_catalogos_clinicos, sembrar_obras_desde_planilla


def test_crud_obras(client):
    creado = client.post("/obras/", json={"nombre": "Mina Norte"}).json()
    assert creado["nombre"] == "Mina Norte"
    assert creado["id"]

    nombres = [o["nombre"] for o in client.get("/obras/").json()]
    assert nombres.count("Mina Norte") == 1

    editado = client.put(f"/obras/{creado['id']}", json={"nombre": "Mina Sur"}).json()
    assert editado["nombre"] == "Mina Sur"
    assert "Mina Norte" not in [o["nombre"] for o in client.get("/obras/").json()]

    client.delete(f"/obras/{creado['id']}")
    assert client.get("/obras/").json() == []


def test_obras_rechaza_duplicado(client):
    assert client.post("/obras/", json={"nombre": "Tajo"}).status_code == 200
    segundo = client.post("/obras/", json={"nombre": "Tajo"})
    assert segundo.status_code == 400


def test_aplicar_no_siembra_obra_en_sistemas_ni_clasificaciones(client, db):
    aplicar(engine)
    db.expire_all()
    sistemas = [
        s.nombre
        for s in db.query(models.SistemaAtencion).filter(models.SistemaAtencion.is_deleted == False)  # noqa: E712
    ]
    clasificaciones = [
        c.nombre
        for c in db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.is_deleted == False)  # noqa: E712
    ]
    assert all(n.upper() != "OBRA" for n in sistemas)
    assert all(n.upper() != "OBRA" for n in clasificaciones)


def test_listados_del_api_no_incluyen_obra_sembrada(client):
    aplicar(engine)
    nombres_sistemas = [s["nombre"] for s in client.get("/sistemas/").json()]
    nombres_contingencias = [c["nombre"] for c in client.get("/clasificaciones/").json()]
    assert "OBRA" not in nombres_sistemas
    assert "OBRA" not in nombres_contingencias


def test_limpiar_obra_soft_delete_es_idempotente_y_no_toca_planilla(client, db):
    db.add(models.SistemaAtencion(nombre="OBRA"))
    db.add(models.ClasificacionAtencion(nombre="obra"))
    db.add(models.Trabajador(
        nombre="Ana", apellidos="Lopez", dni="87654321", rol="OBRERO", obra="Proyecto Alpha",
    ))
    db.commit()

    limpiar_obra_de_catalogos_clinicos(engine)
    limpiar_obra_de_catalogos_clinicos(engine)
    db.expire_all()

    sistema = db.query(models.SistemaAtencion).filter(models.SistemaAtencion.nombre == "OBRA").one()
    clasificacion = (
        db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.nombre == "obra").one()
    )
    trabajador = db.query(models.Trabajador).filter(models.Trabajador.dni == "87654321").one()
    assert sistema.is_deleted is True
    assert clasificacion.is_deleted is True
    assert trabajador.obra == "Proyecto Alpha"
    assert trabajador.is_deleted is False


def test_limpiar_no_toca_otros_nombres(client, db):
    db.add(models.SistemaAtencion(nombre="RESPIRATORIO"))
    db.add(models.ClasificacionAtencion(nombre="COMUN"))
    db.commit()

    limpiar_obra_de_catalogos_clinicos(engine)
    db.expire_all()

    assert db.query(models.SistemaAtencion).filter(models.SistemaAtencion.nombre == "RESPIRATORIO").one().is_deleted is False
    assert db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.nombre == "COMUN").one().is_deleted is False


def test_sembrar_obras_desde_planilla_es_idempotente(client, db):
    db.add(models.Trabajador(
        nombre="Luis", apellidos="Diaz", dni="11223344", rol="OBRERO", obra="Campamento Este",
    ))
    db.commit()

    sembrar_obras_desde_planilla(engine)
    sembrar_obras_desde_planilla(engine)
    db.expire_all()

    vigentes = [
        o.nombre
        for o in db.query(models.Obra).filter(models.Obra.is_deleted == False)  # noqa: E712
    ]
    assert vigentes.count("Campamento Este") == 1
    assert any(o["nombre"] == "Campamento Este" for o in client.get("/obras/").json())
