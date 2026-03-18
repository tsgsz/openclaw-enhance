from __future__ import annotations

import json
import os
import time
from pathlib import Path

from openclaw_enhance.project.detector import ProjectInfo, ProjectKind, ProjectType
from openclaw_enhance.project.registry import (
    REGISTRY_FILENAME,
    REGISTRY_SCHEMA_VERSION,
    ProjectRegistry,
)


def _make_project_dir(tmp_path: Path, name: str = "my-proj") -> Path:
    project_dir = tmp_path / name
    project_dir.mkdir(parents=True, exist_ok=True)
    indicator = project_dir / "pyproject.toml"
    indicator.write_text('[tool.poetry]\nname = "my-proj"\n')
    return project_dir


def _make_project_info(project_dir: Path) -> ProjectInfo:
    indicator = project_dir / "pyproject.toml"
    return ProjectInfo(
        path=project_dir.resolve(),
        name=project_dir.name,
        type=ProjectType.python,
        subtype="poetry",
        indicator_file="pyproject.toml",
        indicator_mtime=indicator.stat().st_mtime,
    )


def test_register_and_get_roundtrip(tmp_path: Path) -> None:
    project_dir = _make_project_dir(tmp_path)
    info = _make_project_info(project_dir)
    registry_file = tmp_path / REGISTRY_FILENAME
    registry = ProjectRegistry(registry_file)

    key = registry.register(info, kind="permanent")
    result = registry.get(project_dir)

    assert result is not None
    assert result["name"] == "my-proj"
    assert result["type"] == "python"
    assert result["kind"] == "permanent"
    assert key == str(project_dir.resolve())


def test_list_projects_returns_all_registered(tmp_path: Path) -> None:
    registry_file = tmp_path / REGISTRY_FILENAME
    registry = ProjectRegistry(registry_file)

    for name in ("proj-a", "proj-b", "proj-c"):
        d = _make_project_dir(tmp_path, name)
        registry.register(_make_project_info(d), kind="permanent")

    projects = registry.list_projects()
    assert len(projects) == 3
    names = {p["name"] for p in projects}
    assert names == {"proj-a", "proj-b", "proj-c"}


def test_list_projects_filters_by_kind(tmp_path: Path) -> None:
    registry_file = tmp_path / REGISTRY_FILENAME
    registry = ProjectRegistry(registry_file)

    perm_dir = _make_project_dir(tmp_path, "perm-proj")
    temp_dir = _make_project_dir(tmp_path, "temp-proj")
    registry.register(_make_project_info(perm_dir), kind="permanent")
    registry.register(_make_project_info(temp_dir), kind="temporary")

    permanent = registry.list_projects(kind="permanent")
    temporary = registry.list_projects(kind="temporary")

    assert len(permanent) == 1
    assert permanent[0]["name"] == "perm-proj"
    assert len(temporary) == 1
    assert temporary[0]["name"] == "temp-proj"


def test_canonical_path_dedup(tmp_path: Path) -> None:
    project_dir = _make_project_dir(tmp_path, "dedup-proj")
    info = _make_project_info(project_dir)
    registry_file = tmp_path / REGISTRY_FILENAME
    registry = ProjectRegistry(registry_file)

    registry.register(info, kind="permanent")

    # Register again via a relative-style path (still resolves to same)
    info_again = ProjectInfo(
        path=project_dir,  # not .resolve() explicitly, registry should resolve
        name="dedup-proj-alias",
        type=ProjectType.python,
        subtype="poetry",
        indicator_file="pyproject.toml",
        indicator_mtime=info.indicator_mtime,
    )
    registry.register(info_again, kind="permanent")

    projects = registry.list_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "dedup-proj-alias"  # last write wins


def test_v1_to_v2_migration(tmp_path: Path) -> None:
    registry_file = tmp_path / REGISTRY_FILENAME
    v1_data = {"version": "1.0.0", "projects": []}
    registry_file.write_text(json.dumps(v1_data), encoding="utf-8")

    registry = ProjectRegistry(registry_file)
    data = registry.load()

    assert data["schema_version"] == REGISTRY_SCHEMA_VERSION
    assert isinstance(data["projects"], dict)
    assert len(data["projects"]) == 0


def test_corrupt_file_recovery(tmp_path: Path) -> None:
    registry_file = tmp_path / REGISTRY_FILENAME
    registry_file.write_text("{{invalid json content", encoding="utf-8")

    registry = ProjectRegistry(registry_file)

    projects = registry.list_projects()
    assert projects == []


def test_is_stale_detects_modified_indicator(tmp_path: Path) -> None:
    project_dir = _make_project_dir(tmp_path)
    info = _make_project_info(project_dir)
    registry_file = tmp_path / REGISTRY_FILENAME
    registry = ProjectRegistry(registry_file)
    registry.register(info, kind="permanent")

    assert registry.is_stale(project_dir) is False

    # Modify the indicator file to change its mtime
    time.sleep(0.05)
    indicator = project_dir / "pyproject.toml"
    indicator.write_text('[tool.poetry]\nname = "updated"\n')

    assert registry.is_stale(project_dir) is True


def test_atomic_save_cleans_up_tmp(tmp_path: Path) -> None:
    registry_file = tmp_path / REGISTRY_FILENAME
    registry = ProjectRegistry(registry_file)

    project_dir = _make_project_dir(tmp_path)
    registry.register(_make_project_info(project_dir), kind="permanent")
    registry.save()

    assert registry_file.exists()
    tmp_file = registry_file.parent / f"{REGISTRY_FILENAME}.tmp"
    assert not tmp_file.exists()

    # Verify content is valid JSON
    data = json.loads(registry_file.read_text(encoding="utf-8"))
    assert data["schema_version"] == REGISTRY_SCHEMA_VERSION
    assert len(data["projects"]) == 1


def test_missing_registry_file_creates_empty_state(tmp_path: Path) -> None:
    registry_file = tmp_path / "nonexistent" / REGISTRY_FILENAME

    registry = ProjectRegistry(registry_file)

    projects = registry.list_projects()
    assert projects == []
    result = registry.get(tmp_path / "some-path")
    assert result is None
