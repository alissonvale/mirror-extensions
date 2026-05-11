"""Unit tests for the report helpers (US-10)."""

from __future__ import annotations

import math

import pytest

from src.models import Account, BalanceSnapshot, RecurringBill, Transaction
from src.reports import (
    BalanceTotals,
    MonthlyFlow,
    calculate_runway,
    consolidated_balance,
    financial_context_text,
    monthly_burn_from_bills,
    monthly_burn_from_history,
    summarize_by_month,
)


# --- consolidated_balance ------------------------------------------------


def _acc(id_, balance, liquidity="liquid"):
    return Account(
        id=id_,
        name=f"acc-{id_}",
        type="checking",
        entity="personal",
        liquidity=liquidity,
        opening_balance=balance,
        opening_date="2026-01-01",
    )


def _snap(account_id, balance, date="2026-05-01"):
    return BalanceSnapshot(
        id=f"snap-{account_id}",
        account_id=account_id,
        date=date,
        balance=balance,
    )


def test_consolidated_balance_sums_by_bucket():
    accounts = [
        _acc("a", 1000, "liquid"),
        _acc("b", 5000, "liquid"),
        _acc("c", 20000, "semi_liquid"),
        _acc("d", 300000, "illiquid"),
    ]
    snapshots = {acc.id: None for acc in accounts}

    totals = consolidated_balance(accounts, snapshots)
    assert totals.liquid == 6000
    assert totals.semi_liquid == 20000
    assert totals.illiquid == 300000
    assert totals.total == 326000


def test_consolidated_balance_prefers_snapshot_over_opening():
    accounts = [_acc("a", 1000, "liquid")]
    snapshots = {"a": _snap("a", 9999)}

    totals = consolidated_balance(accounts, snapshots)
    assert totals.liquid == 9999


def test_consolidated_balance_with_no_accounts():
    totals = consolidated_balance([], {})
    assert totals == BalanceTotals(liquid=0, semi_liquid=0, illiquid=0)


# --- summarize_by_month --------------------------------------------------


def _txn(date, amount, type_=None):
    return Transaction(
        id=f"t-{date}-{amount}",
        account_id="acc",
        date=date,
        description="x",
        amount=amount,
        type=type_ or ("credit" if amount >= 0 else "debit"),
    )


def test_summarize_by_month_groups_and_sorts():
    txns = [
        _txn("2026-03-10", 500),
        _txn("2026-03-20", -200),
        _txn("2026-01-15", 100),
        _txn("2026-02-05", -50),
    ]
    out = summarize_by_month(txns)
    assert [m.month for m in out] == ["2026-01", "2026-02", "2026-03"]
    assert out[0].income == 100 and out[0].expense == 0
    assert out[1].income == 0 and out[1].expense == -50
    assert out[2].income == 500 and out[2].expense == -200
    assert out[2].net == 300


def test_summarize_by_month_empty():
    assert summarize_by_month([]) == []


# --- burn helpers --------------------------------------------------------


def test_monthly_burn_from_bills_negative():
    bills = [
        RecurringBill(id="b1", name="rent", entity="personal", category="fixed", amount=-1500),
        RecurringBill(id="b2", name="gym", entity="personal", category="variable", amount=-100),
    ]
    assert monthly_burn_from_bills(bills) == -1600


def test_monthly_burn_from_bills_empty_returns_none():
    assert monthly_burn_from_bills([]) is None


def test_monthly_burn_from_history_averages_recent():
    flows = [
        MonthlyFlow("2026-01", 1000, -1500),  # net -500
        MonthlyFlow("2026-02", 1000, -1500),  # net -500
        MonthlyFlow("2026-03", 1000, -2000),  # net -1000
        MonthlyFlow("2026-04", 1000, -1700),  # net -700  <-
        MonthlyFlow("2026-05", 1000, -1400),  # net -400  <-
        MonthlyFlow("2026-06", 1000, -1300),  # net -300  <-
    ]
    avg = monthly_burn_from_history(flows, lookback_months=3)
    assert avg == pytest.approx(-(700 + 400 + 300) / 3)


def test_monthly_burn_from_history_empty_returns_none():
    assert monthly_burn_from_history([]) is None


# --- calculate_runway ----------------------------------------------------


def test_runway_basic():
    assert calculate_runway(10000, -1000) == 10.0


def test_runway_with_none_burn():
    assert calculate_runway(10000, None) is None


def test_runway_with_positive_burn_is_unbounded():
    assert calculate_runway(10000, 500) == math.inf


def test_runway_with_negative_balance_is_zero():
    assert calculate_runway(-500, -1000) == 0


# --- financial_context_text (uses ExtensionAPI from fixture) --------------


def test_financial_context_text_returns_none_on_empty_db(finances_api):
    assert financial_context_text(finances_api) is None


def test_financial_context_text_renders_after_legacy_migration(
    finances_api, legacy_db
):
    """End-to-end: migrate the synthetic legacy seed and confirm the
    composed text has every section we expect."""
    from src.migrate_legacy import migrate_legacy

    migrate_legacy(finances_api, source=legacy_db, dry_run=False)
    text = financial_context_text(finances_api)
    assert text is not None
    assert "Liquid (immediately available)" in text
    assert "Cash flow (last 6 months)" in text
    assert "Burn & runway" in text
    # The seed has rent as the only active bill, R$ 1,500.00 negative.
    assert "Monthly burn (from bills): R$ 1.500,00" in text
    # The seed has three personal+business accounts, two of which have
    # snapshots; the third uses its opening balance.
    assert "Test Checking" in text
    assert "Test Business" in text


def test_financial_context_text_renders_after_real_migration(
    finances_api, legacy_db
):
    """Smoke-shape test: enough numbers to know the formatter works."""
    from src.migrate_legacy import migrate_legacy

    migrate_legacy(finances_api, source=legacy_db, dry_run=False)
    text = financial_context_text(finances_api)
    assert text is not None
    # Header structure.
    sections = ["Liquid (immediately available)", "Cash flow", "Burn"]
    for s in sections:
        assert s in text, f"missing section '{s}' in output"
    # Money formatting uses BRL convention with comma decimal.
    assert "R$ " in text
    # No raw Python repr leakage.
    assert "<" not in text and ">" not in text
