"""RAG local: recuperación de fragmentos con BM25 sobre data/conocimiento/.

Es una recuperación léxica (no usa embeddings ni red): es determinista, gratuita,
funciona en Render sin servicios extra y se puede probar sin API Key.
Soporta documentos .md, .txt y .pdf (este último requiere `pypdf`).
"""

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

CONOCIMIENTO_DIR = Path(__file__).resolve().parent.parent / "data" / "conocimiento"
EXTENSIONES = {".md", ".txt", ".pdf"}

STOPWORDS = set(
    "a al algo ante como con contra cual cuales cuando de del desde donde el ella ellos en entre "
    "es esa ese eso esta este esto estoy hay la las le les lo los me mi mis muy no nos o para pero "
    "por que se si sin sobre su sus te tu tus un una uno unos unas y ya yo cuanto cuantas cuantos "
    "quien quienes cual puedo debo tengo es son fue ser".split()
)


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()


def _raiz(palabra: str) -> str:
    """Stemming mínimo para plurales en español (créditos -> credito)."""
    if len(palabra) > 4 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


# Sinónimos del lenguaje estudiantil -> término usado en los documentos.
SINONIMOS = {"materia": "asignatura", "curso": "asignatura"}


def tokenizar(texto: str) -> list[str]:
    palabras = re.findall(r"[a-z0-9]+", normalizar(texto))
    raices = (_raiz(p) for p in palabras if p not in STOPWORDS and len(p) > 1)
    return [SINONIMOS.get(r, r) for r in raices]


@dataclass
class Fragmento:
    fuente: str
    texto: str
    tokens: list[str] = field(default_factory=list)


def _leer_documento(ruta: Path) -> str:
    if ruta.suffix.lower() == ".pdf":
        from pypdf import PdfReader  # import perezoso: solo si hay PDFs

        return "\n\n".join((p.extract_text() or "") for p in PdfReader(str(ruta)).pages)
    return ruta.read_text(encoding="utf-8")


_TITULO = re.compile(r"^#{1,6}\s")


def _secciones(texto: str) -> list[str]:
    """Divide el texto en secciones por títulos Markdown (#, ##, ...).
    Un título sin contenido propio se une a la sección siguiente."""
    secciones: list[str] = []
    actual: list[str] = []
    for linea in texto.splitlines():
        if _TITULO.match(linea) and any(l.strip() and not _TITULO.match(l) for l in actual):
            secciones.append("\n".join(actual).strip())
            actual = []
        actual.append(linea)
    if actual:
        secciones.append("\n".join(actual).strip())
    return [s for s in secciones if s]


def dividir_en_fragmentos(texto: str, maximo: int = 800) -> list[str]:
    """Un fragmento por sección; las secciones largas se parten por párrafos.
    Los fragmentos nunca mezclan secciones distintas (mantiene el tema concentrado)."""
    fragmentos: list[str] = []
    for seccion in _secciones(texto):
        actual = ""
        for parrafo in (p.strip() for p in re.split(r"\n\s*\n", seccion) if p.strip()):
            if actual and len(actual) + len(parrafo) > maximo:
                fragmentos.append(actual)
                actual = parrafo
            else:
                actual = f"{actual}\n\n{parrafo}" if actual else parrafo
        if actual:
            fragmentos.append(actual)
    return fragmentos


def cargar_fragmentos(directorio: Path | None = None) -> list[Fragmento]:
    directorio = directorio or CONOCIMIENTO_DIR  # se lee al llamar, no al definir la función
    fragmentos: list[Fragmento] = []
    if not directorio.exists():
        return fragmentos
    for ruta in sorted(directorio.iterdir()):
        if ruta.suffix.lower() not in EXTENSIONES or ruta.name.upper().startswith("LEEME"):
            continue
        try:
            texto = _leer_documento(ruta)
        except Exception:  # un documento dañado no debe tumbar todo el índice
            continue
        for trozo in dividir_en_fragmentos(texto):
            fragmentos.append(Fragmento(fuente=ruta.name, texto=trozo, tokens=tokenizar(trozo)))
    return fragmentos


class IndiceBM25:
    def __init__(self, fragmentos: list[Fragmento], k1: float = 1.5, b: float = 0.75):
        self.fragmentos = fragmentos
        self.k1, self.b = k1, b
        self.n = len(fragmentos)
        self.longitud_media = (sum(len(f.tokens) for f in fragmentos) / self.n) if self.n else 0.0
        self.df: Counter = Counter()
        for f in fragmentos:
            self.df.update(set(f.tokens))
        self._frecuencias = [Counter(f.tokens) for f in fragmentos]

    def _idf(self, termino: str) -> float:
        df = self.df.get(termino, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def buscar(self, consulta: str, k: int = 3) -> list[tuple[float, Fragmento]]:
        terminos = tokenizar(consulta)
        if not terminos or not self.n:
            return []
        resultados = []
        for frag, frec in zip(self.fragmentos, self._frecuencias):
            largo = len(frag.tokens) or 1
            score = 0.0
            for t in terminos:
                f = frec.get(t, 0)
                if f:
                    norma = f + self.k1 * (1 - self.b + self.b * largo / (self.longitud_media or 1))
                    score += self._idf(t) * f * (self.k1 + 1) / norma
            if score > 0:
                resultados.append((score, frag))
        resultados.sort(key=lambda x: x[0], reverse=True)
        return resultados[:k]


@lru_cache(maxsize=1)
def obtener_indice() -> IndiceBM25:
    return IndiceBM25(cargar_fragmentos())


def reconstruir_indice() -> IndiceBM25:
    """Úsalo después de agregar o cambiar documentos en data/conocimiento/."""
    obtener_indice.cache_clear()
    return obtener_indice()
