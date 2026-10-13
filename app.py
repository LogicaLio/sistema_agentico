"""Interfaz Streamlit del Agente Académico v03 (LangGraph)."""

import streamlit as st

from config.settings import validar_configuracion
from core.session import (
    enviar_mensaje,
    inicializar_sesion,
    obtener_grafo,
    reiniciar_sesion,
)

st.set_page_config(page_title="Agente Académico v03", page_icon="🎓")

try:
    validar_configuracion()
except ValueError as error:
    st.error(str(error))
    st.stop()

inicializar_sesion()

st.title("Agente Académico v03")
st.caption("Universidad Católica Luis Amigó · LangGraph")
st.write(
    "Consulta tu horario, actividades, calendario académico o información de "
    "tus asignaturas, o pregunta dudas conceptuales."
)

with st.sidebar:
    st.subheader("Estudiante")
    est = st.session_state.estudiante
    est["nombre"] = st.text_input("Nombre", est["nombre"])
    est["programa"] = st.text_input("Programa", est["programa"])
    est["semestre"] = st.text_input("Semestre", est["semestre"])

    st.divider()
    st.subheader("Trazabilidad")
    st.write("Thread ID activo:")
    st.code(st.session_state.thread_id, language=None)
    if st.session_state.ultima_traza:
        recorrido = ["START", *st.session_state.ultima_traza, "END"]
        st.write("Nodos recorridos (último turno):")
        st.code(" ➔ ".join(recorrido), language=None)

    with st.expander("Diagrama del grafo (Mermaid)"):
        st.code(obtener_grafo().get_graph().draw_mermaid(), language="text")

    st.divider()
    if st.button("Reiniciar conversación"):
        reiniciar_sesion()
        st.rerun()

for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

prompt = st.chat_input("Escribe tu consulta académica...")
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.mensajes.append({"role": "user", "content": prompt})

    try:
        respuesta, pasos, tools = enviar_mensaje(prompt)
        st.session_state.ultima_traza = pasos
    except Exception as error:
        respuesta = f"Ocurrió un error al consultar el agente: {error}"

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
    st.rerun()
