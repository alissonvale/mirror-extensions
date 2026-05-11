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

from src.cli.accounts import cmd_accounts  # noqa: E402
from src.cli.balance import cmd_balance, cmd_snapshot  # noqa: E402
from src.cli.bills import cmd_bills  # noqa: E402
from src.cli.categories import cmd_categories, cmd_categorize  # noqa: E402
from src.cli.migrate_legacy import cmd_migrate_legacy  # noqa: E402
from src.cli.report import cmd_report  # noqa: E402
from src.cli.runway import cmd_runway  # noqa: E402
from src.cli.transactions import cmd_transactions  # noqa: E402
from src.reports import financial_context_text  # noqa: E402


def register(api: ExtensionAPI) -> None:
    api.register_cli(
        "accounts",
        cmd_accounts,
        summary="Register and list accounts (US-01)",
    )
    api.register_cli(
        "balance",
        cmd_balance,
        summary="Show latest balance per account (US-02)",
    )
    api.register_cli(
        "snapshot",
        cmd_snapshot,
        summary="Record a balance snapshot for an account (US-02)",
    )
    api.register_cli(
        "transactions",
        cmd_transactions,
        summary="List and filter transactions (US-05)",
    )
    api.register_cli(
        "bills",
        cmd_bills,
        summary="Manage recurring bills (US-06)",
    )
    api.register_cli(
        "categories",
        cmd_categories,
        summary="Manage transaction categories (US-09)",
    )
    api.register_cli(
        "categorize",
        cmd_categorize,
        summary="Attach a category to a transaction (US-09)",
    )
    api.register_cli(
        "runway",
        cmd_runway,
        summary="Compute runway under explicit assumptions (US-07)",
    )
    api.register_cli(
        "report",
        cmd_report,
        summary="Monthly income/expense/net report (US-08)",
    )
    api.register_cli(
        "migrate-legacy",
        cmd_migrate_legacy,
        summary="Migrate legacy mirror finance data into ext_finances_* tables (US-11)",
    )
    api.register_mirror_context("financial_summary", _provide_financial_summary)


def _provide_financial_summary(
    api: ExtensionAPI, ctx: ContextRequest
) -> str | None:
    """Live financial summary for injection into the Mirror Mode prompt.

    Reads accounts, latest snapshots, transactions, and active bills,
    and composes a markdown block. Returns None when the extension has
    no accounts, so an empty database does not pollute the prompt.

    Any failure inside the composer (bad data, unexpected NULLs) is
    caught here; the framework's context dispatcher already isolates
    raises, but catching locally keeps the failure attributable.
    """
    try:
        return financial_context_text(api)
    except Exception as exc:  # noqa: BLE001 — surface, do not crash Mirror Mode
        api.log(
            "warning",
            "financial_summary provider failed; returning None",
            error=str(exc),
        )
        return None
