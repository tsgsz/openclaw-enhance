"""Integration tests for project occupancy locking via ProjectRegistry.

Tests acquire_for_work() and release_after_work() which bridge
registry (knows project kind) with runtime state (manages occupancy locks).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openclaw_enhance.project.registry import ProjectRegistry


@dataclass
class _FakeProjectInfo:
    """Minimal stand-in for ProjectInfo used by register()."""

    path: str
    name: str = "test-project"
    type: str = "python"
    subtype: str | None = None
    indicator_file: str = "pyproject.toml"
    indicator_mtime: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


def _make_registry(tmp_path: Path) -> ProjectRegistry:
    """Create an isolated ProjectRegistry backed by tmp_path."""
    return ProjectRegistry(tmp_path / "registry.json")


def _make_project_dir(tmp_path: Path, name: str = "myproj") -> Path:
    """Create a fake project directory with an indicator file."""
    proj = tmp_path / name
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    return proj


class TestAcquirePermanentProjectSuccess:
    """Permanent project can be acquired by first session."""

    def test_acquire_permanent_project_success(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path)
        proj = _make_project_dir(tmp_path)
        info = _FakeProjectInfo(path=str(proj))
        reg.register(info, kind="permanent")

        user_home = tmp_path / "home"
        user_home.mkdir()

        ok, owner = reg.acquire_for_work(proj, "sess-1", user_home=user_home)

        assert ok is True
        assert owner is None


class TestAcquirePermanentProjectBlocked:
    """Second session is blocked when permanent project is already occupied."""

    def test_acquire_permanent_project_blocked(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path)
        proj = _make_project_dir(tmp_path)
        info = _FakeProjectInfo(path=str(proj))
        reg.register(info, kind="permanent")

        user_home = tmp_path / "home"
        user_home.mkdir()

        ok1, _ = reg.acquire_for_work(proj, "sess-1", user_home=user_home)
        assert ok1 is True

        ok2, owner = reg.acquire_for_work(proj, "sess-2", user_home=user_home)
        assert ok2 is False
        assert owner == "sess-1"


class TestAcquireTemporaryProjectNoLock:
    """Temporary projects never lock — multiple sessions succeed."""

    def test_acquire_temporary_project_no_lock(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path)
        proj = _make_project_dir(tmp_path)
        info = _FakeProjectInfo(path=str(proj))
        reg.register(info, kind="temporary")

        user_home = tmp_path / "home"
        user_home.mkdir()

        ok1, owner1 = reg.acquire_for_work(proj, "sess-1", user_home=user_home)
        ok2, owner2 = reg.acquire_for_work(proj, "sess-2", user_home=user_home)

        assert ok1 is True
        assert owner1 is None
        assert ok2 is True
        assert owner2 is None


class TestReleaseAndReacquire:
    """After release, another session can acquire the permanent project."""

    def test_release_and_reacquire(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path)
        proj = _make_project_dir(tmp_path)
        info = _FakeProjectInfo(path=str(proj))
        reg.register(info, kind="permanent")

        user_home = tmp_path / "home"
        user_home.mkdir()

        ok1, _ = reg.acquire_for_work(proj, "sess-1", user_home=user_home)
        assert ok1 is True

        released = reg.release_after_work(proj, "sess-1", user_home=user_home)
        assert released is True

        ok2, owner = reg.acquire_for_work(proj, "sess-2", user_home=user_home)
        assert ok2 is True
        assert owner is None


class TestAcquireUnregisteredProject:
    """Acquiring a project not in the registry returns (False, None)."""

    def test_acquire_unregistered_project(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path)
        unknown = tmp_path / "nonexistent"
        unknown.mkdir()

        user_home = tmp_path / "home"
        user_home.mkdir()

        ok, owner = reg.acquire_for_work(unknown, "sess-1", user_home=user_home)
        assert ok is False
        assert owner is None
