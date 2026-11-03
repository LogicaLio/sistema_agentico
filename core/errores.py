"""Traduce excepciones técnicas a mensajes claros para el estudiante."""

from langgraph.errors import GraphRecursionError


class TurnoFallido(Exception):
    """Un turno falló. Conserva la excepción original y las métricas del turno."""

    def __init__(self, original: Exception, metricas: dict | None = None):
        super().__init__(str(original))
        self.original = original
        self.metricas = metricas or {}


def mensaje_amigable(exc: Exception) -> str:
    original = exc.original if isinstance(exc, TurnoFallido) else exc
    texto = f"{type(original).__name__} {original}".lower()

    if isinstance(original, GraphRecursionError):
        return ("⚠️ El agente dio demasiadas vueltas sin llegar a una respuesta y se detuvo por seguridad. "
                "Intenta reformular la pregunta de forma más concreta.")
    if any(s in texto for s in ("429", "resource_exhausted", "quota", "rate limit", "rate_limit")):
        return ("⏳ Se alcanzó el límite de uso del modelo (cuota o solicitudes por minuto). "
                "Espera un momento e inténtalo de nuevo.")
    if any(s in texto for s in ("api key", "api_key", "401", "403", "permission_denied", "unauthenticated")):
        return ("🔑 No fue posible autenticarse con el modelo. Verifica que la GEMINI_API_KEY esté "
                "configurada y vigente.")
    if any(s in texto for s in ("timeout", "timed out", "deadline", "connection", "unavailable", "503")):
        return ("🌐 El servicio del modelo no respondió a tiempo. Revisa tu conexión e inténtalo de nuevo.")
    return "❌ Ocurrió un error inesperado al procesar tu consulta. Inténtalo de nuevo en unos segundos."
