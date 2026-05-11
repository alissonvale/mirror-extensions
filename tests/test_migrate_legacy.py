"""Tests for the legacy-data migration (US-11).

These tests run the migration end to end against a synthetic legacy
database. The real ``~/.espelho/memoria.db`` is never touched by
automated tests; a smoke step against it is performed manually after
the implementation lands and documented in the user story.
"""

from __future__ import annotations

import sqlite3

import pytest

from src.migrate_legacy import (
    LEGACY_TABLE_MAP,
    LegacyMigrationError,
    migrate_legacy,
)

from tests.conftest import LEGACY_FIXTURE_COUNTS


def _new_table_count(api, table: str) -> int:
    return api.read(f"SELECT count(*) AS c FROM {table}").fetchone()["c"]


# --- Happy path -----------------------------------------------------------


def test_dry_run_reports_counts_without_writing(finances_api, legacy_db):
    result = migrate_legacy(finances_api, source=legacy_db, dry_run=True)

    assert result.dry_run is True
    counts = {t.table: t.imported for t in result.tables}
    assert counts == LEGACY_FIXTURE_COUNTS
    assert result.total_imported == sum(LEGACY_FIXTURE_COUNTS.values())

    # Nothing was written.
    for table in LEGACY_FIXTURE_COUNTS:
        assert _new_table_count(finances_api, table) == 0


def test_real_run_imports_expected_counts(finances_api, legacy_db):
    result = migrate_legacy(finances_api, source=legacy_db, dry_run=False)

    assert result.dry_run is False
    counts = {t.table: t.imported for t in result.tables}
    assert counts == LEGACY_FIXTURE_COUNTS

    for table, expected in LEGACY_FIXTURE_COUNTS.items():
        assert _new_table_count(finances_api, table) == expected


def test_imported_rows_preserve_legacy_column_values(finances_api, legacy_db):
    """Spot-check a few rows column-by-column to confirm the copy is faithful."""
    migrate_legacy(finances_api, source=legacy_db, dry_run=False)

    # Account.
    row = finances_api.read(
        "SELECT * FROM ext_finances_accounts WHERE id = 'acc00001'"
    ).fetchone()
    assert row["name"] == "Test Checking"
    assert row["bank"] == "TestBank"
    assert row["type"] == "checking"
    assert row["entity"] == "personal"
    assert row["liquidity"] == "liquid"
    assert row["opening_balance"] == 0.0

    # Transaction with a category.
    row = finances_api.read(
        "SELECT * FROM ext_finances_transactions WHERE id = 'txn00002'"
    ).fetchone()
    assert row["account_id"] == "acc00001"
    assert row["amount"] == -123.45
    assert row["type"] == "debit"
    assert row["category_id"] == "cat00001"
    assert row["fit_id"] == "fit-2"

    # Snapshot.
    row = finances_api.read(
        "SELECT * FROM ext_finances_balance_snapshots WHERE id = 'snp00002'"
    ).fetchone()
    assert row["account_id"] == "acc00003"
    assert row["balance"] == 8500.0
    assert row["source"] == "ofx"

    # Recurring bill (inactive).
    row = finances_api.read(
        "SELECT * FROM ext_finances_recurring_bills WHERE id = 'bil00002'"
    ).fetchone()
    assert row["active"] == 0


def test_foreign_keys_resolve_after_migration(finances_api, legacy_db):
    """Every transaction.account_id resolves to an account row."""
    migrate_legacy(finances_api, source=legacy_db, dry_run=False)

    dangling = finances_api.read(
        "SELECT count(*) AS c FROM ext_finances_transactions t "
        "WHERE NOT EXISTS (SELECT 1 FROM ext_finances_accounts a "
        "                   WHERE a.id = t.account_id)"
    ).fetchone()["c"]
    assert dangling == 0


# --- Idempotence ---------------------------------------------------------


def test_running_twice_imports_zero_on_second_run(finances_api, legacy_db):
    first = migrate_legacy(finances_api, source=legacy_db, dry_run=False)
    second = migrate_legacy(finances_api, source=legacy_db, dry_run=False)

    assert first.total_imported == sum(LEGACY_FIXTURE_COUNTS.values())
    assert second.total_imported == 0
    # Each table reports its row count as 'skipped'.
    for table_result in second.tables:
        assert table_result.imported == 0
        assert table_result.skipped == LEGACY_FIXTURE_COUNTS[table_result.table]


def test_dry_run_after_real_run_reports_zero(finances_api, legacy_db):
    migrate_legacy(finances_api, source=legacy_db, dry_run=False)
    dry = migrate_legacy(finances_api, source=legacy_db, dry_run=True)
    assert dry.total_imported == 0


def test_partial_state_is_topped_up(finances_api, legacy_db):
    """If only some rows exist already, the migration imports just the rest."""
    migrate_legacy(finances_api, source=legacy_db, dry_run=False)
    # Delete one account and three transactions; the deleted txns first to keep FKs.
    finances_api.execute("DELETE FROM ext_finances_transactions WHERE id = 'txn00001'")
    finances_api.execute("DELETE FROM ext_finances_transactions WHERE id = 'txn00002'")
    finances_api.execute("DELETE FROM ext_finances_balance_snapshots WHERE account_id = 'acc00001'")
    finances_api.execute("DELETE FROM ext_finances_accounts WHERE id = 'acc00001'")
    finances_api.commit()

    result = migrate_legacy(finances_api, source=legacy_db, dry_run=False)
    by_table = {t.table: t for t in result.tables}
    assert by_table["ext_finances_accounts"].imported == 1
    assert by_table["ext_finances_transactions"].imported == 2
    assert by_table["ext_finances_balance_snapshots"].imported == 1
    # All rows now back in place.
    for table, expected in LEGACY_FIXTURE_COUNTS.items():
        assert _new_table_count(finances_api, table) == expected


# --- Failure modes -------------------------------------------------------


def test_missing_source_raises_clean_error(finances_api, tmp_path):
    with pytest.raises(LegacyMigrationError) as excinfo:
        migrate_legacy(finances_api, source=tmp_path / "does-not-exist.db")
    assert "not found" in str(excinfo.value)


def test_non_sqlite_source_raises_clean_error(finances_api, tmp_path):
    bogus = tmp_path / "not-a-db.txt"
    bogus.write_text("this is not a sqlite file")
    with pytest.raises(LegacyMigrationError) as excinfo:
        migrate_legacy(finances_api, source=bogus)
    # Either 'not a valid SQLite file' (from our error path) or the SQLite
    # message about an unknown header — both are acceptable.
    msg = str(excinfo.value).lower()
    assert "sqlite" in msg or "valid" in msg


def test_legacy_missing_table_raises_naming_what_is_missing(finances_api, tmp_path):
    partial = tmp_path / "partial.db"
    conn = sqlite3.connect(str(partial))
    try:
        conn.execute(
            "CREATE TABLE eco_accounts (id TEXT PRIMARY KEY, name TEXT NOT NULL, "
            "bank TEXT, agency TEXT, account_number TEXT, type TEXT NOT NULL, "
            "entity TEXT NOT NULL, opening_balance REAL NOT NULL DEFAULT 0, "
            "opening_date TEXT NOT NULL, created_at TEXT NOT NULL, metadata TEXT, "
            "liquidity TEXT NOT NULL DEFAULT 'liquid')"
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(LegacyMigrationError) as excinfo:
        migrate_legacy(finances_api, source=partial)
    msg = str(excinfo.value)
    assert "missing" in msg.lower()
    for missing in ("eco_categories", "eco_transactions", "eco_balance_snapshots", "eco_recurring_bills"):
        assert missing in msg


def test_orphan_fk_aborts_migration_with_clean_state(finances_api, tmp_path):
    """A transaction pointing at a non-existent account triggers full rollback."""
    bad = tmp_path / "bad.db"
    conn = sqlite3.connect(str(bad))
    try:
        # Same schema as legacy_seed.sql but with one orphan transaction.
        conn.executescript(
            (tmp_path.parent / "tests" / "fixtures" / "legacy_seed.sql").read_text()
            if (tmp_path.parent / "tests" / "fixtures" / "legacy_seed.sql").exists()
            else _inline_minimal_legacy_schema()
        )
        conn.execute(
            "INSERT INTO eco_transactions VALUES "
            "('orphan01', 'NO_SUCH_ACCOUNT', '2026-01-01', 'orphan', NULL, "
            " -10.0, 'debit', NULL, NULL, NULL, '2026-01-01T00:00:00Z', NULL)"
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(Exception):  # noqa: BLE001 — sqlite3.IntegrityError underneath
        migrate_legacy(finances_api, source=bad, dry_run=False)

    # Destination must be untouched by the failed run.
    for table in LEGACY_FIXTURE_COUNTS:
        assert _new_table_count(finances_api, table) == 0


def _inline_minimal_legacy_schema() -> str:
    """Fallback when the on-disk fixture file is not addressable from tmp_path."""
    from pathlib import Path
    fixtures = Path(__file__).parent / "fixtures" / "legacy_seed.sql"
    return fixtures.read_text(encoding="utf-8")


# --- Table mapping invariants --------------------------------------------


def test_table_map_covers_every_legacy_table():
    """Defensive: if the legacy schema grows, the map must grow too."""
    legacy_tables = {legacy for legacy, _, _ in LEGACY_TABLE_MAP}
    expected = {
        "eco_accounts",
        "eco_categories",
        "eco_balance_snapshots",
        "eco_transactions",
        "eco_recurring_bills",
    }
    assert legacy_tables == expected


def test_table_map_order_respects_fk_dependencies():
    """accounts must come before snapshots and transactions; categories before transactions."""
    order = [new for _, new, _ in LEGACY_TABLE_MAP]
    assert order.index("ext_finances_accounts") < order.index("ext_finances_balance_snapshots")
    assert order.index("ext_finances_accounts") < order.index("ext_finances_transactions")
    assert order.index("ext_finances_categories") < order.index("ext_finances_transactions")
