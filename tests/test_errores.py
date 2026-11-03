"""Pruebas del manejo de errores hacia el usuario."""

import pytest
from langgraph.errors import GraphRecursionError

from core.errores import TurnoFallido, mensaje_amigable


@pytest.mark.parametrize(
    "excepcion, fragmento",
    [
        (GraphRecursionError("limite"), "demasiadas vueltas"),
        (RuntimeError("429 RESOURCE_EXHAUSTED quota exceeded"), "límite de uso"),
        (RuntimeError("API key not valid"), "GEMINI_API_KEY"),
        (TimeoutError("request timed out"), "no respondió a tiempo"),
        (ValueError("algo raro"), "error inesperado"),
    ],
)
def test_mensajes_amigables(excepcion, fragmento):
    assert fragmento in mensaje_amigable(excepcion)


def test_desempaqueta_turno_fallido():
    assert "límite de uso" in mensaje_amigable(TurnoFallido(RuntimeError("429 quota")))


def test_el_mensaje_no_filtra_detalles_tecnicos():
    msg = mensaje_amigable(RuntimeError("Traceback secreto con AIzaSyXXXX"))
    assert "AIza" not in msg and "Traceback" not in msg
