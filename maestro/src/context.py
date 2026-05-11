"""Mirror Mode context provider for the Maestro extension."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.coherence import check_project, render_cli_report
from src.project import ProjectResolutionError, resolve_project_root

if TYPE_CHECKING:
    from memory.extensions.api import ContextRequest, ExtensionAPI


def provide_coherence_status(api: ExtensionAPI, ctx: ContextRequest) -> str | None:
    """Always inject the active journey's current coherence status.

    The provider is bound to a journey, not a persona. It resolves the
    journey's ``metadata.project_path``, checks the project live, and
    returns a compact block. All failures return ``None`` so Mirror Mode
    never breaks because the coherence layer is unavailable.
    """
    try:
        root, _journey_id = resolve_project_root(api, journey_id=ctx.journey_id)
        result = check_project(root)
    except ProjectResolutionError as exc:
        api.log("warning", "coherence_status: project root not configured", error=str(exc))
        return None
    except Exception as exc:
        api.log("warning", "coherence_status: check failed", error=str(exc))
        return None

    return _format_context_block(result)


def _format_context_block(result) -> str:
    lines = [
        "## Maestro Coherence Status",
        "",
        f"Project root: `{result.state.root}`",
        f"Locale: `{result.state.config.locale}` | Mode: `{result.state.config.mode}`",
        "",
    ]

    if not result.has_open_gaps:
        lines.append("✅ No open coherence gaps for the Maestro Base Lens.")
        return "\n".join(lines)

    if result.has_blocking_gaps:
        lines.append("🛑 Blocking coherence gaps are open.")
    else:
        lines.append("⚠️ Non-blocking coherence gaps are open.")
    lines.extend(["", "```text", render_cli_report(result).rstrip(), "```"])
    return "\n".join(lines)
