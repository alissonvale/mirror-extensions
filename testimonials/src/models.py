"""Typed view over an ext_testimonials_records row."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Testimonial:
    id: str
    author_name: str
    content: str
    created_at: str
    source: str | None = None
    product: str | None = None
    highlight: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    received_at: str | None = None
    # Embedding kept separate to avoid bytes-equality surprises in
    # places that compare Testimonial objects.
    embedding: bytes | None = None


def parse_tags(raw: Any) -> tuple[str, ...]:
    """Decode the tags column (stored as JSON text) into a tuple.

    Tolerates None, empty string, and malformed JSON: every failure
    mode yields an empty tuple rather than raising.
    """
    if raw is None or raw == "":
        return ()
    if isinstance(raw, (list, tuple)):
        return tuple(str(item) for item in raw)
    try:
        decoded = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ()
    if isinstance(decoded, list):
        return tuple(str(item) for item in decoded)
    return ()


def encode_tags(tags: list[str] | tuple[str, ...] | None) -> str | None:
    if not tags:
        return None
    return json.dumps(list(tags))
