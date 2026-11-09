"""Petit modèle d'embedding multilingue, exécuté sur le processeur."""
from __future__ import annotations

import config

_model = None


def _load():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(config.EMBED_MODEL, device=config.EMBED_DEVICE)
    return _model


def _prefixes() -> tuple[str, str]:
    # Les modèles E5 demandent ces préfixes ; bge-m3 n'en veut pas.
    if "e5" in config.EMBED_MODEL.lower():
        return "passage: ", "query: "
    return "", ""


def embed_passages(texts: list[str]) -> list[list[float]]:
    p, _ = _prefixes()
    vecs = _load().encode([p + t for t in texts], normalize_embeddings=True, batch_size=16,
                          show_progress_bar=len(texts) > 32)
    return vecs.tolist()


def embed_query(text: str) -> list[float]:
    _, q = _prefixes()
    return _load().encode([q + text], normalize_embeddings=True)[0].tolist()
