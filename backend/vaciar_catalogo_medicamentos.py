"""Vacia por completo el catalogo de medicamentos (soft-delete, igual que el
boton Eliminar de la app: is_deleted=True, no un DELETE fisico) y sus
movimientos de Kardex, para arrancar realmente desde cero -- a diferencia de
reset_stock.py, que solo pone el stock en 0 pero deja los medicamentos
importados en el catalogo. Pide confirmacion explicita antes de tocar nada.
Correr con:

    python vaciar_catalogo_medicamentos.py
"""
import os


def _cargar_env_local():
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
            print("El catalogo ya esta vacio, no hay nada que hacer.")
            return

        confirm = input(
            "Esto BORRA (soft-delete) los medicamentos y movimientos de "
            "Kardex de arriba, dejando el catalogo completamente vacio. "
            "Escribe 'SI' para continuar: "
        ).strip()
        if confirm != "SI":
            print("Cancelado, no se cambio nada.")
            return

        for m in medicamentos:
            m.is_deleted = True
        for k in kardex_rows:
            k.is_deleted = True

        db.commit()
        print(f"Listo: {len(medicamentos)} medicamentos y {len(kardex_rows)} movimientos de Kardex borrados. El catalogo quedo vacio.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
