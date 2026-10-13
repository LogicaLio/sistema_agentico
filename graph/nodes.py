"""Nodos del grafo: funciones state -> dict con los cambios a aplicar."""

from functools import lru_cache
from typing import Literal

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from graph.state import AcademicState
from prompts.academic_prompt import (
    AGENT_SYSTEM_TEMPLATE,
    CONCEPTUAL_SYSTEM_PROMPT,
    ROUTER_SYSTEM_PROMPT,
)
from tools import TOOLS_ACADEMICAS


class DecisionRuta(BaseModel):
    """Decisión estructurada del nodo enrutador."""

    ruta: Literal["conceptual", "herramientas"] = Field(
        description="'conceptual' si es teórica; 'herramientas' si requiere datos del estudiante."
    )
    motivo: str = Field(description="Justificación breve de la ruta elegida.")


@lru_cache(maxsize=2)
def obtener_modelo(temperatura: float = 0.3) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=temperatura,
    )


def _traza(state: AcademicState, nodo: str) -> list[str]:
    return state.get("pasos_ejecutados", []) + [nodo]


# Nodo 1: clasificador estructurado (temperatura 0)
def enrutador_node(state: AcademicState) -> dict:
    clasificador = obtener_modelo(0.0).with_structured_output(DecisionRuta)
    decision = clasificador.invoke(
        [SystemMessage(content=ROUTER_SYSTEM_PROMPT), state["messages"][-1]]
    )
    return {
        "ruta": decision.ruta,
        "motivo": decision.motivo,
        "pasos_ejecutados": _traza(state, "enrutador"),
    }


# Nodo 2: respuesta teórica sin herramientas
def conceptual_node(state: AcademicState) -> dict:
    respuesta = obtener_modelo().invoke(
        [SystemMessage(content=CONCEPTUAL_SYSTEM_PROMPT), *state["messages"]]
    )
    return {"messages": [respuesta], "pasos_ejecutados": _traza(state, "nodo_conceptual")}


# Nodo 3: razonamiento con herramientas vinculadas
def agente_academico_node(state: AcademicState) -> dict:
    estudiante = state.get(
        "estudiante",
        {"nombre": "Estudiante", "programa": "No definido", "semestre": "No definido"},
    )
    sistema = SystemMessage(content=AGENT_SYSTEM_TEMPLATE.format(**estudiante))
    modelo_con_tools = obtener_modelo().bind_tools(TOOLS_ACADEMICAS)
    respuesta = modelo_con_tools.invoke([sistema, *state["messages"]])
    return {"messages": [respuesta], "pasos_ejecutados": _traza(state, "agente_academico")}


# Nodo 4: ejecución nativa de herramientas con ToolNode
_ejecutor_tools = ToolNode(TOOLS_ACADEMICAS)


def herramientas_node(state: AcademicState) -> dict:
    solicitadas = [call["name"] for call in state["messages"][-1].tool_calls]
    resultado = _ejecutor_tools.invoke(state)
    return {
        "messages": resultado["messages"],
        "herramientas_usadas": state.get("herramientas_usadas", []) + solicitadas,
        "pasos_ejecutados": _traza(state, "herramientas"),
    }
