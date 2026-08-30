"""Micro-servicio opcional de cupos de licencia (NO forma parte del API web).

Se desplega aparte del repositorio MEDGLOBAL del VPS: es un proceso sidecar
para controlar cuantas PCs activan una misma licencia por cupo.

No necesita el codigo de main.py del VPS. Nginx puede proxiar, por ejemplo:

    location /licencias-api/ {
        proxy_pass http://127.0.0.1:8010/;
    }

Uso:
    set MEDGLOBAL_LICENCIAS_URL=https://api.medglobal.../licencias-api
    en el .env de cada PC de escritorio (solo si emite licencias con --max-pcs
    sin --machine-id).

    cd desktop/servidor_licencias
    pip install fastapi uvicorn cryptography
    # Copiar licencia_publica.pem a este directorio
    uvicorn app:app --host 127.0.0.1 --port 8010
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Reusa la misma logica de verificacion si el parent esta en el path; si no,
# implementa un chequeo minimo local.
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if os.path.isdir(_BACKEND):
    import sys
    sys.path.insert(0, _BACKEND)

DB_PATH = os.getenv("LICENCIAS_DB", os.path.join(os.path.dirname(__file__), "licencias_cupos.db"))
PUBLICA = os.getenv(
    "LICENCIA_PUBLICA",
    os.path.join(os.path.dirname(__file__), "licencia_publica.pem"),
)

app = FastAPI(title="MEDGLOBAL Licencias (sidecar)", docs_url=None, redoc_url=None)


def _init_db():
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS activaciones (
                licencia_id TEXT NOT NULL,
                machine_id  TEXT NOT NULL,
                cliente     TEXT,
                max_pcs     INTEGER NOT NULL,
                activado_en TEXT NOT NULL,
                revocado    INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (licencia_id, machine_id)
            )
            """
        )


@contextmanager
def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


class ActivarIn(BaseModel):
    codigo: str
    machine_id: str
    cliente: Optional[str] = None
    licencia_id: Optional[str] = None
    max_pcs: int = Field(default=1, ge=1)


def _verificar_codigo(codigo: str) -> dict:
    try:
        import licencias
        # Asegura que use la publica del sidecar
        os.environ.setdefault("MEDGLOBAL_ESCRITORIO", "0")
        payload, firma = licencias._decodificar_licencia(codigo)
        # Forzar lectura de la publica del sidecar si existe
        if os.path.exists(PUBLICA):
            original = licencias._cargar_publica

            def _cargar():
                with open(PUBLICA, "rb") as f:
                    return f.read()

            licencias._cargar_publica = _cargar  # type: ignore
            try:
                ok = licencias.verificar_firma(payload, firma)
            finally:
                licencias._cargar_publica = original  # type: ignore
        else:
            ok = licencias.verificar_firma(payload, firma)
        if not ok:
            raise HTTPException(status_code=400, detail="Firma de licencia invalida.")
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Codigo invalido: {e}")


@app.on_event("startup")
def _startup():
    _init_db()


@app.get("/salud")
def salud():
    return {"ok": True}


@app.post("/activar")
def activar(body: ActivarIn):
    payload = _verificar_codigo(body.codigo)
    licencia_id = str(payload.get("licencia_id") or payload.get("id") or body.licencia_id or "")
    if not licencia_id:
        raise HTTPException(status_code=400, detail="La licencia no tiene id.")
    mid = body.machine_id.strip().upper()
    max_pcs = int(payload.get("max_pcs") or payload.get("cupo") or body.max_pcs or 1)
    cliente = payload.get("cliente") or body.cliente

    # Si trae lista de machines, solo esas pueden activarse.
    maquinas = payload.get("machines") or []
    if maquinas and mid not in [str(m).upper() for m in maquinas]:
        raise HTTPException(status_code=403, detail="Esta PC no esta autorizada en la licencia.")

    with _conn() as c:
        activa = c.execute(
            "SELECT machine_id FROM activaciones WHERE licencia_id=? AND revocado=0",
            (licencia_id,),
        ).fetchall()
        ya = {row["machine_id"] for row in activa}
        if mid in ya:
            return {"ok": True, "detalle": "Esta PC ya estaba registrada.", "activadas": len(ya), "max_pcs": max_pcs}
        if len(ya) >= max_pcs:
            raise HTTPException(
                status_code=403,
                detail=f"Cupo agotado: {len(ya)}/{max_pcs} PCs ya activadas para esta licencia.",
            )
        c.execute(
            """
            INSERT INTO activaciones (licencia_id, machine_id, cliente, max_pcs, activado_en, revocado)
            VALUES (?, ?, ?, ?, ?, 0)
            ON CONFLICT(licencia_id, machine_id) DO UPDATE SET revocado=0, activado_en=excluded.activado_en
            """,
            (licencia_id, mid, cliente, max_pcs, datetime.now(timezone.utc).isoformat()),
        )
        total = len(ya) + 1
    return {"ok": True, "detalle": "PC registrada en el cupo.", "activadas": total, "max_pcs": max_pcs}


@app.post("/revocar")
def revocar(licencia_id: str, machine_id: str, token: str = ""):
    """Revoca un equipo. Protegido por LICENCIAS_ADMIN_TOKEN si esta definido."""
    esperado = os.getenv("LICENCIAS_ADMIN_TOKEN", "")
    if esperado and token != esperado:
        raise HTTPException(status_code=401, detail="Token de administrador invalido.")
    with _conn() as c:
        c.execute(
            "UPDATE activaciones SET revocado=1 WHERE licencia_id=? AND machine_id=?",
            (licencia_id, machine_id.strip().upper()),
        )
    return {"ok": True}


@app.get("/estado/{licencia_id}")
def estado(licencia_id: str):
    with _conn() as c:
        rows = c.execute(
            "SELECT machine_id, cliente, max_pcs, activado_en, revocado FROM activaciones WHERE licencia_id=?",
            (licencia_id,),
        ).fetchall()
    return {
        "licencia_id": licencia_id,
        "activaciones": [dict(r) for r in rows],
        "activas": sum(1 for r in rows if not r["revocado"]),
    }
