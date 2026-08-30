"""Emite codigos de licencia firmados para PCs de escritorio MEDGLOBAL.

Requiere licencia_privada.pem (ver generar_claves_licencia.py).

Ejemplos:

  # Una PC (recomendado): el cliente envia su machine_id desde la pantalla
  # de activacion y usted emite:
  python generar_licencia.py --cliente "Clinica Norte" --machine-id ABC123... --dias 365

  # Varias PCs del mismo cliente (cupo = cantidad de machine-id):
  python generar_licencia.py --cliente "Clinica Norte" \\
      --machine-id AAA --machine-id BBB --machine-id CCC --dias 365

  # Licencia por cupo (requiere micro-servicio desktop/servidor_licencias):
  python generar_licencia.py --cliente "Clinica Norte" --max-pcs 5 --dias 365

La salida es un codigo de una sola linea que se pega en la app.
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone


def main(argv=None):
    parser = argparse.ArgumentParser(description="Emite una licencia MEDGLOBAL de escritorio")
    parser.add_argument("--cliente", required=True, help="Nombre del cliente / clinica")
    parser.add_argument(
        "--machine-id",
        action="append",
        dest="machines",
        default=[],
        help="ID de PC autorizada (repetible). Se muestra en la pantalla de activacion.",
    )
    parser.add_argument("--max-pcs", type=int, default=0, help="Cupo de PCs (modo registro online)")
    parser.add_argument("--dias", type=int, default=365, help="Vigencia en dias (0 = sin caducidad)")
    parser.add_argument(
        "--privada",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "licencia_privada.pem"),
        help="Ruta a licencia_privada.pem",
    )
    parser.add_argument("--salida", default="", help="Si se indica, guarda el codigo en este archivo")
    args = parser.parse_args(argv)

    machines = [m.strip().upper() for m in (args.machines or []) if m and m.strip()]
    max_pcs = args.max_pcs or len(machines)

    if not machines and max_pcs <= 0:
        print("Indique al menos un --machine-id o un --max-pcs > 0.", file=sys.stderr)
        return 2

    if not os.path.exists(args.privada):
        print(
            f"No se encontro {args.privada}. Ejecute primero: python generar_claves_licencia.py",
            file=sys.stderr,
        )
        return 1

    # Import local para reutilizar el codec de firma
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import licencias

    ahora = datetime.now(timezone.utc)
    payload = {
        "producto": "MEDGLOBAL-DESKTOP",
        "licencia_id": str(uuid.uuid4()),
        "cliente": args.cliente,
        "emitida": ahora.isoformat(),
        "max_pcs": max_pcs,
        "machines": machines,
    }
    if args.dias > 0:
        payload["expira"] = (ahora + timedelta(days=args.dias)).isoformat()

    with open(args.privada, "rb") as f:
        privada = f.read()

    codigo = licencias.firmar_payload(payload, privada)

    if args.salida:
        with open(args.salida, "w", encoding="utf-8") as f:
            f.write(codigo)
        print(f"Licencia guardada en {args.salida}")

    print("--- LICENCIA MEDGLOBAL ---")
    print(f"Cliente:    {args.cliente}")
    print(f"ID:         {payload['licencia_id']}")
    print(f"Max PCs:    {max_pcs}")
    print(f"Machines:   {', '.join(machines) if machines else '(cupo online)'}")
    print(f"Expira:     {payload.get('expira', 'sin caducidad')}")
    print("--- CODIGO (copiar completo) ---")
    print(codigo)
    print("--- FIN ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
