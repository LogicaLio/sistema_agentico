"""Configuración central: variables de entorno, validación y parámetros operativos."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# --- Parámetros operativos (todos ajustables por variable de entorno) ---
# Máximo de mensajes del historial que se reenvían al modelo (ventana deslizante).
MAX_MENSAJES_CONTEXTO = int(os.getenv("MAX_MENSAJES_CONTEXTO", "14"))
# Tope de pasos del grafo por turno: evita bucles infinitos de herramientas.
RECURSION_LIMIT = int(os.getenv("RECURSION_LIMIT", "12"))
# Tiempo máximo (s) y reintentos de cada llamada al modelo.
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
# Carpeta del registro de métricas (JSONL).
LOG_DIR = Path(os.getenv("LOG_DIR", str(RAIZ / "logs")))


def validar_configuracion() -> None:
    """Lanza ValueError si falta la API Key de Gemini."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_API_KEY_AQUI":
        raise ValueError("Configura GEMINI_API_KEY en tu archivo .env (o en las variables de Render).")
