import json
from pathlib import Path

import pytest

from openclaw_enhance.project.context import build_project_context, resolve_project_context
from openclaw_enhance.project.detector import ProjectKind, detect_project
from openclaw_enhance.project.registry import ProjectRegistry


@pytest.fixture
def registry(tmp_path):
    reg_path = tmp_path / "registry.json"
    return ProjectRegistry(reg_path)


def test_build_project_context_registered(tmp_path, registry):
    # Setup: create a python project
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    (project_dir / "pyproject.toml").write_text('[project]\nname = "my-project"', encoding="utf-8")

    info = detect_project(project_dir)
    registry.register(info, kind=ProjectKind.permanent.value)

    context = build_project_context(project_dir, registry)

    assert context["project_id"] == str(project_dir.resolve())
    assert context["project_name"] == "my-project"
    assert context["project_type"] == "python"
    assert context["project_kind"] == "permanent"
    assert context["working_dir"] == str(project_dir.resolve())
    assert "git_context" in context
    assert isinstance(context["metadata"], dict)

    # Evidence for task-4-full-context.txt
    evidence_path = Path(".sisyphus/evidence/task-4-full-context.txt")
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(context, indent=2), encoding="utf-8")


def test_resolve_explicit_path_wins(tmp_path, registry):
    project_dir = tmp_path / "explicit-project"
    project_dir.mkdir()
    (project_dir / "pyproject.toml").write_text('[project]\nname = "explicit"', encoding="utf-8")

    info = detect_project(project_dir)
    registry.register(info, kind=ProjectKind.permanent.value)

    context = resolve_project_context(project_dir, registry)
    assert context["project_name"] == "explicit"
    assert context["project_kind"] == "permanent"


def test_resolve_active_project(tmp_path, registry):
    # Register a project
    project_dir = tmp_path / "active-project"
    project_dir.mkdir()
    (project_dir / "pyproject.toml").write_text('[project]\nname = "active"', encoding="utf-8")
    info = detect_project(project_dir)
    registry.register(info, kind=ProjectKind.permanent.value)

    # Call resolve with a different path but active_project set to the registered path
    other_dir = tmp_path / "other"
    other_dir.mkdir()

    context = resolve_project_context(other_dir, registry, active_project=str(project_dir))
    assert context["project_name"] == "active"
    assert context["project_id"] == str(project_dir.resolve())


def test_resolve_fallback_default(tmp_path, registry):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    context = resolve_project_context(empty_dir, registry)
    assert context["project_id"] == "default"
    assert context["project_name"] == "default"
    assert context["project_type"] == "unknown"

    # Evidence for task-4-fallback-default.txt
    evidence_path = Path(".sisyphus/evidence/task-4-fallback-default.txt")
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(context, indent=2), encoding="utf-8")


def test_resolve_auto_register_temp(tmp_path, registry):
    project_dir = tmp_path / "temp-project"
    project_dir.mkdir()
    (project_dir / "pyproject.toml").write_text('[project]\nname = "temp"', encoding="utf-8")

    # Registry is empty, but project exists on disk
    context = resolve_project_context(project_dir, registry)

    assert context["project_name"] == "temp"
    assert context["project_type"] == "python"
    assert context["project_kind"] == "temporary"

    # Verify it was registered
    assert registry.get(project_dir) is not None
    assert registry.get(project_dir)["kind"] == "temporary"
