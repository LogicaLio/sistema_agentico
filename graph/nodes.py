"""Nodos del grafo: funciones state -> dict con los cambios a aplicar.

Cada nodo reporta sus métricas (tiempo, tokens, herramientas) a observabilidad.
"""

import time
from functools import lru_cache
from typing import Literal

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from config import settings
from graph.state import AcademicState
from observabilidad.metricas import REGISTRO, extraer_tokens
from prompts.academic_prompt import (
    AGENT_SYSTEM_TEMPLATE,
    CONCEPTUAL_SYSTEM_PROMPT,
    ROUTER_SYSTEM_PROMPT,
)
from tools import TOOLS_ACADEMICAS


class DecisionRuta(BaseModel):
    """Decisión estructurada del nodo enrutador."""

    ruta: Literal["conceptual", "herramientas"] = Field(
        description="'conceptual' si es teórica; 'herramientas' si requiere datos del estudiante o documentos."
    )
    motivo: str = Field(description="Justificación breve de la ruta elegida.")


@lru_cache(maxsize=2)
def obtener_modelo(temperatura: float = 0.3) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperatura,
        timeout=settings.LLM_TIMEOUT,
        max_retries=settings.LLM_MAX_RETRIES,
    )


def _traza(state: AcademicState, nodo: str) -> list[str]:
    return state.get("pasos_ejecutados", []) + [nodo]


def ventana_contexto(mensajes: list[BaseMessage], maximo: int | None = None) -> list[BaseMessage]:
    """Ventana deslizante: reenvía solo los últimos mensajes al modelo.

    La ventana siempre empieza en un HumanMessage para no separar una llamada a
    herramienta de su ToolMessage (Gemini rechaza respuestas huérfanas).
    """
    maximo = settings.MAX_MENSAJES_CONTEXTO if maximo is None else maximo
    if maximo <= 0 or len(mensajes) <= maximo:
        return list(mensajes)
    inicio = len(mensajes) - maximo
    while inicio < len(mensajes) and not isinstance(mensajes[inicio], HumanMessage):
        inicio += 1
    if inicio >= len(mensajes):  # no hay HumanMessage en la ventana: usa el último del historial
        inicio = max(i for i, m in enumerate(mensajes) if isinstance(m, HumanMessage))
    return list(mensajes[inicio:])


def _chars(mensajes: list[BaseMessage]) -> int:
    return sum(len(str(m.content)) for m in mensajes)


def _invocar(state: AcademicState, nodo: str, modelo, mensajes: list[BaseMessage]):
    """Llama al modelo registrando tiempo, tokens y errores."""
    t0 = time.perf_counter()
    try:
        respuesta = modelo.invoke(mensajes)
    except Exception as exc:
        REGISTRO.evento(
            state.get("turno_id"), "llm", nodo=nodo, ms=(time.perf_counter() - t0) * 1000,
            error=f"{type(exc).__name__}: {exc}"[:1500], chars_contexto=_chars(mensajes),
        )
        raise
    REGISTRO.evento(
        state.get("turno_id"), "llm", nodo=nodo, ms=(time.perf_counter() - t0) * 1000,
        chars_contexto=_chars(mensajes), **extraer_tokens(respuesta),
    )
    return respuesta


# Nodo 1: clasificador estructurado (temperatura 0)
def enrutador_node(state: AcademicState) -> dict:
    mensajes = [SystemMessage(content=ROUTER_SYSTEM_PROMPT), state["messages"][-1]]
    clasificador = obtener_modelo(0.0).with_structured_output(DecisionRuta, include_raw=True)
    t0 = time.perf_counter()
    try:
        salida = clasificador.invoke(mensajes)
    except Exception as exc:
        REGISTRO.evento(
            state.get("turno_id"), "llm", nodo="enrutador", ms=(time.perf_counter() - t0) * 1000,
            error=f"{type(exc).__name__}: {exc}"[:1500], chars_contexto=_chars(mensajes),
        )
        raise
    REGISTRO.evento(
        state.get("turno_id"), "llm", nodo="enrutador", ms=(time.perf_counter() - t0) * 1000,
        chars_contexto=_chars(mensajes), **extraer_tokens(salida.get("raw")),
    )
    decision = salida.get("parsed")
    if decision is None:  # el modelo no devolvió JSON válido: ruta segura por defecto
        return {
            "ruta": "herramientas",
            "motivo": "Respaldo: no se pudo interpretar la clasificación.",
            "pasos_ejecutados": _traza(state, "enrutador"),
        }
    return {
        "ruta": decision.ruta,
        "motivo": decision.motivo,
        "pasos_ejecutados": _traza(state, "enrutador"),
    }


# Nodo 2: respuesta teórica sin herramientas
def conceptual_node(state: AcademicState) -> dict:
    mensajes = [SystemMessage(content=CONCEPTUAL_SYSTEM_PROMPT), *ventana_contexto(state["messages"])]
    respuesta = _invocar(state, "nodo_conceptual", obtener_modelo(), mensajes)
    return {"messages": [respuesta], "pasos_ejecutados": _traza(state, "nodo_conceptual")}


# Nodo 3: razonamiento con herramientas vinculadas
def agente_academico_node(state: AcademicState) -> dict:
    estudiante = state.get(
        "estudiante",
        {"nombre": "Estudiante", "programa": "No definido", "semestre": "No definido"},
    )
    sistema = SystemMessage(content=AGENT_SYSTEM_TEMPLATE.format(**estudiante))
    modelo_con_tools = obtener_modelo().bind_tools(TOOLS_ACADEMICAS)
    mensajes = [sistema, *ventana_contexto(state["messages"])]
    respuesta = _invocar(state, "agente_academico", modelo_con_tools, mensajes)
    return {"messages": [respuesta], "pasos_ejecutados": _traza(state, "agente_academico")}


# Nodo 4: ejecución nativa de herramientas con ToolNode
_ejecutor_tools = ToolNode(TOOLS_ACADEMICAS)


def herramientas_node(state: AcademicState) -> dict:
    solicitadas = [call["name"] for call in state["messages"][-1].tool_calls]
    t0 = time.perf_counter()
    resultado = _ejecutor_tools.invoke(state)
    errores = sum(1 for m in resultado["messages"] if getattr(m, "status", None) == "error")
    REGISTRO.evento(
        state.get("turno_id"), "tool", nombres=solicitadas,
        ms=(time.perf_counter() - t0) * 1000, errores=errores,
    )
    return {
        "messages": resultado["messages"],
        "herramientas_usadas": state.get("herramientas_usadas", []) + solicitadas,
        "pasos_ejecutados": _traza(state, "herramientas"),
    }
