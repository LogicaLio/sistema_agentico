"""Pruebas de la interfaz Streamlit completa (AppTest) con el modelo simulado."""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from tests.escenarios import plan_simulado
from tests.fakes import ModeloFalso

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(autouse=True)
def limpiar_cache():
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


def _app():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def test_la_app_arranca_sin_excepciones(modelo_normal):
    at = _app()
    assert not at.exception
    assert any("Consultor Académico" in m.value for m in at.markdown)
    assert len(at.sidebar.text_input) == 3  # nombre, programa, semestre
    assert len(at.button) >= 4  # sugerencias + nueva conversación


def test_enviar_un_mensaje_muestra_respuesta_y_metricas(modelo_normal):
    at = _app()
    at.chat_input[0].set_value("¿Qué clases tengo el lunes?").run()
    assert not at.exception
    roles = [m.name for m in at.chat_message]
    assert roles == ["user", "assistant"]
    assert "Respuesta basada en" in at.chat_message[1].markdown[0].value
    assert len(at.session_state["metricas_sesion"]) == 1
    assert at.session_state["ultima_traza"][-1] == "agente_academico"


def test_la_memoria_acumula_turnos_y_reiniciar_la_borra(modelo_normal):
    at = _app()
    at.chat_input[0].set_value("¿Qué es un crédito académico?").run()
    at.chat_input[0].set_value("¿Qué clases tengo el lunes?").run()
    assert len(at.chat_message) == 4
    hilo = at.session_state["thread_id"]
    nuevo = next(b for b in at.sidebar.button if "Nueva conversación" in b.label)
    nuevo.click().run()
    assert len(at.chat_message) == 0
    assert at.session_state["thread_id"] != hilo


def test_boton_de_sugerencia_envia_la_pregunta(modelo_normal):
    at = _app()
    at.button[0].click().run()
    assert not at.exception
    assert len(at.chat_message) == 2
    assert "lunes" in at.chat_message[0].markdown[0].value


def test_error_del_modelo_se_muestra_amigable_y_la_app_sigue_viva(usar_modelo):
    usar_modelo(ModeloFalso(plan_simulado, error=RuntimeError("429 RESOURCE_EXHAUSTED quota")))
    at = _app()
    at.chat_input[0].set_value("hola").run()
    assert not at.exception
    assert "límite de uso" in at.chat_message[1].markdown[0].value
    assert "429" not in at.chat_message[1].markdown[0].value  # sin detalles técnicos


def test_sin_api_key_muestra_error_de_configuracion(modelo_normal, monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    at = _app()
    assert at.error and "GEMINI_API_KEY" in at.error[0].value
    assert len(at.chat_input) == 0  # st.stop(): no se ofrece el chat
