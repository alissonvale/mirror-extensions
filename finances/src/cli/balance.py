"""CLI handlers for balance snapshot and balance lookups.

  balance                            -> latest balance per account
  balance <account_id>               -> latest balance of one account
  snapshot <account_id> <date> <balance> [--source manual|ofx|reconciliation]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.store import get_latest_snapshot, list_accounts
from src.store_writes import VALID_SNAPSHOT_SOURCES, record_snapshot

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def cmd_balance(api: "ExtensionAPI", args: list[str]) -> int:
    """Show the latest known balance per account, or for one account."""
    if args and args[0] in {"--help", "-h", "help"}:
        print(
            "usage:\n"
            "  python -m memory ext finances balance\n"
            "  python -m memory ext finances balance <account_id>"
        )
        return 0

    accounts = list_accounts(api)
    if not accounts:
        print("(no accounts)")
        return 0

    if args:
        target = args[0]
        matching = [a for a in accounts if a.id == target]
        if not matching:
            print(f"error: no account with id '{target}'")
            return 1
        accounts = matching

    for acc in accounts:
        snap = get_latest_snapshot(api, acc.id)
        balance = snap.balance if snap else acc.opening_balance
        on_date = snap.date if snap else acc.opening_date
        source = snap.source if snap else "opening"
        print(
            f"{acc.id}  {acc.name} ({acc.entity}/{acc.type})  "
            f"{_brl(balance)}  on {on_date}  [{source}]"
        )
    return 0


def cmd_snapshot(api: "ExtensionAPI", args: list[str]) -> int:
    """Record a balance snapshot for an account."""
    if args and args[0] in {"--help", "-h", "help"}:
        _print_snapshot_usage()
        return 0
    if len(args) < 3:
        print("error: snapshot requires <account_id> <date> <balance>")
        _print_snapshot_usage()
        return 1

    account_id, date, raw_balance = args[0], args[1], args[2]
    rest = args[3:]
    try:
        balance = float(raw_balance)
    except ValueError:
        print(f"error: balance must be a number, got '{raw_balance}'")
        return 1

    source = "manual"
    if rest:
        if rest[0] != "--source" or len(rest) < 2:
            print(f"error: unrecognised arguments {rest}")
            _print_snapshot_usage()
            return 1
        source = rest[1]

    # Validate account exists (clear error early).
    accounts = list_accounts(api)
    if not any(a.id == account_id for a in accounts):
        print(f"error: no account with id '{account_id}'")
        return 1

    try:
        snap_id = record_snapshot(
            api,
            account_id=account_id,
            date=date,
            balance=balance,
            source=source,
        )
    except ValueError as exc:
        print(f"error: {exc}")
        return 1

    print(f"recorded snapshot {snap_id}: {_brl(balance)} on {date} ({source})")
    return 0


def _print_snapshot_usage() -> None:
    print(
        "usage: python -m memory ext finances snapshot "
        "<account_id> <YYYY-MM-DD> <balance> "
        f"[--source {'|'.join(sorted(VALID_SNAPSHOT_SOURCES))}]"
    )


def _brl(value: float) -> str:
    formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if value < 0 else ""
    return f"R$ {sign}{formatted}"
