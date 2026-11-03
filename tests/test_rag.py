"""Pruebas del RAG: tokenización, fragmentación, recuperación y PDF."""

from rag.buscador import (
    IndiceBM25,
    cargar_fragmentos,
    dividir_en_fragmentos,
    obtener_indice,
    tokenizar,
)


def test_tokenizar_quita_tildes_stopwords_y_plurales():
    assert tokenizar("¿Cuántos créditos académicos?") == ["credito", "academico"]


def test_fragmentos_respetan_el_maximo():
    texto = "\n\n".join(f"Párrafo número {i}. " + "palabra " * 60 for i in range(10))
    trozos = dividir_en_fragmentos(texto, maximo=800)
    assert len(trozos) > 1
    assert all(len(t) <= 800 for t in trozos)


def test_fragmentos_no_mezclan_secciones():
    texto = "# Título\n\nIntro.\n\n## Uno\n\nTexto uno.\n\n## Dos\n\nTexto dos."
    trozos = dividir_en_fragmentos(texto)
    assert len(trozos) == 3
    assert any(t.startswith("## Uno") and "Texto dos" not in t for t in trozos)


def test_titulo_sin_contenido_se_une_a_la_seccion_siguiente():
    trozos = dividir_en_fragmentos("# Solo título\n## Sección\n\nContenido.")
    assert len(trozos) == 1 and "Solo título" in trozos[0] and "Contenido" in trozos[0]


def test_sinonimos_estudiantiles():
    assert tokenizar("la materia") == tokenizar("la asignatura")


def test_indice_cubre_los_documentos_de_ejemplo():
    fuentes = {f.fuente for f in cargar_fragmentos()}
    assert {"creditos_academicos.md", "guia_estudio.md", "faq_ejemplo_reglamento.md",
            "capacidades_del_agente.md"} <= fuentes
    assert not any(f.startswith("LEEME") for f in fuentes)


def test_recupera_el_documento_correcto():
    casos = {
        "¿Cuántas horas equivale un crédito?": "creditos_academicos.md",
        "técnica pomodoro para estudiar": "guia_estudio.md",
        "pierdo la materia por inasistencia": "faq_ejemplo_reglamento.md",
        "qué herramientas tiene el agente": "capacidades_del_agente.md",
    }
    indice = obtener_indice()
    for pregunta, esperado in casos.items():
        mejor = indice.buscar(pregunta, k=1)
        assert mejor, pregunta
        assert mejor[0][1].fuente == esperado, (pregunta, mejor[0][1].fuente)


def test_consulta_sin_relacion_no_devuelve_nada():
    assert obtener_indice().buscar("zzzz qqqq xxxx") == []


def test_indice_vacio_no_falla():
    assert IndiceBM25([]).buscar("cualquier cosa") == []


def test_lee_pdf(tmp_path):
    from reportlab.pdfgen import canvas

    ruta = tmp_path / "reglamento.pdf"
    c = canvas.Canvas(str(ruta))
    c.drawString(72, 750, "El estudiante puede solicitar homologacion de asignaturas en admisiones.")
    c.save()
    fragmentos = cargar_fragmentos(tmp_path)
    assert fragmentos and fragmentos[0].fuente == "reglamento.pdf"
    assert IndiceBM25(fragmentos).buscar("homologacion de asignaturas")
