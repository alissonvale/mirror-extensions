"""Tests for the read-only CLI surfaces (US-05, US-07, US-08).

These three subcommands wrap helpers that already have unit tests in
test_reports.py; here we focus on the CLI: argument parsing, filter
composition, formatting, and edge cases (empty input, unknown flag,
unknown account).
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.cli.report import cmd_report
from src.cli.runway import cmd_runway
from src.cli.transactions import cmd_transactions
from src.store import list_transactions
from src.store_writes import create_account, create_bill


def _seed_txns(api, account_id: str, rows: list[tuple[str, str, float, str]]) -> None:
    """rows: (id, date, amount, description)."""
    for tid, date, amount, desc in rows:
        api.execute(
            "INSERT INTO ext_finances_transactions "
            "(id, account_id, date, description, amount, type, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                tid,
                account_id,
                date,
                desc,
                amount,
                "credit" if amount >= 0 else "debit",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    api.commit()


# --- transactions (US-05) ------------------------------------------------


def test_transactions_empty(finances_api, capsys):
    rc = cmd_transactions(finances_api, [])
    out = capsys.readouterr().out
    assert rc == 0
    assert "(no transactions matched)" in out


def test_transactions_lists_with_totals(finances_api, capsys):
    a = create_account(finances_api, name="A", type="checking", entity="personal")
    _seed_txns(
        finances_api,
        a,
        [
            ("t1", "2026-01-10", 1000.0, "salary"),
            ("t2", "2026-01-20", -250.0, "rent"),
            ("t3", "2026-02-05", -100.0, "groceries"),
        ],
    )

    rc = cmd_transactions(finances_api, [])
    out = capsys.readouterr().out
    assert rc == 0
    assert "salary" in out and "rent" in out and "groceries" in out
    assert "Rows: 3" in out
    assert "In: R$ 1.000,00" in out
    assert "Out: R$ 350,00" in out
    assert "Net: R$ 650,00" in out


def test_transactions_filters_by_date_range(finances_api, capsys):
    a = create_account(finances_api, name="A", type="checking", entity="personal")
    _seed_txns(
        finances_api,
        a,
        [
            ("t1", "2026-01-10", 1000.0, "in-jan"),
            ("t2", "2026-02-10", 500.0, "in-feb"),
            ("t3", "2026-03-10", 800.0, "in-mar"),
        ],
    )
    cmd_transactions(finances_api, ["--from", "2026-02-01", "--to", "2026-02-28"])
    out = capsys.readouterr().out
    assert "in-feb" in out
    assert "in-jan" not in out
    assert "in-mar" not in out


def test_transactions_filters_by_description(finances_api, capsys):
    a = create_account(finances_api, name="A", type="checking", entity="personal")
    _seed_txns(
        finances_api,
        a,
        [
            ("t1", "2026-01-10", -50.0, "Grocery store"),
            ("t2", "2026-01-11", -25.0, "Coffee shop"),
        ],
    )
    cmd_transactions(finances_api, ["--description", "GROCERY"])
    out = capsys.readouterr().out
    assert "Grocery store" in out
    assert "Coffee shop" not in out


def test_transactions_unknown_flag(finances_api, capsys):
    rc = cmd_transactions(finances_api, ["--nope", "x"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "unrecognised flag" in out


def test_transactions_filters_compose_correctly(finances_api):
    a = create_account(finances_api, name="A", type="checking", entity="personal")
    b = create_account(finances_api, name="B", type="checking", entity="business")
    _seed_txns(finances_api, a, [("t1", "2026-01-10", 100.0, "x"), ("t2", "2026-01-20", -50.0, "y")])
    _seed_txns(finances_api, b, [("t3", "2026-01-15", 999.0, "z")])
    rows = list_transactions(finances_api, account_id=a, type="credit")
    assert [t.id for t in rows] == ["t1"]


# --- report (US-08) -----------------------------------------------------


def test_report_empty(finances_api, capsys):
    rc = cmd_report(finances_api, [])
    out = capsys.readouterr().out
    assert rc == 0
    assert "(no transactions" in out


def test_report_groups_by_month_with_totals(finances_api, capsys):
    a = create_account(finances_api, name="A", type="checking", entity="personal")
    _seed_txns(
        finances_api,
        a,
        [
            ("t1", "2026-01-10", 1000.0, "salary"),
            ("t2", "2026-01-20", -300.0, "rent"),
            ("t3", "2026-02-10", 1000.0, "salary"),
            ("t4", "2026-02-15", -500.0, "rent"),
        ],
    )
    rc = cmd_report(finances_api, [])
    out = capsys.readouterr().out
    assert rc == 0
    assert "2026-01" in out and "2026-02" in out
    # Total row exists at the bottom.
    assert "Total" in out


def test_report_unknown_flag(finances_api, capsys):
    rc = cmd_report(finances_api, ["--bogus", "x"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "unrecognised flag" in out


# --- runway (US-07) -----------------------------------------------------


def test_runway_no_accounts(finances_api, capsys):
    rc = cmd_runway(finances_api, [])
    out = capsys.readouterr().out
    assert rc == 0
    assert "no accounts" in out


def test_runway_with_bills_source(finances_api, capsys):
    a = create_account(
        finances_api, name="A", type="checking", entity="personal",
        opening_balance=10000.0, opening_date="2026-01-01",
    )
    create_bill(
        finances_api, name="Rent", entity="personal", category="fixed", amount=-1000
    )
    rc = cmd_runway(finances_api, [])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Burn (bills):" in out
    # 10000 / 1000 = 10.0 months
    assert "10.0 months" in out


def test_runway_with_history_source_fallback(finances_api, capsys):
    a = create_account(
        finances_api, name="A", type="checking", entity="personal",
        opening_balance=10000.0, opening_date="2026-01-01",
    )
    _seed_txns(
        finances_api,
        a,
        [
            ("t1", "2026-01-15", 1000.0, "in"),
            ("t2", "2026-01-25", -2000.0, "out"),
        ],
    )
    rc = cmd_runway(finances_api, ["--burn-source", "history"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Burn (history" in out


def test_runway_invalid_burn_source(finances_api, capsys):
    create_account(finances_api, name="A", type="checking", entity="personal")
    rc = cmd_runway(finances_api, ["--burn-source", "magic"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "must be" in out


def test_runway_invalid_liquidity(finances_api, capsys):
    create_account(finances_api, name="A", type="checking", entity="personal")
    rc = cmd_runway(finances_api, ["--include-liquidity", "liquid,frozen"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "not a valid liquidity bucket" in out


def test_runway_unknown_flag(finances_api, capsys):
    rc = cmd_runway(finances_api, ["--nope", "x"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "unrecognised flag" in out
