"""Tests for the base Maestro coherence engine."""

from __future__ import annotations

from src.coherence import (
    check_project,
    configure_project,
    find_git_repository_path,
    render_cli_report,
    render_coherence_index,
    resolve_project_name,
)


def test_empty_project_has_open_blocking_uoc_for_working_name(tmp_path):
    result = check_project(tmp_path)
    name_unit = next(unit for unit in result.units if unit.id == "UoC-001")
    git_unit = next(unit for unit in result.units if unit.id == "UoC-002")

    assert name_unit.status == "open"
    assert name_unit.severity == "blocking"
    assert "working name" in (name_unit.gap or "")
    assert git_unit.status == "open"
    assert git_unit.severity == "important"
    assert result.has_blocking_gaps is True


def test_resolving_project_name_creates_config_readme_and_index(tmp_path):
    result = resolve_project_name(tmp_path, "Maestro POC")

    name_unit = next(unit for unit in result.units if unit.id == "UoC-001")
    git_unit = next(unit for unit in result.units if unit.id == "UoC-002")

    assert name_unit.status == "resolved"
    assert git_unit.status == "open"
    assert (tmp_path / "maestro.yml").read_text().startswith('name: "Maestro POC"')
    assert (tmp_path / "README.md").read_text() == "# Maestro POC\n"
    index = (tmp_path / "docs" / "coherence" / "index.md").read_text()
    assert "UoC-001: Project working name" in index
    assert "UoC-002: Git repository" in index


def test_git_repository_uoc_resolves_when_dot_git_exists(tmp_path):
    resolve_project_name(tmp_path, "Versioned")
    (tmp_path / ".git").mkdir()

    result = check_project(tmp_path)
    git_unit = next(unit for unit in result.units if unit.id == "UoC-002")

    assert git_unit.status == "resolved"
    assert git_unit.evidence == (f".git found at {tmp_path / '.git'}",)
    assert result.has_open_gaps is False
    assert "Ready to move" in render_cli_report(result)


def test_git_repository_uoc_resolves_when_project_is_inside_monorepo(tmp_path):
    repo = tmp_path / "repo"
    project = repo / "packages" / "maestro"
    project.mkdir(parents=True)
    (repo / ".git").mkdir()
    resolve_project_name(project, "Maestro Extension")

    assert find_git_repository_path(project) == repo / ".git"
    result = check_project(project)
    git_unit = next(unit for unit in result.units if unit.id == "UoC-002")

    assert git_unit.status == "resolved"
    assert str(repo / ".git") in git_unit.observed_state


def test_configure_stores_pt_br_locale_and_mode_without_requiring_name(tmp_path):
    state = configure_project(tmp_path, locale="pt-BR", mode="non-technical")

    assert state.config.name is None
    assert state.config.locale == "pt-BR"
    assert state.config.mode == "non-technical"

    config = (tmp_path / "maestro.yml").read_text()
    assert "locale: pt-BR" in config
    assert "mode: non-technical" in config

    result = check_project(tmp_path)
    name_unit = next(unit for unit in result.units if unit.id == "UoC-001")
    assert name_unit.title == "Nome provisório do projeto"
    assert "Escolha um nome provisório" in (name_unit.suggested_action or "")


def test_coherence_index_renders_pt_br_surface(tmp_path):
    result = resolve_project_name(
        tmp_path,
        "Projeto Maestro",
        locale="pt-BR",
        mode="technical",
    )
    index = render_coherence_index(result.units, result.state.config.locale)

    assert "# Índice de Coerência" in index
    assert "Nome provisório do projeto" in index
    assert "Repositório git" in index
    assert "ID semântico: project.working_name" in index
