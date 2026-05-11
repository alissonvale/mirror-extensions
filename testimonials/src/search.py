"""Semantic search over testimonials.

The legacy mirror stored embeddings as a float32 vector serialised via
``numpy.tobytes``. The framework's ``api.embed()`` returns bytes in the
same layout, so any vector that round-trips through ``bytes`` is
directly comparable with cosine similarity. No re-embedding needed
across the migration boundary.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from src.models import Testimonial
from src.store import all_with_embeddings

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def _vector_from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def cosine_similarity(a: bytes, b: bytes) -> float:
    """Cosine similarity between two float32 BLOB embeddings.

    Returns 0.0 when either vector is empty, has zero norm, or differs
    in dimensionality from the other (defensive against legacy data
    that might have been generated with a different model).
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    va = _vector_from_blob(a)
    vb = _vector_from_blob(b)
    if va.size == 0 or vb.size == 0:
        return 0.0
    norm_a = float(np.linalg.norm(va))
    norm_b = float(np.linalg.norm(vb))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def search_testimonials(
    api: "ExtensionAPI", query: str, *, limit: int = 5
) -> list[tuple[Testimonial, float]]:
    """Embed ``query``, rank every stored testimonial by cosine
    similarity, return the top ``limit`` (testimonial, score) tuples.

    Returns an empty list when no testimonials carry embeddings.
    """
    candidates = all_with_embeddings(api)
    if not candidates:
        return []

    query_blob = api.embed(query)

    scored: list[tuple[Testimonial, float]] = []
    for t in candidates:
        if t.embedding is None:
            continue
        score = cosine_similarity(query_blob, t.embedding)
        if math.isfinite(score):
            scored.append((t, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]
