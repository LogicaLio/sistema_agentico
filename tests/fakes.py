"""Modelo simulado para probar el grafo sin API Key ni red.

Imita lo que hace Gemini: clasifica la ruta, decide qué herramientas invocar y,
al recibir los ToolMessages, redacta la respuesta final. También informa
`usage_metadata` (tokens estimados como caracteres / 4).
"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from graph.nodes import DecisionRuta


def _tokens(texto: str) -> int:
    return max(1, len(texto) // 4)


def _usage(entrada: str, salida: str) -> dict:
    e, s = _tokens(entrada), _tokens(salida)
    return {"input_tokens": e, "output_tokens": s, "total_tokens": e + s}


def _texto_mensajes(msgs) -> str:
    return " ".join(str(m.content) for m in msgs)


class _Salida:
    def __init__(self, fn):
        self.fn = fn

    def invoke(self, msgs):
        return self.fn(msgs)


class ModeloFalso:
    """plan: función(pregunta_en_minusculas) -> lista de (nombre_tool, args) o None si es conceptual."""

    def __init__(self, plan, ruta_forzada=None, parsing_falla=False, siempre_tools=False, error=None):
        self.plan = plan
        self.ruta_forzada = ruta_forzada
        self.parsing_falla = parsing_falla
        self.siempre_tools = siempre_tools  # simula un bucle desbocado de herramientas
        self.error = error                  # excepción a lanzar en cada llamada
        self.llamadas = 0

    def _revisar_error(self):
        if self.error:
            raise self.error

    # --- enrutador ---
    def with_structured_output(self, schema, include_raw=False):
        def decidir(msgs):
            self._revisar_error()
            self.llamadas += 1
            pregunta = msgs[-1].content.lower()
            ruta = self.ruta_forzada or ("herramientas" if self.plan(pregunta) else "conceptual")
            raw = AIMessage(content="", usage_metadata=_usage(_texto_mensajes(msgs), ruta))
            parsed = None if self.parsing_falla else DecisionRuta(ruta=ruta, motivo="simulado")
            return {"raw": raw, "parsed": parsed, "parsing_error": None}

        return _Salida(decidir)

    # --- nodo conceptual ---
    def invoke(self, msgs):
        self._revisar_error()
        self.llamadas += 1
        salida = "Un crédito académico equivale a 48 horas de trabajo total del estudiante."
        return AIMessage(content=salida, usage_metadata=_usage(_texto_mensajes(msgs), salida))

    # --- agente con herramientas ---
    def bind_tools(self, tools):
        return _Salida(self._agente)

    def _agente(self, msgs):
        self._revisar_error()
        self.llamadas += 1
        idx = max(i for i, m in enumerate(msgs) if isinstance(m, HumanMessage))
        pregunta = msgs[idx].content.lower()
        plan = self.plan(pregunta) or []
        hechos = sum(1 for m in msgs[idx:] if isinstance(m, AIMessage) and m.tool_calls)
        if self.siempre_tools or hechos < len(plan):
            nombre, args = ("obtener_fecha", {}) if self.siempre_tools else plan[hechos]
            salida = AIMessage(content="", tool_calls=[{"name": nombre, "args": args, "id": f"c{self.llamadas}"}])
        else:
            ultimo = msgs[-1]
            assert isinstance(ultimo, ToolMessage), "el agente debe recibir el ToolMessage antes de responder"
            texto = f"Respuesta basada en: {str(ultimo.content)[:120]}"
            salida = AIMessage(content=texto)
        salida.usage_metadata = _usage(_texto_mensajes(msgs), str(salida.content) or "tool_call")
        return salida
