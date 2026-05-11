"""CLI: `testimonials add "<free text>"` (US-01)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.parse import parse_testimonial
from src.store_writes import insert_testimonial

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def cmd_add(api: "ExtensionAPI", args: list[str]) -> int:
    """Register a testimonial from free text. LLM extracts the fields."""
    if not args or args[0] in {"--help", "-h", "help"}:
        _print_usage()
        return 0 if (args and args[0] != "") else 1

    text = " ".join(args).strip()
    if not text:
        print("error: testimonial text cannot be empty")
        _print_usage()
        return 1

    parsed = parse_testimonial(api, text)

    # Embedding the verbatim content (not the raw paraphrase): search
    # ranks against what the customer actually said, which is what the
    # user is most likely searching for later.
    try:
        embedding = api.embed(parsed["content"])
    except Exception as exc:  # noqa: BLE001
        print(f"warning: embedding failed, record will be saved without it: {exc}")
        embedding = None

    testimonial_id = insert_testimonial(
        api,
        author_name=parsed["author_name"],
        content=parsed["content"],
        source=parsed["source"],
        product=parsed["product"],
        highlight=parsed["highlight"],
        tags=parsed["tags"],
        received_at=parsed["received_at"],
        embedding=embedding,
    )

    print(f"added testimonial {testimonial_id}")
    print(f"  author: {parsed['author_name']}" + (
        f" ({parsed['source']})" if parsed["source"] else ""
    ))
    if parsed["product"]:
        print(f"  product: {parsed['product']}")
    if parsed["highlight"]:
        print(f"  highlight: \"{parsed['highlight']}\"")
    if parsed["tags"]:
        print(f"  tags: {', '.join(parsed['tags'])}")
    if parsed["received_at"]:
        print(f"  received: {parsed['received_at']}")
    return 0


def _print_usage() -> None:
    print(
        "usage: python -m memory ext testimonials add \"<free text>\"\n"
        "  The free text is the user's description of the testimonial. "
        "The LLM extracts:\n"
        "    author_name, content (verbatim quote), source, product, "
        "highlight, tags, received_at."
    )
