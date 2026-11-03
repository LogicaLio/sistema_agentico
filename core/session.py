"""Integra Streamlit con el grafo: estado de sesión, thread_id y ejecución de cada turno."""

import uuid

import streamlit as st

from core.ejecutor import ResultadoTurno, ejecutar_turno
from core.errores import TurnoFallido
from graph.workflow import crear_grafo_academico


@st.cache_resource
def obtener_grafo():
    """Un solo grafo (y un solo MemorySaver) para toda la app; así la memoria
    no se pierde entre reruns de Streamlit. Cada usuario usa su propio thread_id."""
    return crear_grafo_academico()


def inicializar_sesion() -> None:
    valores = {
        "thread_id": lambda: str(uuid.uuid4()),
        "estudiante": lambda: {"nombre": "Estudiante", "programa": "No definido", "semestre": "No definido"},
        "mensajes": list,        # historial para pintar la interfaz
        "ultima_traza": list,
        "metricas_sesion": list,  # un resumen por turno
        "pendiente": lambda: None,
    }
    for clave, fabrica in valores.items():
        if clave not in st.session_state:
            st.session_state[clave] = fabrica()


def reiniciar_sesion() -> None:
    """Nuevo thread_id = conversación nueva (el checkpointer no mezcla hilos)."""
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.mensajes = []
    st.session_state.ultima_traza = []
    st.session_state.metricas_sesion = []
    st.session_state.pendiente = None


def enviar_mensaje(texto: str) -> ResultadoTurno:
    """Ejecuta un turno y acumula sus métricas. Si falla, lanza TurnoFallido."""
    try:
        resultado = ejecutar_turno(
            obtener_grafo(), texto, st.session_state.estudiante, st.session_state.thread_id
        )
    except TurnoFallido as fallo:
        st.session_state.metricas_sesion.append(fallo.metricas)
        raise
    st.session_state.ultima_traza = resultado.pasos
    st.session_state.metricas_sesion.append(resultado.metricas)
    return resultado
