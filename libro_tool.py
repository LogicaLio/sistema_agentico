import json
from pathlib import Path
from typing import TypedDict


class Libro(TypedDict):
    """Representa un libro dentro del catálogo de la biblioteca."""

    titulo: str
    autor: str
    genero: str
    anio: int
    sinopsis: str
    disponible: bool
    ejemplares_disponibles: int
    ubicacion: str


# Ruta al archivo que contiene el catálogo de libros de la biblioteca.
DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "libros.json"


def consultar_libro(consulta: str) -> dict:
    """Busca libros en el catálogo según un criterio de consulta.

    La búsqueda no distingue entre mayúsculas y minúsculas y permite
    coincidencias parciales por título, autor o género. Devuelve la
    información completa de cada libro encontrado, incluyendo
    disponibilidad, sinopsis y ubicación.

    Args:
        consulta: Título, autor, género o fragmento de texto utilizado
            como criterio de búsqueda.

    Returns:
        Diccionario con la consulta original, la lista de libros que
        coinciden y la cantidad de resultados encontrados.

    Raises:
        FileNotFoundError: Si el archivo del catálogo no existe.
        json.JSONDecodeError: Si el archivo contiene un JSON inválido.
    """
    with DATA_FILE.open("r", encoding="utf-8") as archivo:
        catalogo: list[Libro] = json.load(archivo)

    criterio = consulta.lower().strip()

    resultados = [
        libro
        for libro in catalogo
        if criterio in libro["titulo"].lower()
        or criterio in libro["autor"].lower()
        or criterio in libro["genero"].lower()
    ]

    # Retorno en diccionario estructurado para Gemini Function Calling
    return {
        "consulta": consulta,
        "resultados": resultados,
        "cantidad": len(resultados),
    }
