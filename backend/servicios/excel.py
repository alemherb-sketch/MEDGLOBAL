"""Lectura de los Excel reales de la clinica (catalogo e importaciones).

Los archivos que llegan no son una tabla limpia: traen fila de titulo arriba,
encabezados con acentos y de varias formas ("Costo Unitario", "PRECIO",
"Fec. Venc."), precios formateados como moneda ("S/ 37.20") y vencimientos
abreviados en espanol ("sep.-28"). Todo eso se normaliza aca para que los
endpoints de importacion queden con la logica de negocio y nada mas.
"""
import re
from datetime import datetime

import pandas as pd

TIPOS_VALIDOS = {"MEDICAMENTO", "INSUMO", "OTROS"}

# Encabezado normalizado -> nombre del campo del modelo.
ALIAS_ENCABEZADOS = {
    "codigo": "codigo",
    "nombre": "nombre",
    "medicamento": "nombre",
    "producto": "nombre",
    "presentacion": "presentacion",
    "tipo": "tipo",
    "descripcion": "descripcion",
    "costounitario": "costo_unitario",
    "costo": "costo_unitario",
    "precio": "costo_unitario",
    "preciounitario": "costo_unitario",
    "lote": "lote",
    "fechavencimiento": "fecha_vencimiento",
    "vencimiento": "fecha_vencimiento",
    "fecvenc": "fecha_vencimiento",
    "fecvencimiento": "fecha_vencimiento",
    "stock": "stock_inicial",
    "stockactual": "stock_inicial",
    "stockinicial": "stock_inicial",
}

_MESES_ES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
}

_SIN_ACENTOS = str.maketrans("áéíóúñ", "aeioun")


def normalizar_encabezado(valor) -> str:
    """"Costo Unitario" / "COSTO_UNITARIO" / "Costo-Unitario" -> "costounitario"."""
    texto = str(valor).strip().lower().translate(_SIN_ACENTOS)
    return re.sub(r"[\s_\-\.]+", "", texto)


def fila_de_encabezados(contenido: bytes, buscar_en: int = 10) -> int:
    """Indice de la fila que trae los encabezados.

    No siempre es la primera: varios archivos reales tienen una fila de titulo
    o una fila vacia arriba de la tabla. Gana la fila con mas encabezados
    reconocibles; -1 si ninguna tiene alguno."""
    import io as _io

    muestra = pd.read_excel(_io.BytesIO(contenido), header=None, nrows=buscar_en)
    mejor_fila, mejor_cantidad = 0, -1
    for i in range(len(muestra)):
        cantidad = sum(1 for v in muestra.iloc[i].tolist() if ALIAS_ENCABEZADOS.get(normalizar_encabezado(v)))
        if cantidad > mejor_cantidad:
            mejor_fila, mejor_cantidad = i, cantidad
    return mejor_fila if mejor_cantidad > 0 else -1


def parsear_costo(valor) -> float:
    """Numeros tal cual, o texto con simbolo de moneda ("S/ 1,234.50")."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = re.sub(r"[^\d.,\-]", "", str(valor))
    if not texto:
        return 0.0
    if "," in texto and "." in texto:
        texto = texto.replace(",", "")       # 1,234.50 -> separador de miles
    elif "," in texto:
        texto = texto.replace(",", ".")      # 1234,50  -> decimal europeo
    try:
        return float(texto)
    except ValueError:
        return 0.0


def parsear_vencimiento(valor):
    """Fechas reales de Excel y el abreviado en espanol ("sep.-28" -> 2028-09-01)."""
    if valor is None:
        return None
    if isinstance(valor, (pd.Timestamp, datetime)):
        return valor.strftime("%Y-%m-%d")
    texto = str(valor).strip()
    encontrado = re.match(r"^([a-zA-Z]{3})\.?-?(\d{2,4})$", texto)
    if encontrado:
        mes = _MESES_ES.get(encontrado.group(1).lower())
        anio = int(encontrado.group(2))
        if anio < 100:
            anio += 2000
        if mes:
            return f"{anio:04d}-{mes:02d}-01"
    return texto


def recortar(valor, largo: int):
    """Recorta al limite de la columna: una celda mas larga de lo esperado no
    debe tumbar el INSERT de las 200+ filas restantes de la misma importacion."""
    return valor if valor is None else str(valor).strip()[:largo]


def valor_de_celda(fila, columna, columnas_presentes):
    if columna not in columnas_presentes:
        return None
    valor = fila[columna]
    if isinstance(valor, pd.Series):   # encabezado duplicado en el archivo
        valor = valor.iloc[0]
    return None if pd.isna(valor) else valor
