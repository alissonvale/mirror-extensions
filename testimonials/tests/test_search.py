"""Tests for cosine search over testimonials (US-03 internals)."""

from __future__ import annotations

import numpy as np

from src.search import cosine_similarity, search_testimonials
from src.store_writes import insert_testimonial


def _vec_blob(seed: int, dim: int = 1536) -> bytes:
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim, dtype=np.float32)
    vec = vec / np.linalg.norm(vec)
    return vec.tobytes()


# --- cosine_similarity -------------------------------------------------


def test_cosine_identical_vectors_score_one():
    blob = _vec_blob(1)
    assert cosine_similarity(blob, blob) == 1.0


def test_cosine_orthogonal_vectors_score_near_zero():
    # In 1536-dim space, two random gaussian vectors are nearly orthogonal.
    a = _vec_blob(1)
    b = _vec_blob(2)
    score = cosine_similarity(a, b)
    assert -0.1 < score < 0.1


def test_cosine_handles_empty_bytes():
    assert cosine_similarity(b"", _vec_blob(1)) == 0.0
    assert cosine_similarity(_vec_blob(1), b"") == 0.0


def test_cosine_handles_dimensionality_mismatch():
    a = _vec_blob(1, dim=1536)
    b = _vec_blob(2, dim=768)
    assert cosine_similarity(a, b) == 0.0


# --- search_testimonials ------------------------------------------------


def test_search_returns_empty_when_no_embeddings(testimonials_api, deterministic_embedder):
    # Row exists but has no embedding.
    insert_testimonial(testimonials_api, author_name="X", content="y")
    assert search_testimonials(testimonials_api, "anything") == []


def test_search_ranks_by_similarity(testimonials_api, deterministic_embedder):
    # Two records: one whose content matches the query exactly, one that does not.
    matching_blob = deterministic_embedder("course transformation")
    other_blob = deterministic_embedder("rainfall in october")
    insert_testimonial(
        testimonials_api,
        author_name="Match",
        content="course transformation",
        embedding=np.asarray(matching_blob, dtype=np.float32).tobytes()
        if not isinstance(matching_blob, bytes)
        else matching_blob,
    )
    insert_testimonial(
        testimonials_api,
        author_name="Other",
        content="rainfall in october",
        embedding=np.asarray(other_blob, dtype=np.float32).tobytes()
        if not isinstance(other_blob, bytes)
        else other_blob,
    )
    # Hmm: deterministic_embedder fixture returns numpy arrays; convert to bytes here
    # explicitly to keep the call path realistic. (insert_testimonial expects bytes.)
    results = search_testimonials(testimonials_api, "course transformation", limit=2)
    assert len(results) == 2
    assert results[0][0].author_name == "Match"
    assert results[0][1] >= results[1][1]


def test_search_respects_limit(testimonials_api, deterministic_embedder):
    for idx in range(5):
        vec = deterministic_embedder(f"text-{idx}")
        blob = (
            np.asarray(vec, dtype=np.float32).tobytes()
            if not isinstance(vec, bytes)
            else vec
        )
        insert_testimonial(
            testimonials_api,
            author_name=f"A{idx}",
            content=f"text-{idx}",
            embedding=blob,
        )
    results = search_testimonials(testimonials_api, "query", limit=2)
    assert len(results) == 2


def test_search_skips_rows_without_embedding(testimonials_api, deterministic_embedder):
    vec = deterministic_embedder("good content")
    blob = np.asarray(vec, dtype=np.float32).tobytes() if not isinstance(vec, bytes) else vec
    insert_testimonial(
        testimonials_api, author_name="With", content="good content", embedding=blob
    )
    insert_testimonial(
        testimonials_api, author_name="Without", content="other", embedding=None
    )
    results = search_testimonials(testimonials_api, "good content", limit=5)
    authors = [t.author_name for t, _ in results]
    assert "With" in authors
    assert "Without" not in authors
