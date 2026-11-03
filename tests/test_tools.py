"""Pruebas funcionales de las 7 herramientas (Tools)."""

import json

from tools import TOOLS_ACADEMICAS
from tools.actividades_tool import consultar_actividades, priorizar_actividades
from tools.asignatura_tool import consultar_informacion_asignatura
from tools.calendario_tool import consultar_calendario_academico
from tools.fecha_tool import obtener_fecha
from tools.horario_tool import consultar_horario
from tools.rag_tool import consultar_base_conocimiento


def test_catalogo_tiene_7_herramientas_con_descripcion():
    assert len(TOOLS_ACADEMICAS) == 7
    assert len({t.name for t in TOOLS_ACADEMICAS}) == 7
    assert all(t.description.strip() for t in TOOLS_ACADEMICAS)


def test_obtener_fecha():
    assert "Hoy es" in obtener_fecha.invoke({})


def test_horario_por_dia_y_por_asignatura():
    por_dia = json.loads(consultar_horario.invoke({"consulta": "lunes"}))
    assert {c["asignatura"] for c in por_dia} >= {"Bases de Datos", "Programación"}
    por_materia = json.loads(consultar_horario.invoke({"consulta": "redes"}))
    assert por_materia and por_materia[0]["dia"] == "viernes"


def test_horario_sin_resultados():
    assert "No encontré" in consultar_horario.invoke({"consulta": "domingo"})


def test_actividades_filtro_y_sin_filtro():
    todas = json.loads(consultar_actividades.invoke({}))
    redes = json.loads(consultar_actividades.invoke({"asignatura": "Redes"}))
    assert len(todas) == 5 and len(redes) == 1


def test_priorizar_ordena_por_urgencia():
    lista = json.loads(priorizar_actividades.invoke({}))
    claves = [(a["dias_restantes"]) for a in lista]
    assert claves == sorted(claves)


def test_calendario_y_asignatura():
    fin = json.loads(consultar_calendario_academico.invoke({"consulta": "fin de clases"}))
    assert fin[0]["fecha"] == "2026-11-27"
    asig = json.loads(consultar_informacion_asignatura.invoke({"nombre": "Sistemas Agénticos"}))
    assert asig[0]["creditos"] == 3
    assert "No encontré" in consultar_informacion_asignatura.invoke({"nombre": "Inexistente"})


def test_rag_tool_devuelve_fuente_y_texto():
    r = consultar_base_conocimiento.invoke({"pregunta": "¿Cuántas horas equivale un crédito académico?"})
    assert "[Fuente: creditos_academicos.md]" in r and "48 horas" in r


def test_rag_tool_sin_resultados():
    r = consultar_base_conocimiento.invoke({"pregunta": "zzzz qqqq xxxx"})
    assert "No encontré información" in r
