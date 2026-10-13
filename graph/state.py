"""Esquema de estado del grafo (sin lógica de negocio ni llamadas al LLM)."""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class EstudianteInfo(TypedDict):
    nombre: str
    programa: str
    semestre: str


class AcademicState(TypedDict, total=False):
    # Reducer: gestiona HumanMessage, AIMessage y ToolMessage sin duplicados.
    messages: Annotated[list[BaseMessage], add_messages]
    estudiante: EstudianteInfo
    ruta: str
    motivo: str
    herramientas_usadas: list[str]
    pasos_ejecutados: list[str]  # Traza de nodos recorridos en el turno
