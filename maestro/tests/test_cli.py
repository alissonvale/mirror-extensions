"""Tests for Maestro extension CLI handlers."""

from __future__ import annotations

from src.cli import cmd_check, cmd_configure, cmd_init

from tests.conftest import seed_journey


def _check_runs(api):
    return api.read("SELECT * FROM ext_maestro_check_runs ORDER BY created_at").fetchall()


def test_init_resolves_project_from_journey_and_records_check_run(maestro_api, tmp_path, capsys):
    seed_journey(maestro_api, "maestro", tmp_path)

    rc = cmd_init(maestro_api, ["--journey", "maestro", "--name", "Maestro"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "Project working name: resolved" in out
    assert (tmp_path / "maestro.yml").exists()

    runs = _check_runs(maestro_api)
    assert len(runs) == 1
    assert runs[0]["journey_id"] == "maestro"
    assert runs[0]["project_root"] == str(tmp_path.resolve())
    assert runs[0]["open_count"] == 1
    assert runs[0]["important_count"] == 1


def test_check_updates_index_and_records_history(maestro_api, tmp_path, capsys):
    seed_journey(maestro_api, "maestro", tmp_path)
    cmd_init(maestro_api, ["--journey", "maestro", "--name", "Maestro"])
    capsys.readouterr()

    rc = cmd_check(maestro_api, ["--journey", "maestro"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "Git repository: open" in out
    assert (tmp_path / "docs" / "coherence" / "index.md").exists()
    assert len(_check_runs(maestro_api)) == 2


def test_configure_pt_br_changes_report_surface(maestro_api, tmp_path, capsys):
    seed_journey(maestro_api, "maestro", tmp_path)

    rc = cmd_configure(
        maestro_api,
        ["--journey", "maestro", "--locale", "pt-BR", "--mode", "non-technical"],
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "Configured Maestro project: locale=pt-BR, mode=non-technical" in out
    assert "Nome provisório do projeto: aberta" in out
    assert "Bloqueado" in out


def test_check_returns_error_when_journey_has_no_project_path(maestro_api, capsys):
    seed_journey(maestro_api, "maestro", None)

    rc = cmd_check(maestro_api, ["--journey", "maestro"])

    captured = capsys.readouterr()
    assert rc == 1
    assert "has no project_path configured" in captured.err
