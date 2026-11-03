import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("GEMINI_API_KEY", "clave-falsa-solo-para-pruebas")

import pytest  # noqa: E402

import graph.nodes as nodes  # noqa: E402
from observabilidad.metricas import REGISTRO  # noqa: E402
from tests.escenarios import plan_simulado  # noqa: E402
from tests.fakes import ModeloFalso  # noqa: E402


@pytest.fixture(autouse=True)
def datos_de_prueba():
    """Todas las pruebas usan tests/datos_prueba/, no tus datos reales de data/."""
    from tests import datos

    anterior = datos.activar()
    yield
    datos.restaurar(anterior)


@pytest.fixture(autouse=True)
def registro_temporal(tmp_path):
    """Las pruebas escriben sus métricas en una carpeta temporal, no en logs/."""
    original = REGISTRO.archivo
    REGISTRO.archivo = tmp_path / "metricas.jsonl"
    yield REGISTRO
    REGISTRO.archivo = original


@pytest.fixture
def usar_modelo(monkeypatch):
    """Sustituye el modelo real por uno simulado. Uso: usar_modelo(ModeloFalso(...))."""

    def _usar(modelo):
        monkeypatch.setattr(nodes, "obtener_modelo", lambda temperatura=0.3: modelo)
        return modelo

    return _usar


@pytest.fixture
def modelo_normal(usar_modelo):
    return usar_modelo(ModeloFalso(plan_simulado))
