"""CLI handlers for statement imports (US-03 and US-04).

  import-statement              -> bank statement (US-03)
  import-credit-card-statement  -> credit card statement (US-04)

Both share the same argument shape:
  <file>  [--format <name>]  [--account <id>]
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.import_statement import (
    import_bank_statement,
    import_credit_card_statement,
    read_statement_file,
)
from src.parsers.registry import (
    list_bank_formats,
    list_credit_card_formats,
)

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def cmd_import_statement(api: "ExtensionAPI", args: list[str]) -> int:
    """Import a bank statement (US-03)."""
    return _cmd_import(
        api,
        args,
        kind="bank",
        runner=import_bank_statement,
        formats=list_bank_formats(),
        command_label="import-statement",
    )


def cmd_import_credit_card_statement(
    api: "ExtensionAPI", args: list[str]
) -> int:
    """Import a credit card statement (US-04)."""
    return _cmd_import(
        api,
        args,
        kind="credit-card",
        runner=import_credit_card_statement,
        formats=list_credit_card_formats(),
        command_label="import-credit-card-statement",
    )


def _cmd_import(
    api: "ExtensionAPI",
    args: list[str],
    *,
    kind: str,
    runner,
    formats: list[str],
    command_label: str,
) -> int:
    if args and args[0] in {"--help", "-h", "help"}:
        _print_usage(command_label, formats)
        return 0
    if not args:
        print("error: <file> is required")
        _print_usage(command_label, formats)
        return 1

    path_arg = args[0]
    rest = args[1:]
    format_flag, account_flag = _parse_flags(rest)
    if format_flag is _PARSE_ERROR:
        _print_usage(command_label, formats)
        return 1

    path = Path(path_arg).expanduser()
    if not path.exists():
        print(f"error: file not found: {path}")
        return 1
    if not path.is_file():
        print(f"error: not a regular file: {path}")
        return 1

    try:
        content = read_statement_file(path)
    except Exception as exc:  # noqa: BLE001
        print(f"error: failed to read {path}: {exc}")
        return 1

    try:
        result = runner(
            api,
            content=content,
            format=format_flag,
            account_id=account_flag,
        )
    except ValueError as exc:
        print(f"error: {exc}")
        return 1

    print(f"imported into account {result.account_id}:")
    print(f"  rows: {result.imported} new, {result.skipped} skipped (already present)")
    if result.period:
        print(f"  period: {result.period}")
    if result.ledger_balance is not None:
        print(f"  ledger balance: {_brl(result.ledger_balance)}")
    if result.closing_date:
        print(f"  closing date: {result.closing_date}")
    if result.total is not None:
        print(f"  statement total: {_brl(result.total)}")
    return 0


_PARSE_ERROR = object()


def _parse_flags(args: list[str]) -> tuple[str | None, str | None]:
    """Returns (format, account_id). Uses _PARSE_ERROR as a sentinel
    on argument errors so the caller can print usage."""
    format_flag: str | None = None
    account_flag: str | None = None
    i = 0
    while i < len(args):
        if args[i] == "--format" and i + 1 < len(args):
            format_flag = args[i + 1]
            i += 2
            continue
        if args[i] == "--account" and i + 1 < len(args):
            account_flag = args[i + 1]
            i += 2
            continue
        print(f"error: unrecognised argument '{args[i]}'")
        return _PARSE_ERROR, None
    return format_flag, account_flag


def _print_usage(command_label: str, formats: list[str]) -> None:
    fmt_list = ", ".join(formats) if formats else "(none registered)"
    print(
        f"usage: python -m memory ext finances {command_label} "
        f"<file> [--format <name>] [--account <id>]\n"
        f"  formats: {fmt_list}\n"
        f"  --account is required when the file's account/card number "
        f"does not match any registered account."
    )


def _brl(value: float) -> str:
    formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if value < 0 else ""
    return f"R$ {sign}{formatted}"
