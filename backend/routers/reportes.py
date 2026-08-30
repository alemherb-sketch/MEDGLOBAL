"""Dashboard y reportes.

Todo lo de aca es solo lectura y agrega sobre muchas filas, asi que la regla
es: agrupar en la base cuando se puede, y cuando hay que recorrer en Python
traer las relaciones de una vez (`joinedload`/`selectinload`). Antes varios de
estos endpoints recorrian miles de atenciones leyendo `a.trabajador`,
`a.empresa` y `a.medicamentos` de a una fila: cada acceso era una consulta
nueva y el reporte tardaba mas cuanto mas datos habia.
"""
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

import models
from dependencias import RequiereSesion, SesionDB

router = APIRouter(dependencies=[RequiereSesion])

IGV = 1.18
SIN_DATO = "—"


def _filtrar_por_fecha(consulta, columna, desde: Optional[str], hasta: Optional[str]):
    if desde:
        consulta = consulta.filter(func.date(columna) >= desde)
    if hasta:
        consulta = consulta.filter(func.date(columna) <= hasta)
    return consulta


def _lista_de_ids(valor: Optional[str]):
    """Un parametro que acepta varios ids separados por coma."""
    if not valor:
        return []
    return [x.strip() for x in str(valor).split(",") if x and x.strip()]


def _filtrar_por_lista(consulta, columna, valor: Optional[str], comparacion="exacta"):
    valores = _lista_de_ids(valor)
    if not valores:
        return consulta
    if len(valores) == 1:
        if comparacion == "parcial":
            return consulta.filter(columna.ilike(f"%{valores[0]}%"))
        return consulta.filter(columna == valores[0])
    return consulta.filter(columna.in_(valores))


def _totales_con_igv(total: float) -> dict:
    """El total incluye IGV; se desglosa hacia atras, como en las facturas."""
    total = round(total, 2)
    sub_total = round(total / IGV, 2) if total else 0.0
    return {"sub_total": sub_total, "igv": round(total - sub_total, 2) if total else 0.0, "total": total}


def _atenciones_con_relaciones(db, desde, hasta, filtros_extra=None):
    consulta = (
        db.query(models.Atencion)
        .options(
            joinedload(models.Atencion.trabajador),
            joinedload(models.Atencion.empresa),
            selectinload(models.Atencion.medicamentos).joinedload(models.AtencionMedicamento.medicamento),
        )
        .filter(models.Atencion.is_deleted == False)  # noqa: E712
    )
    for filtro in filtros_extra or []:
        consulta = consulta.filter(filtro)
    return _filtrar_por_fecha(consulta, models.Atencion.fecha, desde, hasta).all()


# --- Indicadores ------------------------------------------------------------

STOCK_BAJO = 10


@router.get("/dashboard/kpis", tags=["dashboard"])
def indicadores(db: SesionDB, fecha_inicio: str = None, fecha_fin: str = None):
    """Cifras de las tarjetas del dashboard.

    El rango de fechas aplica SOLO a las atenciones, que es lo unico que
    ocurre en un periodo. Los otros tres son inventarios del momento: cuantos
    trabajadores hay registrados, cuantos productos tiene el catalogo y
    cuantos estan por debajo del minimo. Filtrarlos por fecha no querria decir
    nada.
    """
    def contar(model):
        return db.query(model).filter(model.is_deleted == False).count()  # noqa: E712

    atenciones = db.query(models.Atencion).filter(models.Atencion.is_deleted == False)  # noqa: E712

    return {
        "total_atenciones": _filtrar_por_fecha(
            atenciones, models.Atencion.fecha, fecha_inicio, fecha_fin
        ).count(),
        "total_trabajadores": contar(models.Trabajador),
        "total_medicamentos": contar(models.Medicamento),
        "medicamentos_stock_bajo": db.query(models.Medicamento).filter(
            models.Medicamento.is_deleted == False,  # noqa: E712
            models.Medicamento.stock_actual < STOCK_BAJO,
        ).count(),
    }


@router.get("/dashboard/stats", tags=["dashboard"])
def estadisticas(db: SesionDB, fecha_inicio: str = None, fecha_fin: str = None):
    def por_fecha(consulta):
        return _filtrar_por_fecha(consulta, models.Atencion.fecha, fecha_inicio, fecha_fin)

    vigentes = models.Atencion.is_deleted == False  # noqa: E712
    total = func.count(models.Atencion.id)

    enfermedades = por_fecha(
        db.query(models.Atencion.diagnostico, total.label("total")).filter(
            vigentes,
            models.Atencion.diagnostico.isnot(None),
            models.Atencion.diagnostico != "",
        )
    ).group_by(models.Atencion.diagnostico).order_by(total.desc()).limit(5).all()

    pacientes = por_fecha(
        db.query(models.Trabajador.nombre, models.Trabajador.apellidos, total.label("total"))
        .join(models.Atencion, models.Trabajador.id == models.Atencion.trabajador_id)
        .filter(vigentes)
    ).group_by(models.Trabajador.id).order_by(total.desc()).limit(5).all()

    empresas = por_fecha(
        db.query(models.Empresa.nombre, total.label("total"))
        .join(models.Atencion, models.Empresa.id == models.Atencion.empresa_id)
        .filter(vigentes)
    ).group_by(models.Empresa.id).order_by(total.desc()).limit(5).all()

    unidades = func.sum(models.AtencionMedicamento.cantidad)
    medicamentos = por_fecha(
        db.query(models.Medicamento.nombre, unidades.label("total"))
        .join(models.AtencionMedicamento, models.Medicamento.id == models.AtencionMedicamento.medicamento_id)
        .join(models.Atencion, models.Atencion.id == models.AtencionMedicamento.atencion_id)
        .filter(vigentes)
    ).group_by(models.Medicamento.id).order_by(unidades.desc()).limit(5).all()

    gasto = func.sum(models.AtencionMedicamento.cantidad * models.Medicamento.costo_unitario)
    costos = por_fecha(
        db.query(models.Empresa.nombre, gasto.label("total_costo"))
        .join(models.Atencion, models.Empresa.id == models.Atencion.empresa_id)
        .join(models.AtencionMedicamento, models.Atencion.id == models.AtencionMedicamento.atencion_id)
        .join(models.Medicamento, models.AtencionMedicamento.medicamento_id == models.Medicamento.id)
        .filter(vigentes)
    ).group_by(models.Empresa.id).order_by(gasto.desc()).limit(10).all()

    estados = (
        db.query(models.Empresa.estado, func.count(models.Empresa.id).label("total"))
        .filter(models.Empresa.is_deleted == False)  # noqa: E712
        .group_by(models.Empresa.estado)
        .all()
    )

    # Los 14 dias MAS RECIENTES: se ordena descendente para quedarse con el
    # final de la serie y recien despues se invierte para graficar de izquierda
    # a derecha. Ordenando ascendente, el limite se quedaba con los 14 dias mas
    # ANTIGUOS y el grafico mostraba siempre el arranque del historial.
    dia = func.date(models.Atencion.fecha)
    ultimos_dias = por_fecha(
        db.query(dia.label("dia"), total.label("total")).filter(vigentes)
    ).group_by(dia).order_by(dia.desc()).limit(14).all()

    sistemas = por_fecha(
        db.query(models.SistemaAtencion.nombre, total.label("total"))
        .join(models.Atencion, models.SistemaAtencion.id == models.Atencion.sistema_id)
        .filter(vigentes)
    ).group_by(models.SistemaAtencion.id).order_by(total.desc()).limit(10).all()

    ultimas = (
        por_fecha(
            db.query(models.Atencion)
            .options(joinedload(models.Atencion.trabajador), joinedload(models.Atencion.sistema))
            .filter(vigentes)
        )
        .order_by(models.Atencion.fecha.desc())
        .limit(10)
        .all()
    )

    return {
        "enfermedades": [{"name": str(e.diagnostico), "value": int(e.total)} for e in enfermedades],
        "pacientes": [{"name": f"{p.nombre} {p.apellidos}", "value": int(p.total)} for p in pacientes],
        "empresas": [{"name": str(e.nombre), "value": int(e.total)} for e in empresas],
        "medicamentos": [{"name": str(m.nombre), "value": int(m.total or 0)} for m in medicamentos],
        "costos": [{"name": str(c.nombre), "value": float(c.total_costo or 0)} for c in costos],
        "estado_empresas": [{"name": str(e.estado or "Desconocido"), "value": int(e.total)} for e in estados],
        "atenciones_por_dia": [
            {"name": str(d.dia), "value": int(d.total)} for d in reversed(ultimos_dias)
        ],
        "ultimas_atenciones": [
            {
                "id": a.id,
                "fecha": str(a.fecha.date()) if a.fecha else "",
                "paciente": f"{a.trabajador.nombre} {a.trabajador.apellidos}" if a.trabajador else "N/A",
                "diagnostico": str(a.diagnostico or ""),
                "sistema": a.sistema.nombre if a.sistema else "N/A",
            }
            for a in ultimas
        ],
        "sistemas_afectados": [{"name": str(s.nombre), "value": int(s.total)} for s in sistemas],
    }


@router.get("/dashboard/reporte-sistemas", tags=["dashboard"])
def reporte_sistemas(
    db: SesionDB,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    sistema_id: Optional[str] = None,
    empresa_id: Optional[str] = None,
    obra: str = None,
):
    total = func.count(models.Atencion.id)
    consulta = (
        db.query(models.SistemaAtencion.nombre, total.label("total"))
        .join(models.Atencion, models.SistemaAtencion.id == models.Atencion.sistema_id)
        .filter(models.Atencion.is_deleted == False)  # noqa: E712
    )
    consulta = _filtrar_por_fecha(consulta, models.Atencion.fecha, fecha_inicio, fecha_fin)
    if sistema_id:
        consulta = consulta.filter(models.Atencion.sistema_id == sistema_id)
    consulta = _filtrar_por_lista(consulta, models.Atencion.empresa_id, empresa_id)
    if obra:
        consulta = consulta.join(
            models.Trabajador, models.Atencion.trabajador_id == models.Trabajador.id
        ).filter(models.Trabajador.obra == obra)

    filas = consulta.group_by(models.SistemaAtencion.id).order_by(total.desc()).all()
    return {
        "total_general": sum(f.total for f in filas),
        "sistemas": [{"name": str(f.nombre), "value": int(f.total)} for f in filas],
    }


# --- Detalle de cada tarjeta del dashboard ----------------------------------

def _detalle_enfermedades(db, desde, hasta):
    agrupado = defaultdict(list)
    for a in _atenciones_con_relaciones(db, desde, hasta, [
        models.Atencion.diagnostico.isnot(None), models.Atencion.diagnostico != "",
    ]):
        trabajador, empresa = a.trabajador, a.empresa
        agrupado[a.diagnostico].append({
            "fecha": a.fecha.strftime("%d/%m/%Y") if a.fecha else "",
            "paciente": f"{trabajador.nombre} {trabajador.apellidos}" if trabajador else SIN_DATO,
            "dni": trabajador.dni if trabajador else SIN_DATO,
            "empresa": empresa.nombre if empresa else SIN_DATO,
            "area": (trabajador.area or SIN_DATO) if trabajador else SIN_DATO,
        })
    ordenado = sorted(agrupado.items(), key=lambda par: len(par[1]), reverse=True)
    return [{"name": diag, "total": len(items), "details": items} for diag, items in ordenado][:10]


def _detalle_pacientes(db, desde, hasta):
    agrupado = defaultdict(list)
    datos_paciente = {}
    for a in _atenciones_con_relaciones(db, desde, hasta):
        trabajador = a.trabajador
        if not trabajador:
            continue
        datos_paciente[trabajador.id] = {
            "name": f"{trabajador.nombre} {trabajador.apellidos}",
            "dni": trabajador.dni,
            "cargo": trabajador.cargo or SIN_DATO,
            "area": trabajador.area or SIN_DATO,
        }
        agrupado[trabajador.id].append({
            "fecha": a.fecha.strftime("%d/%m/%Y") if a.fecha else "",
            "diagnostico": a.diagnostico or SIN_DATO,
            "empresa": a.empresa.nombre if a.empresa else SIN_DATO,
            "destino": a.destino or SIN_DATO,
        })
    ordenado = sorted(agrupado.items(), key=lambda par: len(par[1]), reverse=True)
    return [
        {**datos_paciente[tid], "total": len(items), "details": items} for tid, items in ordenado
    ][:10]


def _detalle_empresas(db, desde, hasta):
    agrupado = defaultdict(list)
    datos_empresa = {}
    for a in _atenciones_con_relaciones(db, desde, hasta, [models.Atencion.empresa_id.isnot(None)]):
        empresa = a.empresa
        if not empresa:
            continue
        datos_empresa[empresa.id] = {"name": empresa.nombre, "ruc": empresa.ruc}
        trabajador = a.trabajador
        agrupado[empresa.id].append({
            "fecha": a.fecha.strftime("%d/%m/%Y") if a.fecha else "",
            "paciente": f"{trabajador.nombre} {trabajador.apellidos}" if trabajador else SIN_DATO,
            "diagnostico": a.diagnostico or SIN_DATO,
            "destino": a.destino or SIN_DATO,
        })
    ordenado = sorted(agrupado.items(), key=lambda par: len(par[1]), reverse=True)
    return [
        {**datos_empresa[eid], "total": len(items), "details": items} for eid, items in ordenado
    ][:10]


def _detalle_medicamentos(db, desde, hasta):
    unidades = func.sum(models.AtencionMedicamento.cantidad)
    consulta = (
        db.query(
            models.Medicamento.nombre,
            models.Medicamento.presentacion,
            models.Medicamento.costo_unitario,
            models.Medicamento.stock_actual,
            unidades.label("total"),
        )
        .join(models.AtencionMedicamento, models.Medicamento.id == models.AtencionMedicamento.medicamento_id)
        .join(models.Atencion, models.Atencion.id == models.AtencionMedicamento.atencion_id)
        .filter(models.Atencion.is_deleted == False)  # noqa: E712
    )
    filas = (
        _filtrar_por_fecha(consulta, models.Atencion.fecha, desde, hasta)
        .group_by(models.Medicamento.id)
        .order_by(unidades.desc())
        .limit(10)
        .all()
    )
    resultado = []
    for f in filas:
        costo = float(f.costo_unitario or 0)
        cantidad = int(f.total or 0)
        resultado.append({
            "name": str(f.nombre),
            "presentacion": str(f.presentacion or SIN_DATO),
            "costo_unitario": costo,
            "stock_actual": int(f.stock_actual or 0),
            "total": cantidad,
            "costo_total": round(costo * cantidad, 2),
        })
    return resultado


def _detalle_costos(db, desde, hasta):
    empresas = {}
    for a in _atenciones_con_relaciones(db, desde, hasta, [models.Atencion.empresa_id.isnot(None)]):
        empresa = a.empresa
        if not empresa:
            continue
        datos = empresas.setdefault(
            empresa.id, {"name": empresa.nombre, "ruc": empresa.ruc or SIN_DATO, "meds": {}}
        )
        for recetado in a.medicamentos:
            medicamento = recetado.medicamento
            if not medicamento:
                continue
            linea = datos["meds"].setdefault(medicamento.id, {
                "medicamento": medicamento.nombre,
                "presentacion": medicamento.presentacion or "",
                "cantidad": 0,
                "costo_unitario": float(medicamento.costo_unitario or 0),
            })
            linea["cantidad"] += recetado.cantidad

    resultado = []
    for datos in empresas.values():
        detalles, total = [], 0.0
        for linea in datos["meds"].values():
            subtotal = linea["cantidad"] * linea["costo_unitario"]
            total += subtotal
            detalles.append({**linea, "subtotal": round(subtotal, 2)})
        resultado.append({
            "name": datos["name"],
            "ruc": datos["ruc"],
            "total": round(total, 2),
            "details": sorted(detalles, key=lambda d: d["subtotal"], reverse=True),
        })
    resultado.sort(key=lambda e: e["total"], reverse=True)
    return resultado[:10]


DETALLES = {
    "enfermedades": _detalle_enfermedades,
    "pacientes": _detalle_pacientes,
    "empresas": _detalle_empresas,
    "medicamentos": _detalle_medicamentos,
    "costos": _detalle_costos,
}


@router.get("/dashboard/report/{report_type}", tags=["dashboard"])
def detalle_de_reporte(report_type: str, db: SesionDB, fecha_inicio: str = None, fecha_fin: str = None):
    generar = DETALLES.get(report_type)
    return generar(db, fecha_inicio, fecha_fin) if generar else []


# --- Reportes de consumo ----------------------------------------------------

@router.get("/reportes/consumo-medicamentos", tags=["reportes"])
def consumo_medicamentos(
    db: SesionDB,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    empresa_id: Optional[str] = None,
    obra: str = None,
):
    consulta = (
        db.query(models.AtencionMedicamento, models.Atencion, models.Medicamento)
        .join(models.Atencion, models.Atencion.id == models.AtencionMedicamento.atencion_id)
        .join(models.Medicamento, models.Medicamento.id == models.AtencionMedicamento.medicamento_id)
        .filter(models.Atencion.is_deleted == False)  # noqa: E712
    )
    consulta = _filtrar_por_fecha(consulta, models.Atencion.fecha, fecha_inicio, fecha_fin)
    if empresa_id:
        consulta = consulta.filter(models.Atencion.empresa_id == empresa_id)
    if obra:
        consulta = consulta.join(
            models.Trabajador, models.Atencion.trabajador_id == models.Trabajador.id
        ).filter(models.Trabajador.obra == obra)

    por_medicamento, fechas = {}, set()
    # Se usa el `medicamento` que YA trajo el JOIN. Antes esta linea lo pisaba
    # con `am.medicamento`, que dispara una consulta por cada fila del reporte.
    for recetado, atencion, medicamento in consulta.all():
        if not atencion.fecha:
            continue
        fecha = atencion.fecha.strftime("%Y-%m-%d")
        fechas.add(fecha)
        acumulado = por_medicamento.setdefault(medicamento.id, {
            "id": medicamento.id,
            "codigo": medicamento.codigo or "",
            "nombre": medicamento.nombre or "",
            "presentacion": medicamento.presentacion or "",
            "precio_und": float(medicamento.costo_unitario or 0),
            "consumos": defaultdict(int),
            "sub_total_cantidad": 0,
            "total_soles": 0.0,
        })
        cantidad = recetado.cantidad or 0
        acumulado["consumos"][fecha] += cantidad
        acumulado["sub_total_cantidad"] += cantidad

    lista, total_general = [], 0.0
    for acumulado in por_medicamento.values():
        acumulado["total_soles"] = round(acumulado["sub_total_cantidad"] * acumulado["precio_und"], 2)
        total_general += acumulado["total_soles"]
        acumulado["consumos"] = dict(acumulado["consumos"])
        lista.append(acumulado)

    return {
        "rango_fechas": sorted(fechas),
        "medicamentos": lista,
        "totales": _totales_con_igv(total_general),
    }


@router.get("/reportes/consumo-insumos-botiquin", tags=["reportes"])
def consumo_insumos_botiquin(
    db: SesionDB,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    empresa_id: Optional[str] = None,
    botiquin_id: Optional[str] = None,
    area: Optional[str] = None,
    ubicacion: Optional[str] = None,
    tipo_equipo: Optional[str] = None,
    equipo: Optional[str] = None,
):
    """Consumo de insumos registrado en inspecciones de botiquin, con su costo."""
    consulta = (
        db.query(models.BotiquinInspeccionInsumo, models.BotiquinInspeccion, models.Medicamento)
        .join(models.BotiquinInspeccion,
              models.BotiquinInspeccion.id == models.BotiquinInspeccionInsumo.inspeccion_id)
        .join(models.Botiquin, models.Botiquin.id == models.BotiquinInspeccion.botiquin_id)
        .join(models.Medicamento,
              models.Medicamento.id == models.BotiquinInspeccionInsumo.medicamento_id)
        .filter(
            models.BotiquinInspeccion.is_deleted == False,  # noqa: E712
            models.Botiquin.is_deleted == False,  # noqa: E712
        )
    )
    consulta = _filtrar_por_fecha(consulta, models.BotiquinInspeccion.fecha, fecha_inicio, fecha_fin)
    if empresa_id:
        consulta = consulta.filter(models.Botiquin.empresa_id == empresa_id)
    if botiquin_id:
        consulta = consulta.filter(models.Botiquin.id == botiquin_id)
    consulta = _filtrar_por_lista(consulta, models.Botiquin.area, area, comparacion="parcial")
    consulta = _filtrar_por_lista(consulta, models.Botiquin.ubicacion, ubicacion)
    consulta = _filtrar_por_lista(consulta, models.Botiquin.tipo_equipo, tipo_equipo)
    consulta = _filtrar_por_lista(consulta, models.Botiquin.equipo, equipo)

    por_insumo, fechas = {}, set()
    for item, inspeccion, medicamento in consulta.all():
        if not inspeccion.fecha:
            continue
        fecha = inspeccion.fecha.strftime("%Y-%m-%d")
        fechas.add(fecha)
        acumulado = por_insumo.setdefault(medicamento.id, {
            "id": medicamento.id,
            "codigo": medicamento.codigo or "",
            "nombre": medicamento.nombre or "",
            "presentacion": medicamento.presentacion or "",
            "tipo": medicamento.tipo or "",
            "precio_und": float(medicamento.costo_unitario or 0),
            "consumos": defaultdict(int),
            "sub_total_cantidad": 0,
            "total_soles": 0.0,
        })
        cantidad = item.cantidad or 0
        acumulado["consumos"][fecha] += cantidad
        acumulado["sub_total_cantidad"] += cantidad

    lista, total_general = [], 0.0
    for acumulado in por_insumo.values():
        acumulado["total_soles"] = round(acumulado["sub_total_cantidad"] * acumulado["precio_und"], 2)
        total_general += acumulado["total_soles"]
        acumulado["consumos"] = dict(acumulado["consumos"])
        lista.append(acumulado)
    lista.sort(key=lambda i: i["total_soles"], reverse=True)

    return {
        "rango_fechas": sorted(fechas),
        "insumos": lista,
        "totales": _totales_con_igv(total_general),
    }
