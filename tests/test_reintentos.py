"""Pruebas de los reintentos ante errores transitorios."""

import pytest

from core.reintentos import con_reintentos


def _falla_n_veces(n, error):
    estado = {"llamadas": 0}

    def f():
        estado["llamadas"] += 1
        if estado["llamadas"] <= n:
            raise error
        return "ok"

    return f, estado


def test_reintenta_y_termina_bien():
    f, estado = _falla_n_veces(2, RuntimeError("503 UNAVAILABLE high demand"))
    esperas = []
    resultado, reintentos = con_reintentos(f, intentos=3, espera=5, dormir=esperas.append)
    assert resultado == "ok" and reintentos == 2 and estado["llamadas"] == 3
    assert esperas == [5, 10]  # espera creciente


def test_no_reintenta_errores_permanentes():
    f, estado = _falla_n_veces(5, RuntimeError("404 NOT_FOUND modelo"))
    with pytest.raises(RuntimeError):
        con_reintentos(f, intentos=3, dormir=lambda s: None)
    assert estado["llamadas"] == 1


def test_el_ultimo_intento_propaga_el_error():
    f, estado = _falla_n_veces(9, RuntimeError("503 UNAVAILABLE"))
    with pytest.raises(RuntimeError):
        con_reintentos(f, intentos=3, dormir=lambda s: None)
    assert estado["llamadas"] == 3


def test_sin_fallos_no_hay_reintentos():
    resultado, reintentos = con_reintentos(lambda: 42, dormir=lambda s: None)
    assert (resultado, reintentos) == (42, 0)
