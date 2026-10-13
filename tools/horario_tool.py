import json

from langchain_core.tools import tool

from tools._datos import cargar_json


@tool
def consultar_horario(consulta: str) -> str:
    """Consulta el horario de clases del estudiante.
    El parámetro 'consulta' puede ser un día de la semana (ej. 'lunes')
    o el nombre de una asignatura (ej. 'Bases de Datos')."""
    horarios = cargar_json("horarios.json")
    if isinstance(horarios, dict):
        # Si el JSON viene como {"horarios": [...]} se toma la primera lista.
        horarios = next((v for v in horarios.values() if isinstance(v, list)), [])

    termino = consulta.strip().lower()
    coincidencias = [
        clase for clase in horarios
        if termino in json.dumps(clase, ensure_ascii=False).lower()
    ]
    if not coincidencias:
        return f"No encontré clases que coincidan con '{consulta}'."
    return json.dumps(coincidencias, ensure_ascii=False)
