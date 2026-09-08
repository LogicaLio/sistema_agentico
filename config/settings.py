import os
from dotenv import load_dotenv


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.6-flash"


def validar_configuracion() -> None:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_API_KEY_AQUI":
        raise ValueError(
            "Configura una API Key válida en el archivo .env "
            "usando GEMINI_API_KEY."
        )