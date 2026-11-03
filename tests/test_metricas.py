"""Pruebas de observabilidad: tokens, agregación por turno, JSONL y resumen global."""

import json

from langchain_core.messages import AIMessage

from observabilidad.metricas import Registro, extraer_tokens, resumen_global


def test_extraer_tokens():
    r = AIMessage(content="x", usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})
    assert extraer_tokens(r) == {"tokens_entrada": 10, "tokens_salida": 5, "tokens_total": 15}
    assert extraer_tokens(AIMessage(content="x"))["tokens_total"] == 0
    assert extraer_tokens(None)["tokens_total"] == 0


def test_cerrar_turno_agrega_eventos_y_escribe_jsonl(tmp_path):
    reg = Registro(tmp_path / "m.jsonl")
    reg.evento("t1", "llm", nodo="enrutador", ms=100, tokens_entrada=10, tokens_salida=2, tokens_total=12,
               chars_contexto=40)
    reg.evento("t1", "llm", nodo="agente_academico", ms=300, tokens_entrada=50, tokens_salida=8,
               tokens_total=58, chars_contexto=200)
    reg.evento("t1", "tool", nombres=["consultar_horario"], ms=5, errores=0)
    resumen = reg.cerrar_turno("t1", "hilo", "pregunta", "respuesta", 450, ruta="herramientas",
                               pasos=["enrutador"])
    assert resumen["llamadas_llm"] == 2
    assert resumen["tokens_total"] == 70 and resumen["tokens_entrada"] == 60
    assert resumen["ms_llm"] == 400 and resumen["ms_tools"] == 5
    assert resumen["herramientas"] == ["consultar_horario"]
    assert resumen["chars_contexto_max"] == 200
    lineas = (tmp_path / "m.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(lineas[0])["turno_id"] == "t1"
    assert reg.leer_historial()[0]["ruta"] == "herramientas"


def test_eventos_de_un_turno_no_se_mezclan_con_otro(tmp_path):
    reg = Registro(tmp_path / "m.jsonl")
    reg.evento("a", "llm", ms=1, tokens_total=10)
    reg.evento("b", "llm", ms=1, tokens_total=99)
    assert reg.cerrar_turno("a", "h", "p", "r", 5)["tokens_total"] == 10
    assert reg.cerrar_turno("b", "h", "p", "r", 5)["tokens_total"] == 99


def test_fallo_de_escritura_no_rompe(tmp_path):
    bloqueado = tmp_path / "archivo"
    bloqueado.write_text("x")
    reg = Registro(bloqueado / "no_se_puede" / "m.jsonl")  # el padre es un archivo: mkdir falla
    assert reg.cerrar_turno("z", "h", "p", "r", 1)["turno_id"] == "z"


def test_resumen_global():
    turnos = [
        {"latencia_ms": 1000, "tokens_total": 100, "llamadas_llm": 2, "herramientas": ["a"], "errores_tools": 0},
        {"latencia_ms": 3000, "tokens_total": 300, "llamadas_llm": 3, "herramientas": ["a", "b"],
         "errores_tools": 1, "error": None},
    ]
    g = resumen_global(turnos)
    assert g["turnos"] == 2 and g["tokens_total"] == 400 and g["llamadas_llm"] == 5
    assert g["latencia_media_ms"] == 2000 and g["errores"] == 1
    assert g["uso_herramientas"] == {"a": 2, "b": 1}
    assert resumen_global([])["turnos"] == 0
