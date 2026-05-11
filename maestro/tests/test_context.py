"""Tests for the Maestro Mirror Mode context provider."""

from __future__ import annotations

from dataclasses import dataclass

from src.coherence import resolve_project_name
from src.context import provide_coherence_status

from tests.conftest import seed_journey


@dataclass(frozen=True)
class _Ctx:
    persona_id: str | None = None
    journey_id: str | None = "maestro"
    user: str = "test-user"
    query: str | None = None
    binding_kind: str = "journey"
    binding_target: str | None = "maestro"


def test_provider_always_injects_status_for_bound_journey(maestro_api, tmp_path):
    seed_journey(maestro_api, "maestro", tmp_path)
    resolve_project_name(tmp_path, "Maestro")

    out = provide_coherence_status(maestro_api, _Ctx(journey_id="maestro"))

    assert out is not None
    assert "Maestro Coherence Status" in out
    assert str(tmp_path.resolve()) in out
    assert "Git repository" in out
    assert "Non-blocking coherence gaps" in out


def test_provider_injects_no_gap_message_when_all_base_uocs_resolved(maestro_api, tmp_path):
    seed_journey(maestro_api, "maestro", tmp_path)
    resolve_project_name(tmp_path, "Maestro")
    (tmp_path / ".git").mkdir()

    out = provide_coherence_status(maestro_api, _Ctx(journey_id="maestro"))

    assert out is not None
    assert "No open coherence gaps" in out


def test_provider_returns_none_when_journey_has_no_project_path(maestro_api):
    seed_journey(maestro_api, "maestro", None)

    out = provide_coherence_status(maestro_api, _Ctx(journey_id="maestro"))

    assert out is None


def test_provider_does_not_record_check_runs(maestro_api, tmp_path):
    """Prompt injection checks are live context, not durable check history."""
    seed_journey(maestro_api, "maestro", tmp_path)
    resolve_project_name(tmp_path, "Maestro")

    provide_coherence_status(maestro_api, _Ctx(journey_id="maestro"))

    rows = maestro_api.read("SELECT * FROM ext_maestro_check_runs").fetchall()
    assert rows == []
