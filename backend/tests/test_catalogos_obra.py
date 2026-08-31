"""OBRA tiene que existir en sistemas clinicos y contingencias.

Los catalogos son solo de base de datos: Atenciones y el Dashboard cargan
GET /sistemas/ y GET /clasificaciones/ sin filtrar por nombre. La semilla
de arranque inserta OBRA si falta, para que aparezca en esos desplegables
sin que alguien tenga que cargarla a mano.
"""
import models
from database import engine
from migraciones import sembrar_catalogos


def test_sembrar_obra_en_ambos_catalogos_es_idempotente(client, db):
    sembrar_catalogos(engine)
    sembrar_catalogos(engine)
    db.expire_all()

    sistemas = [
        s.nombre
        for s in db.query(models.SistemaAtencion).filter(models.SistemaAtencion.is_deleted == False)  # noqa: E712
    ]
    clasificaciones = [
        c.nombre
        for c in db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.is_deleted == False)  # noqa: E712
    ]
    assert sistemas.count("OBRA") == 1
    assert clasificaciones.count("OBRA") == 1


def test_listados_del_api_incluyen_obra(client):
    sembrar_catalogos(engine)
    nombres_sistemas = [s["nombre"] for s in client.get("/sistemas/").json()]
    nombres_contingencias = [c["nombre"] for c in client.get("/clasificaciones/").json()]
    assert "OBRA" in nombres_sistemas
    assert "OBRA" in nombres_contingencias


def test_sembrar_obra_reactiva_si_estaba_borrada(client, db):
    sembrar_catalogos(engine)
    db.expire_all()
    sistema = db.query(models.SistemaAtencion).filter(models.SistemaAtencion.nombre == "OBRA").one()
    clasificacion = (
        db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.nombre == "OBRA").one()
    )
    sistema.is_deleted = True
    clasificacion.is_deleted = True
    db.commit()

    sembrar_catalogos(engine)
    db.expire_all()
    assert db.query(models.SistemaAtencion).filter(models.SistemaAtencion.nombre == "OBRA").one().is_deleted is False
    assert (
        db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.nombre == "OBRA").one().is_deleted
        is False
    )


def test_sembrar_no_duplica_si_ya_existe_con_otra_capitalizacion(client, db):
    db.add(models.SistemaAtencion(nombre="Obra"))
    db.add(models.ClasificacionAtencion(nombre="obra"))
    db.commit()

    sembrar_catalogos(engine)
    db.expire_all()
    assert db.query(models.SistemaAtencion).filter(models.SistemaAtencion.is_deleted == False).count() == 1  # noqa: E712
    assert db.query(models.ClasificacionAtencion).filter(models.ClasificacionAtencion.is_deleted == False).count() == 1  # noqa: E712
