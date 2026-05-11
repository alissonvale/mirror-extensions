"""Tests for the balance and snapshot CLI paths (US-02)."""

from __future__ import annotations

from src.cli.balance import cmd_balance, cmd_snapshot
from src.store import get_latest_snapshot
from src.store_writes import create_account, record_snapshot


# --- store_writes.record_snapshot ----------------------------------------


def test_record_snapshot_inserts_row(finances_api):
    account_id = create_account(
        finances_api, name="A", type="checking", entity="personal",
        opening_date="2026-01-01",
    )
    snap_id = record_snapshot(
        finances_api,
        account_id=account_id,
        date="2030-05-10",
        balance=987.65,
    )
    snap = get_latest_snapshot(finances_api, account_id)
    assert snap.id == snap_id
    assert snap.balance == 987.65
    assert snap.date == "2030-05-10"
    assert snap.source == "manual"


def test_record_snapshot_rejects_invalid_source(finances_api):
    account_id = create_account(
        finances_api, name="A", type="checking", entity="personal"
    )
    import pytest
    with pytest.raises(ValueError, match="invalid source"):
        record_snapshot(
            finances_api,
            account_id=account_id,
            date="2030-05-10",
            balance=10.0,
            source="vibes",
        )


# --- CLI: balance --------------------------------------------------------


def test_balance_on_empty_db(finances_api, capsys):
    rc = cmd_balance(finances_api, [])
    assert rc == 0
    assert "(no accounts)" in capsys.readouterr().out


def test_balance_lists_all_accounts_with_latest_snapshot(finances_api, capsys):
    a = create_account(
        finances_api, name="A", type="checking", entity="personal",
        opening_balance=100,
        opening_date="2026-01-01",
    )
    record_snapshot(finances_api, account_id=a, date="2030-05-10", balance=250)

    rc = cmd_balance(finances_api, [])
    out = capsys.readouterr().out
    assert rc == 0
    # Latest snapshot wins over opening snap created by create_account.
    assert "R$ 250,00" in out
    assert "2030-05-10" in out
    assert "[manual]" in out


def test_balance_single_account(finances_api, capsys):
    a = create_account(
        finances_api, name="A", type="checking", entity="personal"
    )
    b = create_account(
        finances_api, name="B", type="checking", entity="business"
    )

    rc = cmd_balance(finances_api, [a])
    out = capsys.readouterr().out
    assert rc == 0
    assert "A (personal" in out
    assert "B (business" not in out


def test_balance_unknown_account_id(finances_api, capsys):
    create_account(finances_api, name="A", type="checking", entity="personal")
    rc = cmd_balance(finances_api, ["bogus"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "no account with id" in out


# --- CLI: snapshot -------------------------------------------------------


def test_snapshot_requires_three_positional_args(finances_api, capsys):
    rc = cmd_snapshot(finances_api, ["only-one-arg"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "requires" in out


def test_snapshot_records_when_account_exists(finances_api, capsys):
    a = create_account(
        finances_api, name="A", type="checking", entity="personal",
        opening_date="2026-01-01",
    )
    rc = cmd_snapshot(finances_api, [a, "2030-05-10", "1234.56"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "recorded snapshot" in out
    assert "R$ 1.234,56" in out
    snap = get_latest_snapshot(finances_api, a)
    assert snap.balance == 1234.56


def test_snapshot_rejects_non_numeric_balance(finances_api, capsys):
    a = create_account(finances_api, name="A", type="checking", entity="personal")
    rc = cmd_snapshot(finances_api, [a, "2026-05-10", "not-a-number"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "must be a number" in out


def test_snapshot_rejects_unknown_account(finances_api, capsys):
    rc = cmd_snapshot(finances_api, ["ghost", "2026-05-10", "100"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "no account with id" in out


def test_snapshot_custom_source(finances_api, capsys):
    a = create_account(
        finances_api, name="A", type="checking", entity="personal",
        opening_date="2026-01-01",
    )
    rc = cmd_snapshot(
        finances_api, [a, "2030-05-10", "100", "--source", "reconciliation"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    snap = get_latest_snapshot(finances_api, a)
    assert snap.source == "reconciliation"
