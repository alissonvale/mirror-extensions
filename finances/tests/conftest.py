"""Shared fixtures for the finances extension test suite.

These fixtures construct a real ExtensionAPI bound to an in-memory
SQLite database, run the extension's migrations against it, and seed
a tiny synthetic legacy database when the test requests one.

No mocks of the mirror core: this exercises the same ``ExtensionAPI``
the loader gives the extension at runtime, so the tests catch any
real boundary problem (e.g. prefix enforcement breaking a write).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

# pytest auto-imports conftest.py before any test module. The finances
# source tree lives under ``src/`` next to this file; insert the
# extension root on sys.path so tests can ``from src.x import y``
# the same way ``extension.py`` does at runtime.
_EXTENSION_ROOT = Path(__file__).resolve().parents[1]
if str(_EXTENSION_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXTENSION_ROOT))

from memory.db.schema import SCHEMA  # noqa: E402 — provides _ext_migrations/_ext_bindings
from memory.extensions.api import ExtensionAPI  # noqa: E402
from memory.extensions.migrations import run_migrations  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MIGRATIONS_DIR = _EXTENSION_ROOT / "migrations"


@pytest.fixture
def finances_api():
    """A real ExtensionAPI bound to a fresh in-memory mirror database.

    Bootstraps the core schema (so ``_ext_migrations`` and
    ``_ext_bindings`` exist), runs the finances extension's own
    migrations, and yields an ExtensionAPI configured the way the
    runtime loader would configure it.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    run_migrations(conn, extension_id="finances", migrations_dir=MIGRATIONS_DIR)
    yield ExtensionAPI(extension_id="finances", connection=conn)
    conn.close()


@pytest.fixture
def legacy_db(tmp_path: Path) -> Path:
    """Build a small representative legacy database on disk and return its path.

    Disk-backed because the migration opens it via the SQLite URI form
    in read-only mode, which is the production path. Each test gets a
    fresh file under ``tmp_path``.
    """
    target = tmp_path / "legacy.sqlite3"
    seed = (FIXTURES_DIR / "legacy_seed.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(target))
    try:
        conn.executescript(seed)
        conn.commit()
    finally:
        conn.close()
    return target


# Expected fixture counts (per legacy_seed.sql).
LEGACY_FIXTURE_COUNTS = {
    "ext_finances_accounts": 3,
    "ext_finances_categories": 1,
    "ext_finances_balance_snapshots": 2,
    "ext_finances_transactions": 4,
    "ext_finances_recurring_bills": 2,
}
