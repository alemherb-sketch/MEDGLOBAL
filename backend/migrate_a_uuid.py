"""Migración de datos: esquema con IDs enteros (actual) -> esquema con IDs UUID (Fase 1).

CONTEXTO
--------
Fase 1 del plan de sincronización cambió cada id de Integer a UUID (ver
models.py). Una base de datos que ya tiene datos con ids enteros NO puede
actualizarse con un simple ALTER TABLE, porque cambia el tipo de cada llave
primaria y hay más de una docena de llaves foráneas apuntando a esos ids.

Este script NO modifica la base de datos ORIGEN. Lee todo en memoria, arma
un mapeo id_entero -> uuid por tabla, y ESCRIBE en una base de datos DESTINO
(vacía, con el esquema nuevo ya creado vía create_all). Si algo falla a
mitad de camino, no se dañó nada: se vacía el destino y se corre de nuevo,
el origen sigue intacto.

De paso, sirve como el script de migración de datos Render -> VPS que ya
estaba planeado por separado — hace las dos cosas en un solo paso (cambia
de base de datos y de esquema a la vez), en vez de migrar dos veces.

CÓMO CORRERLO (con cuidado, no es automático)
----------------------------------------------
1. Respaldo del origen ANTES que nada, sin excepción:
     pg_dump "$SOURCE_DATABASE_URL" > backup_antes_de_migrar_uuid.sql

2. Tener lista la base de datos DESTINO (puede ser una base nueva en Render,
   o ya la de Postgres en el VPS) — debe estar VACÍA o no tener estas tablas
   todavía.

3. Correr, con las dos URLs de conexión como variables de entorno:

     SOURCE_DATABASE_URL=postgresql://usuario:pass@host/db_actual \\
     TARGET_DATABASE_URL=postgresql://usuario:pass@host/db_nueva \\
     python migrate_a_uuid.py

4. El script imprime cuántas filas copió por tabla. Comparar ese conteo
   contra un SELECT count(*) manual en el origen para cada tabla.

5. Recién después de verificar los conteos y revisar algunos registros a
   mano, cambiar DATABASE_URL de la app para que apunte al destino nuevo.

No se ejecuta solo al arrancar la app ni en ningún deploy — es un script
aparte, pensado para correrse una sola vez, a propósito, con las dos
variables de entorno de arriba.
"""
import os
import sys
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text, inspect as sa_inspect
from sqlalchemy.orm import sessionmaker

import models  # esquema NUEVO (UUID) — se usa solo para escribir en el destino


def _connect(url_env_var):
    url = os.getenv(url_env_var)
    if not url:
        print(f"Falta la variable de entorno {url_env_var}")
        sys.exit(1)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return create_engine(url)


def new_uuid():
    return str(uuid.uuid4())


def _parse_dt(value):
    """Postgres (el origen real) ya entrega datetime nativo; esto es solo
    por si el driver de origen devuelve texto (ej. al probar con SQLite)."""
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def main():
    source_engine = _connect("SOURCE_DATABASE_URL")
    target_engine = _connect("TARGET_DATABASE_URL")

    # Crea el esquema nuevo (con UUIDs) en el destino, si no existe ya
    models.Base.metadata.create_all(bind=target_engine)
    TargetSession = sessionmaker(bind=target_engine)
    target = TargetSession()

    now = datetime.utcnow()
    counts = {}
    id_maps = {}

    with source_engine.connect() as src:
        source_inspector = sa_inspect(src)

        def fetch_all(table, order_by=None):
            if not source_inspector.has_table(table):
                print(f"  (tabla '{table}' no existe en el origen — se omite, 0 filas)")
                return []
            sql = f"SELECT * FROM {table}"
            if order_by:
                sql += f" ORDER BY {order_by} ASC"
            return src.execute(text(sql)).mappings().all()

        # ── Tablas sin FK propias ──
        def migrate_simple(table, model, columns):
            rows = fetch_all(table)
            id_map = {}
            for row in rows:
                nid = new_uuid()
                id_map[row["id"]] = nid
                kwargs = {c: row.get(c) for c in columns}
                target.add(model(id=nid, created_at=now, updated_at=now, **kwargs))
            target.commit()
            counts[table] = len(rows)
            return id_map

        id_maps["empresas"] = migrate_simple(
            "empresas", models.Empresa,
            ["nombre", "ruc", "direccion", "telefono", "correo_electronico", "estado"],
        )
        id_maps["sistemas"] = migrate_simple("sistemas", models.SistemaAtencion, ["nombre"])
        id_maps["clasificaciones"] = migrate_simple(
            "clasificaciones", models.ClasificacionAtencion, ["nombre"]
        )
        id_maps["diagnosticos_cie10"] = migrate_simple(
            "diagnosticos_cie10", models.DiagnosticoCie10, ["codigo", "descripcion", "estado"]
        )
        id_maps["medicamentos"] = migrate_simple(
            "medicamentos", models.Medicamento,
            ["codigo", "nombre", "presentacion", "descripcion", "stock_actual", "costo_unitario"],
        )
        id_maps["personal_salud"] = migrate_simple(
            "personal_salud", models.PersonalSalud,
            ["nombre", "apellidos", "especialidad", "cmp", "telefono", "correo", "estado"],
        )

        # Usuarios: se preserva el hash de password tal cual, nada que reinterpretar
        rows = fetch_all("usuarios")
        for row in rows:
            target.add(models.Usuario(
                id=new_uuid(), username=row["username"], password_hash=row["password_hash"],
                nombre=row.get("nombre"), rol=row.get("rol"), estado=row.get("estado"),
                creado_en=_parse_dt(row.get("creado_en")),
            ))
        target.commit()
        counts["usuarios"] = len(rows)

        # ── Trabajadores (FK -> empresas) ──
        rows = fetch_all("trabajadores")
        id_maps["trabajadores"] = {}
        for row in rows:
            nid = new_uuid()
            id_maps["trabajadores"][row["id"]] = nid
            empresa_old = row.get("empresa_id")
            target.add(models.Trabajador(
                id=nid, created_at=now, updated_at=now,
                nombre=row["nombre"], apellidos=row["apellidos"], dni=row["dni"],
                tipo_contrato=row.get("tipo_contrato"), afp_onp=row.get("afp_onp"), rol=row.get("rol"),
                codigo_trabajador=row.get("codigo_trabajador"), cargo=row.get("cargo"),
                fecha_ingreso=row.get("fecha_ingreso"), fecha_cese=row.get("fecha_cese"),
                estado_trabajador=row.get("estado_trabajador"), subdivision_sede=row.get("subdivision_sede"),
                centro_costo=row.get("centro_costo"), tipo_calculo_nomina=row.get("tipo_calculo_nomina"),
                area=row.get("area"), obra=row.get("obra"), area_personal=row.get("area_personal"),
                grupo_personal=row.get("grupo_personal"),
                nivel_org_1=row.get("nivel_org_1"), nivel_org_2=row.get("nivel_org_2"),
                nivel_org_3=row.get("nivel_org_3"), nivel_org_4=row.get("nivel_org_4"),
                nivel_org_5=row.get("nivel_org_5"),
                fecha_nacimiento=row.get("fecha_nacimiento"), genero=row.get("genero"),
                jefe_inmediato=row.get("jefe_inmediato"), telefono=row.get("telefono"),
                correo_electronico=row.get("correo_electronico"),
                empresa_id=id_maps["empresas"].get(empresa_old) if empresa_old else None,
            ))
        target.commit()
        counts["trabajadores"] = len(rows)

        # ── Citas (FK -> trabajadores, personal_salud) ──
        rows = fetch_all("citas")
        id_maps["citas"] = {}
        for row in rows:
            nid = new_uuid()
            id_maps["citas"][row["id"]] = nid
            target.add(models.Cita(
                id=nid, created_at=now, updated_at=now,
                fecha_hora=_parse_dt(row["fecha_hora"]), motivo=row.get("motivo"), estado=row.get("estado"),
                paciente_id=id_maps["trabajadores"].get(row["paciente_id"]),
                personal_salud_id=id_maps["personal_salud"].get(row["personal_salud_id"]),
            ))
        target.commit()
        counts["citas"] = len(rows)

        # ── Atenciones (FK -> trabajadores, sistemas, clasificaciones, citas, empresas, personal_salud) ──
        # El folio nuevo sigue el mismo orden que los ids viejos (ORDER BY id),
        # para que "Ficha N°" en las fichas impresas siga significando lo mismo
        # que antes de migrar, aunque el id interno ahora sea un UUID.
        rows = fetch_all("atenciones", order_by="id")
        id_maps["atenciones"] = {}
        for folio, row in enumerate(rows, start=1):
            nid = new_uuid()
            id_maps["atenciones"][row["id"]] = nid
            cita_old = row.get("cita_id")
            personal_old = row.get("personal_salud_id")
            empresa_old = row.get("empresa_id")
            target.add(models.Atencion(
                id=nid, folio=folio, created_at=now, updated_at=now,
                fecha=_parse_dt(row["fecha"]), hora_ingreso=row.get("hora_ingreso"), hora_salida=row.get("hora_salida"),
                tiempo_topico=row.get("tiempo_topico"), edad=row.get("edad"), residencia=row.get("residencia"),
                cargo=row.get("cargo"), descripcion=row["descripcion"],
                funciones_biologicas=row.get("funciones_biologicas"), signos_vitales=row.get("signos_vitales"),
                examen_fisico=row.get("examen_fisico"), examenes_auxiliares=row.get("examenes_auxiliares"),
                codigo_diagnostico=row.get("codigo_diagnostico"), diagnostico=row.get("diagnostico"),
                diagnostico_1=row.get("diagnostico_1"), diagnostico_2=row.get("diagnostico_2"),
                diagnostico_3=row.get("diagnostico_3"),
                tratamiento=row.get("tratamiento"), destino=row.get("destino"),
                sede_atencion=row.get("sede_atencion"), jefe_inmediato=row.get("jefe_inmediato"),
                observaciones=row.get("observaciones"),
                trabajador_id=id_maps["trabajadores"].get(row["trabajador_id"]),
                sistema_id=id_maps["sistemas"].get(row["sistema_id"]),
                clasificacion_id=id_maps["clasificaciones"].get(row["clasificacion_id"]),
                cita_id=id_maps["citas"].get(cita_old) if cita_old else None,
                personal_salud_id=id_maps["personal_salud"].get(personal_old) if personal_old else None,
                empresa_id=id_maps["empresas"].get(empresa_old) if empresa_old else None,
            ))
        target.commit()
        counts["atenciones"] = len(rows)

        # ── Atencion_medicamentos (FK -> atenciones, medicamentos) ──
        rows = fetch_all("atencion_medicamentos")
        for row in rows:
            target.add(models.AtencionMedicamento(
                id=new_uuid(),
                atencion_id=id_maps["atenciones"].get(row["atencion_id"]),
                medicamento_id=id_maps["medicamentos"].get(row["medicamento_id"]),
                cantidad=row.get("cantidad", 1),
            ))
        target.commit()
        counts["atencion_medicamentos"] = len(rows)

        # ── Kardex (FK -> medicamentos) ──
        rows = fetch_all("kardex")
        for row in rows:
            target.add(models.Kardex(
                id=new_uuid(), created_at=now, updated_at=now,
                medicamento_id=id_maps["medicamentos"].get(row["medicamento_id"]),
                fecha=_parse_dt(row["fecha"]), tipo_movimiento=row["tipo_movimiento"],
                cantidad=row["cantidad"], saldo=row["saldo"],
            ))
        target.commit()
        counts["kardex"] = len(rows)

    target.close()

    print("\nMigración completa. Filas copiadas por tabla:")
    for table, n in counts.items():
        print(f"  {table}: {n}")
    print("\nLa base de datos ORIGEN no fue modificada. Compara los conteos de")
    print("arriba contra un SELECT count(*) manual en el origen antes de apuntar")
    print("la app al destino nuevo.")


if __name__ == "__main__":
    main()
