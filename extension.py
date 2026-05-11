"""Entrypoint for the finances extension.

Registers CLI subcommands and the financial_summary Mirror Mode context
provider. Concrete subcommand handlers and the summary builder live in
the src/ subpackage; this file is intentionally thin so the contract
with the mirror is obvious at a glance.

User stories that motivate each registered surface live under
docs/user-stories/.
"""

from __future__ import annotations

import sys
from pathlib import Path

# The framework loader imports this module by path via
# importlib.util.spec_from_file_location, which does NOT add the
# extension directory to sys.path. Our submodules under src/ would
# therefore fail to import. Insert the extension root explicitly,
# idempotently, so 'from src.x import y' resolves.
#
# This is a known authoring rough edge; future framework work
# (CV14.E2 — Authoring QoL) is expected to move this concern into
# the loader itself. Until then every command-skill extension that
# splits code across submodules needs the same prelude.
_EXTENSION_ROOT = Path(__file__).resolve().parent
if str(_EXTENSION_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXTENSION_ROOT))

from memory.extensions.api import ContextRequest, ExtensionAPI  # noqa: E402

from src.cli.migrate_legacy import cmd_migrate_legacy  # noqa: E402


def register(api: ExtensionAPI) -> None:
    api.register_cli(
        "migrate-legacy",
        cmd_migrate_legacy,
        summary="Migrate legacy mirror finance data into ext_finances_* tables",
    )
    # The financial_summary capability is declared in skill.yaml so the
    # mirror knows the extension intends to provide Mirror Mode context,
    # but the provider returns None until US-10 lands.
    api.register_mirror_context("financial_summary", _provide_financial_summary)


def _provide_financial_summary(api: ExtensionAPI, ctx: ContextRequest) -> str | None:
    """Live financial summary for injection into the Mirror Mode prompt.

    Implementation pending — see US-10. Returns None until the underlying
    report functions land, so a premature bind does no harm.
    """
    return None
