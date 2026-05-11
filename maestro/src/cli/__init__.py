"""CLI subcommands for the Maestro extension."""

from __future__ import annotations

import argparse
import sys

from src.coherence import (
    check_project,
    configure_project,
    ensure_default_docs,
    render_cli_report,
    resolve_project_name,
    write_coherence_index,
)
from src.project import ProjectResolutionError, resolve_project_root
from src.store_writes import insert_check_run


def _common_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--root", help="Project root to inspect")
    group.add_argument(
        "--journey",
        help="Journey whose metadata.project_path should be used (default: maestro)",
    )
    return parser


def cmd_check(api, argv: list[str]) -> int:
    """Inspect the journey project and update docs/coherence/index.md."""
    parser = _common_parser("Inspect Maestro project coherence")
    args = parser.parse_args(argv)
    return _with_resolution(api, args, lambda root, journey_id: _check(api, root, journey_id))


def cmd_init(api, argv: list[str]) -> int:
    """Resolve the first blocking UoC by setting a project name."""
    parser = _common_parser("Initialize a Maestro project")
    parser.add_argument("--name", required=True, help="Provisional project name")
    parser.add_argument("--locale", choices=["en-US", "pt-BR"])
    parser.add_argument("--mode", choices=["technical", "non-technical"])
    args = parser.parse_args(argv)

    def _run(root, journey_id):
        result = resolve_project_name(
            root,
            args.name,
            locale=args.locale,
            mode=args.mode,
        )
        insert_check_run(api, result, journey_id=journey_id, source="cli")
        sys.stdout.write(render_cli_report(result))
        return 0

    return _with_resolution(api, args, _run)


def cmd_configure(api, argv: list[str]) -> int:
    """Set locale/mode for a Maestro project without requiring a name."""
    parser = _common_parser("Configure Maestro human surface")
    parser.add_argument("--locale", choices=["en-US", "pt-BR"])
    parser.add_argument("--mode", choices=["technical", "non-technical"])
    args = parser.parse_args(argv)
    if args.locale is None and args.mode is None:
        parser.error("at least one of --locale or --mode is required")

    def _run(root, journey_id):
        state = configure_project(
            root,
            locale=args.locale,
            mode=args.mode,
        )
        result = check_project(state.root)
        insert_check_run(api, result, journey_id=journey_id, source="cli")
        sys.stdout.write(
            f"Configured Maestro project: locale={state.config.locale}, mode={state.config.mode}\n"
        )
        sys.stdout.write(render_cli_report(result))
        return 0

    return _with_resolution(api, args, _run)


def _check(api, root, journey_id) -> int:
    result = check_project(root)
    ensure_default_docs(root, result.state.config.locale)
    write_coherence_index(root, result.units, result.state.config.locale)
    insert_check_run(api, result, journey_id=journey_id, source="cli")
    sys.stdout.write(render_cli_report(result))
    return 0


def _with_resolution(api, args, fn) -> int:
    try:
        root, journey_id = resolve_project_root(
            api,
            root=args.root,
            journey_id=args.journey,
        )
    except ProjectResolutionError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    return fn(root, journey_id)


__all__ = ["cmd_check", "cmd_configure", "cmd_init"]
