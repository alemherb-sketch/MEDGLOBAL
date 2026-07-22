"""Reinicia el catalogo a estado 'limpio': pone stock_actual en 0 en todos
los medicamentos y borra (soft-delete) todos los movimientos de Kardex, para
arrancar el conteo de inventario desde cero despues de una importacion de
prueba. Pide confirmacion explicita antes de tocar nada. Correr con:

    python reset_stock.py
"""
import os


def _cargar_env_local():
    """Si DATABASE_URL no esta ya en el ambiente, la carga desde el .env
    junto a este archivo -- para poder correr el script suelto sin tener
    que exportar variables a mano (igual que app_desktop.py)."""
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


_cargar_env_local()

import models
from database import SessionLocal


def main():
    db = SessionLocal()
    try:
        medicamentos = db.query(models.Medicamento).filter(models.Medicamento.is_deleted == False).all()
        kardex_rows = db.query(models.Kardex).filter(models.Kardex.is_deleted == False).all()

        print(f"Medicamentos en el catalogo: {len(medicamentos)}")
        print(f"Movimientos de Kardex activos: {len(kardex_rows)}")

        if not medicamentos and not kardex_rows:
            print("No hay nada que reiniciar.")
            return

        confirm = input(
            "Esto pone el stock en 0 en TODOS los medicamentos de arriba y "
            "borra TODOS los movimientos de Kardex de arriba. Escribe 'SI' "
            "para continuar: "
        ).strip()
        if confirm != "SI":
            print("Cancelado, no se cambio nada.")
            return

        for m in medicamentos:
            m.stock_actual = 0
        for k in kardex_rows:
            k.is_deleted = True

        db.commit()
        print(f"Listo: {len(medicamentos)} medicamentos con stock en 0, {len(kardex_rows)} movimientos de Kardex borrados.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
