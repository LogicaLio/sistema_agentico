"""Pruebas de integración de LangGraph: rutas, memoria, estado, límites y métricas."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from core.ejecutor import ejecutar_turno
from core.errores import TurnoFallido
from graph.nodes import ventana_contexto
from graph.workflow import crear_grafo_academico
from tests.escenarios import ESCENARIOS, ESTUDIANTE, plan_simulado
from tests.fakes import ModeloFalso


@pytest.mark.parametrize("id_, func, pregunta, pasos, tools", ESCENARIOS, ids=[e[0] for e in ESCENARIOS])
def test_escenarios(modelo_normal, id_, func, pregunta, pasos, tools):
    r = ejecutar_turno(crear_grafo_academico(), pregunta, ESTUDIANTE, f"hilo-{id_}")
    assert r.pasos == pasos
    assert r.herramientas == tools
    assert r.respuesta.strip()


def test_las_metricas_del_turno_son_coherentes(modelo_normal):
    r = ejecutar_turno(crear_grafo_academico(), "¿Hoy tengo clase?", ESTUDIANTE, "h")
    m = r.metricas
    assert m["llamadas_llm"] == 4  # enrutador + agente + agente + agente
    assert m["tokens_total"] > 0 and m["tokens_total"] == m["tokens_entrada"] + m["tokens_salida"]
    assert m["herramientas"] == ["obtener_fecha", "consultar_horario"]
    assert m["latencia_ms"] >= m["ms_llm"] + m["ms_tools"] - 1
    assert m["error"] is None and m["ruta"] == "herramientas"


def test_la_memoria_persiste_en_el_hilo_y_se_aisla_entre_hilos(modelo_normal):
    grafo = crear_grafo_academico()
    ejecutar_turno(grafo, "¿Qué es un crédito académico?", ESTUDIANTE, "hilo-A")
    ejecutar_turno(grafo, "¿Qué clases tengo el lunes?", ESTUDIANTE, "hilo-A")
    msgs_a = grafo.get_state({"configurable": {"thread_id": "hilo-A"}}).values["messages"]
    assert sum(isinstance(m, HumanMessage) for m in msgs_a) == 2
    assert grafo.get_state({"configurable": {"thread_id": "hilo-B"}}).values == {}


def test_la_traza_es_por_turno_no_acumulada(modelo_normal):
    grafo = crear_grafo_academico()
    ejecutar_turno(grafo, "¿Qué clases tengo el lunes?", ESTUDIANTE, "h")
    r2 = ejecutar_turno(grafo, "¿Qué es un crédito académico?", ESTUDIANTE, "h")
    assert r2.pasos == ["enrutador", "nodo_conceptual"]


def test_respaldo_si_el_enrutador_no_devuelve_json_valido(usar_modelo):
    usar_modelo(ModeloFalso(plan_simulado, parsing_falla=True))
    r = ejecutar_turno(crear_grafo_academico(), "¿Qué clases tengo el lunes?", ESTUDIANTE, "h")
    assert r.ruta == "herramientas" and r.herramientas == ["consultar_horario"]


def test_bucle_de_herramientas_se_corta_por_limite_de_recursion(usar_modelo):
    usar_modelo(ModeloFalso(plan_simulado, ruta_forzada="herramientas", siempre_tools=True))
    with pytest.raises(TurnoFallido) as exc:
        ejecutar_turno(crear_grafo_academico(), "pregunta cualquiera", ESTUDIANTE, "h")
    assert type(exc.value.original).__name__ == "GraphRecursionError"
    assert exc.value.metricas["error"].startswith("GraphRecursionError")
    assert exc.value.metricas["llamadas_llm"] >= 3  # se registró lo ocurrido antes del corte


def test_error_del_modelo_se_registra_y_se_propaga(usar_modelo, registro_temporal):
    usar_modelo(ModeloFalso(plan_simulado, error=RuntimeError("429 RESOURCE_EXHAUSTED")))
    with pytest.raises(TurnoFallido) as exc:
        ejecutar_turno(crear_grafo_academico(), "hola", ESTUDIANTE, "h")
    assert "429" in exc.value.metricas["error"]
    assert registro_temporal.leer_historial()[-1]["error"]


def test_el_registro_conserva_el_error_completo(usar_modelo):
    """Un error largo (como los 429 de Google, que traen el detalle del límite al final) no se corta."""
    largo = "429 RESOURCE_EXHAUSTED " + "detalle " * 100 + "limit: 20 per day"
    usar_modelo(ModeloFalso(plan_simulado, error=RuntimeError(largo)))
    with pytest.raises(TurnoFallido) as exc:
        ejecutar_turno(crear_grafo_academico(), "hola", ESTUDIANTE, "h")
    assert len(exc.value.metricas["error"]) > 300
    assert exc.value.metricas["error"].endswith("limit: 20 per day")


def test_cada_turno_queda_en_el_jsonl(modelo_normal, registro_temporal):
    grafo = crear_grafo_academico()
    for pregunta in ("¿Qué es un crédito académico?", "¿Qué clases tengo el lunes?"):
        ejecutar_turno(grafo, pregunta, ESTUDIANTE, "h")
    assert len(registro_temporal.leer_historial()) == 2


# ---- ventana deslizante ----
def _historial_largo(rondas: int):
    msgs = []
    for i in range(rondas):
        msgs += [
            HumanMessage(content=f"pregunta {i}"),
            AIMessage(content="", tool_calls=[{"name": "obtener_fecha", "args": {}, "id": f"c{i}"}]),
            ToolMessage(content="fecha", tool_call_id=f"c{i}"),
            AIMessage(content=f"respuesta {i}"),
        ]
    return msgs


def test_ventana_recorta_y_empieza_en_un_mensaje_humano():
    msgs = _historial_largo(10)
    for maximo in (5, 6, 7, 9, 14):
        v = ventana_contexto(msgs, maximo)
        assert isinstance(v[0], HumanMessage)
        assert len(v) <= maximo
        assert v[-1] is msgs[-1]


def test_ventana_nunca_deja_un_toolmessage_huerfano():
    msgs = _historial_largo(10)
    for maximo in range(1, 30):
        v = ventana_contexto(msgs, maximo)
        ids_llamadas = {c["id"] for m in v if isinstance(m, AIMessage) for c in m.tool_calls}
        for m in v:
            if isinstance(m, ToolMessage):
                assert m.tool_call_id in ids_llamadas


def test_ventana_no_toca_historiales_cortos():
    msgs = _historial_largo(2)
    assert ventana_contexto(msgs, 14) == msgs


def test_la_ventana_reduce_el_contexto_enviado_al_modelo(usar_modelo, monkeypatch):
    from config import settings

    def contexto_final(maximo):
        monkeypatch.setattr(settings, "MAX_MENSAJES_CONTEXTO", maximo)
        usar_modelo(ModeloFalso(plan_simulado))
        grafo = crear_grafo_academico()
        ultimo = None
        for _ in range(8):
            ultimo = ejecutar_turno(grafo, "¿Qué clases tengo el lunes?", ESTUDIANTE, f"h-{maximo}")
        return ultimo.metricas["chars_contexto_max"]

    assert contexto_final(10) < contexto_final(0)  # 0 = sin ventana
