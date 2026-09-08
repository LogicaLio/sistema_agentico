from typing import TypedDict

from google import genai
from google.genai import types

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from tools.libro_tool import consultar_libro


class Usuario(TypedDict):
    """Representa la información básica del usuario de la biblioteca."""

    nombre: str
    programa: str
    semestre: str


# Cliente utilizado para realizar solicitudes a la API de Gemini.
client = genai.Client(api_key=GEMINI_API_KEY)


def construir_contexto(usuario: Usuario, memoria: str) -> str:
    """Construye las instrucciones de contexto para el asistente de biblioteca.

    Combina la información actual del usuario con la memoria reciente
    de la conversación y las instrucciones que determinan el comportamiento
    del modelo.

    El contexto también indica cuándo debe utilizarse la herramienta
    ``consultar_libro`` y establece restricciones para evitar respuestas
    con información de libros no disponible en el catálogo.

    Args:
        usuario: Información básica del usuario que consulta la biblioteca.
        memoria: Representación textual de los mensajes recientes de la
            conversación.

    Returns:
        Instrucción de sistema que se enviará al modelo Gemini como contexto.
    """
    return f"""
Eres el asistente virtual de la biblioteca de la Universidad Católica Luis Amigó.

Ayudas al usuario a saber si un libro está disponible y a conocer datos
sobre él: sinopsis, autor, género, año y ubicación en la biblioteca.

ESTADO ACTUAL DEL USUARIO:
Nombre: {usuario["nombre"]}
Programa: {usuario["programa"]}
Semestre: {usuario["semestre"]}

MEMORIA RECIENTE:
{memoria}

Dispones de una herramienta llamada consultar_libro.

Usa consultar_libro cuando el usuario pregunte por un libro específico:
su disponibilidad, sinopsis, autor, género, año o ubicación.

El catálogo de la biblioteca es reducido. Si consultar_libro no
encuentra resultados, indica claramente que el libro no está en el
catálogo consultado; no inventes datos de libros que no existan en él.

Si puedes responder usando el estado o la memoria, responde directamente.
Sé breve, claro y cordial.
""".strip()


def responder(
    mensaje_usuario: str,
    usuario: Usuario,
    memoria: str,
) -> str:
    """Genera una respuesta del asistente de biblioteca mediante Gemini.

    Construye el contexto de la conversación y envía el mensaje del
    usuario al modelo configurado de Gemini. El modelo puede utilizar
    la herramienta ``consultar_libro`` cuando la consulta requiere
    información relacionada con el catálogo de libros.

    Args:
        mensaje_usuario: Mensaje enviado por el usuario.
        usuario: Información básica del usuario que consulta la biblioteca.
        memoria: Representación textual de los mensajes recientes de la
            conversación.

    Returns:
        Respuesta textual generada por Gemini. Si el modelo no devuelve
        contenido textual, se retorna un mensaje predeterminado.
    """
    contexto = construir_contexto(usuario, memoria)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=mensaje_usuario,
        config=types.GenerateContentConfig(
            system_instruction=contexto,
            tools=[consultar_libro],
        ),
    )

    return response.text or "No fue posible generar una respuesta."
