"""Topología del grafo: aristas, bifurcaciones, ciclo ReAct y checkpointer."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from graph.nodes import (
    agente_academico_node,
    conceptual_node,
    enrutador_node,
    herramientas_node,
)
from graph.state import AcademicState


def _elegir_ruta(state: AcademicState) -> str:
    return "nodo_conceptual" if state.get("ruta") == "conceptual" else "agente_academico"


def _evaluar_tools(state: AcademicState) -> str:
    ultimo = state["messages"][-1]
    if getattr(ultimo, "tool_calls", None):
        return "herramientas"
    return END


def crear_grafo_academico():
    builder = StateGraph(AcademicState)
    builder.add_node("enrutador", enrutador_node)
    builder.add_node("nodo_conceptual", conceptual_node)
    builder.add_node("agente_academico", agente_academico_node)
    builder.add_node("herramientas", herramientas_node)

    builder.add_edge(START, "enrutador")
    builder.add_conditional_edges(
        "enrutador",
        _elegir_ruta,
        {"nodo_conceptual": "nodo_conceptual", "agente_academico": "agente_academico"},
    )
    builder.add_conditional_edges(
        "agente_academico",
        _evaluar_tools,
        {"herramientas": "herramientas", END: END},
    )
    builder.add_edge("herramientas", "agente_academico")  # bucle cíclico ReAct
    builder.add_edge("nodo_conceptual", END)

    return builder.compile(checkpointer=MemorySaver())
