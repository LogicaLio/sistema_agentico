from tools.actividades_tool import consultar_actividades, priorizar_actividades
from tools.asignatura_tool import consultar_informacion_asignatura
from tools.calendario_tool import consultar_calendario_academico
from tools.fecha_tool import obtener_fecha
from tools.horario_tool import consultar_horario
from tools.rag_tool import consultar_base_conocimiento

TOOLS_ACADEMICAS = [
    obtener_fecha,
    consultar_horario,
    consultar_actividades,
    consultar_calendario_academico,
    consultar_informacion_asignatura,
    priorizar_actividades,
    consultar_base_conocimiento,  # RAG
]
