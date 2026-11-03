"""Matriz de escenarios compartida por pytest y por el generador de evidencias."""

ESTUDIANTE = {"nombre": "Alexander", "programa": "Ingeniería de Sistemas", "semestre": "6"}


def plan_simulado(pregunta: str):
    """Decisiones que tomaría Gemini en cada pregunta (solo para el modo simulado)."""
    if "lunes" in pregunta:
        return [("consultar_horario", {"consulta": "lunes"})]
    if "hoy tengo clase" in pregunta:
        return [("obtener_fecha", {}), ("consultar_horario", {"consulta": "martes"})]
    if "prioriza" in pregunta:
        return [("priorizar_actividades", {})]
    if "terminan las clases" in pregunta:
        return [("consultar_calendario_academico", {"consulta": "fin de clases"})]
    if "sistemas agénticos" in pregunta or "sistemas agenticos" in pregunta:
        return [("consultar_informacion_asignatura", {"nombre": "Sistemas Agénticos"})]
    if "actividades de redes" in pregunta:
        return [("consultar_actividades", {"asignatura": "Redes"})]
    if "inasistencia" in pregunta or "faltas" in pregunta:
        return [("consultar_base_conocimiento", {"pregunta": "pérdida por inasistencia"})]
    return None  # conceptual


AGENTE = ["enrutador", "agente_academico", "herramientas", "agente_academico"]

# id, funcionalidad, pregunta, pasos esperados, tools esperadas
ESCENARIOS = [
    ("T01", "Ruta conceptual (sin herramientas)", "¿Qué es un crédito académico?",
     ["enrutador", "nodo_conceptual"], []),
    ("T02", "Tool consultar_horario", "¿Qué clases tengo el lunes?", AGENTE, ["consultar_horario"]),
    ("T03", "Ciclo ReAct con 2 herramientas", "¿Hoy tengo clase?",
     AGENTE + ["herramientas", "agente_academico"], ["obtener_fecha", "consultar_horario"]),
    ("T04", "Tool priorizar_actividades", "Prioriza mis actividades pendientes", AGENTE, ["priorizar_actividades"]),
    ("T05", "Tool consultar_calendario_academico", "¿Cuándo terminan las clases?", AGENTE,
     ["consultar_calendario_academico"]),
    ("T06", "Tool consultar_informacion_asignatura", "¿Cuántos créditos tiene Sistemas Agénticos?", AGENTE,
     ["consultar_informacion_asignatura"]),
    ("T07", "Tool consultar_actividades", "Muéstrame las actividades de Redes", AGENTE, ["consultar_actividades"]),
    ("T08", "RAG: base de conocimiento", "¿Qué pasa si tengo muchas faltas por inasistencia?", AGENTE,
     ["consultar_base_conocimiento"]),
]
