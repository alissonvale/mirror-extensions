"""Read helpers over ext_testimonials_records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models import Testimonial, parse_tags

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def _row_to_testimonial(row) -> Testimonial:
    return Testimonial(
        id=row["id"],
        author_name=row["author_name"],
        content=row["content"],
        created_at=row["created_at"],
        source=row["source"],
        product=row["product"],
        highlight=row["highlight"],
        tags=parse_tags(row["tags"]),
        received_at=row["received_at"],
        embedding=row["embedding"],
    )


def list_testimonials(
    api: "ExtensionAPI",
    *,
    product: str | None = None,
    author_like: str | None = None,
    source: str | None = None,
) -> list[Testimonial]:
    """List testimonials, optionally narrowed by product / author / source."""
    clauses: list[str] = []
    params: list[object] = []
    if product:
        clauses.append("LOWER(product) = LOWER(?)")
        params.append(product)
    if author_like:
        clauses.append("LOWER(author_name) LIKE ?")
        params.append(f"%{author_like.lower()}%")
    if source:
        clauses.append("LOWER(source) = LOWER(?)")
        params.append(source)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = api.read(
        f"SELECT * FROM ext_testimonials_records{where} "
        f"ORDER BY received_at DESC, created_at DESC",
        params,
    ).fetchall()
    return [_row_to_testimonial(r) for r in rows]


def get_testimonial(api: "ExtensionAPI", testimonial_id: str) -> Testimonial | None:
    row = api.read(
        "SELECT * FROM ext_testimonials_records WHERE id = ?",
        (testimonial_id,),
    ).fetchone()
    return _row_to_testimonial(row) if row else None


def all_with_embeddings(api: "ExtensionAPI") -> list[Testimonial]:
    """Every testimonial that has a non-null embedding (search input)."""
    rows = api.read(
        "SELECT * FROM ext_testimonials_records "
        "WHERE embedding IS NOT NULL "
        "ORDER BY received_at DESC, created_at DESC"
    ).fetchall()
    return [_row_to_testimonial(r) for r in rows]
