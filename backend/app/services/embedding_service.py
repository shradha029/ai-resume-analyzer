"""Optional Sentence-Transformers wrapper.

If the library (or the model download) is unavailable, get_embedder() returns None and the
matcher falls back to rules + TF-IDF. The analysis result always states which method was used.
"""
import logging

from app.config import settings

logger = logging.getLogger(__name__)
_cache: dict = {}


class Embedder:
    def __init__(self, model):
        self.model = model

    def similarities(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        vecs = self.model.encode([query] + texts, normalize_embeddings=True)
        q, rest = vecs[0], vecs[1:]
        return [float(v @ q) for v in rest]


def get_embedder():
    if not settings.ENABLE_EMBEDDINGS:
        return None
    if "e" in _cache:
        return _cache["e"]
    try:
        from sentence_transformers import SentenceTransformer

        _cache["e"] = Embedder(SentenceTransformer(settings.EMBEDDING_MODEL))
    except Exception as exc:  # not installed, or no internet for the first model download
        logger.warning("Semantic matching disabled (%s: %s)", type(exc).__name__, exc)
        _cache["e"] = None
    return _cache["e"]
