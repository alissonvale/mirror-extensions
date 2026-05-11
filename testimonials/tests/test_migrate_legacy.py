"""Tests for the legacy testimonial migration (US-04)."""

from __future__ import annotations

import sqlite3

import pytest
from src.migrate_legacy import LegacyMigrationError, migrate_legacy


def _count(api):
    return api.read("SELECT count(*) AS c FROM ext_testimonials_records").fetchone()["c"]


def test_dry_run_reports_counts_without_writing(testimonials_api, legacy_db):
    result = migrate_legacy(testimonials_api, source=legacy_db, dry_run=True)
    assert result.dry_run is True
    assert result.imported == 5
    assert result.skipped == 0
    assert _count(testimonials_api) == 0


def test_real_run_imports_all_rows_with_embeddings(testimonials_api, legacy_db):
    result = migrate_legacy(testimonials_api, source=legacy_db)
    assert result.imported == 5
    assert _count(testimonials_api) == 5

    rows = testimonials_api.read(
        "SELECT id, author_name, embedding FROM ext_testimonials_records ORDER BY id"
    ).fetchall()
    assert [r["id"] for r in rows] == [f"leg0000{i}" for i in range(1, 6)]
    # Embeddings copied verbatim; 1536 float32 = 6144 bytes.
    for row in rows:
        assert row["embedding"] is not None
        assert len(row["embedding"]) == 6144


def test_running_twice_is_idempotent(testimonials_api, legacy_db):
    first = migrate_legacy(testimonials_api, source=legacy_db)
    second = migrate_legacy(testimonials_api, source=legacy_db)
    assert first.imported == 5
    assert second.imported == 0
    assert second.skipped == 5
    assert _count(testimonials_api) == 5


def test_partial_state_is_topped_up(testimonials_api, legacy_db):
    migrate_legacy(testimonials_api, source=legacy_db)
    testimonials_api.execute("DELETE FROM ext_testimonials_records WHERE id = 'leg00001'")
    testimonials_api.commit()
    result = migrate_legacy(testimonials_api, source=legacy_db)
    assert result.imported == 1
    assert result.skipped == 4


def test_dry_run_after_real_run_reports_zero(testimonials_api, legacy_db):
    migrate_legacy(testimonials_api, source=legacy_db)
    dry = migrate_legacy(testimonials_api, source=legacy_db, dry_run=True)
    assert dry.imported == 0
    assert dry.skipped == 5


# --- failure modes ------------------------------------------------------


def test_missing_source_raises(testimonials_api, tmp_path):
    with pytest.raises(LegacyMigrationError, match="not found"):
        migrate_legacy(testimonials_api, source=tmp_path / "nope.db")


def test_non_sqlite_source_raises(testimonials_api, tmp_path):
    bogus = tmp_path / "bogus.txt"
    bogus.write_text("not a database")
    with pytest.raises(LegacyMigrationError):
        migrate_legacy(testimonials_api, source=bogus)


def test_legacy_missing_table_raises(testimonials_api, tmp_path):
    db_path = tmp_path / "empty.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE other (id TEXT)")
    conn.commit()
    conn.close()

    with pytest.raises(LegacyMigrationError, match="missing required table"):
        migrate_legacy(testimonials_api, source=db_path)


def test_imported_rows_keep_all_columns(testimonials_api, legacy_db):
    migrate_legacy(testimonials_api, source=legacy_db)
    row = testimonials_api.read(
        "SELECT * FROM ext_testimonials_records WHERE id = 'leg00001'"
    ).fetchone()
    assert row["author_name"] == "Alice"
    assert row["content"] == "Loved the workshop, learned a lot."
    assert row["source"] == "email"
    assert row["product"] == "Workshop"
    assert row["highlight"] == "Loved the workshop"
    assert row["received_at"] == "2026-01-15"
    # Tags survived the column-for-column copy as JSON text.
    assert row["tags"] == '["workshop","clarity"]'
