"""Pruebas del manejo de errores hacia el usuario."""

import pytest
from langgraph.errors import GraphRecursionError

from core.errores import TurnoFallido, es_transitorio, mensaje_amigable


@pytest.mark.parametrize(
    "excepcion, fragmento",
    [
        (GraphRecursionError("limite"), "demasiadas vueltas"),
        (RuntimeError("429 RESOURCE_EXHAUSTED quota exceeded"), "límite de uso"),
        (RuntimeError("API key not valid"), "GEMINI_API_KEY"),
        (RuntimeError("429 RESOURCE_EXHAUSTED requests per day limit exceeded on Free Tier"), "cuota diaria"),
        (RuntimeError("quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier 429"), "cuota diaria"),
        (TimeoutError("request timed out"), "no respondió a tiempo"),
        (ValueError("algo raro"), "error inesperado"),
        # errores reales de Gemini observados al probar con la API
        (RuntimeError("404 NOT_FOUND. This model is no longer available to new users"), "GEMINI_MODEL"),
        (RuntimeError("503 UNAVAILABLE. This model is currently experiencing high demand"), "saturado"),
    ],
)
def test_mensajes_amigables(excepcion, fragmento):
    assert fragmento in mensaje_amigable(excepcion)


def test_desempaqueta_turno_fallido():
    assert "límite de uso" in mensaje_amigable(TurnoFallido(RuntimeError("429 quota")))


def test_el_mensaje_no_filtra_detalles_tecnicos():
    msg = mensaje_amigable(RuntimeError("Traceback secreto con AIzaSyXXXX"))
    assert "AIza" not in msg and "Traceback" not in msg


@pytest.mark.parametrize("texto, esperado", [
    ("503 UNAVAILABLE high demand", True),
    ("429 RESOURCE_EXHAUSTED", True),
    ("request timed out", True),
    ("404 NOT_FOUND model", False),
    ("API key not valid", False),
])
def test_clasifica_errores_transitorios(texto, esperado):
    assert es_transitorio(RuntimeError(texto)) is esperado
    assert es_transitorio(TurnoFallido(RuntimeError(texto))) is esperado
