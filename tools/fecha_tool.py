from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


@tool
def obtener_fecha() -> str:
    """Devuelve la fecha actual, el día de la semana y la hora en Colombia.
    Úsala siempre que necesites saber qué día es hoy o mañana."""
    ahora = datetime.now(ZoneInfo("America/Bogota"))
    return (
        f"Hoy es {DIAS[ahora.weekday()]} {ahora.strftime('%Y-%m-%d')}, "
        f"hora {ahora.strftime('%H:%M')} (Colombia)."
    )
