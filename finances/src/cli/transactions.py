"""CLI handler for `python -m memory ext finances transactions`.

Pure read surface. Filters compose with AND semantics; the underlying
SQL is in src.store.list_transactions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.store import list_accounts, list_transactions

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def cmd_transactions(api: "ExtensionAPI", args: list[str]) -> int:
    """List transactions, optionally filtered."""
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
        category_id=flags.get("category"),
        type=flags.get("type"),
        description_like=flags.get("description"),
    )

    if not txns:
        print("(no transactions matched)")
        return 0

    # Account name lookup for display, single pass.
    accounts = {a.id: a for a in list_accounts(api)}

    print(
        f"{'Date':<10}  {'Account':<28}  {'Type':<6}  "
        f"{'Amount':>14}  Description"
    )
    income = 0.0
    expense = 0.0
    for t in txns:
        acc = accounts.get(t.account_id)
        acc_label = acc.name if acc else t.account_id
        print(
            f"{t.date:<10}  {acc_label[:28]:<28}  {t.type:<6}  "
            f"{_brl(t.amount):>14}  {t.description}"
        )
        if t.amount >= 0:
            income += t.amount
        else:
            expense += t.amount

    print()
    print(f"Rows: {len(txns)}  |  In: {_brl(income)}  |  Out: {_brl(abs(expense))}  |  Net: {_brl(income + expense)}")
    return 0


def _print_usage() -> None:
    print(
        "usage: python -m memory ext finances transactions "
        "[--account <id>] [--from <YYYY-MM-DD>] [--to <YYYY-MM-DD>] "
        "[--category <id>] [--type credit|debit] [--description <substring>]"
    )


def _parse_flags(args: list[str]) -> dict[str, str] | None:
    allowed = {
        "--account": "account",
        "--from": "from",
        "--to": "to",
        "--category": "category",
        "--type": "type",
        "--description": "description",
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


def _brl(value: float) -> str:
    formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if value < 0 else ""
    return f"R$ {sign}{formatted}"
