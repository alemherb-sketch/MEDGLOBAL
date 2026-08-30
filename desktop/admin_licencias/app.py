"""Panel remoto de licencias MEDGLOBAL (servicio independiente del API web).

Arquitectura recomendada
------------------------
  - La CLAVE PRIVADA vive SOLO aqui (servidor de admin / VPS interno).
  - Las PCs de clinica solo llevan la CLAVE PUBLICA y verifican offline.
  - Este servicio emite codigos firmados, lleva el registro de cupos y
    permite revocar licencias o equipos sin tocar el codigo de la app web.

No forma parte de main.py del VPS de la web: se despliega aparte
(p.ej. licencias.su-dominio.com → 127.0.0.1:8010).

Arranque local:

  set LICENCIAS_ADMIN_TOKEN=su-token-largo
  set LICENCIA_PRIVADA=ruta\\licencia_privada.pem
  set LICENCIA_PUBLICA=ruta\\licencia_publica.pem
  uvicorn app:app --host 127.0.0.1 --port 8010

Variables:
  LICENCIAS_ADMIN_TOKEN   obligatorio para el panel
  LICENCIA_PRIVADA        PEM Ed25519 (solo en este servidor)
  LICENCIA_PUBLICA        PEM publica (mismas claves que empaqueta el .exe)
  LICENCIAS_DB            sqlite (default: licencias_admin.db)
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Importar licencias del backend MEDGLOBAL (firma / decode)
_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _ROOT / "backend"
if _BACKEND.is_dir():
    sys.path.insert(0, str(_BACKEND))

import licencias as core  # noqa: E402

DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("LICENCIAS_DB", str(DIR / "licencias_admin.db"))
PRIVADA = os.getenv("LICENCIA_PRIVADA", str(_BACKEND / "licencia_privada.pem"))
PUBLICA = os.getenv("LICENCIA_PUBLICA", str(_BACKEND / "licencia_publica.pem"))
ADMIN_TOKEN = os.getenv("LICENCIAS_ADMIN_TOKEN", "").strip()

app = FastAPI(title="MEDGLOBAL — Admin de licencias", docs_url="/api/docs", redoc_url=None)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

@contextmanager
def _db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _init_db():
    with _db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS licencias (
                licencia_id   TEXT PRIMARY KEY,
                cliente       TEXT NOT NULL,
                max_pcs       INTEGER NOT NULL,
                machines_json TEXT NOT NULL DEFAULT '[]',
                codigo        TEXT NOT NULL,
                expira        TEXT,
                emitida       TEXT NOT NULL,
                revocada      INTEGER NOT NULL DEFAULT 0,
                notas         TEXT
            );
            CREATE TABLE IF NOT EXISTS activaciones (
                licencia_id   TEXT NOT NULL,
                machine_id    TEXT NOT NULL,
                cliente       TEXT,
                max_pcs       INTEGER NOT NULL,
                activado_en   TEXT NOT NULL,
                revocado      INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (licencia_id, machine_id)
            );
            """
        )


@app.on_event("startup")
def _startup():
    _init_db()
    if not ADMIN_TOKEN:
        # No tumbar el arranque, pero avisar: sin token el panel no se usa.
        print("AVISO: defina LICENCIAS_ADMIN_TOKEN para proteger el panel.")
    if not os.path.exists(PRIVADA):
        print(f"AVISO: no se encuentra la privada en {PRIVADA} — no se podran emitir.")
    if not os.path.exists(PUBLICA):
        print(f"AVISO: no se encuentra la publica en {PUBLICA}.")


# Asegura tablas al importar (TestClient / uvicorn)
_init_db()


# ---------------------------------------------------------------------------
# Auth admin
# ---------------------------------------------------------------------------

def _require_admin(authorization: Optional[str] = Header(None), x_admin_token: Optional[str] = Header(None)):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="LICENCIAS_ADMIN_TOKEN no configurado en el servidor.")
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token and x_admin_token:
        token = x_admin_token.strip()
    if not token or not secrets.compare_digest(token, ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="No autorizado.")
    return True


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginIn(BaseModel):
    token: str


class EmitirIn(BaseModel):
    cliente: str = Field(..., min_length=1, max_length=200)
    machines: List[str] = Field(default_factory=list, description="IDs de PC (recomendado)")
    max_pcs: int = Field(default=0, ge=0, description="Cupo si no hay lista de machines")
    dias: int = Field(default=365, ge=0, description="0 = sin caducidad")
    notas: str = ""


class RevocarIn(BaseModel):
    licencia_id: str


class RevocarPcIn(BaseModel):
    licencia_id: str
    machine_id: str


class ActivarIn(BaseModel):
    codigo: str
    machine_id: str
    cliente: Optional[str] = None
    licencia_id: Optional[str] = None
    max_pcs: int = Field(default=1, ge=1)


# ---------------------------------------------------------------------------
# Helpers de firma
# ---------------------------------------------------------------------------

def _cargar_privada() -> bytes:
    if not os.path.exists(PRIVADA):
        raise HTTPException(status_code=500, detail=f"Falta licencia_privada.pem en {PRIVADA}")
    with open(PRIVADA, "rb") as f:
        return f.read()


def _verificar_publica_para_activar():
    """Hace que core.verificar_firma use la publica de este servicio."""
    if not os.path.exists(PUBLICA):
        raise HTTPException(status_code=500, detail="Falta licencia_publica.pem en el servidor de licencias.")
    with open(PUBLICA, "rb") as f:
        pem = f.read()
    original = core._cargar_publica

    def _cargar():
        return pem

    core._cargar_publica = _cargar  # type: ignore
    return original


# ---------------------------------------------------------------------------
# API admin
# ---------------------------------------------------------------------------

@app.post("/api/login")
def api_login(body: LoginIn):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Admin no configurado.")
    if not secrets.compare_digest(body.token.strip(), ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="Token incorrecto.")
    return {"ok": True, "token": ADMIN_TOKEN}


@app.get("/api/resumen")
def api_resumen(_: bool = Depends(_require_admin)):
    with _db() as c:
        total = c.execute("SELECT COUNT(*) AS n FROM licencias").fetchone()["n"]
        activas = c.execute("SELECT COUNT(*) AS n FROM licencias WHERE revocada=0").fetchone()["n"]
        pcs = c.execute("SELECT COUNT(*) AS n FROM activaciones WHERE revocado=0").fetchone()["n"]
        revocadas = c.execute("SELECT COUNT(*) AS n FROM licencias WHERE revocada=1").fetchone()["n"]
    return {
        "licencias_total": total,
        "licencias_activas": activas,
        "licencias_revocadas": revocadas,
        "pcs_activadas": pcs,
        "tiene_privada": os.path.exists(PRIVADA),
        "tiene_publica": os.path.exists(PUBLICA),
    }


@app.get("/api/licencias")
def api_listar(_: bool = Depends(_require_admin)):
    with _db() as c:
        rows = c.execute(
            "SELECT * FROM licencias ORDER BY emitida DESC"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["machines"] = json.loads(d.pop("machines_json") or "[]")
            act = c.execute(
                "SELECT machine_id, activado_en, revocado FROM activaciones WHERE licencia_id=? ORDER BY activado_en",
                (d["licencia_id"],),
            ).fetchall()
            d["activaciones"] = [dict(a) for a in act]
            d["pcs_activas"] = sum(1 for a in act if not a["revocado"])
            result.append(d)
    return {"licencias": result}


@app.post("/api/emitir")
def api_emitir(body: EmitirIn, _: bool = Depends(_require_admin)):
    machines = [m.strip().upper() for m in body.machines if m and m.strip()]
    max_pcs = body.max_pcs or len(machines)
    if max_pcs <= 0 and not machines:
        raise HTTPException(status_code=400, detail="Indique al menos un machine_id o un max_pcs > 0.")
    if machines and max_pcs < len(machines):
        max_pcs = len(machines)

    ahora = datetime.now(timezone.utc)
    licencia_id = str(uuid.uuid4())
    payload = {
        "producto": "MEDGLOBAL-DESKTOP",
        "licencia_id": licencia_id,
        "cliente": body.cliente.strip(),
        "emitida": ahora.isoformat(),
        "max_pcs": max_pcs,
        "machines": machines,
    }
    expira = None
    if body.dias > 0:
        expira = (ahora + timedelta(days=body.dias)).isoformat()
        payload["expira"] = expira

    codigo = core.firmar_payload(payload, _cargar_privada())

    with _db() as c:
        c.execute(
            """
            INSERT INTO licencias
              (licencia_id, cliente, max_pcs, machines_json, codigo, expira, emitida, revocada, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                licencia_id,
                body.cliente.strip(),
                max_pcs,
                json.dumps(machines),
                codigo,
                expira,
                ahora.isoformat(),
                body.notas or "",
            ),
        )

    return {
        "ok": True,
        "licencia_id": licencia_id,
        "cliente": body.cliente.strip(),
        "max_pcs": max_pcs,
        "machines": machines,
        "expira": expira,
        "codigo": codigo,
        "detalle": "Licencia emitida. Copie el codigo completo y peguelo en la PC de la clinica.",
    }


@app.post("/api/revocar")
def api_revocar(body: RevocarIn, _: bool = Depends(_require_admin)):
    with _db() as c:
        cur = c.execute(
            "UPDATE licencias SET revocada=1 WHERE licencia_id=?",
            (body.licencia_id,),
        )
        c.execute(
            "UPDATE activaciones SET revocado=1 WHERE licencia_id=?",
            (body.licencia_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Licencia no encontrada.")
    return {"ok": True, "detalle": "Licencia revocada. Las PCs con chequeo online dejaran de usarla."}


@app.post("/api/revocar-pc")
def api_revocar_pc(body: RevocarPcIn, _: bool = Depends(_require_admin)):
    mid = body.machine_id.strip().upper()
    with _db() as c:
        cur = c.execute(
            "UPDATE activaciones SET revocado=1 WHERE licencia_id=? AND machine_id=?",
            (body.licencia_id, mid),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Activacion no encontrada.")
    return {"ok": True, "detalle": f"PC {mid} revocada."}


@app.get("/api/licencia/{licencia_id}/codigo")
def api_remostrar_codigo(licencia_id: str, _: bool = Depends(_require_admin)):
    with _db() as c:
        row = c.execute(
            "SELECT codigo, revocada FROM licencias WHERE licencia_id=?",
            (licencia_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No encontrada.")
    return {"codigo": row["codigo"], "revocada": bool(row["revocada"])}


# ---------------------------------------------------------------------------
# API publica (PCs de escritorio)
# ---------------------------------------------------------------------------

@app.get("/salud")
def salud():
    return {"ok": True, "servicio": "medglobal-licencias"}


@app.get("/estado/{licencia_id}")
def estado_publico(licencia_id: str):
    """La app de escritorio puede consultar si la licencia sigue vigente."""
    with _db() as c:
        lic = c.execute(
            "SELECT revocada, expira, max_pcs, cliente FROM licencias WHERE licencia_id=?",
            (licencia_id,),
        ).fetchone()
        if not lic:
            return {"conocida": False, "valida": True}  # desconocida = solo offline
        act = c.execute(
            "SELECT machine_id, revocado FROM activaciones WHERE licencia_id=?",
            (licencia_id,),
        ).fetchall()
    expira_ok = True
    if lic["expira"]:
        try:
            exp = datetime.fromisoformat(lic["expira"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp:
                expira_ok = False
        except ValueError:
            pass
    return {
        "conocida": True,
        "valida": (not lic["revocada"]) and expira_ok,
        "revocada": bool(lic["revocada"]),
        "expira": lic["expira"],
        "cliente": lic["cliente"],
        "max_pcs": lic["max_pcs"],
        "activaciones": [dict(a) for a in act],
        "pcs_activas": sum(1 for a in act if not a["revocado"]),
    }


@app.post("/activar")
def activar_pc(body: ActivarIn):
    """Registro de cupo (licencias por max_pcs) o revalidacion online."""
    original = _verificar_publica_para_activar()
    try:
        payload, firma = core._decodificar_licencia(body.codigo)
        if not core.verificar_firma(payload, firma):
            raise HTTPException(status_code=400, detail="Firma de licencia invalida.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Codigo invalido: {e}") from e
    finally:
        core._cargar_publica = original  # type: ignore

    licencia_id = str(payload.get("licencia_id") or payload.get("id") or body.licencia_id or "")
    if not licencia_id:
        raise HTTPException(status_code=400, detail="La licencia no tiene id.")
    mid = body.machine_id.strip().upper()
    max_pcs = int(payload.get("max_pcs") or payload.get("cupo") or body.max_pcs or 1)
    cliente = payload.get("cliente") or body.cliente

    # Si esta revocada en el registro, rechazar.
    with _db() as c:
        lic = c.execute(
            "SELECT revocada FROM licencias WHERE licencia_id=?",
            (licencia_id,),
        ).fetchone()
        if lic and lic["revocada"]:
            raise HTTPException(status_code=403, detail="Esta licencia fue revocada por el administrador.")

        maquinas = payload.get("machines") or []
        if maquinas and mid not in [str(m).upper() for m in maquinas]:
            raise HTTPException(status_code=403, detail="Esta PC no esta en la lista de la licencia.")

        activas = c.execute(
            "SELECT machine_id FROM activaciones WHERE licencia_id=? AND revocado=0",
            (licencia_id,),
        ).fetchall()
        ya = {row["machine_id"] for row in activas}
        if mid in ya:
            return {
                "ok": True,
                "detalle": "Esta PC ya estaba registrada.",
                "activadas": len(ya),
                "max_pcs": max_pcs,
            }
        if len(ya) >= max_pcs:
            raise HTTPException(
                status_code=403,
                detail=f"Cupo agotado: {len(ya)}/{max_pcs} PCs ya activadas.",
            )
        c.execute(
            """
            INSERT INTO activaciones (licencia_id, machine_id, cliente, max_pcs, activado_en, revocado)
            VALUES (?, ?, ?, ?, ?, 0)
            ON CONFLICT(licencia_id, machine_id) DO UPDATE SET
              revocado=0, activado_en=excluded.activado_en
            """,
            (licencia_id, mid, cliente, max_pcs, datetime.now(timezone.utc).isoformat()),
        )
        # Asegura que exista fila en licencias si se emitio offline y registra primera vez
        c.execute(
            """
            INSERT OR IGNORE INTO licencias
              (licencia_id, cliente, max_pcs, machines_json, codigo, expira, emitida, revocada, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'registrada-al-activar')
            """,
            (
                licencia_id,
                cliente or "",
                max_pcs,
                json.dumps([str(m).upper() for m in maquinas]),
                body.codigo.strip(),
                payload.get("expira"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        total = len(ya) + 1
    return {"ok": True, "detalle": "PC registrada.", "activadas": total, "max_pcs": max_pcs}


# ---------------------------------------------------------------------------
# UI estatica
# ---------------------------------------------------------------------------

STATIC = DIR / "static"
if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/", response_class=HTMLResponse)
def panel():
    index = STATIC / "index.html"
    if index.is_file():
        return FileResponse(index)
    return HTMLResponse("<h1>MEDGLOBAL Licencias</h1><p>Falta static/index.html</p>")
