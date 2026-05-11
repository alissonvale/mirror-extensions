"""CLI handler for `python -m memory ext finances runway`.

Exposes the runway calculation under user-configurable assumptions.
The same numbers feed the financial_summary Mirror Mode provider; this
subcommand is for scenarios where the user wants to play with
``--include-liquidity`` or ``--burn-source``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from src.reports import (
    calculate_runway,
    consolidated_balance,
    monthly_burn_from_bills,
    monthly_burn_from_history,
    summarize_by_month,
)
from src.store import (
    get_latest_snapshot,
    list_accounts,
    list_active_bills,
    list_transactions,
)

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def cmd_runway(api: "ExtensionAPI", args: list[str]) -> int:
    """Compute runway under explicit assumptions."""
    if args and args[0] in {"--help", "-h", "help"}:
        _print_usage()
        return 0

    flags = _parse_flags(args)
    if flags is None:
        return 1

    include_liquidity = _parse_liquidity_csv(flags.get("include_liquidity", "liquid"))
    if include_liquidity is None:
        return 1
    burn_source = flags.get("burn_source", "bills")
    if burn_source not in {"bills", "history"}:
        print(f"error: --burn-source must be 'bills' or 'history', got '{burn_source}'")
        return 1
    try:
        lookback = int(flags.get("lookback_months", "3"))
    except ValueError:
        print(f"error: --lookback-months must be an integer, got '{flags['lookback_months']}'")
        return 1

    accounts = list_accounts(api)
    if not accounts:
        print("(no accounts registered)")
        return 0

    snapshots = {a.id: get_latest_snapshot(api, a.id) for a in accounts}
    eligible = [a for a in accounts if a.liquidity in include_liquidity]
    totals = consolidated_balance(eligible, snapshots)

    txns = list_transactions(api)
    monthly = summarize_by_month(txns)
    history_burn = monthly_burn_from_history(monthly, lookback_months=lookback)
    bills_burn = monthly_burn_from_bills(list_active_bills(api))

    burn = bills_burn if burn_source == "bills" else history_burn
    if burn is None and burn_source == "bills" and history_burn is not None:
        print(
            "note: no active recurring bills registered; falling back to history."
        )
        burn = history_burn
        burn_source = "history (fallback)"

    print(f"Balance scope: {', '.join(include_liquidity)}")
    print(f"  Total: {_brl(totals.liquid + totals.semi_liquid + totals.illiquid)}")
    if "liquid" in include_liquidity:
        print(f"  Liquid:      {_brl(totals.liquid)}")
    if "semi_liquid" in include_liquidity:
        print(f"  Semi-liquid: {_brl(totals.semi_liquid)}")
    if "illiquid" in include_liquidity:
        print(f"  Illiquid:    {_brl(totals.illiquid)}")

    print()
    if bills_burn is not None:
        print(f"Burn (bills):   {_brl(abs(bills_burn))}/month")
    if history_burn is not None:
        print(f"Burn (history, last {lookback}mo): {_brl(abs(history_burn))}/month")

    runway = calculate_runway(
        totals.liquid + totals.semi_liquid + totals.illiquid, burn
    )
    print()
    if runway is None:
        print(f"Runway: indeterminate (no burn signal from source '{burn_source}')")
    elif math.isinf(runway):
        print("Runway: unbounded (net positive flow)")
    else:
        print(f"Runway (source: {burn_source}): {runway:.1f} months")
    return 0


def _print_usage() -> None:
    print(
        "usage: python -m memory ext finances runway "
        "[--include-liquidity liquid,semi_liquid,illiquid] "
        "[--burn-source bills|history] "
        "[--lookback-months 3]"
    )


def _parse_flags(args: list[str]) -> dict[str, str] | None:
    allowed = {
        "--include-liquidity": "include_liquidity",
        "--burn-source": "burn_source",
        "--lookback-months": "lookback_months",
    }
    out: dict[str, str] = {}
    i = 0
    while i < len(args):
        flag = args[i]
        if flag not in allowed:
            print(f"error: unrecognised flag '{flag}'")
            _print_usage()
            return None
        if i + 1 >= len(args):
            print(f"error: flag '{flag}' requires a value")
            _print_usage()
            return None
        out[allowed[flag]] = args[i + 1]
        i += 2
    return out


def _parse_liquidity_csv(raw: str) -> list[str] | None:
    valid = {"liquid", "semi_liquid", "illiquid"}
    items = [x.strip() for x in raw.split(",") if x.strip()]
    for item in items:
        if item not in valid:
            print(
                f"error: '{item}' is not a valid liquidity bucket "
                f"(expected one or more of: {', '.join(sorted(valid))})"
            )
            return None
    return items


def _brl(value: float) -> str:
    formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if value < 0 else ""
    return f"R$ {sign}{formatted}"
