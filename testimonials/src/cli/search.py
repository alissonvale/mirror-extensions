"""CLI: `testimonials search "<query>"` (US-03)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.search import search_testimonials

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def cmd_search(api: "ExtensionAPI", args: list[str]) -> int:
    """Semantic search across testimonials."""
    if not args or args[0] in {"--help", "-h", "help"}:
        _print_usage()
        return 0 if (args and args[0] != "") else 1

    # The query is whatever the user typed; --limit is optional.
    query_parts: list[str] = []
    limit = 5
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--limit" and i + 1 < len(args):
            try:
                limit = int(args[i + 1])
            except ValueError:
                print(f"error: --limit must be an integer, got '{args[i + 1]}'")
                return 1
            i += 2
            continue
        query_parts.append(token)
        i += 1

    query = " ".join(query_parts).strip()
    if not query:
        print("error: search query cannot be empty")
        _print_usage()
        return 1

    try:
        results = search_testimonials(api, query, limit=limit)
    except Exception as exc:  # noqa: BLE001
        print(f"error: search failed: {exc}")
        return 1

    if not results:
        print(
            "(no testimonials with embeddings to search; add some first "
            "with `testimonials add`, or run `migrate-legacy` if you "
            "have a legacy archive)"
        )
        return 0

    print(f"{len(results)} result(s) for: {query}")
    print()
    for testimonial, score in results:
        print(f"[{testimonial.id}] {testimonial.author_name} (score: {score:.3f})")
        if testimonial.product:
            print(f"  product: {testimonial.product}")
        preview = (
            testimonial.highlight
            or (testimonial.content[:160] + ("..." if len(testimonial.content) > 160 else ""))
        )
        print(f"  \"{preview}\"")
        print()
    return 0


def _print_usage() -> None:
    print(
        "usage: python -m memory ext testimonials search \"<query>\" "
        "[--limit <N>]"
    )
