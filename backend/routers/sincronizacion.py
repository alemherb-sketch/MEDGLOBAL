"""Endpoints de sincronizacion entre el servidor central y cada instalacion.

El protocolo (que tablas viajan, como se copia una fila) esta en
servicios/sincronizacion.py; aca queda el manejo de cambios y conflictos.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

import models
import schemas
from dependencias import RequiereSesion, SesionDB
from servicios import sincronizacion as protocolo
from servicios.codigos import siguiente_codigo
from servicios.tiempo import ahora_utc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sincronizacion"], dependencies=[RequiereSesion])

# Import diferido y protegido: sync_client necesita `requests`, que no todo
# despliegue tiene instalado (el VPS solo sirve la API web y nunca corre el
# ciclo de sincronizacion). Sin esto, ese despliegue no arrancaria.
try:
    import sync_client
except ImportError:  # pragma: no cover - depende del despliegue
    sync_client = None

# Hijos que se reconstruyen cuando una fila llega por primera vez. Editar los
# hijos de una fila que ya existe no esta soportado por sync, igual que
# tampoco lo esta en el endpoint normal de edicion.
_TABLAS_CON_HIJOS = ("atenciones", "tipos_botiquin", "botiquin_inspecciones", "kardex")


@router.get("/estado")
def estado():
    """Para el indicador del frontend. No dice si hay conexion ahora mismo: la
    sincronizacion es manual, asi que refleja como termino la ultima vez que
    alguien apreto «Sincronizar ahora»."""
    if sync_client is None:
        return {"estado": "desactivado", "ultima_sincronizacion": None, "ultimo_error": None}
    return sync_client.obtener_estado()


@router.post("/ahora")
def sincronizar_ahora():
    """Dispara un ciclo completo (sube lo local, despues baja lo del servidor)
    y espera a que termine.

    Es el boton «Sincronizar ahora» del escritorio y la UNICA forma de
    sincronizar: no hay ciclo automatico, para poder trabajar sin internet todo
    el dia y subir todo junto cuando convenga."""
    if sync_client is None:
        raise HTTPException(
            status_code=400,
            detail="Esta instalacion no tiene la sincronizacion disponible.",
        )
    resultado = sync_client.sincronizar_ahora(origen="manual")
    sync_client._actualizar_estado(resultado)
    return resultado


@router.get("/cambios")
def cambios(db: SesionDB, since: Optional[str] = None):
    """Pull: todo lo que cambio desde `since` (ISO 8601), incluidos los
    borrados (is_deleted actua de lapida). Sin `since` devuelve todo, que es la
    sincronizacion inicial de un dispositivo nuevo.

    `server_time` va en la respuesta a proposito: el cliente debe guardar ESE
    valor como proximo cursor y no su propio reloj, para que una PC
    desincronizada no cause huecos ni duplicados."""
    hora_servidor = ahora_utc()
    desde = None
    if since:
        try:
            desde = protocolo.parsear_fecha(since)
        except ValueError:
            raise HTTPException(status_code=400, detail="Parametro 'since' invalido, usa formato ISO 8601")

    resultado = {}
    for tabla, model in protocolo.SYNCABLE_MODELS.items():
        consulta = db.query(model)
        if desde:
            consulta = consulta.filter(model.server_updated_at > desde)

        filas = []
        for fila in consulta.all():
            datos = protocolo.fila_a_dict(fila)
            if tabla == "atenciones":
                datos["medicamentos"] = [
                    {"medicamento_id": m.medicamento_id, "cantidad": m.cantidad}
                    for m in fila.medicamentos
                ]
            elif tabla in ("tipos_botiquin", "botiquin_inspecciones"):
                datos["insumos"] = [
                    {"medicamento_id": i.medicamento_id, "cantidad": i.cantidad}
                    for i in fila.insumos
                ]
            filas.append(datos)
        resultado[tabla] = filas

    return {"server_time": hora_servidor.isoformat(), "cambios": resultado}


# --- Reconstruccion de los hijos de una fila nueva --------------------------

def _atencion_nueva(db, atencion, medicamentos) -> None:
    """Asigna folio y reconstruye la receta de una atencion recien llegada.

    A PROPOSITO no toca el stock ni escribe en kardex, aunque crear una
    atencion por el API si lo haga: cuando el dispositivo la registro, ya
    escribio localmente su fila de kardex SALIDA, y esa fila viaja en el mismo
    push. Ahi la recoge `_kardex_nuevo`, que recalcula el stock contra el
    estado actual del servidor. Si ademas se descontara aca, cada atencion
    sincronizada restaria el doble y dejaria dos movimientos duplicados: el
    inventario del servidor se degradaba en cada sincronizacion.

    Regla: la fila de kardex es la unica fuente de verdad de un movimiento.
    """
    atencion.folio = (db.query(func.max(models.Atencion.folio)).scalar() or 0) + 1
    for item in medicamentos or []:
        if not item.get("medicamento_id"):
            continue
        db.add(models.AtencionMedicamento(
            atencion_id=atencion.id,
            medicamento_id=item["medicamento_id"],
            cantidad=item.get("cantidad", 1),
        ))


def _insumos_de_tipo(db, tipo, insumos) -> None:
    db.query(models.TipoBotiquinInsumo).filter(
        models.TipoBotiquinInsumo.tipo_botiquin_id == tipo.id
    ).delete(synchronize_session=False)
    for item in insumos or []:
        if not item.get("medicamento_id"):
            continue
        db.add(models.TipoBotiquinInsumo(
            tipo_botiquin_id=tipo.id,
            medicamento_id=item["medicamento_id"],
            cantidad=max(1, int(item.get("cantidad") or 1)),
        ))


def _inspeccion_nueva(db, inspeccion, insumos) -> None:
    """Asigna correlativo INS0001 y reconstruye los insumos de una fila nueva."""
    if not inspeccion.codigo:
        inspeccion.codigo = siguiente_codigo(
            db, models.BotiquinInspeccion, "codigo", "INS", separador=""
        )
    _insumos_de_inspeccion(db, inspeccion, insumos)


def _insumos_de_inspeccion(db, inspeccion, insumos) -> None:
    for item in insumos or []:
        if not item.get("medicamento_id"):
            continue
        estado_insumo = (item.get("estado") or "BUENO").upper()
        reposicion = (item.get("reposicion") or "NO").upper()
        if reposicion not in ("SI", "NO"):
            reposicion = "NO"
        db.add(models.BotiquinInspeccionInsumo(
            inspeccion_id=inspeccion.id,
            medicamento_id=item["medicamento_id"],
            cantidad=max(1, int(item.get("cantidad") or 1)),
            estado=estado_insumo,
            reposicion=reposicion,
        ))


def _kardex_nuevo(db, movimiento) -> None:
    """El stock y el saldo se recalculan contra el estado ACTUAL del servidor.

    Nunca se confia en el stock que traiga el dispositivo: puede estar
    desactualizado si otro sincronizo movimientos del mismo medicamento
    mientras tanto."""
    medicamento = db.query(models.Medicamento).filter(
        models.Medicamento.id == movimiento.medicamento_id
    ).first()
    if not medicamento:
        return
    actual = medicamento.stock_actual or 0
    cantidad = movimiento.cantidad or 0
    if movimiento.tipo_movimiento == "INGRESO":
        medicamento.stock_actual = actual + cantidad
    elif movimiento.tipo_movimiento == "SALIDA":
        medicamento.stock_actual = actual - cantidad
    movimiento.saldo = medicamento.stock_actual


def _reconstruir_hijos(db, tabla: str, fila, datos: dict) -> None:
    if tabla == "atenciones":
        _atencion_nueva(db, fila, datos.get("medicamentos", []))
    elif tabla == "tipos_botiquin":
        _insumos_de_tipo(db, fila, datos.get("insumos", []))
    elif tabla == "botiquin_inspecciones":
        _inspeccion_nueva(db, fila, datos.get("insumos", []))
    elif tabla == "kardex":
        _kardex_nuevo(db, fila)


def _guardar_conflicto(db, tabla: str, registro_id: str, perdedora: dict, ganadora_id=None) -> None:
    db.add(models.ConflictoSync(
        tabla=tabla,
        registro_id=registro_id,
        version_perdedora=json.dumps(perdedora, default=str),
        version_ganadora_id=ganadora_id,
    ))


@router.post("/subir")
def subir(payload: schemas.SyncPushRequest, db: SesionDB):
    """Push: aplica los cambios locales de un dispositivo.

    Deteccion de conflicto real (no toda sincronizacion es un conflicto): el
    payload trae el `since` del ULTIMO pull exitoso del dispositivo. Para cada
    fila que ya existe en el servidor:
      - si el servidor NO cambio desde ese `since`, un solo dispositivo la
        toco: es una actualizacion limpia y se aplica.
      - si SI cambio, otro dispositivo edito lo mismo mientras este estaba
        desconectado. Gana el `updated_at` mas reciente y la version perdedora
        se guarda entera en conflictos_sync, en vez de perderse en silencio.

    Se confirma fila por fila (no una vez por tabla) a proposito: varias tablas
    tienen columnas UNIQUE y dos dispositivos offline pueden crear el mismo
    valor sin saberlo. Con un commit por tabla, esa fila chocando tumbaria la
    transaccion entera, incluidas las filas anteriores ya aplicadas.
    """
    desde = protocolo.parsear_fecha(payload.since) if payload.since else None

    resultado = {}
    for tabla, filas in payload.cambios.items():
        model = protocolo.SYNCABLE_MODELS.get(tabla)
        if model is None:
            raise HTTPException(status_code=400, detail=f"Tabla no sincronizable: {tabla}")

        aplicados = conflictos = 0
        for datos in filas:
            registro_id = datos.get("id")
            if not registro_id:
                continue
            try:
                entrante_editada = protocolo.parsear_fecha(datos.get("updated_at")) or ahora_utc()
                existente = db.query(model).filter(model.id == registro_id).first()

                if existente is None:
                    fila = model(id=registro_id)
                    protocolo.aplicar_campos(fila, datos, tabla)
                    db.add(fila)
                    db.flush()
                    if tabla in _TABLAS_CON_HIJOS:
                        _reconstruir_hijos(db, tabla, fila, datos)
                    db.commit()
                    aplicados += 1
                    continue

                servidor_cambio = desde is None or (
                    existente.server_updated_at is not None and existente.server_updated_at > desde
                )

                if not servidor_cambio:
                    protocolo.aplicar_campos(existente, datos, tabla)
                    db.commit()
                    aplicados += 1
                    continue

                conflictos += 1
                if existente.updated_at is None or entrante_editada >= existente.updated_at:
                    _guardar_conflicto(db, tabla, registro_id,
                                       protocolo.fila_a_dict(existente), registro_id)
                    protocolo.aplicar_campos(existente, datos, tabla)
                else:
                    # El servidor conserva su version; la entrante se archiva.
                    _guardar_conflicto(db, tabla, registro_id, datos, registro_id)
                db.commit()

            except IntegrityError:
                # Choque contra una columna UNIQUE (username, ruc, dni, codigo,
                # nombre... creado en paralelo por otro dispositivo). Se
                # descarta SOLO esta fila: el rollback no afecta a las
                # anteriores porque cada una ya confirmo su propio commit.
                db.rollback()
                conflictos += 1
                _guardar_conflicto(db, tabla, registro_id, datos, None)
                db.commit()
            except Exception:
                # Un dato invalido en una fila (una fecha ilegible, por
                # ejemplo) no puede tumbar el push entero ni dejar la sesion
                # rota para las filas siguientes: antes cualquier excepcion que
                # no fuera IntegrityError abortaba la sincronizacion completa
                # con un 500 y el dispositivo no sabia que se habia aplicado.
                db.rollback()
                conflictos += 1
                logger.warning("Fila rechazada al sincronizar %s/%s", tabla, registro_id, exc_info=True)
                try:
                    _guardar_conflicto(db, tabla, registro_id, datos, None)
                    db.commit()
                except Exception:
                    db.rollback()

        resultado[tabla] = {"aplicados": aplicados, "conflictos": conflictos}

    return {"server_time": ahora_utc().isoformat(), "resultado": resultado}
