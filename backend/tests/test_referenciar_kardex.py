"""Reconstruccion de la referencia de movimientos viejos (referenciar_kardex.py).

Se arma la historia como la dejaba la version anterior -- filas de kardex sin
observacion -- y se comprueba que cada movimiento termine apuntando a su ficha.
"""
from datetime import datetime, timedelta

import pytest

import models
import referenciar_kardex
from database import Base, engine

T0 = datetime(2026, 9, 1, 15, 0, 0)


@pytest.fixture
def historia(db):
    Base.metadata.create_all(bind=engine)
    for modelo in (models.AtencionMedicamento, models.Kardex, models.Atencion, models.Medicamento):
        db.query(modelo).delete()
    naproxeno = models.Medicamento(nombre="NAPROXENO", codigo="T-1")
    loratadina = models.Medicamento(nombre="LORATADINA", codigo="T-2")
    db.add_all([naproxeno, loratadina])
    db.flush()

    def atencion(folio, creada, editada, receta):
        fila = models.Atencion(folio=folio, created_at=creada, updated_at=editada)
        db.add(fila)
        db.flush()
        for medicamento, cantidad in receta:
            db.add(models.AtencionMedicamento(
                atencion_id=fila.id, medicamento_id=medicamento.id, cantidad=cantidad))
        return fila

    def movimiento(cuando, tipo, medicamento, cantidad, observacion=None):
        fila = models.Kardex(fecha=cuando, created_at=cuando, tipo_movimiento=tipo,
                             medicamento_id=medicamento.id, cantidad=cantidad, saldo=0,
                             observacion=observacion)
        db.add(fila)
        return fila

    # Ficha 10: alta con 6 + 6; a la hora se edita y el naproxeno pasa a 10.
    # Ficha 11: misma receta inicial, nunca editada.
    f10 = atencion(10, T0, T0 + timedelta(hours=1), [(naproxeno, 10), (loratadina, 6)])
    f11 = atencion(11, T0 + timedelta(minutes=5), T0 + timedelta(minutes=5),
                   [(naproxeno, 6), (loratadina, 6)])
    movs = {
        "alta10": movimiento(T0, "SALIDA", naproxeno, 6),
        "alta11": movimiento(T0 + timedelta(minutes=5), "SALIDA", naproxeno, 6),
        "dev10": movimiento(T0 + timedelta(hours=1), "INGRESO", naproxeno, 6),
        "sal10": movimiento(T0 + timedelta(hours=1, microseconds=500), "SALIDA", naproxeno, 10),
        "manual": movimiento(T0 + timedelta(days=1), "INGRESO", loratadina, 50),
        "con_obs": movimiento(T0 + timedelta(days=2), "SALIDA", loratadina, 1, "Reposición botiquín B-1"),
    }
    for clave, cuando in (("alta10b", T0), ("alta11b", T0 + timedelta(minutes=5))):
        movs[clave] = movimiento(cuando, "SALIDA", loratadina, 6)
    movs["dev10b"] = movimiento(T0 + timedelta(hours=1), "INGRESO", loratadina, 6)
    movs["sal10b"] = movimiento(T0 + timedelta(hours=1, microseconds=600), "SALIDA", loratadina, 6)
    db.commit()
    return {"f10": f10.id, "f11": f11.id, **{k: v.id for k, v in movs.items()}}


def _aplicar():
    with engine.begin() as conexion:
        plan, *_ = referenciar_kardex.reconstruir(conexion)
        referenciar_kardex.aplicar(conexion, plan)
    return plan


def _fila(db, kardex_id):
    db.expire_all()
    return db.query(models.Kardex).filter(models.Kardex.id == kardex_id).one()


def test_cada_movimiento_queda_apuntando_a_su_ficha(db, historia):
    _aplicar()

    assert _fila(db, historia["alta10"]).observacion == "Atención N.º 10"
    assert _fila(db, historia["alta11"]).observacion == "Atención N.º 11"
    # Las dos fichas tenian la misma receta: la edicion es de la 10 porque es
    # la unica editada a esa hora.
    devolucion = _fila(db, historia["dev10"])
    assert devolucion.observacion == "Devolución por edición de atención N.º 10"
    assert devolucion.atencion_id == historia["f10"]
    assert _fila(db, historia["sal10"]).observacion == "Edición de atención N.º 10"


def test_lo_que_no_es_de_una_atencion_y_lo_ya_referenciado(db, historia):
    _aplicar()

    manual = _fila(db, historia["manual"])
    assert manual.observacion == "Registro manual en Almacén"
    assert manual.atencion_id is None
    assert _fila(db, historia["con_obs"]).observacion == "Reposición botiquín B-1"


def test_una_vez_aplicado_no_se_vuelve_a_correr(db, historia):
    """Despues de aplicarlo, lo que queda sin referencia ya no tiene su
    historia completa: atribuirlo de nuevo seria adivinar."""
    with engine.connect() as conexion:
        assert not referenciar_kardex.ya_aplicado(conexion)
    _aplicar()
    with engine.connect() as conexion:
        assert referenciar_kardex.ya_aplicado(conexion)


def test_las_referencias_del_sistema_no_cuentan_como_aplicado(client):
    """Una atencion nueva tambien escribe 'Atención N.º X', pero con usuario."""
    sistema = client.post("/sistemas/", json={"nombre": "RESPIRATORIO"}).json()
    clasificacion = client.post("/clasificaciones/", json={"nombre": "COMUN"}).json()
    trabajador = client.post("/trabajadores/", json={
        "nombre": "Ana", "apellidos": "Quispe", "dni": "40404040", "rol": "Operario",
    }).json()
    medicamento = client.post("/medicamentos/", json={"nombre": "PARACETAMOL", "presentacion": "TAB"}).json()
    client.post("/kardex/", json={"medicamento_id": medicamento["id"], "tipo_movimiento": "INGRESO",
                                  "cantidad": 5, "observacion": "Compra"})
    client.post("/atenciones/", json={
        "descripcion": "Dolor", "trabajador_id": trabajador["id"], "sistema_id": sistema["id"],
        "clasificacion_id": clasificacion["id"],
        "medicamentos": [{"medicamento_id": medicamento["id"], "cantidad": 1}],
    })

    with engine.connect() as conexion:
        assert not referenciar_kardex.ya_aplicado(conexion)
