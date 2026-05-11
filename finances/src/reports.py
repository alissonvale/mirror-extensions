"""Aggregations over ext_finances_* data.

Three responsibilities:

  * consolidated balances per liquidity bucket, derived from each
    account's latest snapshot (or its opening balance when no
    snapshot exists yet);
  * monthly cash flow per YYYY-MM, summing transactions;
  * monthly burn (from active bills, with history as a fallback) and
    runway in months.

All helpers are pure functions over typed inputs. The text composer
``financial_context_text`` at the bottom turns those numbers into the
markdown block that the Mirror Mode provider injects.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.models import (
    Account,
    BalanceSnapshot,
    RecurringBill,
    Transaction,
)
from src.store import (
    get_latest_snapshot,
    list_accounts,
    list_active_bills,
    list_transactions,
)

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


# --- Balances ------------------------------------------------------------


@dataclass(frozen=True)
class BalanceTotals:
    liquid: float
    semi_liquid: float
    illiquid: float

    @property
    def total(self) -> float:
        return self.liquid + self.semi_liquid + self.illiquid


def consolidated_balance(
    accounts: list[Account],
    snapshots: dict[str, BalanceSnapshot | None],
) -> BalanceTotals:
    """Sum each account's current balance by liquidity bucket.

    Current balance = latest snapshot when present, otherwise the
    account's opening balance.
    """
    totals = {"liquid": 0.0, "semi_liquid": 0.0, "illiquid": 0.0}
    for acc in accounts:
        snap = snapshots.get(acc.id)
        balance = snap.balance if snap else acc.opening_balance
        bucket = acc.liquidity if acc.liquidity in totals else "liquid"
        totals[bucket] += balance
    return BalanceTotals(
        liquid=totals["liquid"],
        semi_liquid=totals["semi_liquid"],
        illiquid=totals["illiquid"],
    )


# --- Monthly cash flow ---------------------------------------------------


@dataclass(frozen=True)
class MonthlyFlow:
    month: str        # 'YYYY-MM'
    income: float     # sum of positive amounts
    expense: float    # sum of negative amounts (negative number)

    @property
    def net(self) -> float:
        return self.income + self.expense


def summarize_by_month(
    transactions: list[Transaction],
) -> list[MonthlyFlow]:
    """Group transactions by 'YYYY-MM' and sum income vs expense.

    Returned list is sorted chronologically.
    """
    by_month: dict[str, dict[str, float]] = defaultdict(
        lambda: {"income": 0.0, "expense": 0.0}
    )
    for txn in transactions:
        month = txn.date[:7]  # ISO 'YYYY-MM-DD' -> 'YYYY-MM'
        if txn.amount >= 0:
            by_month[month]["income"] += txn.amount
        else:
            by_month[month]["expense"] += txn.amount
    return [
        MonthlyFlow(month=m, income=v["income"], expense=v["expense"])
        for m, v in sorted(by_month.items())
    ]


# --- Burn and runway -----------------------------------------------------


def monthly_burn_from_bills(bills: list[RecurringBill]) -> float | None:
    """Sum active recurring bills as expected monthly burn.

    Returns a negative number (outflow). Returns None when no active
    bills exist so the caller can fall back to history.
    """
    if not bills:
        return None
    total = sum(b.amount for b in bills)
    return -abs(total)


def monthly_burn_from_history(
    monthly_flows: list[MonthlyFlow],
    *,
    lookback_months: int = 3,
) -> float | None:
    """Average net flow over the most recent ``lookback_months``.

    Returns a number that is **negative** when the user spent more
    than they earned (the convention "burn is a negative number" is
    consistent across the rest of the module). Returns None when no
    history exists.
    """
    if not monthly_flows:
        return None
    recent = monthly_flows[-lookback_months:]
    if not recent:
        return None
    avg = sum(m.net for m in recent) / len(recent)
    return avg


def calculate_runway(balance: float, burn: float | None) -> float | None:
    """Months of liquidity given ``balance`` and signed ``burn``.

    Returns:
      * ``None`` when ``burn`` is None (no signal).
      * ``math.inf`` when ``burn`` is positive (net inflow) — the
        runway is unbounded.
      * ``balance / abs(burn)`` otherwise.

    Negative balances return 0 to avoid emitting nonsensical positive
    runway from a deficit position.
    """
    if burn is None:
        return None
    if burn >= 0:
        return math.inf
    if balance <= 0:
        return 0.0
    return balance / abs(burn)


# --- Composer: financial_context_text ------------------------------------


def _money(value: float) -> str:
    """Brazilian currency format: R$ 1.234,56 (used in this user's identity)."""
    formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if value < 0 else ""
    return f"R$ {sign}{formatted}"


_LIQUIDITY_LABEL = {
    "liquid": "Liquid (immediately available)",
    "semi_liquid": "Semi-liquid (redeemable in days)",
    "illiquid": "Illiquid (real estate, vehicles, etc.)",
}


def financial_context_text(api: "ExtensionAPI") -> str | None:
    """Compose the text block injected into the Mirror Mode prompt.

    Returns None when the extension has no data at all (no accounts).
    """
    accounts = list_accounts(api)
    if not accounts:
        return None

    snapshots = {acc.id: get_latest_snapshot(api, acc.id) for acc in accounts}
    txns = list_transactions(api)
    bills = list_active_bills(api)

    lines: list[str] = []

    # --- Balances by liquidity ------------------------------------
    bucket_rows: dict[str, list[str]] = {"liquid": [], "semi_liquid": [], "illiquid": []}
    bucket_totals: dict[str, float] = {"liquid": 0.0, "semi_liquid": 0.0, "illiquid": 0.0}

    for acc in accounts:
        snap = snapshots.get(acc.id)
        balance = snap.balance if snap else acc.opening_balance
        on_date = snap.date if snap else acc.opening_date
        bucket = acc.liquidity if acc.liquidity in bucket_rows else "liquid"
        entity_label = "PF" if acc.entity == "personal" else "PJ"
        type_label = {
            "checking": "CC",
            "credit_card": "Cartão",
            "savings": "RDB/Pop",
        }.get(acc.type, acc.type)
        bank = acc.bank or "—"
        bucket_rows[bucket].append(
            f"  [{entity_label}] {bank} {type_label} {acc.name} — "
            f"{_money(balance)} (on {on_date})"
        )
        bucket_totals[bucket] += balance

    for bucket in ("liquid", "semi_liquid", "illiquid"):
        if bucket_rows[bucket]:
            lines.append(f"--- {_LIQUIDITY_LABEL[bucket]} ---")
            lines.extend(bucket_rows[bucket])
            lines.append(f"  Subtotal: {_money(bucket_totals[bucket])}")
            lines.append("")

    totals = BalanceTotals(
        liquid=bucket_totals["liquid"],
        semi_liquid=bucket_totals["semi_liquid"],
        illiquid=bucket_totals["illiquid"],
    )
    lines.append(f"Total liquid: {_money(totals.liquid)}")
    lines.append(f"Total consolidated: {_money(totals.total)}")
    lines.append("")

    # --- Monthly cash flow ----------------------------------------
    flows = summarize_by_month(txns)
    if flows:
        # Show last six months to keep the block bounded.
        recent = flows[-6:]
        lines.append("--- Cash flow (last 6 months) ---")
        for m in recent:
            lines.append(
                f"  {m.month}: in {_money(m.income)} | "
                f"out {_money(abs(m.expense))} | net {_money(m.net)}"
            )
        lines.append("")

    # --- Burn and runway ------------------------------------------
    bills_burn = monthly_burn_from_bills(bills)
    history_burn = monthly_burn_from_history(flows)

    if bills_burn is not None or history_burn is not None:
        lines.append("--- Burn & runway ---")
        if bills_burn is not None:
            lines.append(f"  Monthly burn (from bills): {_money(abs(bills_burn))}")
        if history_burn is not None:
            lines.append(f"  Monthly burn (from history, last 3 mo): {_money(abs(history_burn))}")

        # Prefer bills as the runway driver; fall back to history.
        burn = bills_burn if bills_burn is not None else history_burn
        runway_liquid = calculate_runway(totals.liquid, burn)
        runway_with_semi = calculate_runway(
            totals.liquid + totals.semi_liquid, burn
        )
        if runway_liquid is not None and math.isfinite(runway_liquid):
            lines.append(f"  Runway (liquid only): {runway_liquid:.1f} months")
        elif runway_liquid == math.inf:
            lines.append("  Runway (liquid only): unbounded (net positive)")
        if totals.semi_liquid > 0 and runway_with_semi is not None:
            if math.isfinite(runway_with_semi):
                lines.append(
                    f"  Runway (+ semi-liquid): {runway_with_semi:.1f} months"
                )
            elif runway_with_semi == math.inf:
                lines.append("  Runway (+ semi-liquid): unbounded (net positive)")

    return "\n".join(lines).rstrip()
