"""Write helpers for the Maestro extension tables."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from src.models import CheckResult

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def insert_check_run(
    api: ExtensionAPI,
    result: CheckResult,
    *,
    journey_id: str | None,
    source: str = "cli",
) -> str:
    """Record a check summary in ``ext_maestro_check_runs``."""
    run_id = uuid4().hex
    units = result.units
    open_count = sum(1 for unit in units if unit.status == "open")
    resolved_count = sum(1 for unit in units if unit.status == "resolved")
    blocking_count = sum(
        1 for unit in units if unit.status == "open" and unit.severity == "blocking"
    )
    important_count = sum(
        1 for unit in units if unit.status == "open" and unit.severity == "important"
    )
    optional_count = sum(
        1 for unit in units if unit.status == "open" and unit.severity == "optional"
    )

    if not open_count:
        summary = "no open coherence gaps"
    elif blocking_count:
        summary = f"{blocking_count} blocking gap(s), {open_count} open gap(s) total"
    else:
        summary = f"{open_count} non-blocking open gap(s)"

    api.execute(
        """
        INSERT INTO ext_maestro_check_runs (
            id, journey_id, project_root, locale, mode, source,
            open_count, resolved_count, blocking_count, important_count,
            optional_count, summary, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            journey_id,
            str(result.state.root),
            result.state.config.locale,
            result.state.config.mode,
            source,
            open_count,
            resolved_count,
            blocking_count,
            important_count,
            optional_count,
            summary,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    api.commit()
    return run_id
