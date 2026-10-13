"""Utilidad compartida para leer los JSON de la carpeta data/."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def cargar_json(nombre_archivo: str):
    ruta = DATA_DIR / nombre_archivo
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)
