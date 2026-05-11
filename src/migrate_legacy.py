"""Copy a legacy mirror finance dataset into the extension's tables.

The legacy data lives in a separate SQLite database (the path is
supplied by the operator at run time via ``--source``) under the
``eco_*`` table prefix. The target tables in the active mirror live
under ``ext_finances_*``.
The two schemas are column-isomorphic: this module is a pure
table-by-table copy, not an interpretation. See
``docs/user-stories/US-11-migrate-legacy-data.md`` for the user
story and ``docs/legacy-migration.md`` for the operator-facing
procedure.

The copy:

* opens the legacy database in read-only mode through the SQLite
  URI form (``file:<path>?mode=ro``) — the legacy file is never
  modified;
* runs inside a single savepoint on the destination so a partial
  failure rolls back cleanly;
* dedupes by primary key (``id``) so re-running after a successful
  run imports zero rows.

The five legacy tables are copied in dependency order:

  1. ``eco_accounts``         -> ``ext_finances_accounts``
  2. ``eco_categories``       -> ``ext_finances_categories``
  3. ``eco_balance_snapshots`` -> ``ext_finances_balance_snapshots``
  4. ``eco_transactions``     -> ``ext_finances_transactions``
  5. ``eco_recurring_bills``  -> ``ext_finances_recurring_bills``

Accounts come first because three other tables hold foreign keys to
``eco_accounts(id)``; categories come before transactions for the
same reason.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


# Each tuple: (legacy_table, new_table, comma-separated column list).
# The column list is identical on both sides; using the same string
# for both SELECT and INSERT guarantees positional alignment.
LEGACY_TABLE_MAP: list[tuple[str, str, str]] = [
    (
        "eco_accounts",
        "ext_finances_accounts",
        "id, name, bank, agency, account_number, type, entity, liquidity, "
        "opening_balance, opening_date, created_at, metadata",
    ),
    (
        "eco_categories",
        "ext_finances_categories",
        "id, name, type, created_at",
    ),
    (
        "eco_balance_snapshots",
        "ext_finances_balance_snapshots",
        "id, account_id, date, balance, source, created_at",
    ),
    (
        "eco_transactions",
        "ext_finances_transactions",
        "id, account_id, date, description, memo, amount, type, "
        "category_id, fit_id, balance_after, created_at, metadata",
    ),
    (
        "eco_recurring_bills",
        "ext_finances_recurring_bills",
        "id, name, entity, category, amount, day_of_month, notes, "
        "active, created_at",
    ),
]


@dataclass
class TableResult:
    table: str          # destination table name (ext_finances_*)
    imported: int       # rows newly inserted (or would-be-inserted on dry run)
    skipped: int        # rows already present in destination (deduplicated by id)


@dataclass
class MigrationResult:
    source: Path
    dry_run: bool
    tables: list[TableResult] = field(default_factory=list)

    @property
    def total_imported(self) -> int:
        return sum(t.imported for t in self.tables)


class LegacyMigrationError(RuntimeError):
    """Raised when the legacy source cannot be opened or is malformed."""


def _open_legacy_readonly(source: Path) -> sqlite3.Connection:
    """Open the legacy database in read-only URI mode.

    Using the SQLite URI form guarantees that even if the caller has
    write permission on the file, the connection cannot mutate it.

    ``sqlite3.connect`` is lazy: it succeeds on a path that is not a
    SQLite database and only fails on the first query. Probe the file
    with a cheap ``PRAGMA schema_version`` so the error surfaces here
    with a clear message instead of leaking later as a confusing
    ``DatabaseError`` from a downstream call.
    """
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


def _validate_legacy_tables(legacy: sqlite3.Connection) -> None:
    """Confirm every expected legacy table exists before we touch anything."""
    rows = legacy.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    present = {row["name"] for row in rows}
    missing = [
        legacy_table
        for legacy_table, _, _ in LEGACY_TABLE_MAP
        if legacy_table not in present
    ]
    if missing:
        raise LegacyMigrationError(
            "legacy database is missing required tables: " + ", ".join(missing)
        )


def _existing_ids(api: "ExtensionAPI", new_table: str) -> set[str]:
    rows = api.read(f"SELECT id FROM {new_table}").fetchall()
    return {row[0] for row in rows}


def _copy_table(
    api: "ExtensionAPI",
    legacy: sqlite3.Connection,
    legacy_table: str,
    new_table: str,
    columns: str,
    *,
    dry_run: bool,
) -> TableResult:
    """Copy one table. Returns imported + skipped counts."""
    existing = _existing_ids(api, new_table)
    column_count = columns.count(",") + 1
    placeholders = ", ".join(["?"] * column_count)
    rows = legacy.execute(f"SELECT {columns} FROM {legacy_table}").fetchall()

    imported = 0
    skipped = 0
    for row in rows:
        legacy_id = row[0]  # column order starts with 'id'
        if legacy_id in existing:
            skipped += 1
            continue
        if not dry_run:
            api.execute(
                f"INSERT INTO {new_table} ({columns}) VALUES ({placeholders})",
                tuple(row),
            )
        imported += 1
    return TableResult(table=new_table, imported=imported, skipped=skipped)


def migrate_legacy(
    api: "ExtensionAPI",
    *,
    source: Path,
    dry_run: bool = False,
) -> MigrationResult:
    """Copy every legacy ``eco_*`` row missing from ``ext_finances_*``.

    Real runs execute inside a single ``api.transaction()`` savepoint:
    if any table copy fails (e.g. a foreign key the legacy data does
    not resolve, a SQLite type mismatch), the entire migration rolls
    back and nothing in the destination changes.

    Dry runs do not touch the destination — they only read both sides
    and report the count of rows that would land.

    Idempotent in both modes: a second invocation after a successful
    migration reports zero ``imported`` per table.
    """
    legacy = _open_legacy_readonly(source)
    try:
        _validate_legacy_tables(legacy)
        result = MigrationResult(source=source, dry_run=dry_run)

        if dry_run:
            # Read-only path: count outside the savepoint.
            for legacy_table, new_table, columns in LEGACY_TABLE_MAP:
                result.tables.append(
                    _copy_table(
                        api,
                        legacy,
                        legacy_table,
                        new_table,
                        columns,
                        dry_run=True,
                    )
                )
            return result

        with api.transaction():
            for legacy_table, new_table, columns in LEGACY_TABLE_MAP:
                result.tables.append(
                    _copy_table(
                        api,
                        legacy,
                        legacy_table,
                        new_table,
                        columns,
                        dry_run=False,
                    )
                )
        return result
    finally:
        legacy.close()
