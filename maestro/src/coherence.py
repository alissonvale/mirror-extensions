"""Mirror-native port of the Maestro proof-of-concept coherence engine.

The source of truth remains project-local:

* ``maestro.yml`` stores the project's working name, locale, and mode.
* ``docs/coherence/rules.md`` describes the active base lens.
* ``docs/coherence/index.md`` is the live coherence ledger.

This module intentionally keeps the first lens tiny: two base UoCs that
bootstrap every project — working name and git repository.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.models import (
    AudienceMode,
    CheckResult,
    Locale,
    MaestroConfig,
    ProjectState,
    UnitOfCoherence,
    UoCSeverity,
)

DEFAULT_LOCALE: Locale = "en-US"
DEFAULT_MODE: AudienceMode = "technical"

UOC_DISPLAY_IDS: dict[str, str] = {
    "project.working_name": "UoC-001",
    "project.git_repository": "UoC-002",
}


@dataclass(frozen=True)
class UoCText:
    title: str
    expected_state: str
    observed_resolved: Callable[[ProjectState], str]
    observed_open: str
    gap_open: str
    suggested_action_open: dict[AudienceMode, str]
    evidence_resolved: Callable[[ProjectState], tuple[str, ...]]
    evidence_open: Callable[[ProjectState], tuple[str, ...]]


TEXT: dict[Locale, dict[str, UoCText]] = {
    "en-US": {
        "project.working_name": UoCText(
            title="Project working name",
            expected_state="Every Maestro project has a provisional working name.",
            observed_resolved=lambda state: f'Project working name is "{state.name}".',
            observed_open="No maestro.yml name and no README title were found.",
            gap_open="The project cannot create stable folders, docs, or repository identity without a working name.",
            suggested_action_open={
                "technical": "Provide a provisional project name.",
                "non-technical": "Choose a simple provisional name. It does not need to be final; it only gives the project a stable identity so Maestro can create files around it.",
            },
            evidence_resolved=lambda state: (
                *(["maestro.yml exists"] if state.has_maestro_config else []),
                *([f'README.md title is "{state.readme_title}"'] if state.readme_title else []),
            ),
            evidence_open=lambda state: (
                "maestro.yml exists but has no name"
                if state.has_maestro_config
                else "maestro.yml not found",
                "README.md exists but has no title" if state.has_readme else "README.md not found",
            ),
        ),
        "project.git_repository": UoCText(
            title="Git repository",
            expected_state="Every Maestro project should be tracked in git.",
            observed_resolved=lambda state: (
                f'Project is tracked in git at "{state.git_repository_path}".'
            ),
            observed_open="No .git directory was found.",
            gap_open="The project has no version-control history yet.",
            suggested_action_open={
                "technical": "Run git init, or defer this gap explicitly.",
                "non-technical": "Start version history for this project, so changes can be traced and undone later. You can also defer this if you are only exploring.",
            },
            evidence_resolved=lambda state: (f".git found at {state.git_repository_path}",),
            evidence_open=lambda _state: (".git not found",),
        ),
    },
    "pt-BR": {
        "project.working_name": UoCText(
            title="Nome provisório do projeto",
            expected_state="Todo projeto Maestro tem um nome provisório.",
            observed_resolved=lambda state: f'O nome provisório do projeto é "{state.name}".',
            observed_open="Nenhum nome em maestro.yml e nenhum título em README.md foram encontrados.",
            gap_open="O projeto não consegue criar pastas, docs ou identidade de repositório de forma estável sem um nome provisório.",
            suggested_action_open={
                "technical": "Informe um nome provisório para o projeto.",
                "non-technical": "Escolha um nome provisório simples. Ele não precisa ser definitivo; serve apenas para dar uma identidade estável ao projeto enquanto o Maestro cria os arquivos iniciais.",
            },
            evidence_resolved=lambda state: (
                *(["maestro.yml existe"] if state.has_maestro_config else []),
                *(
                    [f'O título de README.md é "{state.readme_title}"']
                    if state.readme_title
                    else []
                ),
            ),
            evidence_open=lambda state: (
                "maestro.yml existe, mas não tem nome"
                if state.has_maestro_config
                else "maestro.yml não encontrado",
                "README.md existe, mas não tem título"
                if state.has_readme
                else "README.md não encontrado",
            ),
        ),
        "project.git_repository": UoCText(
            title="Repositório git",
            expected_state="Todo projeto Maestro deveria ser acompanhado em git.",
            observed_resolved=lambda state: (
                f'O projeto está em git em "{state.git_repository_path}".'
            ),
            observed_open="Nenhum diretório .git foi encontrado.",
            gap_open="O projeto ainda não tem histórico de controle de versão.",
            suggested_action_open={
                "technical": "Execute git init, ou adie este gap explicitamente.",
                "non-technical": "Inicie o histórico de versões do projeto, para que mudanças possam ser rastreadas e desfeitas depois. Você também pode adiar isso se estiver apenas explorando.",
            },
            evidence_resolved=lambda state: (f".git encontrado em {state.git_repository_path}",),
            evidence_open=lambda _state: (".git não encontrado",),
        ),
    },
}


def find_git_repository_path(root: str | Path) -> Path | None:
    """Return the nearest .git path at or above ``root``.

    Maestro projects may live inside monorepos. In that case the project
    root does not contain ``.git`` itself, but it is still versioned.
    """
    current = Path(root).expanduser().resolve()
    for candidate in (current, *current.parents):
        git_path = candidate / ".git"
        if git_path.exists():
            return git_path
    return None


def inspect_project(root: str | Path) -> ProjectState:
    """Read project-local state and return the observed facts."""
    project_root = Path(root).expanduser().resolve()
    maestro_config_path = project_root / "maestro.yml"
    readme_path = project_root / "README.md"

    has_maestro_config = maestro_config_path.exists()
    has_readme = readme_path.exists()
    git_repository_path = find_git_repository_path(project_root)
    has_git_repository = git_repository_path is not None

    config = MaestroConfig()
    if has_maestro_config:
        parsed = parse_maestro_config(maestro_config_path.read_text())
        config = MaestroConfig(
            name=parsed.name,
            locale=parsed.locale or config.locale,
            mode=parsed.mode or config.mode,
        )

    readme_title = None
    if has_readme:
        readme_title = parse_readme_title(readme_path.read_text())

    return ProjectState(
        root=project_root,
        config=config,
        name=config.name or readme_title,
        has_readme=has_readme,
        readme_title=readme_title,
        has_maestro_config=has_maestro_config,
        has_git_repository=has_git_repository,
        git_repository_path=git_repository_path,
    )


def evaluate_coherence(state: ProjectState) -> tuple[UnitOfCoherence, ...]:
    """Evaluate the base lens over ``state``."""
    return (evaluate_project_name(state), evaluate_git_repository(state))


def check_project(root: str | Path) -> CheckResult:
    """Inspect and evaluate the project root."""
    state = inspect_project(root)
    return CheckResult(state=state, units=evaluate_coherence(state))


def resolve_project_name(
    root: str | Path,
    name: str,
    *,
    locale: Locale | None = None,
    mode: AudienceMode | None = None,
) -> CheckResult:
    """Resolve UoC-001 by setting the project's provisional name."""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Project name cannot be empty.")

    project_root = Path(root).expanduser().resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    existing = inspect_project(project_root)
    config = MaestroConfig(
        name=clean_name,
        locale=locale or existing.config.locale,
        mode=mode or existing.config.mode,
    )

    (project_root / "maestro.yml").write_text(render_maestro_config(config))
    (project_root / "README.md").write_text(f"# {clean_name}\n")
    ensure_default_docs(project_root, config.locale)

    result = check_project(project_root)
    write_coherence_index(project_root, result.units, result.state.config.locale)
    return result


def configure_project(
    root: str | Path,
    *,
    locale: Locale | None = None,
    mode: AudienceMode | None = None,
) -> ProjectState:
    """Configure locale/mode without requiring a project name."""
    project_root = Path(root).expanduser().resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    existing = inspect_project(project_root)
    config = MaestroConfig(
        name=existing.config.name,
        locale=locale or existing.config.locale,
        mode=mode or existing.config.mode,
    )

    (project_root / "maestro.yml").write_text(render_maestro_config(config))
    ensure_default_docs(project_root, config.locale, overwrite_rules=True)

    result = check_project(project_root)
    write_coherence_index(project_root, result.units, result.state.config.locale)
    return result.state


def ensure_default_docs(
    root: str | Path,
    locale: Locale = DEFAULT_LOCALE,
    *,
    overwrite_rules: bool = False,
) -> None:
    """Create base lens docs if missing."""
    project_root = Path(root).expanduser().resolve()
    coherence_dir = project_root / "docs" / "coherence"
    coherence_dir.mkdir(parents=True, exist_ok=True)
    rules_path = coherence_dir / "rules.md"
    if overwrite_rules or not rules_path.exists():
        rules_path.write_text(default_rules_document(locale))


def write_coherence_index(
    root: str | Path,
    units: tuple[UnitOfCoherence, ...],
    locale: Locale = DEFAULT_LOCALE,
) -> None:
    project_root = Path(root).expanduser().resolve()
    coherence_dir = project_root / "docs" / "coherence"
    coherence_dir.mkdir(parents=True, exist_ok=True)
    (coherence_dir / "index.md").write_text(render_coherence_index(units, locale))


def render_coherence_index(
    units: tuple[UnitOfCoherence, ...],
    locale: Locale = DEFAULT_LOCALE,
) -> str:
    labels = index_labels(locale)
    resolved = tuple(unit for unit in units if unit.status == "resolved")
    open_units = tuple(unit for unit in units if unit.status != "resolved")

    lines = [
        f"# {labels['title']}",
        "",
        labels["description"],
        "",
        f"## {labels['resolved']}",
        "",
    ]
    if resolved:
        for unit in resolved:
            lines.extend(render_unit_summary(unit, labels))
    else:
        lines.append(labels["no_resolved"])

    lines.extend(["", f"## {labels['open']}", ""])
    if open_units:
        for unit in open_units:
            lines.extend(render_unit_summary(unit, labels))
    else:
        lines.append(labels["no_open"])
    lines.append("")
    return "\n".join(lines)


def default_rules_document(locale: Locale = DEFAULT_LOCALE) -> str:
    if locale == "pt-BR":
        return """# Regras de Coerência

## UoC-001: Nome provisório do projeto

Estado esperado:
Todo projeto Maestro tem um nome provisório.

Severidade:
Bloqueante.

Resolução:
Pergunte ao usuário um nome provisório. Depois crie ou atualize `maestro.yml`, `README.md` e `docs/coherence/index.md`.

## UoC-002: Repositório git

Estado esperado:
Todo projeto Maestro deveria ser acompanhado em git.

Severidade:
Importante, não-bloqueante.

Resolução:
Sugira `git init`. Se o usuário adiar, registre a UoC como adiada.
"""

    return """# Coherence Rules

## UoC-001: Project working name

Expected state:
Every Maestro project has a provisional working name.

Severity:
Blocking.

Resolution:
Ask the user for a provisional name. Then create or update `maestro.yml`, `README.md`, and `docs/coherence/index.md`.

## UoC-002: Git repository

Expected state:
Every Maestro project should be tracked in git.

Severity:
Important, non-blocking.

Resolution:
Suggest `git init`. If the user defers, record the UoC as deferred.
"""


def render_cli_report(result: CheckResult) -> str:
    """Render a compact CLI report with the same UX as the POC."""
    locale = result.state.config.locale
    lines: list[str] = []
    for unit in result.units:
        marker = "✓" if unit.status == "resolved" else "!" if unit.severity == "blocking" else "•"
        lines.append(f"{marker} {unit.id} {unit.title}: {localize_status(unit.status, locale)}")
        if unit.gap:
            lines.append(f"  {'lacuna' if locale == 'pt-BR' else 'gap'}: {unit.gap}")
        if unit.suggested_action:
            lines.append(f"  {'ação' if locale == 'pt-BR' else 'action'}: {unit.suggested_action}")

    if not result.has_open_gaps:
        message = (
            "Pronto para avançar - sem gaps de coerência."
            if locale == "pt-BR"
            else "Ready to move - no coherence gaps."
        )
        lines.append(f"✅  {message}")
    elif result.has_blocking_gaps:
        message = (
            "Bloqueado - gaps de coerência precisam de atenção."
            if locale == "pt-BR"
            else "Blocked - coherence gaps need attention."
        )
        lines.append(f"🛑  {message}")
    else:
        message = (
            "Atenção - gaps de coerência não bloqueantes encontrados."
            if locale == "pt-BR"
            else "Attention - non-blocking coherence gaps found."
        )
        lines.append(f"⚠️  {message}")
    return "\n".join(lines) + "\n"


def evaluate_project_name(state: ProjectState) -> UnitOfCoherence:
    semantic_id = "project.working_name"
    text = text_for(state, semantic_id)
    if state.name:
        return resolved_unit(state, semantic_id, text)
    return open_unit(state, semantic_id, "blocking", text)


def evaluate_git_repository(state: ProjectState) -> UnitOfCoherence:
    semantic_id = "project.git_repository"
    text = text_for(state, semantic_id)
    if state.has_git_repository:
        return resolved_unit(state, semantic_id, text)
    return open_unit(state, semantic_id, "important", text)


def resolved_unit(state: ProjectState, semantic_id: str, text: UoCText) -> UnitOfCoherence:
    return UnitOfCoherence(
        id=UOC_DISPLAY_IDS[semantic_id],
        semantic_id=semantic_id,
        title=text.title,
        severity="blocking" if semantic_id == "project.working_name" else "important",
        status="resolved",
        expected_state=text.expected_state,
        observed_state=text.observed_resolved(state),
        evidence=text.evidence_resolved(state),
    )


def open_unit(
    state: ProjectState,
    semantic_id: str,
    severity: UoCSeverity,
    text: UoCText,
) -> UnitOfCoherence:
    return UnitOfCoherence(
        id=UOC_DISPLAY_IDS[semantic_id],
        semantic_id=semantic_id,
        title=text.title,
        severity=severity,
        status="open",
        expected_state=text.expected_state,
        observed_state=text.observed_open,
        gap=text.gap_open,
        evidence=text.evidence_open(state),
        suggested_action=text.suggested_action_open[state.config.mode],
    )


def text_for(state: ProjectState, semantic_id: str) -> UoCText:
    return TEXT[state.config.locale][semantic_id]


def parse_maestro_config(config: str) -> MaestroConfig:
    return MaestroConfig(
        name=parse_scalar(config, "name"),
        locale=parse_locale(parse_scalar(config, "locale")) or DEFAULT_LOCALE,
        mode=parse_mode(parse_scalar(config, "mode")) or DEFAULT_MODE,
    )


def parse_scalar(config: str, key: str) -> str | None:
    match = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", config, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def parse_locale(value: str | None) -> Locale | None:
    return value if value in ("en-US", "pt-BR") else None  # type: ignore[return-value]


def parse_mode(value: str | None) -> AudienceMode | None:
    return value if value in ("technical", "non-technical") else None  # type: ignore[return-value]


def parse_readme_title(readme: str) -> str | None:
    match = re.search(r"^#\s+(.+)$", readme, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def render_maestro_config(config: MaestroConfig) -> str:
    lines: list[str] = []
    if config.name:
        lines.append(f"name: {quote_yaml_string(config.name)}")
    lines.append(f"locale: {config.locale}")
    lines.append(f"mode: {config.mode}")
    lines.append("")
    return "\n".join(lines)


def quote_yaml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def index_labels(locale: Locale) -> dict[str, str | Locale]:
    if locale == "pt-BR":
        return {
            "locale": locale,
            "title": "Índice de Coerência",
            "description": "Este arquivo registra Units of Coherence (UoCs) detectadas pelo Maestro.",
            "resolved": "Resolvidas",
            "open": "Abertas",
            "no_resolved": "Nenhuma UoC resolvida ainda.",
            "no_open": "Nenhuma UoC aberta.",
            "status": "Status",
            "severity": "Severidade",
            "semantic_id": "ID semântico",
            "expected": "Esperado",
            "observed": "Observado",
            "gap": "Lacuna",
            "suggested_action": "Ação sugerida",
            "evidence": "Evidência",
        }
    return {
        "locale": locale,
        "title": "Coherence Index",
        "description": "This file records Units of Coherence (UoCs) detected by Maestro.",
        "resolved": "Resolved",
        "open": "Open",
        "no_resolved": "No resolved UoCs yet.",
        "no_open": "No open UoCs.",
        "status": "Status",
        "severity": "Severity",
        "semantic_id": "Semantic ID",
        "expected": "Expected",
        "observed": "Observed",
        "gap": "Gap",
        "suggested_action": "Suggested action",
        "evidence": "Evidence",
    }


def render_unit_summary(unit: UnitOfCoherence, labels: dict[str, str | Locale]) -> list[str]:
    locale = labels["locale"]  # type: ignore[assignment]
    lines = [
        f"- **{unit.id}: {unit.title}**",
        f"  - {labels['status']}: {localize_status(unit.status, locale)}",
        f"  - {labels['severity']}: {localize_severity(unit.severity, locale)}",
        f"  - {labels['semantic_id']}: {unit.semantic_id}",
        f"  - {labels['expected']}: {unit.expected_state}",
        f"  - {labels['observed']}: {unit.observed_state}",
    ]
    if unit.gap:
        lines.append(f"  - {labels['gap']}: {unit.gap}")
    if unit.suggested_action:
        lines.append(f"  - {labels['suggested_action']}: {unit.suggested_action}")
    lines.append(f"  - {labels['evidence']}:")
    lines.extend(f"    - {item}" for item in unit.evidence)
    return lines


def localize_status(status: str, locale: Locale) -> str:
    if locale == "pt-BR":
        return {
            "open": "aberta",
            "resolved": "resolvida",
            "deferred": "adiada",
            "accepted": "aceita",
        }.get(status, status)
    return status


def localize_severity(severity: str, locale: Locale) -> str:
    if locale == "pt-BR":
        return {
            "blocking": "bloqueante",
            "important": "importante",
            "optional": "opcional",
        }.get(severity, severity)
    return severity
