import json

from langchain_core.tools import tool

from tools._datos import cargar_json


@tool
def consultar_calendario_academico(consulta: str = "") -> str:
    """Consulta el calendario académico institucional: inicio y fin de clases,
    festivos, semanas de parciales y cancelaciones.
    'consulta' es una palabra clave (ej. 'fin de clases', 'festivo', 'parciales');
    si se deja vacío devuelve todos los eventos."""
    eventos = cargar_json("calendario.json")
    termino = consulta.strip().lower()
    if termino:
        eventos = [e for e in eventos if termino in e["evento"].lower()]
    if not eventos:
        return f"No encontré eventos del calendario para '{consulta}'."
    return json.dumps(eventos, ensure_ascii=False)
