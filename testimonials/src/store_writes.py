"""Write helpers over ext_testimonials_records."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.models import encode_tags

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def new_id() -> str:
    """8-char hex matching the legacy id shape so cross-references survive."""
    return uuid.uuid4().hex[:8]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def insert_testimonial(
    api: ExtensionAPI,
    *,
    author_name: str,
    content: str,
    source: str | None = None,
    product: str | None = None,
    highlight: str | None = None,
    tags: list[str] | tuple[str, ...] | None = None,
    received_at: str | None = None,
    embedding: bytes | None = None,
    id: str | None = None,
    created_at: str | None = None,
) -> str:
    """Insert one testimonial row. Returns its id."""
    testimonial_id = id or new_id()
    api.execute(
        "INSERT INTO ext_testimonials_records "
        "(id, author_name, content, source, product, highlight, tags, "
        " received_at, created_at, embedding) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            testimonial_id,
            author_name,
            content,
            source,
            product,
            highlight,
            encode_tags(tags),
            received_at,
            created_at or now_utc_iso(),
            embedding,
        ),
    )
    api.commit()
    return testimonial_id
