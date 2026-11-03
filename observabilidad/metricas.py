"""Observabilidad: registro de métricas por turno (tiempos, tokens, llamadas, tools, errores).

Los nodos del grafo reportan eventos con `REGISTRO.evento(turno_id, ...)`.
Al terminar el turno, `cerrar_turno` los agrega en un resumen y lo guarda
como una línea JSON en `logs/metricas.jsonl`.
"""

import json
import threading
import time
from collections import defaultdict
from pathlib import Path

from config.settings import LOG_DIR

ARCHIVO_POR_DEFECTO = Path(LOG_DIR) / "metricas.jsonl"


def extraer_tokens(respuesta) -> dict:
    """Lee los tokens de una respuesta del modelo (usage_metadata de LangChain).
    Si el proveedor no los informa, devuelve ceros."""
    uso = getattr(respuesta, "usage_metadata", None) or {}
    entrada = int(uso.get("input_tokens", 0) or 0)
    salida = int(uso.get("output_tokens", 0) or 0)
    total = int(uso.get("total_tokens", 0) or (entrada + salida))
    return {"tokens_entrada": entrada, "tokens_salida": salida, "tokens_total": total}


class Registro:
    def __init__(self, archivo: Path | str | None = None):
        self._lock = threading.Lock()
        self._eventos: dict[str, list[dict]] = defaultdict(list)
        self.archivo = Path(archivo) if archivo else ARCHIVO_POR_DEFECTO

    # ---------- eventos dentro de un turno ----------
    def evento(self, turno_id: str | None, tipo: str, **datos) -> None:
        if not turno_id:
            return
        with self._lock:
            self._eventos[turno_id].append({"tipo": tipo, **datos})

    # ---------- cierre del turno ----------
    def cerrar_turno(
        self,
        turno_id: str,
        thread_id: str,
        pregunta: str,
        respuesta: str,
        latencia_ms: float,
        ruta: str = "",
        pasos: list[str] | None = None,
        error: str | None = None,
    ) -> dict:
        with self._lock:
            eventos = self._eventos.pop(turno_id, [])

        llm = [e for e in eventos if e["tipo"] == "llm"]
        tools = [e for e in eventos if e["tipo"] == "tool"]
        herramientas = [n for e in tools for n in e.get("nombres", [])]

        resumen = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "turno_id": turno_id,
            "thread_id": thread_id,
            "pregunta": pregunta[:200],
            "respuesta_chars": len(respuesta),
            "ruta": ruta,
            "pasos": pasos or [],
            "llamadas_llm": len(llm),
            "tokens_entrada": sum(e.get("tokens_entrada", 0) for e in llm),
            "tokens_salida": sum(e.get("tokens_salida", 0) for e in llm),
            "tokens_total": sum(e.get("tokens_total", 0) for e in llm),
            "chars_contexto_max": max((e.get("chars_contexto", 0) for e in llm), default=0),
            "ms_llm": round(sum(e.get("ms", 0) for e in llm), 1),
            "ms_tools": round(sum(e.get("ms", 0) for e in tools), 1),
            "herramientas": herramientas,
            "errores_tools": sum(e.get("errores", 0) for e in tools),
            "latencia_ms": round(latencia_ms, 1),
            "error": error,
        }
        self._escribir(resumen)
        return resumen

    def _escribir(self, resumen: dict) -> None:
        """El registro en disco es best-effort: un fallo de escritura no rompe la app."""
        try:
            self.archivo.parent.mkdir(parents=True, exist_ok=True)
            with open(self.archivo, "a", encoding="utf-8") as f:
                f.write(json.dumps(resumen, ensure_ascii=False) + "\n")
        except OSError:
            pass

    # ---------- lectura ----------
    def leer_historial(self, ultimos: int | None = None) -> list[dict]:
        try:
            with open(self.archivo, encoding="utf-8") as f:
                filas = [json.loads(l) for l in f if l.strip()]
        except (OSError, json.JSONDecodeError):
            return []
        return filas[-ultimos:] if ultimos else filas


def resumen_global(turnos: list[dict]) -> dict:
    """Agrega una lista de resúmenes de turno en indicadores globales."""
    n = len(turnos)
    if n == 0:
        return {"turnos": 0, "tokens_total": 0, "llamadas_llm": 0, "latencia_media_ms": 0.0,
                "latencia_p95_ms": 0.0, "errores": 0, "uso_herramientas": {}}
    lat = sorted(t["latencia_ms"] for t in turnos)
    p95 = lat[min(n - 1, int(round(0.95 * (n - 1))))]
    uso: dict[str, int] = defaultdict(int)
    for t in turnos:
        for h in t.get("herramientas", []):
            uso[h] += 1
    return {
        "turnos": n,
        "tokens_total": sum(t["tokens_total"] for t in turnos),
        "llamadas_llm": sum(t["llamadas_llm"] for t in turnos),
        "latencia_media_ms": round(sum(lat) / n, 1),
        "latencia_p95_ms": p95,
        "errores": sum(1 for t in turnos if t.get("error")) + sum(t.get("errores_tools", 0) for t in turnos),
        "uso_herramientas": dict(uso),
    }


REGISTRO = Registro()
