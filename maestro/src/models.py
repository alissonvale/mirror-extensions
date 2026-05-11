"""Data models for the Maestro coherence engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

UoCSeverity = Literal["blocking", "important", "optional"]
UoCStatus = Literal["open", "resolved", "deferred", "accepted"]
Locale = Literal["en-US", "pt-BR"]
AudienceMode = Literal["technical", "non-technical"]


@dataclass(frozen=True)
class MaestroConfig:
    """Human surface configuration stored in ``maestro.yml``."""

    locale: Locale = "en-US"
    mode: AudienceMode = "technical"
    name: str | None = None


@dataclass(frozen=True)
class UnitOfCoherence:
    """A concrete gap between an expected and observed project state."""

    id: str
    semantic_id: str
    title: str
    severity: UoCSeverity
    status: UoCStatus
    expected_state: str
    observed_state: str
    evidence: tuple[str, ...] = field(default_factory=tuple)
    gap: str | None = None
    suggested_action: str | None = None


@dataclass(frozen=True)
class ProjectState:
    """Observed state of a Maestro project root."""

    root: Path
    config: MaestroConfig
    has_maestro_config: bool
    has_readme: bool
    has_git_repository: bool
    git_repository_path: Path | None = None
    name: str | None = None
    readme_title: str | None = None


@dataclass(frozen=True)
class CheckResult:
    """Output of a coherence inspection."""

    state: ProjectState
    units: tuple[UnitOfCoherence, ...]

    @property
    def open_units(self) -> tuple[UnitOfCoherence, ...]:
        return tuple(unit for unit in self.units if unit.status != "resolved")

    @property
    def resolved_units(self) -> tuple[UnitOfCoherence, ...]:
        return tuple(unit for unit in self.units if unit.status == "resolved")

    @property
    def has_blocking_gaps(self) -> bool:
        return any(unit.status == "open" and unit.severity == "blocking" for unit in self.units)

    @property
    def has_open_gaps(self) -> bool:
        return any(unit.status == "open" for unit in self.units)
