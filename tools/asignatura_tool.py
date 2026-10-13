import json

from langchain_core.tools import tool

from tools._datos import cargar_json


@tool
def consultar_informacion_asignatura(nombre: str) -> str:
    """Devuelve los créditos y la descripción de una asignatura por su nombre
    (ej. 'Bases de Datos')."""
    termino = nombre.strip().lower()
    coincidencias = [
        a for a in cargar_json("asignaturas.json")
        if termino in a["nombre"].lower()
    ]
    if not coincidencias:
        return f"No encontré la asignatura '{nombre}'."
    return json.dumps(coincidencias, ensure_ascii=False)
