"""Entrypoint for the Maestro extension.

Registers the hello-world coherence CLI plus the ``coherence_status``
Mirror Mode capability. The capability is designed to be bound to a
journey (initially ``maestro``), not to a persona; persona orchestration
will come later as Maestro learns to involve specialized lenses.
"""

from __future__ import annotations

from src.cli import cmd_check, cmd_configure, cmd_init
from src.context import provide_coherence_status

from memory.extensions.api import ExtensionAPI


def register(api: ExtensionAPI) -> None:
    api.register_cli(
        "check",
        cmd_check,
        summary="Inspect the journey project and update docs/coherence/index.md.",
    )
    api.register_cli(
        "init",
        cmd_init,
        summary="Resolve the first blocking UoC by setting a project name.",
    )
    api.register_cli(
        "configure",
        cmd_configure,
        summary="Set locale/mode for a Maestro project.",
    )
    api.register_mirror_context(
        "coherence_status",
        provide_coherence_status,
    )
