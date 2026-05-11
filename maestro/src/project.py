"""Resolve Maestro project roots from Mirror journeys or explicit paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI

DEFAULT_JOURNEY = "maestro"


class ProjectResolutionError(ValueError):
    """Raised when the extension cannot resolve a project root."""


def project_path_for_journey(api: ExtensionAPI, journey_id: str) -> Path | None:
    """Return ``identity.metadata.project_path`` for a journey, if configured."""
    row = api.read(
        "SELECT metadata FROM identity WHERE layer = 'journey' AND key = ?",
        (journey_id,),
    ).fetchone()
    if row is None or not row["metadata"]:
        return None
    try:
        metadata = json.loads(row["metadata"])
    except (TypeError, json.JSONDecodeError):
        return None
    project_path = metadata.get("project_path")
    if not isinstance(project_path, str) or not project_path.strip():
        return None
    return Path(project_path).expanduser().resolve()


def resolve_project_root(
    api: ExtensionAPI,
    *,
    root: str | Path | None = None,
    journey_id: str | None = None,
) -> tuple[Path, str | None]:
    """Resolve a project root.

    Explicit ``root`` wins. Otherwise the extension reads the active
    journey's ``project_path`` metadata. CLI commands default to the
    ``maestro`` journey so the hello-world dogfood path is low-friction.
    """
    if root is not None:
        return Path(root).expanduser().resolve(), journey_id

    target_journey = journey_id or DEFAULT_JOURNEY
    project_path = project_path_for_journey(api, target_journey)
    if project_path is None:
        raise ProjectResolutionError(
            f"journey '{target_journey}' has no project_path configured; "
            "pass --root PATH or run: python -m memory journey set-path "
            f"{target_journey} /path/to/project"
        )
    return project_path, target_journey
