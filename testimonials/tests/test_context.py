"""Tests for the recent_testimonials Mirror Mode context provider (US-05)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from src.context import (
    MAX_HITS,
    RELEVANCE_FLOOR,
    provide_recent_testimonials,
)
from src.store_writes import insert_testimonial


@dataclass(frozen=True)
class _Ctx:
    """Minimal stand-in for memory.extensions.api.ContextRequest.

    The provider only reads ``query`` (and we want tests that do not
    depend on the framework being importable from this test process).
    """

    query: str | None = None
    persona_id: str | None = "writer"
    journey_id: str | None = None
    user: str = "test-user"
    binding_kind: str = "persona"
    binding_target: str | None = "writer"


def _seed(api, *, author, content, embedder):
    """Insert one testimonial with a deterministic embedding."""
    vec = embedder(content)
    blob = np.asarray(vec, dtype=np.float32).tobytes() if not isinstance(vec, bytes) else vec
    insert_testimonial(
        api,
        author_name=author,
        content=content,
        product="Workshop",
        highlight=content,
        embedding=blob,
    )


# --- happy path --------------------------------------------------------


def test_provider_returns_relevant_testimonials(testimonials_api, deterministic_embedder):
    _seed(
        testimonials_api,
        author="Maria",
        content="loved the workshop",
        embedder=deterministic_embedder,
    )
    _seed(
        testimonials_api,
        author="Pedro",
        content="rainy day at the beach",
        embedder=deterministic_embedder,
    )

    out = provide_recent_testimonials(testimonials_api, _Ctx(query="loved the workshop"))

    assert out is not None
    # Highest match comes first; the unrelated row may or may not appear
    # depending on its score vs the floor.
    assert "Maria" in out
    assert "Testimonials related to this conversation" in out


def test_provider_caps_at_max_hits(testimonials_api, deterministic_embedder):
    for i in range(MAX_HITS + 2):
        _seed(
            testimonials_api,
            author=f"A{i}",
            content="loved the workshop",
            embedder=deterministic_embedder,
        )
    out = provide_recent_testimonials(testimonials_api, _Ctx(query="loved the workshop"))
    assert out is not None
    # Every row matches the same query identically, so they all clear
    # the floor; the cap must be enforced regardless.
    bullets = [line for line in out.splitlines() if line.startswith("- ")]
    assert len(bullets) == MAX_HITS


# --- skip cases --------------------------------------------------------


def test_provider_returns_none_when_no_query(testimonials_api, deterministic_embedder):
    _seed(
        testimonials_api,
        author="Maria",
        content="loved the workshop",
        embedder=deterministic_embedder,
    )
    assert provide_recent_testimonials(testimonials_api, _Ctx(query=None)) is None
    assert provide_recent_testimonials(testimonials_api, _Ctx(query="")) is None
    assert provide_recent_testimonials(testimonials_api, _Ctx(query="   ")) is None


def test_provider_returns_none_when_archive_is_empty(testimonials_api, deterministic_embedder):
    assert provide_recent_testimonials(testimonials_api, _Ctx(query="anything")) is None


def test_provider_returns_none_below_relevance_floor(testimonials_api, deterministic_embedder):
    """When the best hit is below the floor, the provider returns None.

    The deterministic embedder produces vectors seeded from text hash;
    a query with no shared text typically scores well under the floor.
    """
    _seed(
        testimonials_api,
        author="Maria",
        content="loved the workshop",
        embedder=deterministic_embedder,
    )
    # Probe a few unrelated queries; this exercises the floor logic.
    queries = ["a", "b", "c", "d", "e", "f", "g", "h"]
    has_some_skipped = False
    for q in queries:
        if provide_recent_testimonials(testimonials_api, _Ctx(query=q)) is None:
            has_some_skipped = True
            break
    assert has_some_skipped, (
        "expected at least one unrelated query to fall under the relevance floor"
    )


# --- robustness --------------------------------------------------------


def test_provider_swallows_search_exceptions(testimonials_api, deterministic_embedder, monkeypatch):
    """Mirror Mode must never break because of a testimonials hiccup."""
    from src import context as context_module

    def _explode(*args, **kwargs):
        raise RuntimeError("embedding service down")

    monkeypatch.setattr(context_module, "search_testimonials", _explode)
    out = provide_recent_testimonials(testimonials_api, _Ctx(query="any"))
    assert out is None


def test_provider_block_uses_highlight_when_available(testimonials_api, deterministic_embedder):
    vec = deterministic_embedder("course transformation")
    blob = np.asarray(vec, dtype=np.float32).tobytes() if not isinstance(vec, bytes) else vec
    insert_testimonial(
        testimonials_api,
        author_name="Cara",
        content="The full course content was deep, varied, and challenging — many parts I wish I had access to years ago.",
        highlight="changed my career",
        product="Course",
        embedding=blob,
    )
    out = provide_recent_testimonials(testimonials_api, _Ctx(query="course transformation"))
    assert out is not None
    assert "changed my career" in out
    # The verbose content body should not be inlined when a highlight exists.
    assert "deep, varied, and challenging" not in out


def test_provider_falls_back_to_content_when_no_highlight(testimonials_api, deterministic_embedder):
    vec = deterministic_embedder("the workshop")
    blob = np.asarray(vec, dtype=np.float32).tobytes() if not isinstance(vec, bytes) else vec
    insert_testimonial(
        testimonials_api,
        author_name="X",
        content="A medium-length content body used as a fallback when there is no highlight on record.",
        highlight=None,
        product="Workshop",
        embedding=blob,
    )
    out = provide_recent_testimonials(testimonials_api, _Ctx(query="the workshop"))
    assert out is not None
    assert "medium-length content body" in out


# --- constants are honoured -------------------------------------------


def test_relevance_floor_is_a_sane_default():
    """Sanity-check the configured threshold. If this fails, the
    floor was edited and the test should be revisited intentionally."""
    assert 0.2 <= RELEVANCE_FLOOR <= 0.5
