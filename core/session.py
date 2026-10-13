"""Integra Streamlit con el grafo: sesión, thread_id y ejecución de cada turno."""

import uuid

import streamlit as st
from langchain_core.messages import HumanMessage

from graph.workflow import crear_grafo_academico


@st.cache_resource
def obtener_grafo():
    """Un solo grafo (y un solo MemorySaver) para toda la app; así la memoria
    no se pierde entre reruns de Streamlit. Cada usuario usa su propio thread_id."""
    return crear_grafo_academico()


def inicializar_sesion() -> None:
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "estudiante" not in st.session_state:
        st.session_state.estudiante = {
            "nombre": "Estudiante",
            "programa": "No definido",
            "semestre": "No definido",
        }
    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []  # solo para pintar la interfaz
    if "ultima_traza" not in st.session_state:
        st.session_state.ultima_traza = []


def reiniciar_sesion() -> None:
    """Nuevo thread_id = conversación nueva (el checkpointer no mezcla hilos)."""
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.mensajes = []
    st.session_state.ultima_traza = []


def _texto(contenido) -> str:
    """Gemini puede devolver el contenido como lista de partes; lo unificamos."""
    if isinstance(contenido, str):
        return contenido
    return "".join(
        p.get("text", "") if isinstance(p, dict) else str(p) for p in contenido
    )


def enviar_mensaje(texto: str) -> tuple[str, list[str], list[str]]:
    """Ejecuta un turno. Devuelve (respuesta, nodos_recorridos, tools_usadas)."""
    grafo = obtener_grafo()
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    estado_inicial = {
        "messages": [HumanMessage(content=texto)],
        "estudiante": st.session_state.estudiante,
        "pasos_ejecutados": [],  # la traza es por turno
        "herramientas_usadas": [],
    }
    resultado = grafo.invoke(estado_inicial, config=config)
    respuesta = _texto(resultado["messages"][-1].content)
    return respuesta, resultado.get("pasos_ejecutados", []), resultado.get("herramientas_usadas", [])
