"""Copy a legacy mirror `testimonials` table into ext_testimonials_records.

Same shape as the finances legacy migration: read-only ATTACH on the
source, savepoint-wrapped row-by-row copy, dedup by primary key so
re-runs are no-ops. The legacy `testimonials` columns map 1:1 to the
new table (only the prefix changes), including the embedding BLOB.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


class LegacyMigrationError(RuntimeError):
    """Raised when the legacy source cannot be opened or is malformed."""


_LEGACY_TABLE = "testimonials"
_NEW_TABLE = "ext_testimonials_records"
_COLUMNS = (
    "id, author_name, content, source, product, highlight, tags, received_at, created_at, embedding"
)


@dataclass
class MigrationResult:
    source: Path
    dry_run: bool
    imported: int = 0
    skipped: int = 0

    @property
    def total(self) -> int:
        return self.imported + self.skipped


def _open_legacy_readonly(source: Path) -> sqlite3.Connection:
    if not source.exists():
        raise LegacyMigrationError(f"legacy database not found: {source}")
    try:
        conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        conn.execute("PRAGMA schema_version").fetchone()
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as exc:
        raise LegacyMigrationError(
            f"legacy database is not a valid SQLite file: {source} ({exc})"
        ) from exc
    conn.row_factory = sqlite3.Row
    return conn


def _validate_legacy(legacy: sqlite3.Connection) -> None:
    rows = legacy.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    if not any(row["name"] == _LEGACY_TABLE for row in rows):
        raise LegacyMigrationError(f"legacy database is missing required table: {_LEGACY_TABLE}")


def migrate_legacy(
    api: ExtensionAPI,
    *,
    source: Path,
    dry_run: bool = False,
) -> MigrationResult:
    """Copy every legacy testimonial row missing from the new table.

    Embeddings are copied verbatim: the legacy mirror used the same
    OpenAI text-embedding-3-small model the framework's ``api.embed()``
    uses today, so the existing vectors remain valid for cosine search
    without re-computing.
    """
    legacy = _open_legacy_readonly(source)
    try:
        _validate_legacy(legacy)
        existing_ids = {row[0] for row in api.read(f"SELECT id FROM {_NEW_TABLE}").fetchall()}
        rows = legacy.execute(f"SELECT {_COLUMNS} FROM {_LEGACY_TABLE}").fetchall()

        result = MigrationResult(source=source, dry_run=dry_run)
        column_count = _COLUMNS.count(",") + 1
        placeholders = ", ".join(["?"] * column_count)

        if dry_run:
            for row in rows:
                if row[0] in existing_ids:
                    result.skipped += 1
                else:
                    result.imported += 1
            return result

        with api.transaction():
            for row in rows:
                if row[0] in existing_ids:
                    result.skipped += 1
                    continue
                api.execute(
                    f"INSERT INTO {_NEW_TABLE} ({_COLUMNS}) VALUES ({placeholders})",
                    tuple(row),
                )
                result.imported += 1
        return result
    finally:
        legacy.close()
