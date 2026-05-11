"""CLI: `testimonials list [--product ...]` (US-02)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.store import list_testimonials

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def cmd_list(api: ExtensionAPI, args: list[str]) -> int:
    """List testimonials with optional filters."""
    if args and args[0] in {"--help", "-h", "help"}:
        _print_usage()
        return 0

    flags = _parse_flags(args)
    if flags is None:
        return 1

    items = list_testimonials(
        api,
        product=flags.get("product"),
        author_like=flags.get("author"),
        source=flags.get("source"),
    )
    if not items:
        print("(no testimonials matched)")
        return 0

    print(f"{len(items)} testimonial(s)")
    print()
    for t in items:
        header = f"[{t.id}] {t.author_name}"
        if t.source:
            header += f" ({t.source})"
        if t.received_at:
            header += f" — {t.received_at}"
        print(header)
        if t.product:
            print(f"  product: {t.product}")
        if t.highlight:
            print(f'  "{t.highlight}"')
        else:
            preview = t.content[:120] + ("..." if len(t.content) > 120 else "")
            print(f'  "{preview}"')
        if t.tags:
            print(f"  tags: {', '.join(t.tags)}")
        print()
    return 0


def _print_usage() -> None:
    print(
        "usage: python -m memory ext testimonials list "
        "[--product <name>] [--author <substring>] [--source <channel>]"
    )


def _parse_flags(args: list[str]) -> dict[str, str] | None:
    allowed = {
        "--product": "product",
        "--author": "author",
        "--source": "source",
    }
    out: dict[str, str] = {}
    i = 0
    while i < len(args):
        flag = args[i]
        if flag not in allowed:
            print(f"error: unrecognised flag '{flag}'")
            _print_usage()
            return None
        if i + 1 >= len(args):
            print(f"error: flag '{flag}' requires a value")
            _print_usage()
            return None
        out[allowed[flag]] = args[i + 1]
        i += 2
    return out
