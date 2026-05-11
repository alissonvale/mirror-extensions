"""Shared fixtures for the Maestro extension tests."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_EXTENSION_ROOT = Path(__file__).resolve().parents[1]
if str(_EXTENSION_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXTENSION_ROOT))

from memory.db.schema import SCHEMA  # noqa: E402
from memory.extensions.api import ExtensionAPI  # noqa: E402
from memory.extensions.migrations import run_migrations  # noqa: E402

MIGRATIONS_DIR = _EXTENSION_ROOT / "migrations"


@pytest.fixture
def maestro_api():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    run_migrations(conn, extension_id="maestro", migrations_dir=MIGRATIONS_DIR)
    yield ExtensionAPI(extension_id="maestro", connection=conn)
    conn.close()


def seed_journey(api: ExtensionAPI, journey_id: str, project_path: Path | None = None) -> None:
    metadata = {}
    if project_path is not None:
        metadata["project_path"] = str(project_path)
    now = datetime.now(timezone.utc).isoformat()
    api.db.execute(
        """
        INSERT INTO identity (id, layer, key, content, created_at, updated_at, metadata)
        VALUES (?, 'journey', ?, ?, ?, ?, ?)
        """,
        (
            f"journey-{journey_id}",
            journey_id,
            f"Journey {journey_id}",
            now,
            now,
            json.dumps(metadata) if metadata else None,
        ),
    )
    api.db.commit()
