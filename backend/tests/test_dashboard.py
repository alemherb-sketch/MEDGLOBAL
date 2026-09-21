"""Cifras del dashboard."""
import datetime

import models
from database import SessionLocal


def _sembrar_atenciones(dias):
    """Una atencion por cada dia indicado (offset en dias hacia atras)."""
    sesion = SessionLocal()
    sistema = models.SistemaAtencion(nombre="GENERAL")
    trabajador = models.Trabajador(nombre="Luis", apellidos="Rojas", dni="51515151", rol="Operario")
    sesion.add_all([sistema, trabajador])
    sesion.flush()
    hoy = datetime.datetime(2026, 6, 30)
    for offset in dias:
        sesion.add(models.Atencion(
            descripcion="control",
            fecha=hoy - datetime.timedelta(days=offset),
            trabajador_id=trabajador.id,
            sistema_id=sistema.id,
        ))
    sesion.commit()
    sesion.close()
    return hoy


def test_atenciones_por_dia_muestra_los_ultimos_dias_no_los_primeros(client):
    """El grafico se corta en 14 dias. Ordenando ascendente, ese limite se
    quedaba con los 14 dias MAS ANTIGUOS: un consultorio con un año de
    historial veia siempre el arranque del historial en vez del mes en curso.
    """
    hoy = _sembrar_atenciones(range(30))  # 30 dias consecutivos

    dias = client.get("/dashboard/stats").json()["atenciones_por_dia"]

    assert len(dias) == 14
    # El ultimo punto del grafico tiene que ser el dia mas reciente.
    assert dias[-1]["name"] == hoy.date().isoformat()
    # Y la serie va de mas antiguo a mas nuevo, para graficar de izquierda a derecha.
    assert [d["name"] for d in dias] == sorted(d["name"] for d in dias)


def test_los_kpis_pueden_acotarse_a_un_rango_de_fechas(client):
    """Las fechas del encabezado no cambiaban nada en pantalla: alimentaban un
    endpoint cuya respuesta el dashboard descartaba."""
    _sembrar_atenciones([0, 1, 40, 41])  # dos recientes y dos viejas

    todas = client.get("/dashboard/kpis").json()
    assert todas["total_atenciones"] == 4

    recientes = client.get(
        "/dashboard/kpis", params={"fecha_inicio": "2026-06-25", "fecha_fin": "2026-06-30"}
    ).json()
    assert recientes["total_atenciones"] == 2

    # Los inventarios del momento no dependen del rango.
    assert recientes["total_trabajadores"] == todas["total_trabajadores"]
    assert recientes["total_medicamentos"] == todas["total_medicamentos"]


def test_enfermedades_del_dashboard_usan_el_cie10_principal(client):
    """El ranking leia el campo legado `diagnostico`, vacio en atenciones
    nuevas, y las enfermedades mas frecuentes salian vacias."""
    sesion = SessionLocal()
    sistema = models.SistemaAtencion(nombre="PIEL")
    trabajador = models.Trabajador(nombre="Ana", apellidos="Diaz", dni="61616161", rol="Operario")
    sesion.add_all([sistema, trabajador])
    sesion.flush()
    sesion.add(models.Atencion(
        descripcion="consulta",
        trabajador_id=trabajador.id,
        sistema_id=sistema.id,
        diagnostico_1="L08.9 - Infeccion local de la piel",
        diagnostico="",
    ))
    sesion.commit()
    sesion.close()

    enfermedades = client.get("/dashboard/stats").json()["enfermedades"]
    assert [e["name"] for e in enfermedades] == ["L08.9 - Infeccion local de la piel"]
