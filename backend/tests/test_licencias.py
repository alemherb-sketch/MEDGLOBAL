"""Pruebas del control de licencias de escritorio (offline, firmadas)."""
from __future__ import annotations

import os

import pytest

# cryptography viene con python-jose[cryptography]
pytest.importorskip("cryptography")

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


@pytest.fixture
def claves(tmp_path, monkeypatch):
    privada = Ed25519PrivateKey.generate()
    pub_pem = privada.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv_pem = privada.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_path = tmp_path / "licencia_publica.pem"
    pub_path.write_bytes(pub_pem)

    import licencias
    import rutas

    monkeypatch.setattr(licencias, "_cargar_publica", lambda: pub_pem)
    monkeypatch.setattr(rutas, "CARPETA_DATOS", str(tmp_path / "datos"))
    monkeypatch.setenv("MEDGLOBAL_ESCRITORIO", "1")
    monkeypatch.delenv("MEDGLOBAL_LICENCIA_BYPASS", raising=False)
    monkeypatch.delenv("MEDGLOBAL_LICENCIAS_URL", raising=False)
    return priv_pem, pub_pem, licencias


def test_machine_id_estable(claves):
    _, _, licencias = claves
    a = licencias.machine_id()
    b = licencias.machine_id()
    assert a == b
    assert len(a) == 32


def test_licencia_para_esta_pc(claves):
    priv, _, licencias = claves
    mid = licencias.machine_id()
    payload = {
        "producto": "MEDGLOBAL-DESKTOP",
        "licencia_id": "test-1",
        "cliente": "Prueba",
        "max_pcs": 1,
        "machines": [mid],
    }
    codigo = licencias.firmar_payload(payload, priv)
    r = licencias.activar(codigo)
    assert r["ok"] is True
    estado = licencias.estado_licencia()
    assert estado["valida"] is True
    assert estado["cliente"] == "Prueba"


def test_rechaza_otra_pc(claves):
    priv, _, licencias = claves
    payload = {
        "producto": "MEDGLOBAL-DESKTOP",
        "licencia_id": "test-2",
        "cliente": "Prueba",
        "max_pcs": 1,
        "machines": ["AAAAAAAAAAAAAAAABBBBBBBBBBBBBBBB"],
    }
    codigo = licencias.firmar_payload(payload, priv)
    r = licencias.activar(codigo)
    assert r["ok"] is False
    assert r["motivo"] == "pc_no_autorizada"


def test_firma_invalida(claves):
    priv, _, licencias = claves
    otra = Ed25519PrivateKey.generate()
    priv_otra = otra.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    mid = licencias.machine_id()
    payload = {
        "producto": "MEDGLOBAL-DESKTOP",
        "licencia_id": "test-3",
        "cliente": "Hack",
        "max_pcs": 1,
        "machines": [mid],
    }
    codigo = licencias.firmar_payload(payload, priv_otra)
    r = licencias.activar(codigo)
    assert r["ok"] is False
    assert r["motivo"] == "firma"


def test_web_no_exige_licencia(claves, monkeypatch):
    _, _, licencias = claves
    monkeypatch.delenv("MEDGLOBAL_ESCRITORIO", raising=False)
    estado = licencias.estado_licencia()
    assert estado["requerido"] is False
    assert estado["valida"] is True


def test_multipc_autoriza_todas(claves):
    priv, _, licencias = claves
    mid = licencias.machine_id()
    payload = {
        "producto": "MEDGLOBAL-DESKTOP",
        "licencia_id": "test-4",
        "cliente": "Multi",
        "max_pcs": 3,
        "machines": [mid, "11111111111111112222222222222222", "33333333333333334444444444444444"],
    }
    codigo = licencias.firmar_payload(payload, priv)
    r = licencias.activar(codigo)
    assert r["ok"] is True
    assert r["max_pcs"] == 3
