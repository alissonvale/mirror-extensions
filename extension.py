"""Entrypoint for the finances extension.

Registers CLI subcommands and the financial_summary Mirror Mode context
provider. Concrete subcommand handlers and the summary builder live in
the src/ subpackage; this file is intentionally thin so the contract
with the mirror is obvious at a glance.

User stories that motivate each registered surface live under
docs/user-stories/.
"""

from __future__ import annotations

from memory.extensions.api import ContextRequest, ExtensionAPI


def register(api: ExtensionAPI) -> None:
    # CLI subcommands are added by user story. None implemented yet —
    # see docs/user-stories/US-01..US-11 for the planned surface.
    # The financial_summary capability is declared in skill.yaml so the
    # mirror knows the extension intends to provide Mirror Mode context,
    # but binding it to a persona is a user-controlled action via
    # `python -m memory ext finances bind financial_summary --persona <id>`.
    api.register_mirror_context("financial_summary", _provide_financial_summary)


def _provide_financial_summary(api: ExtensionAPI, ctx: ContextRequest) -> str | None:
    """Live financial summary for injection into the Mirror Mode prompt.

    Implementation pending — see US-10. Returns None until the underlying
    report functions land, so a premature bind does no harm.
    """
    return None
