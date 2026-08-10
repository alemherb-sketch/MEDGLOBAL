"""Licencias de la version de escritorio (control de PCs autorizadas).

Solo se aplica cuando MEDGLOBAL_ESCRITORIO=1 (lo define app_desktop). En el
servidor web del VPS no se exige nada: la version web sigue funcionando igual.

Modelo de control:
  - Cada PC tiene un machine_id estable (huella local).
  - El administrador emite un codigo de licencia firmado con la clave privada
    (generar_licencia.py). La privada nunca va en el instalable.
  - El instalable solo lleva la clave publica (licencia_publica.pem) y verifica
    la firma en local, sin necesidad de internet.
  - Una licencia puede autorizar 1 o N machine_id (cupo de PCs). Solo las
    maquinas listadas en el token pueden activarse.

Opcional (sin tocar el codigo del API web en produccion): si existe
MEDGLOBAL_LICENCIAS_URL, la activacion tambien se registra en un micro-servicio
aparte (desktop/servidor_licencias) que lleva el cupo central y permite
revocar un equipo.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import platform
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import rutas

logger = logging.getLogger(__name__)

_ARCHIVO_LICENCIA = "licencia.mglic"
_ARCHIVO_PUBLICA = "licencia_publica.pem"

# Rutas y endpoints publicos: sin licencia la UI de activacion debe cargar.
RUTAS_SIN_LICENCIA = (
    "/licencias/estado",
    "/licencias/activar",
    "/licencias/desactivar",
    "/docs",
    "/openapi.json",
    "/redoc",
)


def modo_escritorio() -> bool:
    """True solo en la app de escritorio. El VPS no setea esta variable."""
    return os.getenv("MEDGLOBAL_ESCRITORIO", "").strip() in ("1", "true", "True", "yes", "YES")


def licencias_en_bypass() -> bool:
    """Valvula de desarrollo: no exige licencia (jamas en instalables de campo)."""
    return os.getenv("MEDGLOBAL_LICENCIA_BYPASS", "").strip() in ("1", "true", "True", "yes", "YES")


def machine_id() -> str:
    """Huella estable de esta PC. No es secreta: se le envia al administrador
    para que emita la licencia ligada a este equipo."""
    partes = [platform.node() or "", platform.system() or "", str(uuid.getnode())]
    try:
        import winreg  # type: ignore

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            if guid:
                partes.append(str(guid))
    except Exception:
        pass
    crudo = "|".join(partes).encode("utf-8", errors="replace")
    return hashlib.sha256(crudo).hexdigest()[:32].upper()


def _ruta_licencia() -> str:
    return rutas.datos(_ARCHIVO_LICENCIA)


def _cargar_publica() -> bytes:
    """Busca la clave publica empaquetada o junto al codigo (desarrollo)."""
    candidatas = [
        rutas.recurso(_ARCHIVO_PUBLICA),
        os.path.join(os.path.dirname(__file__), _ARCHIVO_PUBLICA),
    ]
    for ruta in candidatas:
        if ruta and os.path.exists(ruta):
            with open(ruta, "rb") as f:
                return f.read()
    raise FileNotFoundError(
        "No se encontro licencia_publica.pem. Empaquete la clave publica "
        "junto al ejecutable o dejela en backend/."
    )


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def codificar_licencia(payload: dict, firma: bytes) -> str:
    cuerpo = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    sig = _b64url_encode(firma)
    return f"{cuerpo}.{sig}"


def _decodificar_licencia(codigo: str) -> tuple[dict, bytes]:
    codigo = (codigo or "").strip().replace("\n", "").replace(" ", "")
    if "." not in codigo:
        raise ValueError("Codigo de licencia invalido")
    cuerpo_b64, sig_b64 = codigo.rsplit(".", 1)
    payload = json.loads(_b64url_decode(cuerpo_b64).decode("utf-8"))
    firma = _b64url_decode(sig_b64)
    return payload, firma


def _mensaje_firmado(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def verificar_firma(payload: dict, firma: bytes) -> bool:
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.exceptions import InvalidSignature

    publica = load_pem_public_key(_cargar_publica())
    try:
        publica.verify(firma, _mensaje_firmado(payload))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def firmar_payload(payload: dict, privada_pem: bytes) -> str:
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    privada = load_pem_private_key(privada_pem, password=None)
    firma = privada.sign(_mensaje_firmado(payload))
    return codificar_licencia(payload, firma)


def _fecha_iso(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    if isinstance(valor, (int, float)):
        return datetime.fromtimestamp(valor, tz=timezone.utc)
    texto = str(valor).strip()
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(texto)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def evaluar_payload(payload: dict, mid: Optional[str] = None) -> dict:
    """Valida la licencia ya decodificada y firmada. No lee disco."""
    mid = mid or machine_id()
    ahora = datetime.now(timezone.utc)

    if payload.get("producto", "MEDGLOBAL-DESKTOP") not in ("MEDGLOBAL-DESKTOP", "MEDGLOBAL"):
        return {"valida": False, "motivo": "producto", "detalle": "Licencia de otro producto."}

    expira = _fecha_iso(payload.get("expira") or payload.get("exp"))
    if expira and ahora > expira:
        return {
            "valida": False,
            "motivo": "expirada",
            "detalle": f"Licencia expirada el {expira.date().isoformat()}.",
            "expira": expira.isoformat(),
        }

    maquinas = payload.get("machines") or payload.get("maquinas") or []
    if isinstance(maquinas, str):
        maquinas = [m.strip() for m in maquinas.split(",") if m.strip()]
    maquinas = [str(m).upper() for m in maquinas]

    mid_unico = (payload.get("machine_id") or payload.get("mid") or "").upper()
    if mid_unico and mid_unico not in maquinas:
        maquinas.append(mid_unico)

    max_pcs = int(payload.get("max_pcs") or payload.get("cupo") or 0)
    if not maquinas and max_pcs <= 0:
        return {"valida": False, "motivo": "sin_cupo", "detalle": "La licencia no autoriza ninguna PC."}

    if maquinas:
        if mid not in maquinas:
            return {
                "valida": False,
                "motivo": "pc_no_autorizada",
                "detalle": (
                    "Esta PC no esta en la lista de equipos autorizados de la licencia. "
                    f"ID de esta PC: {mid}"
                ),
                "machine_id": mid,
                "autorizadas": len(maquinas),
                "max_pcs": max_pcs or len(maquinas),
            }
    elif max_pcs > 0:
        # Licencia por cupo sin lista: requiere registro online para no clonar
        # el mismo codigo en mas PCs de las permitidas.
        return {
            "valida": False,
            "motivo": "requiere_registro",
            "detalle": (
                "Esta licencia controla un cupo de PCs y necesita registro central. "
                "Configure MEDGLOBAL_LICENCIAS_URL o pida una licencia ligada al machine_id."
            ),
            "max_pcs": max_pcs,
        }

    return {
        "valida": True,
        "motivo": None,
        "detalle": None,
        "cliente": payload.get("cliente") or payload.get("customer"),
        "licencia_id": payload.get("licencia_id") or payload.get("id"),
        "machine_id": mid,
        "expira": expira.isoformat() if expira else None,
        "max_pcs": max_pcs or len(maquinas),
        "autorizadas": len(maquinas) if maquinas else max_pcs,
        "machines": maquinas,
    }


def leer_licencia_instalada() -> Optional[str]:
    ruta = _ruta_licencia()
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def guardar_licencia(codigo: str) -> None:
    with open(_ruta_licencia(), "w", encoding="utf-8") as f:
        f.write(codigo.strip())


def borrar_licencia() -> None:
    ruta = _ruta_licencia()
    if os.path.exists(ruta):
        os.remove(ruta)


def estado_licencia() -> dict:
    """Estado completo para el frontend y el middleware."""
    mid = machine_id()
    base = {
        "requerido": modo_escritorio() and not licencias_en_bypass(),
        "modo_escritorio": modo_escritorio(),
        "machine_id": mid,
        "valida": True,
        "motivo": None,
        "detalle": None,
        "cliente": None,
        "licencia_id": None,
        "expira": None,
        "max_pcs": None,
    }

    if not base["requerido"]:
        base["valida"] = True
        base["motivo"] = "no_aplica"
        return base

    if licencias_en_bypass():
        base["valida"] = True
        base["motivo"] = "bypass"
        return base

    codigo = leer_licencia_instalada()
    if not codigo:
        base["valida"] = False
        base["motivo"] = "sin_licencia"
        base["detalle"] = "Esta PC aun no tiene una licencia activada."
        return base

    try:
        payload, firma = _decodificar_licencia(codigo)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        base["valida"] = False
        base["motivo"] = "formato"
        base["detalle"] = "El archivo de licencia esta danado o es ilegible."
        return base

    if not verificar_firma(payload, firma):
        base["valida"] = False
        base["motivo"] = "firma"
        base["detalle"] = "La firma de la licencia no es valida."
        return base

    evaluacion = evaluar_payload(payload, mid=mid)
    base.update(evaluacion)

    # Chequeo remoto opcional: revocacion / caducidad en el panel admin
    if base.get("valida") and os.getenv("MEDGLOBAL_LICENCIAS_URL"):
        lid = base.get("licencia_id") or payload.get("licencia_id") or payload.get("id")
        if lid:
            remoto = _consultar_estado_remoto(lid)
            if remoto and remoto.get("conocida") and not remoto.get("valida"):
                base["valida"] = False
                base["motivo"] = "revocada" if remoto.get("revocada") else "invalida_remota"
                base["detalle"] = (
                    "Esta licencia fue revocada o ya no es valida en el servidor de licencias."
                )
    return base


def _consultar_estado_remoto(licencia_id: str) -> Optional[dict]:
    url = (os.getenv("MEDGLOBAL_LICENCIAS_URL") or "").rstrip("/")
    if not url:
        return None
    try:
        import requests

        r = requests.get(f"{url}/estado/{licencia_id}", timeout=8)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception as e:
        logger.debug("Estado remoto de licencia no disponible: %s", e)
        return None


def activar(codigo: str) -> dict:
    """Valida y persiste un codigo de licencia en esta PC."""
    if not modo_escritorio() and not licencias_en_bypass():
        # Permite activar en desarrollo con BYPASS; en VPS no tiene sentido.
        if not os.getenv("MEDGLOBAL_LICENCIA_BYPASS"):
            return {"ok": False, "motivo": "no_escritorio", "detalle": "Las licencias solo aplican a la app de escritorio."}

    mid = machine_id()
    try:
        payload, firma = _decodificar_licencia(codigo)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return {"ok": False, "motivo": "formato", "detalle": "Codigo de licencia invalido."}

    if not verificar_firma(payload, firma):
        return {"ok": False, "motivo": "firma", "detalle": "La firma de la licencia no es valida."}

    evaluacion = evaluar_payload(payload, mid=mid)

    # Cupo sin lista de machines: intentar registro remoto obligatorio.
    if evaluacion.get("motivo") == "requiere_registro":
        online = _registrar_cupo_online(codigo, payload, mid)
        if not online.get("ok"):
            return online
        evaluacion = {
            "valida": True,
            "cliente": payload.get("cliente"),
            "licencia_id": payload.get("licencia_id") or payload.get("id"),
            "machine_id": mid,
            "max_pcs": payload.get("max_pcs") or payload.get("cupo"),
            "expira": (_fecha_iso(payload.get("expira")) or _fecha_iso(payload.get("exp"))),
        }
        if evaluacion["expira"]:
            evaluacion["expira"] = evaluacion["expira"].isoformat()
    elif not evaluacion.get("valida"):
        return {"ok": False, **evaluacion}

    guardar_licencia(codigo.strip())

    # Registro remoto de cupo / revocacion (opcional)
    if os.getenv("MEDGLOBAL_LICENCIAS_URL"):
        online = _registrar_cupo_online(codigo.strip(), payload, mid)
        if online.get("ok") is False and evaluacion.get("motivo") != "requiere_registro":
            # Para licencias ya ligadas a machine_id, el fallo de red no bloquea
            # la activacion local (sigue siendo offline-first). Si el servidor
            # rechazo por cupo/revocacion, si se propaga.
            if online.get("motivo") in ("cupo_remoto",) or (
                online.get("detalle") and "revocad" in str(online.get("detalle", "")).lower()
            ):
                borrar_licencia()
                return {"ok": False, **online}

    return {
        "ok": True,
        "cliente": evaluacion.get("cliente"),
        "licencia_id": evaluacion.get("licencia_id"),
        "machine_id": mid,
        "max_pcs": evaluacion.get("max_pcs"),
        "expira": evaluacion.get("expira"),
        "detalle": "Licencia activada correctamente en esta PC.",
    }


def _registrar_cupo_online(codigo: str, payload: dict, mid: str) -> dict:
    base = (os.getenv("MEDGLOBAL_LICENCIAS_URL") or "").rstrip("/")
    if not base:
        return {
            "ok": False,
            "motivo": "requiere_registro",
            "detalle": (
                "Esta licencia es por cupo de PCs. Active el registro de licencias "
                "(MEDGLOBAL_LICENCIAS_URL) o solicite una licencia ligada al machine_id de esta PC."
            ),
        }
    try:
        import requests

        r = requests.post(
            f"{base}/activar",
            json={
                "codigo": codigo.strip(),
                "machine_id": mid,
                "cliente": payload.get("cliente"),
                "licencia_id": payload.get("licencia_id") or payload.get("id"),
                "max_pcs": int(payload.get("max_pcs") or payload.get("cupo") or 1),
            },
            timeout=20,
        )
        data = {}
        try:
            data = r.json()
        except Exception:
            pass
        if r.status_code >= 400:
            return {
                "ok": False,
                "motivo": "cupo_remoto",
                "detalle": data.get("detail") or data.get("detalle") or f"Registro remoto rechazo la activacion ({r.status_code}).",
            }
        return {"ok": True, **data}
    except Exception as e:
        return {
            "ok": False,
            "motivo": "sin_conexion_licencias",
            "detalle": f"No se pudo contactar el registro de licencias: {e}",
        }


def licencia_permite_request(path: str) -> bool:
    """True si el path puede atenderse sin licencia valida."""
    if not modo_escritorio() or licencias_en_bypass():
        return True
    if any(path == r or path.startswith(r + "/") for r in RUTAS_SIN_LICENCIA):
        return True
    # Assets estaticos del frontend
    if path in ("/", "/index.html", "/favicon.ico", "/logo.png"):
        return True
    if path.startswith("/assets/"):
        return True
    estado = estado_licencia()
    return bool(estado.get("valida"))
