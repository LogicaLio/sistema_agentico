"""Interfaz Streamlit del Consultor Académico (LangGraph + RAG + observabilidad)."""

import pandas as pd
import streamlit as st

from config.settings import validar_configuracion
from core.errores import TurnoFallido, mensaje_amigable
from core.session import (
    enviar_mensaje,
    inicializar_sesion,
    obtener_grafo,
    reiniciar_sesion,
)
from observabilidad.metricas import resumen_global
from ui.estilos import SUGERENCIAS, aplicar_estilos, encabezado, etiquetas_turno

st.set_page_config(
    page_title="Consultor Académico",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="auto",  # abierta en escritorio, cerrada en celular (no tapa el chat)
)
aplicar_estilos()

try:
    validar_configuracion()
except ValueError as error:
    st.error(str(error))
    st.stop()

inicializar_sesion()
encabezado()

# ----------------------------- Barra lateral -----------------------------
with st.sidebar:
    tab_perfil, tab_metricas, tab_grafo = st.tabs(["👤 Perfil", "📊 Métricas", "🕸️ Grafo"])

    with tab_perfil:
        est = st.session_state.estudiante
        est["nombre"] = st.text_input("Nombre", est["nombre"])
        est["programa"] = st.text_input("Programa", est["programa"])
        est["semestre"] = st.text_input("Semestre", est["semestre"])
        st.caption("Estos datos personalizan las respuestas del agente.")
        st.write("**Thread ID** (memoria de esta conversación):")
        st.code(st.session_state.thread_id, language=None)
        if st.button("🔄 Nueva conversación", use_container_width=True):
            reiniciar_sesion()
            st.rerun()

    with tab_metricas:
        turnos = st.session_state.metricas_sesion
        g = resumen_global(turnos)
        c1, c2 = st.columns(2)
        c1.metric("Consultas", g["turnos"])
        c2.metric("Tokens", f"{g['tokens_total']:,}".replace(",", "."))
        c3, c4 = st.columns(2)
        c3.metric("Latencia media", f"{g['latencia_media_ms'] / 1000:.1f} s")
        c4.metric("Errores", g["errores"])
        st.caption(f"Llamadas al modelo: {g['llamadas_llm']} · p95: {g['latencia_p95_ms'] / 1000:.1f} s")
        if g["uso_herramientas"]:
            st.write("**Uso de herramientas**")
            st.bar_chart(pd.Series(g["uso_herramientas"], name="llamadas"))
        if turnos:
            tabla = pd.DataFrame(turnos)[
                ["pregunta", "ruta", "llamadas_llm", "tokens_total", "latencia_ms", "error"]
            ]
            st.dataframe(tabla, hide_index=True, use_container_width=True)
            st.download_button(
                "⬇️ Descargar métricas (CSV)",
                pd.DataFrame(turnos).to_csv(index=False).encode("utf-8"),
                file_name="metricas_sesion.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("Aún no hay consultas. Las métricas aparecerán aquí.")

    with tab_grafo:
        if st.session_state.ultima_traza:
            st.write("**Último recorrido:**")
            st.code(" ➔ ".join(["START", *st.session_state.ultima_traza, "END"]), language=None)
        with st.expander("Diagrama Mermaid del grafo"):
            st.code(obtener_grafo().get_graph().draw_mermaid(), language="text")

# ----------------------------- Conversación -----------------------------
if not st.session_state.mensajes:
    st.write("**Prueba con una pregunta:**")
    columnas = st.columns(2)
    for i, (etiqueta, pregunta) in enumerate(SUGERENCIAS):
        if columnas[i % 2].button(etiqueta, key=f"sug_{i}"):
            st.session_state.pendiente = pregunta
            st.rerun()

for mensaje in st.session_state.mensajes:
    avatar = "🧑‍🎓" if mensaje["role"] == "user" else "🎓"
    with st.chat_message(mensaje["role"], avatar=avatar):
        st.markdown(mensaje["content"])
        if mensaje["role"] == "assistant" and mensaje.get("meta"):
            st.markdown(mensaje["meta"], unsafe_allow_html=True)

entrada = st.chat_input("Escribe tu consulta académica...")
texto = entrada or st.session_state.pop("pendiente", None)

if texto:
    st.session_state.mensajes.append({"role": "user", "content": texto})
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(texto)

    with st.chat_message("assistant", avatar="🎓"):
        with st.spinner("El agente está consultando y razonando…"):
            try:
                resultado = enviar_mensaje(texto)
                respuesta = resultado.respuesta
                meta = etiquetas_turno(resultado.metricas, resultado.herramientas)
            except TurnoFallido as fallo:
                respuesta, meta = mensaje_amigable(fallo), ""
            except Exception as error:  # cualquier fallo inesperado de la propia app
                respuesta, meta = mensaje_amigable(error), ""
        st.markdown(respuesta)

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta, "meta": meta})
    st.rerun()
