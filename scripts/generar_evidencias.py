"""Genera el informe de pruebas y métricas que se entrega como evidencia.

Uso:
    python scripts/generar_evidencias.py --modo simulado   # sin API Key (modelo simulado)
    python scripts/generar_evidencias.py --modo real       # con Gemini real (requiere GEMINI_API_KEY)

Salida (carpeta evidencias/):
    informe_pruebas_<modo>.md   tabla de pruebas + métricas + experimento de ventana de contexto
    metricas_<modo>.csv         una fila por turno
    metricas_<modo>.jsonl       registro crudo de observabilidad
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

parser = argparse.ArgumentParser()
parser.add_argument("--modo", choices=["simulado", "real"], default="simulado")
args = parser.parse_args()

if args.modo == "simulado":
    os.environ.setdefault("GEMINI_API_KEY", "clave-falsa-solo-para-pruebas")

from config import settings  # noqa: E402

if args.modo == "real":
    settings.validar_configuracion()

import graph.nodes as nodes  # noqa: E402
from core.ejecutor import ejecutar_turno  # noqa: E402
from core.errores import TurnoFallido, mensaje_amigable  # noqa: E402
from core.reintentos import con_reintentos  # noqa: E402
from graph.workflow import crear_grafo_academico  # noqa: E402
from observabilidad.metricas import REGISTRO, resumen_global  # noqa: E402
from tests.escenarios import ESCENARIOS, ESTUDIANTE, plan_simulado  # noqa: E402

EVID = RAIZ / "evidencias"
EVID.mkdir(exist_ok=True)
jsonl = EVID / f"metricas_{args.modo}.jsonl"
jsonl.unlink(missing_ok=True)
REGISTRO.archivo = jsonl


def usar_modelo_simulado():
    from tests.fakes import ModeloFalso

    modelo = ModeloFalso(plan_simulado)
    nodes.obtener_modelo = lambda temperatura=0.3: modelo


if args.modo == "simulado":
    usar_modelo_simulado()
    from tests import datos as datos_prueba  # el modo simulado es reproducible: usa datos de prueba

    datos_prueba.activar()


REINTENTOS = 0  # reintentos por errores transitorios del servicio (solo modo real)
# Llamadas por minuto que el script se permite en modo real (por debajo del límite RPM de tu plan).
LLAMADAS_POR_MINUTO = int(os.getenv("EVID_LLAMADAS_POR_MINUTO", "10"))


def pausa_por_limite(metricas: dict) -> None:
    """Espera lo necesario para no superar el límite de solicitudes por minuto."""
    time.sleep(max(1.0, metricas.get("llamadas_llm", 1) * 60 / LLAMADAS_POR_MINUTO))


def turno(grafo, pregunta, hilo, mismo_hilo=False):
    """Ejecuta un turno. En modo real reintenta si Google responde 503 (saturado), 429 o timeout.
    En cada reintento usa un hilo nuevo, salvo que se pida el mismo (experimento de ventana)."""
    global REINTENTOS
    intentos = {"n": 0}

    def llamar():
        intentos["n"] += 1
        h = hilo if (mismo_hilo or intentos["n"] == 1) else f"{hilo}-reintento{intentos['n'] - 1}"
        return ejecutar_turno(grafo, pregunta, ESTUDIANTE, h)

    if args.modo != "real":
        return llamar()
    resultado, reintentos = con_reintentos(llamar, intentos=4, espera=10)
    REINTENTOS += reintentos
    return resultado


def flecha(lista):
    return " ➔ ".join(lista) if lista else "—"


# ------------------------- 1. Matriz de pruebas -------------------------
filas, turnos = [], []
for id_, func, pregunta, pasos_esp, tools_esp in ESCENARIOS:
    grafo = crear_grafo_academico()
    try:
        r = turno(grafo, pregunta, f"evid-{args.modo}-{id_}")
        ok_ruta = r.pasos[:2] == pasos_esp[:2] and (
            ("nodo_conceptual" in r.pasos) == ("nodo_conceptual" in pasos_esp)
        )
        ok_tools = set(r.herramientas) == set(tools_esp)
        ok = ok_ruta and ok_tools
        if args.modo == "simulado":
            ok = ok and r.pasos == pasos_esp
        m = r.metricas
        filas.append((id_, func, pregunta, f"{flecha(pasos_esp)} | tools: {', '.join(tools_esp) or '—'}",
                      f"{flecha(r.pasos)} | tools: {', '.join(r.herramientas) or '—'}",
                      "✅ Cumple" if ok else "⚠️ Revisar", m["llamadas_llm"], m["tokens_total"],
                      f"{m['latencia_ms']:.0f}"))
        turnos.append(m)
    except TurnoFallido as fallo:
        filas.append((id_, func, pregunta, f"{flecha(pasos_esp)} | tools: {', '.join(tools_esp) or '—'}",
                      f"ERROR: {mensaje_amigable(fallo)}", "❌ Falla", 0, 0,
                      f"{fallo.metricas.get('latencia_ms', 0):.0f}"))
        turnos.append(fallo.metricas)
    if args.modo == "real":
        pausa_por_limite(turnos[-1])

# ---------------- 2. Experimento: ventana deslizante de contexto ----------------
def correr_conversacion(maximo: int, rondas: int = 8):
    settings.MAX_MENSAJES_CONTEXTO = maximo
    grafo = crear_grafo_academico()
    serie = []
    for i in range(rondas):
        r = turno(grafo, "¿Qué clases tengo el lunes?", f"ventana-{args.modo}-{maximo}", mismo_hilo=True)
        serie.append((r.metricas["chars_contexto_max"], r.metricas["tokens_entrada"]))
        if args.modo == "real":
            pausa_por_limite(r.metricas)
    return serie


original = settings.MAX_MENSAJES_CONTEXTO
experimento_ok, error_experimento = True, ""
try:
    sin_ventana = correr_conversacion(0)
    con_ventana = correr_conversacion(14)
except TurnoFallido as fallo:  # no perder el informe completo si el servicio falla aquí
    experimento_ok, error_experimento = False, mensaje_amigable(fallo)
    sin_ventana = con_ventana = []
finally:
    settings.MAX_MENSAJES_CONTEXTO = original
ahorro_chars = ahorro_tokens = 0
if experimento_ok:
    ahorro_chars = 1 - con_ventana[-1][0] / sin_ventana[-1][0] if sin_ventana[-1][0] else 0
    ahorro_tokens = 1 - con_ventana[-1][1] / sin_ventana[-1][1] if sin_ventana[-1][1] else 0

# ------------------------- 3. Escribir el informe -------------------------
todos = [t for t in turnos if t]  # solo los turnos de la matriz (el experimento de ventana va aparte)
g = resumen_global(todos)
aprobadas = sum(1 for f in filas if f[5].startswith("✅"))

L = []
L.append(f"# Informe de pruebas y métricas — modo {args.modo.upper()}\n")
L.append(f"- Fecha de ejecución: {time.strftime('%Y-%m-%d %H:%M')}")
L.append(f"- Modelo: {'Gemini real (' + settings.GEMINI_MODEL + ')' if args.modo == 'real' else 'MODELO SIMULADO (sin red ni API Key): valida orquestación, no la calidad del LLM'}")
L.append(f"- Resultado: **{aprobadas}/{len(filas)} escenarios cumplen**")
if args.modo == "real":
    L.append(f"- Reintentos por saturación o límites temporales del servicio (503/429/timeout): {REINTENTOS}")
L.append("")
L.append("## 1. Pruebas funcionales de integración (LangChain · LangGraph · memoria · estado · RAG · Tools)\n")
L.append("| ID | Funcionalidad | Pregunta | Resultado esperado | Resultado obtenido | Estado | Llamadas LLM | Tokens | Latencia (ms) |")
L.append("|---|---|---|---|---|---|---|---|---|")
for f in filas:
    L.append("| " + " | ".join(str(c).replace("|", "\\|") if i not in (3, 4) else str(c).replace("|", "·")
                               for i, c in enumerate(f)) + " |")
L.append("\n## 2. Métricas de observabilidad\n")
L.append("| Indicador | Valor |\n|---|---|")
L.append(f"| Turnos ejecutados | {g['turnos']} |")
L.append(f"| Llamadas totales al modelo | {g['llamadas_llm']} |")
L.append(f"| Tokens totales | {g['tokens_total']:,} |".replace(",", "."))
L.append(f"| Latencia media por turno | {g['latencia_media_ms']:.0f} ms |")
L.append(f"| Latencia p95 | {g['latencia_p95_ms']:.0f} ms |")
L.append(f"| Errores | {g['errores']} |")
L.append("\n**Uso de herramientas**\n\n| Herramienta | Invocaciones |\n|---|---|")
for nombre, n in sorted(g["uso_herramientas"].items(), key=lambda x: -x[1]):
    L.append(f"| `{nombre}` | {n} |")
L.append("\n## 3. Optimización: ventana deslizante de contexto\n")
if experimento_ok:
    L.append("Se repitió la misma consulta 8 veces en un mismo hilo, sin ventana y con ventana de 14 mensajes. "
             "Se mide el contexto más grande enviado al modelo en cada turno.\n")
    L.append("| Turno | Sin ventana (caracteres) | Con ventana (caracteres) | Sin ventana (tokens entrada) | Con ventana (tokens entrada) |")
    L.append("|---|---|---|---|---|")
    for i, (a, b) in enumerate(zip(sin_ventana, con_ventana), 1):
        L.append(f"| {i} | {a[0]:,} | {b[0]:,} | {a[1]:,} | {b[1]:,} |".replace(",", "."))
    L.append(f"\n**Reducción en el turno 8:** {ahorro_chars:.0%} de caracteres y {ahorro_tokens:.0%} de tokens de entrada. "
             "Sin ventana el contexto crece con cada turno (crecimiento acumulativo); con ventana se estabiliza.")
else:
    L.append(f"⚠️ El experimento no pudo completarse: {error_experimento} Vuelve a ejecutar el script más tarde.")
if args.modo == "simulado":
    L.append("\n> Los tokens del modo simulado se estiman como caracteres/4. Repite con `--modo real` para tokens reales de Gemini.")

hallazgos = EVID / "hallazgos.md"
L.append("\n## 4. Hallazgos y acciones correctivas\n")
L.append(hallazgos.read_text(encoding="utf-8") if hallazgos.exists() else "_Sin hallazgos registrados._")

(EVID / f"informe_pruebas_{args.modo}.md").write_text("\n".join(L) + "\n", encoding="utf-8")

with open(EVID / f"metricas_{args.modo}.csv", "w", newline="", encoding="utf-8") as f:
    campos = ["ts", "turno_id", "pregunta", "ruta", "llamadas_llm", "tokens_entrada", "tokens_salida",
              "tokens_total", "ms_llm", "ms_tools", "latencia_ms", "herramientas", "errores_tools", "error"]
    w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
    w.writeheader()
    for t in todos:
        w.writerow({**t, "herramientas": "|".join(t.get("herramientas", []))})

print(f"{aprobadas}/{len(filas)} escenarios cumplen · reducción ventana (turno 8): "
      + (f"{ahorro_chars:.0%} chars / {ahorro_tokens:.0%} tokens" if experimento_ok else "no disponible"))
print(f"Informe: {EVID / f'informe_pruebas_{args.modo}.md'}")
sys.exit(0 if aprobadas == len(filas) else 1)
