"""CLI handler for `python -m memory ext finances report`.

Surfaces ``summarize_by_month`` from src.reports as a table.
Optionally narrows by account and date range.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.reports import summarize_by_month
from src.store import list_transactions

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def cmd_report(api: "ExtensionAPI", args: list[str]) -> int:
    """Monthly income/expense/net summary."""
    if args and args[0] in {"--help", "-h", "help"}:
        _print_usage()
        return 0

    flags = _parse_flags(args)
    if flags is None:
        return 1

    txns = list_transactions(
        api,
        account_id=flags.get("account"),
        start_date=flags.get("from"),
        end_date=flags.get("to"),
    )
    if not txns:
        print("(no transactions in the requested range)")
        return 0

    flows = summarize_by_month(txns)
    if not flows:
        print("(no transactions in the requested range)")
        return 0

    print(f"{'Month':<8}  {'Income':>14}  {'Expense':>14}  {'Net':>14}")
    total_in = 0.0
    total_out = 0.0
    for f in flows:
        print(
            f"{f.month:<8}  {_brl(f.income):>14}  "
            f"{_brl(abs(f.expense)):>14}  {_brl(f.net):>14}"
        )
        total_in += f.income
        total_out += f.expense
    print()
    print(
        f"{'Total':<8}  {_brl(total_in):>14}  "
        f"{_brl(abs(total_out)):>14}  {_brl(total_in + total_out):>14}"
    )
    return 0


def _print_usage() -> None:
    print(
        "usage: python -m memory ext finances report "
        "[--account <id>] [--from <YYYY-MM-DD>] [--to <YYYY-MM-DD>]"
    )


def _parse_flags(args: list[str]) -> dict[str, str] | None:
    allowed = {"--account": "account", "--from": "from", "--to": "to"}
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


def _brl(value: float) -> str:
    formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if value < 0 else ""
    return f"R$ {sign}{formatted}"
