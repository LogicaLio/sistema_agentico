"""Ejecuta un turno del grafo y devuelve el resultado con sus métricas (sin depender de Streamlit)."""

import time
import uuid
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage

from config import settings
from core.errores import TurnoFallido
from observabilidad.metricas import REGISTRO


@dataclass
class ResultadoTurno:
    respuesta: str
    pasos: list[str] = field(default_factory=list)
    herramientas: list[str] = field(default_factory=list)
    ruta: str = ""
    metricas: dict = field(default_factory=dict)


def texto_de_contenido(contenido) -> str:
    """Gemini puede devolver el contenido como lista de partes; lo unificamos a texto."""
    if isinstance(contenido, str):
        return contenido
    return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in contenido)


def ejecutar_turno(grafo, texto: str, estudiante: dict, thread_id: str) -> ResultadoTurno:
    turno_id = uuid.uuid4().hex[:8]
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": settings.RECURSION_LIMIT,
    }
    estado_inicial = {
        "messages": [HumanMessage(content=texto)],
        "estudiante": estudiante,
        "pasos_ejecutados": [],  # la traza y las tools son por turno
        "herramientas_usadas": [],
        "turno_id": turno_id,
    }
    t0 = time.perf_counter()
    try:
        resultado = grafo.invoke(estado_inicial, config=config)
    except Exception as exc:
        metricas = REGISTRO.cerrar_turno(
            turno_id, thread_id, texto, "", (time.perf_counter() - t0) * 1000,
            error=f"{type(exc).__name__}: {exc}"[:1500],
        )
        raise TurnoFallido(exc, metricas) from exc

    respuesta = texto_de_contenido(resultado["messages"][-1].content)
    pasos = resultado.get("pasos_ejecutados", [])
    metricas = REGISTRO.cerrar_turno(
        turno_id, thread_id, texto, respuesta, (time.perf_counter() - t0) * 1000,
        ruta=resultado.get("ruta", ""), pasos=pasos,
    )
    return ResultadoTurno(
        respuesta=respuesta,
        pasos=pasos,
        herramientas=resultado.get("herramientas_usadas", []),
        ruta=resultado.get("ruta", ""),
        metricas=metricas,
    )
