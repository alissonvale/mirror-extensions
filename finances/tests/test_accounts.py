"""Tests for the accounts CRUD path (US-01)."""

from __future__ import annotations

import pytest

from src.cli.accounts import cmd_accounts
from src.store import get_latest_snapshot, list_accounts
from src.store_writes import create_account


# --- store_writes.create_account -----------------------------------------


def test_create_account_inserts_row_and_opening_snapshot(finances_api):
    account_id = create_account(
        finances_api,
        name="Personal Checking",
        type="checking",
        entity="personal",
        opening_balance=1000.0,
        opening_date="2026-05-01",
        bank="BankA",
    )

    accounts = list_accounts(finances_api)
    assert len(accounts) == 1
    assert accounts[0].id == account_id
    assert accounts[0].name == "Personal Checking"
    assert accounts[0].opening_balance == 1000.0

    snap = get_latest_snapshot(finances_api, account_id)
    assert snap is not None
    assert snap.balance == 1000.0
    assert snap.source == "opening"
    assert snap.date == "2026-05-01"


def test_create_account_defaults_opening_date_to_today(finances_api):
    create_account(
        finances_api,
        name="No Date",
        type="checking",
        entity="personal",
    )
    snap = get_latest_snapshot(finances_api, list_accounts(finances_api)[0].id)
    # ISO date format YYYY-MM-DD
    assert len(snap.date) == 10
    assert snap.date[4] == "-" and snap.date[7] == "-"


def test_create_account_rejects_invalid_type(finances_api):
    with pytest.raises(ValueError, match="invalid type"):
        create_account(
            finances_api,
            name="Bad",
            type="wallet",
            entity="personal",
        )


def test_create_account_rejects_invalid_entity(finances_api):
    with pytest.raises(ValueError, match="invalid entity"):
        create_account(
            finances_api,
            name="Bad",
            type="checking",
            entity="public",
        )


def test_create_account_rejects_invalid_liquidity(finances_api):
    with pytest.raises(ValueError, match="invalid liquidity"):
        create_account(
            finances_api,
            name="Bad",
            type="checking",
            entity="personal",
            liquidity="frozen",
        )


def test_create_account_uses_atomic_transaction(finances_api):
    """Both the account row and the opening snapshot must land together
    (or neither, but here both is the success case)."""
    create_account(
        finances_api,
        name="Atomic",
        type="checking",
        entity="personal",
        opening_balance=42.0,
    )
    # Exactly one account, exactly one snapshot for it.
    account_count = finances_api.read(
        "SELECT count(*) AS c FROM ext_finances_accounts"
    ).fetchone()["c"]
    snap_count = finances_api.read(
        "SELECT count(*) AS c FROM ext_finances_balance_snapshots"
    ).fetchone()["c"]
    assert account_count == 1
    assert snap_count == 1


# --- CLI: accounts list --------------------------------------------------


def test_accounts_list_on_empty_db(finances_api, capsys):
    rc = cmd_accounts(finances_api, [])
    assert rc == 0
    assert "(no accounts)" in capsys.readouterr().out


def test_accounts_list_shows_registered_accounts(finances_api, capsys):
    create_account(
        finances_api,
        name="Personal Checking",
        type="checking",
        entity="personal",
        opening_balance=500,
    )
    create_account(
        finances_api,
        name="Business Reserve",
        type="savings",
        entity="business",
        opening_balance=20000,
        liquidity="semi_liquid",
    )

    rc = cmd_accounts(finances_api, ["list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Personal Checking" in out
    assert "Business Reserve" in out
    assert "personal" in out
    assert "business" in out


def test_accounts_list_filters_by_entity(finances_api, capsys):
    create_account(
        finances_api, name="A", type="checking", entity="personal"
    )
    create_account(
        finances_api, name="B", type="checking", entity="business"
    )

    cmd_accounts(finances_api, ["list", "--entity", "personal"])
    out = capsys.readouterr().out
    assert "Personal" not in out  # we did not name them so
    assert " A " in out or out.endswith(" R$ 0,00\n") or "A " in out
    assert "B " not in out


# --- CLI: accounts add ---------------------------------------------------


def test_accounts_add_creates_row(finances_api, capsys):
    rc = cmd_accounts(
        finances_api,
        [
            "add",
            "--name", "Test Checking",
            "--type", "checking",
            "--entity", "personal",
            "--opening-balance", "500.50",
            "--bank", "BankA",
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "added account" in out
    assert "Test Checking" in out

    accs = list_accounts(finances_api)
    assert len(accs) == 1
    assert accs[0].name == "Test Checking"
    assert accs[0].opening_balance == 500.50
    assert accs[0].bank == "BankA"


def test_accounts_add_reports_missing_required_flag(finances_api, capsys):
    rc = cmd_accounts(finances_api, ["add", "--name", "Incomplete"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "missing required flag" in out


def test_accounts_add_reports_invalid_value(finances_api, capsys):
    rc = cmd_accounts(
        finances_api,
        ["add", "--name", "X", "--type", "wallet", "--entity", "personal"],
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "invalid type" in out


def test_accounts_add_reports_unknown_flag(finances_api, capsys):
    rc = cmd_accounts(
        finances_api,
        ["add", "--name", "X", "--type", "checking", "--entity", "personal", "--rocket", "fuel"],
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "unrecognised flag" in out


def test_accounts_help_alias(finances_api, capsys):
    rc = cmd_accounts(finances_api, ["--help"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "usage:" in out
