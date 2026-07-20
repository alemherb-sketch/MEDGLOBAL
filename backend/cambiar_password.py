"""Cambia la password de un usuario que ya existe. Complementa a
crear_admin.py (que solo crea usuarios nuevos). Correr con:

    python cambiar_password.py
"""
import getpass

import auth
import models
from database import SessionLocal


def main():
    db = SessionLocal()
    try:
        username = input("Usuario a modificar: ").strip()
        usuario = db.query(models.Usuario).filter(models.Usuario.username == username).first()
        if usuario is None:
            print(f"No existe un usuario con el nombre '{username}'.")
            return

        password = getpass.getpass("Password nueva: ")
        password_confirm = getpass.getpass("Confirmar password nueva: ")
        if password != password_confirm:
            print("Las contraseñas no coinciden.")
            return
        if len(password) < 8:
            print("La contraseña debe tener al menos 8 caracteres.")
            return

        usuario.password_hash = auth.hash_password(password)
        db.commit()
        print(f"Password de '{username}' actualizada correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
