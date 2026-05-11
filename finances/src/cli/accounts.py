"""CLI handler for `python -m memory ext finances accounts`.

Two surfaces in one handler:

  accounts
  accounts list             -> list every registered account
  accounts add --name ...   -> register a new account
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.store import list_accounts, get_latest_snapshot
from src.store_writes import (
    VALID_ACCOUNT_TYPES,
    VALID_ENTITIES,
    VALID_LIQUIDITIES,
    create_account,
)

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def cmd_accounts(api: "ExtensionAPI", args: list[str]) -> int:
    """Manage finance accounts: list or add."""
    sub = args[0] if args else "list"
    rest = args[1:] if args else []

    if sub in {"--help", "-h", "help"}:
        _print_usage()
        return 0
    if sub == "list":
        return _cmd_list(api, rest)
    if sub == "add":
        return _cmd_add(api, rest)

    # Unrecognised first token: if it looks like a flag, treat it as
    # 'list <filters>'; otherwise complain.
    if sub.startswith("--"):
        return _cmd_list(api, args)
    print(f"unknown subcommand 'accounts {sub}'")
    _print_usage()
    return 1


def _print_usage() -> None:
    print(
        "usage:\n"
        "  python -m memory ext finances accounts [list] [--entity personal|business]\n"
        "  python -m memory ext finances accounts add --name <name> --type <type> "
        "--entity <entity>\n"
        "                                            [--opening-balance <amount>] "
        "[--opening-date <YYYY-MM-DD>]\n"
        "                                            [--bank <bank>] [--agency <agency>] "
        "[--account-number <num>]\n"
        "                                            [--liquidity liquid|semi_liquid|illiquid]"
    )


def _cmd_list(api: "ExtensionAPI", rest: list[str]) -> int:
    entity_filter = _take_flag(rest, "--entity")
    accounts = list_accounts(api)
    if entity_filter:
        accounts = [a for a in accounts if a.entity == entity_filter]
    if not accounts:
        print("(no accounts)")
        return 0
    print(
        f"{'ID':<10}  {'Entity':<8}  {'Type':<11}  {'Liquidity':<11}  "
        f"{'Bank':<12}  {'Name':<28}  Balance"
    )
    for acc in accounts:
        snap = get_latest_snapshot(api, acc.id)
        balance = snap.balance if snap else acc.opening_balance
        print(
            f"{acc.id:<10}  {acc.entity:<8}  {acc.type:<11}  {acc.liquidity:<11}  "
            f"{(acc.bank or '-'):<12}  {acc.name[:28]:<28}  {_brl(balance)}"
        )
    return 0


def _cmd_add(api: "ExtensionAPI", rest: list[str]) -> int:
    required = {
        "--name": str,
        "--type": str,
        "--entity": str,
    }
    optional = {
        "--opening-balance": float,
        "--opening-date": str,
        "--bank": str,
        "--agency": str,
        "--account-number": str,
        "--liquidity": str,
    }
    try:
        values = _parse_kv(rest, required=required, optional=optional)
    except ValueError as exc:
        print(f"error: {exc}")
        _print_usage()
        return 1

    try:
        account_id = create_account(
            api,
            name=values["--name"],
            type=values["--type"],
            entity=values["--entity"],
            opening_balance=values.get("--opening-balance", 0.0),
            opening_date=values.get("--opening-date"),
            bank=values.get("--bank"),
            agency=values.get("--agency"),
            account_number=values.get("--account-number"),
            liquidity=values.get("--liquidity", "liquid"),
        )
    except ValueError as exc:
        print(f"error: {exc}")
        return 1

    print(f"added account {account_id}: {values['--name']} ({values['--entity']}/{values['--type']})")
    return 0


# --- Tiny argv helpers ----------------------------------------------------


def _take_flag(rest: list[str], flag: str) -> str | None:
    """Mutates `rest` in place: removes the flag and returns its value."""
    if flag in rest:
        idx = rest.index(flag)
        if idx + 1 < len(rest):
            value = rest[idx + 1]
            del rest[idx : idx + 2]
            return value
    return None


def _parse_kv(
    args: list[str],
    *,
    required: dict[str, type],
    optional: dict[str, type],
) -> dict[str, object]:
    """Parse '--flag value' pairs against typed schemas."""
    known = {**required, **optional}
    out: dict[str, object] = {}
    i = 0
    while i < len(args):
        flag = args[i]
        if flag not in known:
            raise ValueError(f"unrecognised flag '{flag}'")
        if i + 1 >= len(args):
            raise ValueError(f"flag '{flag}' requires a value")
        raw = args[i + 1]
        caster = known[flag]
        try:
            out[flag] = caster(raw) if caster is not str else raw
        except ValueError as exc:
            raise ValueError(f"flag '{flag}': invalid value '{raw}' ({exc})") from exc
        i += 2
    missing = [f for f in required if f not in out]
    if missing:
        raise ValueError(f"missing required flag(s): {', '.join(missing)}")
    return out


def _brl(value: float) -> str:
    formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if value < 0 else ""
    return f"R$ {sign}{formatted}"
