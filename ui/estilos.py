"""Estilos y textos de la interfaz (separados de la lógica de la app)."""

import streamlit as st

# (etiqueta del botón, pregunta que se envía)
SUGERENCIAS = [
    ("📅 Mis clases del lunes", "¿Qué clases tengo el lunes?"),
    ("📝 Priorizar tareas", "Prioriza mis actividades pendientes"),
    ("🗓️ Fin de clases", "¿Cuándo terminan las clases?"),
    ("📖 ¿Qué es un crédito?", "¿Cuántas horas de trabajo equivale un crédito académico?"),
]

CSS = """
<style>
  .block-container { max-width: 820px; padding-top: 4.2rem; padding-bottom: 6rem; }
  .hero {
    background: linear-gradient(135deg, #1F4E79 0%, #2E75B6 100%);
    color: #fff; border-radius: 16px; padding: 1.2rem 1.4rem; margin-bottom: 1rem;
  }
  .hero h1 { color: #fff; font-size: 1.6rem; margin: 0 0 .2rem 0; padding: 0; }
  .hero p  { color: #E3EEF8; margin: 0; font-size: .95rem; }
  .meta-turno { color: #5B6B7B; font-size: .78rem; margin-top: .25rem; }
  .chip {
    display: inline-block; background: #E8F0F8; color: #1F4E79; border-radius: 999px;
    padding: .05rem .55rem; margin-right: .3rem; font-size: .75rem;
  }
  div.stButton > button { border-radius: 12px; width: 100%; }
  [data-testid="stChatMessage"] { border-radius: 14px; }
  @media (max-width: 640px) {
    .block-container { padding-left: .8rem; padding-right: .8rem; }
    .hero h1 { font-size: 1.25rem; }
    .hero p { font-size: .85rem; }
  }
</style>
"""


def aplicar_estilos() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def encabezado() -> None:
    st.markdown(
        '<div class="hero"><h1>🎓 Consultor Académico</h1>'
        "<p>Universidad Católica Luis Amigó · Horarios, tareas, calendario, asignaturas "
        "y reglamento en un solo lugar.</p></div>",
        unsafe_allow_html=True,
    )


def etiquetas_turno(metricas: dict, herramientas: list[str]) -> str:
    """Pie de cada respuesta: tiempo, tokens y herramientas usadas."""
    if not metricas:
        return ""
    partes = [f'<span class="chip">⏱ {metricas.get("latencia_ms", 0) / 1000:.1f} s</span>']
    if metricas.get("tokens_total"):
        partes.append(f'<span class="chip">🧮 {metricas["tokens_total"]:,} tokens</span>'.replace(",", "."))
    for h in dict.fromkeys(herramientas):  # únicas, conservando el orden
        partes.append(f'<span class="chip">🔧 {h}</span>')
    return f'<div class="meta-turno">{"".join(partes)}</div>'
