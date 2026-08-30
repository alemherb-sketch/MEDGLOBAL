"""Genera el par de claves Ed25519 para firmar licencias de escritorio.

Uso (en un PC de administracion, NO en las PCs de clinicas):

    cd backend
    python generar_claves_licencia.py

Crea:
  licencia_privada.pem  <-- GUARDELA EN SECRETO. Nunca va en el .exe ni en git.
  licencia_publica.pem  <-- se empaqueta en la app de escritorio.

Si los archivos ya existen, no los pisa salvo que pase --forzar.
"""
from __future__ import annotations

import argparse
import os
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description="Genera claves de licencia MEDGLOBAL")
    parser.add_argument(
        "--dir",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Carpeta de salida (por defecto: backend/)",
    )
    parser.add_argument("--forzar", action="store_true", help="Sobrescribe claves existentes")
    args = parser.parse_args(argv)

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        print("Instale cryptography: pip install cryptography", file=sys.stderr)
        return 1

    privada_path = os.path.join(args.dir, "licencia_privada.pem")
    publica_path = os.path.join(args.dir, "licencia_publica.pem")

    if (os.path.exists(privada_path) or os.path.exists(publica_path)) and not args.forzar:
        print(f"Ya existen claves en {args.dir}. Use --forzar para regenerar.", file=sys.stderr)
        return 2

    clave = Ed25519PrivateKey.generate()
    with open(privada_path, "wb") as f:
        f.write(
            clave.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(publica_path, "wb") as f:
        f.write(
            clave.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    # Restringir permisos en sistemas Unix; en Windows no aplica de igual forma.
    try:
        os.chmod(privada_path, 0o600)
    except OSError:
        pass

    print(f"Privada: {privada_path}")
    print(f"Publica: {publica_path}")
    print("IMPORTANTE: guarde la privada fuera del repositorio y del instalable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
