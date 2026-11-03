from langchain_core.tools import tool

from rag.buscador import obtener_indice


@tool
def consultar_base_conocimiento(pregunta: str) -> str:
    """Busca en la base de conocimiento institucional (reglamento estudiantil,
    guías, preguntas frecuentes y documentos académicos) y devuelve los fragmentos
    más relevantes con su fuente. Úsala para normas, procedimientos, políticas,
    créditos, evaluación, matrícula, y cualquier pregunta sobre documentos."""
    resultados = obtener_indice().buscar(pregunta, k=3)
    if not resultados:
        return "No encontré información relacionada en la base de conocimiento."
    return "\n\n".join(f"[Fuente: {f.fuente}]\n{f.texto}" for _, f in resultados)
