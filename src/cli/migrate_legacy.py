"""CLI handler for ``python -m memory ext finances migrate-legacy``.

Argument shape, output shape, exit codes, and error messages are
documented in
``docs/user-stories/US-11-migrate-legacy-data.md`` and
``docs/legacy-migration.md``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.migrate_legacy import (
    LegacyMigrationError,
    MigrationResult,
    migrate_legacy,
)

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def cmd_migrate_legacy(api: "ExtensionAPI", args: list[str]) -> int:
    """Migrate legacy mirror finance data into ext_finances_* tables."""
    parsed = _parse_args(args)
    if parsed is None:
        return 1

    source, dry_run = parsed
    header_action = "Dry run — no changes will be written." if dry_run else (
        f"Migrating from {source} ..."
    )
    print(header_action)
    print()

    try:
        result = migrate_legacy(api, source=source, dry_run=dry_run)
    except LegacyMigrationError as exc:
        print(f"error: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 — surface any unexpected error cleanly
        print(f"error: migration failed: {exc}")
        return 1

    _print_result(result)
    return 0


def _parse_args(args: list[str]) -> tuple[Path, bool] | None:
    source_arg: str | None = None
    dry_run = False
    i = 0
    while i < len(args):
        if args[i] == "--source" and i + 1 < len(args):
            source_arg = args[i + 1]
            i += 2
        elif args[i] == "--dry-run":
            dry_run = True
            i += 1
        elif args[i] in {"--help", "-h"}:
            _print_usage()
            return None
        else:
            print(f"unrecognised argument: {args[i]}")
            _print_usage()
            return None

    if source_arg is None:
        print("error: --source <path> is required")
        _print_usage()
        return None

    return Path(source_arg).expanduser(), dry_run


def _print_usage() -> None:
    print(
        "usage: python -m memory ext finances migrate-legacy "
        "--source <path> [--dry-run]"
    )


def _print_result(result: MigrationResult) -> None:
    verb_imported = "would be imported" if result.dry_run else "imported"
    verb_skipped = "would be skipped" if result.dry_run else "skipped"

    # Two-column right-aligned table.
    col_width = max(len(t.table) for t in result.tables)
    for table_result in result.tables:
        line = (
            f"  {table_result.table:<{col_width}}  "
            f"{table_result.imported:>4} {verb_imported}, "
            f"{table_result.skipped:>4} {verb_skipped}"
        )
        print(line)
    print()
    total_label = "Total"
    print(f"{total_label}: {result.total_imported} rows {verb_imported}.")
