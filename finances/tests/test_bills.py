"""Tests for the recurring bills CRUD path (US-06)."""

from __future__ import annotations

import pytest

from src.cli.bills import cmd_bills
from src.store import list_active_bills
from src.store_writes import create_bill, deactivate_bill


# --- store_writes -------------------------------------------------------


def test_create_bill_persists_active(finances_api):
    bill_id = create_bill(
        finances_api,
        name="Rent",
        entity="personal",
        category="fixed",
        amount=-1500,
        day_of_month=5,
    )
    bills = list_active_bills(finances_api)
    assert len(bills) == 1
    assert bills[0].id == bill_id
    assert bills[0].name == "Rent"
    assert bills[0].amount == -1500
    assert bills[0].active is True


def test_create_bill_auto_flips_positive_amount(finances_api):
    """Expenses are stored negative by convention; positive inputs are
    silently flipped so callers that forget the convention still produce
    correct runway calculations."""
    create_bill(
        finances_api,
        name="Insurance",
        entity="personal",
        category="fixed",
        amount=200,  # positive on purpose
    )
    assert list_active_bills(finances_api)[0].amount == -200


def test_create_bill_rejects_invalid_entity(finances_api):
    with pytest.raises(ValueError, match="invalid entity"):
        create_bill(
            finances_api,
            name="X",
            entity="charity",
            category="fixed",
            amount=-100,
        )


def test_create_bill_rejects_invalid_category(finances_api):
    with pytest.raises(ValueError, match="invalid category"):
        create_bill(
            finances_api,
            name="X",
            entity="personal",
            category="luxury",
            amount=-100,
        )


def test_deactivate_bill_toggles_active_flag(finances_api):
    bill_id = create_bill(
        finances_api, name="Gym", entity="personal", category="variable", amount=-100
    )
    changed = deactivate_bill(finances_api, bill_id)
    assert changed is True
    # No longer in active list.
    assert list_active_bills(finances_api) == []
    # Row preserved.
    rows = finances_api.read(
        "SELECT id, active FROM ext_finances_recurring_bills"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["active"] == 0


def test_deactivate_bill_returns_false_on_missing_id(finances_api):
    assert deactivate_bill(finances_api, "ghost") is False


# --- CLI: bills ----------------------------------------------------------


def test_bills_list_empty(finances_api, capsys):
    rc = cmd_bills(finances_api, [])
    assert rc == 0
    assert "(no active bills)" in capsys.readouterr().out


def test_bills_list_shows_totals(finances_api, capsys):
    create_bill(
        finances_api, name="Rent", entity="personal", category="fixed", amount=-1500
    )
    create_bill(
        finances_api, name="Office", entity="business", category="fixed", amount=-2000
    )
    create_bill(
        finances_api, name="Streaming", entity="personal", category="variable", amount=-30
    )

    rc = cmd_bills(finances_api, ["list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Rent" in out and "Office" in out and "Streaming" in out
    # Totals shown.
    assert "Active total (personal):" in out
    assert "Active total (business):" in out
    assert "Active total:" in out


def test_bills_list_include_inactive(finances_api, capsys):
    bill_id = create_bill(
        finances_api, name="OldGym", entity="personal", category="variable", amount=-100
    )
    deactivate_bill(finances_api, bill_id)
    capsys.readouterr()

    rc = cmd_bills(finances_api, ["list", "--include-inactive"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "OldGym" in out
    # Inactive flag visible.
    assert "—" in out  # the inactive marker


def test_bills_add_happy_path(finances_api, capsys):
    rc = cmd_bills(
        finances_api,
        [
            "add",
            "--name", "Internet",
            "--entity", "personal",
            "--category", "fixed",
            "--amount", "120",
            "--day-of-month", "15",
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "added bill" in out
    bills = list_active_bills(finances_api)
    assert len(bills) == 1
    assert bills[0].name == "Internet"
    assert bills[0].day_of_month == 15


def test_bills_add_missing_required_flag(finances_api, capsys):
    rc = cmd_bills(finances_api, ["add", "--name", "Incomplete"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "missing required flag" in out


def test_bills_remove_deactivates(finances_api, capsys):
    bill_id = create_bill(
        finances_api, name="X", entity="personal", category="fixed", amount=-50
    )
    rc = cmd_bills(finances_api, ["remove", bill_id])
    out = capsys.readouterr().out
    assert rc == 0
    assert "deactivated" in out
    assert list_active_bills(finances_api) == []


def test_bills_remove_unknown_id(finances_api, capsys):
    rc = cmd_bills(finances_api, ["remove", "ghost"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "no bill with id" in out


def test_bills_help_alias(finances_api, capsys):
    rc = cmd_bills(finances_api, ["--help"])
    assert rc == 0
    assert "usage:" in capsys.readouterr().out
