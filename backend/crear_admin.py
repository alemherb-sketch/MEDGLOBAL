"""Crea el primer usuario administrador de MEDGLOBAL.

No hay una pantalla publica de registro (correcto: el alta de usuarios
la hace un administrador). Correr una sola vez por base de datos:

    python crear_admin.py
"""
import getpass

import auth
import models
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)


def main():
    db = SessionLocal()
    try:
        username = input("Usuario (para iniciar sesion): ").strip()
        if not username:
            print("El usuario no puede estar vacio.")
            return
        if db.query(models.Usuario).filter(models.Usuario.username == username).first():
            print(f"Ya existe un usuario con el nombre '{username}'.")
            return

        nombre = input("Nombre completo: ").strip()
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirmar password: ")
        if password != password_confirm:
            print("Las contraseñas no coinciden.")
            return
        if len(password) < 8:
            print("La contraseña debe tener al menos 8 caracteres.")
            return

        admin = models.Usuario(
            username=username,
            nombre=nombre or username,
            password_hash=auth.hash_password(password),
            rol="ADMIN",
            estado="ACTIVO",
        )
        db.add(admin)
        db.commit()
        print(f"Usuario administrador '{username}' creado correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
