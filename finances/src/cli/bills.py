"""CLI handler for `python -m memory ext finances bills`.

  bills [list]                -> list active bills (use --include-inactive for all)
  bills add --name ...        -> register a recurring bill
  bills remove <id>           -> mark a bill inactive (preserves audit trail)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.store import list_active_bills
from src.store_writes import (
    VALID_BILL_CATEGORIES,
    VALID_ENTITIES,
    create_bill,
    deactivate_bill,
)

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def cmd_bills(api: "ExtensionAPI", args: list[str]) -> int:
    """Manage recurring bills."""
    sub = args[0] if args else "list"
    rest = args[1:] if args else []

    if sub in {"--help", "-h", "help"}:
        _print_usage()
        return 0
    if sub == "list":
        return _cmd_list(api, rest)
    if sub == "add":
        return _cmd_add(api, rest)
    if sub == "remove":
        return _cmd_remove(api, rest)

    if sub.startswith("--"):
        return _cmd_list(api, args)
    print(f"unknown subcommand 'bills {sub}'")
    _print_usage()
    return 1


def _print_usage() -> None:
    print(
        "usage:\n"
        "  python -m memory ext finances bills [list] [--include-inactive]\n"
        "  python -m memory ext finances bills add --name <name> --entity <entity> "
        "--category <category> --amount <amount> [--day-of-month <day>] [--notes <text>]\n"
        "  python -m memory ext finances bills remove <bill_id>"
    )


def _cmd_list(api: "ExtensionAPI", rest: list[str]) -> int:
    include_inactive = "--include-inactive" in rest
    if include_inactive:
        rows = api.read(
            "SELECT * FROM ext_finances_recurring_bills "
            "ORDER BY entity, active DESC, name"
        ).fetchall()
    else:
        bills = list_active_bills(api)
        if not bills:
            print("(no active bills)")
            return 0
        rows = [
            {
                "id": b.id,
                "name": b.name,
                "entity": b.entity,
                "category": b.category,
                "amount": b.amount,
                "day_of_month": b.day_of_month,
                "active": 1 if b.active else 0,
            }
            for b in bills
        ]

    if not rows:
        print("(no bills)")
        return 0

    print(
        f"{'ID':<10}  {'Active':<6}  {'Entity':<8}  {'Cat':<8}  "
        f"{'Day':<3}  {'Name':<24}  Amount"
    )
    total_by_entity: dict[str, float] = {"personal": 0.0, "business": 0.0}
    for row in rows:
        active_flag = "✓" if row["active"] else "—"
        day = str(row["day_of_month"]) if row["day_of_month"] else "-"
        print(
            f"{row['id']:<10}  {active_flag:<6}  {row['entity']:<8}  "
            f"{row['category']:<8}  {day:<3}  "
            f"{row['name'][:24]:<24}  {_brl(row['amount'])}"
        )
        if row["active"]:
            total_by_entity[row["entity"]] = (
                total_by_entity.get(row["entity"], 0.0) + row["amount"]
            )

    print()
    for entity in ("personal", "business"):
        if total_by_entity.get(entity):
            print(f"Active total ({entity}): {_brl(total_by_entity[entity])}")
    total = sum(total_by_entity.values())
    if total:
        print(f"Active total: {_brl(total)}")
    return 0


def _cmd_add(api: "ExtensionAPI", rest: list[str]) -> int:
    required = {
        "--name": str,
        "--entity": str,
        "--category": str,
        "--amount": float,
    }
    optional = {
        "--day-of-month": int,
        "--notes": str,
    }
    try:
        values = _parse_kv(rest, required=required, optional=optional)
    except ValueError as exc:
        print(f"error: {exc}")
        _print_usage()
        return 1

    try:
        bill_id = create_bill(
            api,
            name=values["--name"],
            entity=values["--entity"],
            category=values["--category"],
            amount=values["--amount"],
            day_of_month=values.get("--day-of-month"),
            notes=values.get("--notes"),
        )
    except ValueError as exc:
        print(f"error: {exc}")
        return 1

    print(
        f"added bill {bill_id}: {values['--name']} "
        f"({values['--entity']}/{values['--category']}, "
        f"{_brl(values['--amount'])})"
    )
    return 0


def _cmd_remove(api: "ExtensionAPI", rest: list[str]) -> int:
    if not rest:
        print("error: remove requires <bill_id>")
        _print_usage()
        return 1
    bill_id = rest[0]
    if deactivate_bill(api, bill_id):
        print(f"deactivated bill {bill_id}")
        return 0
    print(f"error: no bill with id '{bill_id}'")
    return 1


# --- Tiny argv helper (mirrors the one in cli/accounts.py) ----------------


def _parse_kv(
    args: list[str],
    *,
    required: dict[str, type],
    optional: dict[str, type],
) -> dict[str, object]:
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
