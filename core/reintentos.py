"""Reintentos con espera creciente para errores transitorios del modelo (503, 429, timeouts)."""

import time

from core.errores import es_transitorio


def con_reintentos(funcion, intentos: int = 3, espera: float = 8.0, dormir=time.sleep):
    """Ejecuta `funcion()`. Si falla con un error transitorio, espera y reintenta.

    Devuelve (resultado, reintentos_realizados). Los errores no transitorios y el
    último intento fallido se propagan sin ocultarse.
    """
    for intento in range(1, intentos + 1):
        try:
            return funcion(), intento - 1
        except Exception as exc:
            if intento == intentos or not es_transitorio(exc):
                raise
            dormir(espera * intento)
