"""Datos propios de las pruebas, separados de data/.

Así las pruebas siguen funcionando aunque cambies data/*.json y data/conocimiento/
por tus datos reales: los resultados esperados no dependen de ellos.
"""

from pathlib import Path

import rag.buscador as buscador
import tools._datos as datos_tools

DATOS_PRUEBA = Path(__file__).resolve().parent / "datos_prueba"


def activar() -> tuple:
    """Apunta las herramientas y el RAG a los datos de prueba. Devuelve lo anterior."""
    anterior = (datos_tools.DATA_DIR, buscador.CONOCIMIENTO_DIR)
    datos_tools.DATA_DIR = DATOS_PRUEBA
    buscador.CONOCIMIENTO_DIR = DATOS_PRUEBA / "conocimiento"
    buscador.reconstruir_indice()
    return anterior


def restaurar(anterior: tuple) -> None:
    datos_tools.DATA_DIR, buscador.CONOCIMIENTO_DIR = anterior
    buscador.reconstruir_indice()
