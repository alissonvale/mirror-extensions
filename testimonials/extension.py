"""Entrypoint for the testimonials extension.

Registers the four CLI subcommands. The extension does not provide a
Mirror Mode context provider — testimonials are queried, not always
shown. A future capability could surface "recent testimonials" for
copy/launch personas if the need emerges.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Workaround: the framework loader imports extension.py by path and
# does not add the extension directory to sys.path. See the note in
# the finances extension's extension.py and the CV14.E2 candidate in
# the framework roadmap.
_EXTENSION_ROOT = Path(__file__).resolve().parent
if str(_EXTENSION_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXTENSION_ROOT))

from memory.extensions.api import ExtensionAPI  # noqa: E402

from src.cli.add import cmd_add  # noqa: E402
from src.cli.list import cmd_list  # noqa: E402
from src.cli.migrate_legacy import cmd_migrate_legacy  # noqa: E402
from src.cli.search import cmd_search  # noqa: E402


def register(api: ExtensionAPI) -> None:
    api.register_cli(
        "add",
        cmd_add,
        summary="Register a testimonial from free text (US-01)",
    )
    api.register_cli(
        "list",
        cmd_list,
        summary="List testimonials with filters (US-02)",
    )
    api.register_cli(
        "search",
        cmd_search,
        summary="Semantic search across testimonials (US-03)",
    )
    api.register_cli(
        "migrate-legacy",
        cmd_migrate_legacy,
        summary="Import testimonials from a legacy mirror database (US-04)",
    )
