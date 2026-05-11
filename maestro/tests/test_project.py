"""Tests for project-root resolution."""

from __future__ import annotations

from src.project import project_path_for_journey, resolve_project_root

from tests.conftest import seed_journey


def test_project_path_for_journey_reads_identity_metadata(maestro_api, tmp_path):
    seed_journey(maestro_api, "maestro", tmp_path)

    assert project_path_for_journey(maestro_api, "maestro") == tmp_path.resolve()


def test_explicit_root_wins_without_assigning_default_journey(maestro_api, tmp_path):
    root, journey_id = resolve_project_root(maestro_api, root=tmp_path, journey_id=None)

    assert root == tmp_path.resolve()
    assert journey_id is None


def test_missing_root_defaults_to_maestro_journey(maestro_api, tmp_path):
    seed_journey(maestro_api, "maestro", tmp_path)

    root, journey_id = resolve_project_root(maestro_api, root=None, journey_id=None)

    assert root == tmp_path.resolve()
    assert journey_id == "maestro"
