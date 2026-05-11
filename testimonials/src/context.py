"""Mirror Mode context provider for the testimonials extension.

Exposes ``recent_testimonials`` — a capability the user can bind to a
persona (writer, marketer, mentor, …) so that, when that persona is
active in Mirror Mode, the mirror automatically surfaces a few
testimonials relevant to the current conversation.

Design choices:

* The provider is **query-driven**, not time-driven. It uses the user
  query that the framework passes in ``ContextRequest`` to rank
  testimonials by cosine similarity, the same way the ``search`` CLI
  subcommand does. With no query, the provider returns ``None`` — a
  generic "recent testimonials" block would pollute every Mirror Mode
  turn for the bound persona, which is exactly the failure mode US-05
  set out to avoid.

* A **relevance floor** keeps the block out of unrelated conversations.
  When no testimonial scores above the floor, the provider returns
  ``None`` instead of dragging in weak matches.

* Failures are isolated: any unexpected exception inside the composer
  is caught, logged via ``api.log``, and the provider returns ``None``
  so Mirror Mode never breaks because of a testimonials hiccup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.search import search_testimonials

if TYPE_CHECKING:
    from memory.extensions.api import ContextRequest, ExtensionAPI


# Tuned conservatively: cosine scores below this on
# text-embedding-3-small typically mean "loosely related at best".
# Surfacing those would more often than not distract the persona.
RELEVANCE_FLOOR = 0.30

# Hard cap. We do not want the block to dominate the Mirror Mode
# prompt; three is plenty for the persona to pick a hook from.
MAX_HITS = 3


def provide_recent_testimonials(api: ExtensionAPI, ctx: ContextRequest) -> str | None:
    """Return a Mirror Mode block of testimonials relevant to ``ctx.query``.

    Returns ``None`` when:
    - the user did not pass a query (e.g. an initial empty turn);
    - no testimonial scores above :data:`RELEVANCE_FLOOR`;
    - the testimonials archive is empty;
    - any internal step raises.
    """
    if not ctx.query or not ctx.query.strip():
        return None

    try:
        results = search_testimonials(api, ctx.query, limit=MAX_HITS)
    except Exception as exc:
        api.log(
            "warning",
            "recent_testimonials: search failed; returning None",
            error=str(exc),
        )
        return None

    relevant = [(t, score) for (t, score) in results if score >= RELEVANCE_FLOOR]
    if not relevant:
        return None

    return _format_block(relevant)


def _format_block(hits: list) -> str:
    """Compose the markdown block injected into the Mirror Mode prompt.

    Kept deliberately compact: one line per testimonial with author,
    product (if known), and the verbatim highlight (falling back to a
    trimmed content preview). The persona decides whether and how to
    quote them.
    """
    lines = ["## Testimonials related to this conversation", ""]
    for testimonial, score in hits:
        header_parts = [f"**{testimonial.author_name}**"]
        if testimonial.product:
            header_parts.append(f"on _{testimonial.product}_")
        header_parts.append(f"(score {score:.2f})")
        header = " ".join(header_parts)

        quote = testimonial.highlight or _trim(testimonial.content, 180)
        lines.append(f"- {header}: \u201c{quote}\u201d")
    return "\n".join(lines)


def _trim(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "\u2026"
