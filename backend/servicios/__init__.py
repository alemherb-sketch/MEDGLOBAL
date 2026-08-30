"""Logica de negocio compartida por los routers.

Se separa de los endpoints para que la misma regla (descontar stock, generar
un codigo correlativo, leer un Excel) tenga UNA sola implementacion, en vez de
repetirse en cada endpoint que la necesita.
"""
