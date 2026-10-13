import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

from tools._datos import cargar_json

PESO_PRIORIDAD = {"alta": 3, "media": 2, "baja": 1}


def _hoy() -> date:
    return datetime.now(ZoneInfo("America/Bogota")).date()


@tool
def consultar_actividades(asignatura: str = "") -> str:
    """Lista las actividades (tareas, talleres, entregas) pendientes del estudiante.
    Si se indica 'asignatura', filtra solo las de esa materia; si se deja vacío, devuelve todas."""
    actividades = [a for a in cargar_json("actividades.json") if a.get("estado") == "pendiente"]
    if asignatura.strip():
        actividades = [
            a for a in actividades
            if asignatura.strip().lower() in a["asignatura"].lower()
        ]
    if not actividades:
        return "No hay actividades pendientes para esa consulta."
    return json.dumps(actividades, ensure_ascii=False)


@tool
def priorizar_actividades() -> str:
    """Ordena las actividades pendientes por urgencia: primero las más cercanas
    a su fecha de entrega y, a igual fecha, las de mayor prioridad.
    Úsala cuando el estudiante pida priorizar u organizar sus tareas."""
    hoy = _hoy()
    resultado = []
    for a in cargar_json("actividades.json"):
        if a.get("estado") != "pendiente":
            continue
        dias = (date.fromisoformat(a["fecha_entrega"]) - hoy).days
        resultado.append({**a, "dias_restantes": dias})
    resultado.sort(key=lambda a: (a["dias_restantes"], -PESO_PRIORIDAD.get(a["prioridad"], 0)))
    if not resultado:
        return "No hay actividades pendientes."
    return json.dumps(resultado, ensure_ascii=False)
