"""Completa la referencia de los movimientos de kardex anteriores a la
trazabilidad.

Hasta octubre de 2026 una atencion descontaba stock sin dejar en el kardex de
que ficha venia el movimiento, y editarla devolvia la receta entera (INGRESO) y
la volvia a sacar entera (SALIDA). En pantalla todos esos movimientos salian
con "—". Este script reconstruye la referencia reproduciendo la historia en
orden:

  - Alta: SALIDAs sin observacion en el mismo instante en que se creo una
    atencion -> "Atención N.º X".
    En julio la receta se descontaba unos segundos despues de crear la ficha,
    por eso se acepta hasta VENTANA_ALTA_DIFERIDA si algun medicamento
    coincide con la receta.
  - Edicion: INGRESOs (lo que se devolvia) seguidos de SALIDAs (lo que se
    volvia a sacar). La ficha se identifica porque lo devuelto coincide
    exactamente con lo que esa ficha tenia recetado en ese momento ->
    "Devolución por edición de atención N.º X" / "Edición de atención N.º X".
    Si varias fichas tenian la misma receta, o la edicion solo desconto (hubo
    versiones asi en agosto), decide la hora de la ultima edicion de la ficha.
    Muchas fichas se crearon sin medicamentos y la receta se agrego despues:
    esa edicion no devuelve nada, y se reconoce porque la ficha estaba sin
    receta, es de los dias previos y su receta guardada tiene todos los
    medicamentos que salieron.
  - Lo que no es de ninguna atencion: un movimiento suelto sin actividad de
    atenciones alrededor solo pudo salir del formulario del Almacen, y un
    lote grande de ingresos, de una carga de inventario.

Solo escribe cuando la atribucion es univoca; lo demas queda como estaba.
Solo toca filas sin observacion, asi que correrlo dos veces no cambia nada.

    python referenciar_kardex.py              # simula y muestra el resultado
    python referenciar_kardex.py --aplicar    # escribe (guarda un respaldo antes)
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta

# Dos movimientos del mismo pedido al API se escriben con milisegundos de
# diferencia; dos pedidos distintos, con segundos.
SEPARACION_ENTRE_PEDIDOS = timedelta(seconds=1)
# Cuanto puede separarse la alta (o la ultima edicion) de una atencion de sus
# movimientos.
TOLERANCIA = timedelta(seconds=5)
VENTANA_ALTA_DIFERIDA = timedelta(minutes=2)
# Hasta cuanto despues de crearla se le agrega la receta a una ficha.
VENTANA_RECETA_AGREGADA = timedelta(days=3)
# Desde cuantos ingresos juntos sin atencion se considera una carga de inventario.
MINIMO_CARGA_MASIVA = 10


def _cargar_env_local():
    """Igual que reset_stock.py: toma DATABASE_URL del .env si no esta."""
    if os.getenv("DATABASE_URL"):
        return
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def _fecha(valor):
    """PostgreSQL devuelve datetime; SQLite (el escritorio), texto."""
    return datetime.fromisoformat(valor) if isinstance(valor, str) else valor


def _pedidos(filas):
    """Agrupa los movimientos sin observacion por el pedido que los genero.

    Un pedido de la version anterior es INGRESO* seguido de SALIDA*: si dentro
    de la misma ventana aparece un INGRESO despues de una SALIDA, son dos
    pedidos distintos."""
    pedidos, actual = [], []
    for fila in filas:
        nuevo = actual and (
            fila["fecha"] - actual[-1]["fecha"] > SEPARACION_ENTRE_PEDIDOS
            or (fila["tipo_movimiento"] == "INGRESO" and actual[-1]["tipo_movimiento"] == "SALIDA")
        )
        if nuevo:
            pedidos.append(actual)
            actual = []
        actual.append(fila)
    if actual:
        pedidos.append(actual)
    return pedidos


def _totales(filas, tipo):
    totales = Counter()
    for fila in filas:
        if fila["tipo_movimiento"] == tipo:
            totales[fila["medicamento_id"]] += fila["cantidad"] or 0
    return totales


def _numero(atencion):
    return f"N.º {atencion['folio']}" if atencion["folio"] else "sin N.º"


def reconstruir(conexion):
    """No escribe nada. Devuelve (plan, resumen, ambiguos, sin_atribuir,
    descuadres): `plan` es la lista de (kardex_id, observacion, atencion_id)
    a guardar y `descuadres` los folios cuya historia reproducida no termina
    en la receta que tienen guardada."""
    from sqlalchemy import text

    filas = [dict(f) for f in conexion.execute(text("""
        SELECT id, medicamento_id, fecha, tipo_movimiento, cantidad
        FROM kardex
        WHERE observacion IS NULL OR observacion = ''
        ORDER BY fecha, created_at
    """)).mappings()]
    atenciones = [dict(a) for a in conexion.execute(text(
        "SELECT id, folio, created_at, updated_at FROM atenciones ORDER BY created_at"
    )).mappings()]
    for fila in filas:
        fila["fecha"] = _fecha(fila["fecha"])
    for atencion in atenciones:
        atencion["created_at"] = _fecha(atencion["created_at"])
        atencion["updated_at"] = _fecha(atencion["updated_at"])
    # La receta guardada hoy: confirma altas diferidas y controla el final.
    guardadas = {a["id"]: Counter() for a in atenciones}
    for r in conexion.execute(text(
        "SELECT atencion_id, medicamento_id, cantidad FROM atencion_medicamentos"
    )).mappings():
        if r["atencion_id"] in guardadas:
            guardadas[r["atencion_id"]][r["medicamento_id"]] += r["cantidad"] or 0

    pedidos = _pedidos(filas)
    # Dos pasadas: la primera atribuye lo que es univoco; la segunda usa esas
    # atribuciones para desempatar mirando hacia adelante.
    *_, asignaciones = _reproducir(pedidos, atenciones, guardadas, pistas={})
    return _reproducir(pedidos, atenciones, guardadas, pistas=asignaciones)[:-1]


def _cerca(valor, momento, antes=TOLERANCIA, despues=TOLERANCIA):
    return valor is not None and momento - antes <= valor <= momento + despues


def _reproducir(pedidos, atenciones, guardadas, pistas):
    devueltos = [_totales(p, "INGRESO") for p in pedidos]

    def sigue_sin_editar(indice, atencion_id, receta):
        """True si la proxima edicion conocida de la ficha todavia devuelve
        `receta`: entonces no fue esa ficha la que cambio en `indice`."""
        for siguiente in range(indice + 1, len(pedidos)):
            if pistas.get(siguiente) == atencion_id:
                return devueltos[siguiente] == receta
        return False

    # Lo que cada ficha tiene recetado en el momento que se va reproduciendo.
    # Arranca vacio y lo llena su alta; las fichas sin medicamentos no tienen
    # alta en el kardex y se quedan vacias.
    recetado = {a["id"]: Counter() for a in atenciones}
    con_alta = set()
    plan, resumen, asignaciones = [], Counter(), {}
    ambiguos, sin_atribuir = [], []

    for indice, pedido in enumerate(pedidos):
        momento = pedido[0]["fecha"]
        devuelto = devueltos[indice]
        sacado = _totales(pedido, "SALIDA")
        editadas_ahora = [a for a in atenciones if _cerca(a["updated_at"], momento)]

        if devuelto:
            tipo = "edicion"
            candidatas = [
                a for a in atenciones
                if a["created_at"] <= momento + TOLERANCIA and recetado[a["id"]] == devuelto
            ]
            if len(candidatas) > 1:
                candidatas = [a for a in candidatas if a in editadas_ahora] or candidatas
            if len(candidatas) > 1:
                # updated_at solo avanza: una ficha cuya ultima edicion es
                # anterior a este momento no pudo ser la que se edito ahora.
                candidatas = [
                    a for a in candidatas
                    if a["updated_at"] is None or a["updated_at"] >= momento - TOLERANCIA
                ] or candidatas
            if len(candidatas) > 1 and devuelto != sacado:
                candidatas = [
                    a for a in candidatas if not sigue_sin_editar(indice, a["id"], devuelto)
                ] or candidatas
            if not candidatas:
                candidatas = editadas_ahora
        else:
            tipo = "alta"
            sin_alta = [a for a in atenciones if a["id"] not in con_alta]
            candidatas = [a for a in sin_alta if _cerca(a["created_at"], momento)]
            if not candidatas:
                candidatas = [
                    a for a in sin_alta
                    if _cerca(a["created_at"], momento, antes=VENTANA_ALTA_DIFERIDA)
                    and set(sacado) & set(guardadas[a["id"]])
                ]
            if not candidatas:
                tipo = "edicion"  # una edicion que solo desconto
                candidatas = editadas_ahora
            if not candidatas:
                candidatas = [
                    a for a in atenciones
                    if not recetado[a["id"]]
                    and _cerca(a["created_at"], momento, antes=VENTANA_RECETA_AGREGADA, despues=timedelta(0))
                    and set(sacado) <= set(guardadas[a["id"]])
                ]

        if len(candidatas) != 1:
            if candidatas:
                ambiguos.append((tipo, pedido, candidatas))
                resumen[f"{tipo} ambigua"] += len(pedido)
            else:
                texto = _sin_atencion(pedido, atenciones)
                if texto:
                    plan.extend((fila["id"], texto, None) for fila in pedido)
                    resumen[texto] += len(pedido)
                else:
                    sin_atribuir.append((tipo, pedido, candidatas))
                    resumen["sin atribuir"] += len(pedido)
            continue

        atencion = candidatas[0]
        recetado[atencion["id"]] = sacado
        con_alta.add(atencion["id"])
        asignaciones[indice] = atencion["id"]
        for fila in pedido:
            if tipo == "alta":
                texto = "Atención"
            elif fila["tipo_movimiento"] == "INGRESO":
                texto = "Devolución por edición de atención"
            else:
                texto = "Edición de atención"
            plan.append((fila["id"], f"{texto} {_numero(atencion)}", atencion["id"]))
        resumen[tipo] += len(pedido)

    # Control: al terminar, lo reproducido tiene que coincidir con la receta
    # guardada de cada ficha. Si no, alguna atribucion fue incorrecta.
    descuadres = [
        a["folio"] for a in atenciones
        if a["id"] in con_alta and recetado[a["id"]] != guardadas[a["id"]]
    ]
    return plan, resumen, ambiguos, sin_atribuir, descuadres, asignaciones


def _sin_atencion(pedido, atenciones):
    """Referencia de un pedido que no es de ninguna atencion, o None."""
    momento = pedido[0]["fecha"]
    if len(pedido) >= MINIMO_CARGA_MASIVA and all(f["tipo_movimiento"] == "INGRESO" for f in pedido):
        return "Carga masiva de inventario"
    hubo_atenciones = any(
        _cerca(a["created_at"], momento, VENTANA_ALTA_DIFERIDA, VENTANA_ALTA_DIFERIDA)
        or _cerca(a["updated_at"], momento, VENTANA_ALTA_DIFERIDA, VENTANA_ALTA_DIFERIDA)
        for a in atenciones
    )
    if len(pedido) == 1 and not hubo_atenciones:
        return "Registro manual en Almacén"
    return None


def aplicar(conexion, plan):
    from sqlalchemy import inspect, text

    columnas = {c["name"] for c in inspect(conexion).get_columns("kardex")}
    con_atencion = "atencion_id" in columnas
    sentencia = text(
        "UPDATE kardex SET observacion = :obs"
        + (", atencion_id = :atencion" if con_atencion else "")
        + " WHERE id = :id AND (observacion IS NULL OR observacion = '')"
    )
    for kardex_id, observacion, atencion_id in plan:
        conexion.execute(sentencia, {"obs": observacion, "atencion": atencion_id, "id": kardex_id})


def main():
    _cargar_env_local()
    from database import engine

    escribir = "--aplicar" in sys.argv
    with engine.begin() as conexion:
        plan, resumen, ambiguos, sin_atribuir, descuadres = reconstruir(conexion)

        print("Movimientos sin referencia, por resultado:")
        for clave, valor in sorted(resumen.items()):
            print(f"  {clave}: {valor}")
        print(f"Se completaria la referencia de {len(plan)} movimientos.")
        if descuadres:
            print(f"Fichas cuya historia no termina en su receta guardada: {descuadres}")
        for tipo, pedido, candidatas in ambiguos[:10]:
            folios = ", ".join(str(a["folio"]) for a in candidatas)
            print(f"  ambiguo ({tipo}) {pedido[0]['fecha']}: {len(pedido)} movs, fichas posibles {folios}")
        for tipo, pedido, _ in sin_atribuir[:10]:
            print(f"  sin atribuir ({tipo}) {pedido[0]['fecha']}: {len(pedido)} movs")

        if not escribir:
            print("\nSimulacion: no se escribio nada. Use --aplicar para guardar.")
            return
        respaldo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "respaldo_referencias_kardex.json")
        with open(respaldo, "w", encoding="utf-8") as f:
            json.dump([kardex_id for kardex_id, _, _ in plan], f)
        aplicar(conexion, plan)
        print(f"\nListo. Ids modificados en {respaldo} (antes no tenian observacion).")


if __name__ == "__main__":
    main()
