"""Traduce excepciones técnicas a mensajes claros para el estudiante."""

from langgraph.errors import GraphRecursionError


class TurnoFallido(Exception):
    """Un turno falló. Conserva la excepción original y las métricas del turno."""

    def __init__(self, original: Exception, metricas: dict | None = None):
        super().__init__(str(original))
        self.original = original
        self.metricas = metricas or {}


def _texto_error(exc: Exception) -> str:
    original = exc.original if isinstance(exc, TurnoFallido) else exc
    return f"{type(original).__name__} {original}".lower()


def es_transitorio(exc: Exception) -> bool:
    """Errores que suelen resolverse reintentando: saturación (503), cuota por minuto (429), timeouts."""
    texto = _texto_error(exc)
    return any(s in texto for s in (
        "503", "unavailable", "high demand", "429", "resource_exhausted", "rate limit",
        "timeout", "timed out", "deadline",
    ))


def mensaje_amigable(exc: Exception) -> str:
    original = exc.original if isinstance(exc, TurnoFallido) else exc
    texto = _texto_error(exc)

    if isinstance(original, GraphRecursionError):
        return ("⚠️ El agente dio demasiadas vueltas sin llegar a una respuesta y se detuvo por seguridad. "
                "Intenta reformular la pregunta de forma más concreta.")
    if any(s in texto for s in ("429", "resource_exhausted", "quota", "rate limit", "rate_limit")):
        if "per day" in texto or "perday" in texto:
            return ("📅 Se agotó la cuota diaria del modelo. Se renueva en unas horas; quien administra la "
                    "app puede usar otro modelo (variable GEMINI_MODEL) o ampliar el plan.")
        return ("⏳ Se alcanzó el límite de uso del modelo (solicitudes por minuto). "
                "Espera un momento e inténtalo de nuevo.")
    if any(s in texto for s in ("404", "not_found", "no longer available", "modelnotfound")):
        return ("🤖 El modelo configurado ya no está disponible. Quien administra la app debe actualizar "
                "la variable GEMINI_MODEL con un modelo vigente.")
    if any(s in texto for s in ("503", "high demand", "unavailable")):
        return ("🚦 El modelo de Google está saturado en este momento. Espera unos segundos y vuelve a "
                "intentarlo; suele resolverse solo.")
    if any(s in texto for s in ("api key", "api_key", "401", "403", "permission_denied", "unauthenticated")):
        return ("🔑 No fue posible autenticarse con el modelo. Verifica que la GEMINI_API_KEY esté "
                "configurada y vigente.")
    if any(s in texto for s in ("timeout", "timed out", "deadline", "connection")):
        return ("🌐 El servicio del modelo no respondió a tiempo. Revisa tu conexión e inténtalo de nuevo.")
    return "❌ Ocurrió un error inesperado al procesar tu consulta. Inténtalo de nuevo en unos segundos."
