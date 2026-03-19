"""End-to-end integration tests for project context flow.

Tests the full project context flow from detection → registration →
context building → spawn enrichment.
"""

import subprocess
import time
from pathlib import Path

import pytest

from openclaw_enhance.project.context import build_project_context, resolve_project_context
from openclaw_enhance.project.detector import ProjectInfo, ProjectKind, ProjectType, detect_project
from openclaw_enhance.project.git_ops import gather_git_context, should_auto_commit
from openclaw_enhance.project.registry import ProjectRegistry


def _create_python_repo(path: Path, name: str) -> Path:
    """Helper to create a Python git repository."""
    path.mkdir(parents=True, exist_ok=True)

    # Create pyproject.toml
    pyproject = path / "pyproject.toml"
    pyproject.write_text(f"""[project]
name = "{name}"
version = "1.0.0"
description = "Test project {name}"
""")

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=path, check=True, capture_output=True
    )

    return path


class TestFullContextFlow:
    """Test complete end-to-end context flow."""

    def test_full_end_to_end_context_flow(self, tmp_path: Path):
        """Full flow: detect → register → build context."""
        # Create tmp git repo with pyproject.toml
        repo_path = _create_python_repo(tmp_path / "test_repo", "test-project")

        # detect_project → returns python project
        project_info = detect_project(repo_path)
        assert project_info is not None
        assert project_info.type == ProjectType.python
        assert project_info.kind == ProjectKind.permanent

        # registry.register → stores project
        registry = ProjectRegistry(tmp_path / "registry.json")
        registry.register(project_info, kind=ProjectKind.permanent.value)

        # build_project_context → returns full context
        context = build_project_context(repo_path, registry)

        # Assert: context has project_id, project_type=python, git_context with commits
        assert context["project_id"] == str(repo_path.resolve())
        assert context["project_type"] == "python"
        assert context["git_context"] is not None
        assert len(context["git_context"]["recent_commits"]) >= 1
        assert context["git_context"]["branch"] is not None

    def test_full_flow_with_explicit_path_override(self, tmp_path: Path):
        """Full flow respects explicit path overrides."""
        # Create two projects
        repo1 = _create_python_repo(tmp_path / "repo1", "repo1")
        repo2 = _create_python_repo(tmp_path / "repo2", "repo2")

        registry = ProjectRegistry(tmp_path / "registry.json")

        # Register both
        info1 = detect_project(repo1)
        info2 = detect_project(repo2)
        registry.register(info1, kind=ProjectKind.permanent.value)
        registry.register(info2, kind=ProjectKind.permanent.value)

        # Build context with explicit path to repo2
        context = build_project_context(repo2, registry)

        # Should use explicit path (repo2)
        assert context["project_id"] == str(repo2.resolve())


class TestPermanentProjectOccupancy:
    """Test permanent project locking behavior."""

    def test_permanent_project_occupancy_prevents_concurrent_access(self, tmp_path: Path):
        """Permanent project occupancy prevents concurrent access."""
        # Create and register permanent project
        repo_path = _create_python_repo(tmp_path / "repo", "test-project")
        registry = ProjectRegistry(tmp_path / "registry.json")
        project_info = detect_project(repo_path)
        registry.register(project_info, kind=ProjectKind.permanent.value)

        # acquire_for_work(path, "orch-1") → True
        acquired1, owner1 = registry.acquire_for_work(repo_path, "orch-1")
        assert acquired1 is True
        assert owner1 is None

        # acquire_for_work(path, "orch-2") → False with owner
        acquired2, owner2 = registry.acquire_for_work(repo_path, "orch-2")
        assert acquired2 is False
        assert owner2 == "orch-1"

        # release + re-acquire → True
        registry.release_after_work(repo_path, "orch-1")
        acquired3, owner3 = registry.acquire_for_work(repo_path, "orch-2")
        assert acquired3 is True


class TestTemporaryProjectLocking:
    """Test temporary project locking behavior."""

    def test_temporary_project_has_no_lock(self, tmp_path: Path):
        """Temporary project has no lock."""
        # Create temporary project structure
        temp_path = tmp_path / "temp_project"
        temp_path.mkdir()
        (temp_path / "pyproject.toml").write_text('[project]\nname = "temp"\n')

        registry = ProjectRegistry(tmp_path / "registry.json")
        project_info = detect_project(temp_path)
        # Register as temporary
        registry.register(project_info, kind=ProjectKind.temporary.value)

        # acquire_for_work(path, "orch-1") → True
        acquired1, _ = registry.acquire_for_work(temp_path, "orch-1")
        assert acquired1 is True

        # acquire_for_work(path, "orch-2") → True (no lock for temp)
        acquired2, _ = registry.acquire_for_work(temp_path, "orch-2")
        assert acquired2 is True


class TestResolutionChainPrecedence:
    """Test context resolution chain precedence."""

    def test_resolution_chain_precedence(self, tmp_path: Path):
        """Resolution chain: explicit path → active_project → detect → 'default'."""
        # Create projects
        explicit_repo = _create_python_repo(tmp_path / "explicit", "explicit-project")
        active_repo = _create_python_repo(tmp_path / "active", "active-project")
        detect_repo = _create_python_repo(tmp_path / "detect", "detect-project")

        registry = ProjectRegistry(tmp_path / "registry.json")
        explicit_info = detect_project(explicit_repo)
        active_info = detect_project(active_repo)
        detect_info = detect_project(detect_repo)
        registry.register(explicit_info, kind=ProjectKind.permanent.value)
        registry.register(active_info, kind=ProjectKind.permanent.value)
        registry.register(detect_info, kind=ProjectKind.permanent.value)

        # 1. Explicit path (first arg to resolve_project_context)
        context1 = resolve_project_context(explicit_repo, registry, active_project=None)
        assert context1["project_id"] == str(explicit_repo.resolve())

        # 2. active_project parameter when explicit path not in registry
        empty_path = tmp_path / "empty_for_active"
        empty_path.mkdir()
        context2 = resolve_project_context(
            empty_path, registry, active_project=str(active_repo.resolve())
        )
        assert context2["project_id"] == str(active_repo.resolve())

        # 3. Detect from cwd when neither explicit nor active
        empty_path2 = tmp_path / "empty_for_detect"
        empty_path2.mkdir()
        # Create a project at detect_repo path and use it as cwd
        context3 = resolve_project_context(detect_repo, registry, active_project=None)
        assert context3["project_id"] == str(detect_repo.resolve())

        # 4. Default fallback for unknown directory
        empty_path3 = tmp_path / "empty_default"
        empty_path3.mkdir()
        context4 = resolve_project_context(empty_path3, registry, active_project=None)
        assert context4["project_id"] == "default"


class TestStaleDetection:
    """Test stale detection and re-detection."""

    def test_stale_detection_and_re_detect(self, tmp_path: Path):
        """Modify project file should mark as stale, re-detect updates metadata."""
        # Create project with pyproject.toml
        repo_path = _create_python_repo(tmp_path / "repo", "test-project")
        pyproject = repo_path / "pyproject.toml"

        registry = ProjectRegistry(tmp_path / "registry.json")
        project_info = detect_project(repo_path)
        registry.register(project_info, kind=ProjectKind.permanent.value)

        # Verify initially not stale
        assert registry.is_stale(repo_path) is False

        # Wait a bit for mtime to change
        time.sleep(0.1)

        # Modify pyproject.toml (touch with different mtime)
        content = pyproject.read_text()
        pyproject.write_text(content + "\n# Modified")

        # registry.is_stale → True
        assert registry.is_stale(repo_path) is True

        # Re-detect project → updates metadata
        new_info = detect_project(repo_path)
        registry.register(new_info, kind=ProjectKind.permanent.value)

        # Should not be stale after re-registration
        assert registry.is_stale(repo_path) is False


class TestGitContextInDispatch:
    """Test git context gathering in dispatch scenarios."""

    def test_git_context_in_dispatch(self, tmp_path: Path):
        """Create git repo with 3 commits, verify context has all commits."""
        repo_path = tmp_path / "git_repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create 3 commits
        for i in range(3):
            file_path = repo_path / f"file{i}.txt"
            file_path.write_text(f"Content {i}")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"Commit {i + 1}"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

        # Call gather_git_context
        git_context = gather_git_context(repo_path)

        # Assert: recent_commits has 3 entries, branch is set, status is clean
        assert len(git_context["recent_commits"]) == 3
        assert git_context["branch"] is not None
        assert git_context["status"] == "clean"

    def test_git_context_dirty_repo(self, tmp_path: Path):
        """Dirty repo should have status='dirty'."""
        repo_path = _create_python_repo(tmp_path / "dirty_repo", "dirty-project")

        # Make uncommitted change
        (repo_path / "uncommitted.txt").write_text("uncommitted content")

        # Call gather_git_context
        git_context = gather_git_context(repo_path)

        # Assert: status is dirty
        assert git_context["status"] == "dirty"


class TestAutoCommitBehavior:
    """Test auto-commit behavior detection."""

    def test_auto_commit_clean_repo(self, tmp_path: Path):
        """Clean repo with remote should allow auto-commit."""
        repo_path = _create_python_repo(tmp_path / "clean", "clean-project")

        # Add a fake remote (required for auto-commit)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/test/repo.git"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # should_auto_commit → (True, "")
        result, reason = should_auto_commit(repo_path)
        assert result is True
        assert reason == ""

    def test_auto_commit_no_remote(self, tmp_path: Path):
        """Repo without remote should not allow auto-commit."""
        repo_path = _create_python_repo(tmp_path / "no_remote", "no-remote-project")

        # should_auto_commit → (False, "no remote configured")
        result, reason = should_auto_commit(repo_path)
        assert result is False
        assert "no remote" in reason.lower()

    def test_auto_commit_restricted_paths_blocks(self, tmp_path: Path):
        """Changes outside allowed_paths should prevent auto-commit."""
        repo_path = _create_python_repo(tmp_path / "restricted", "restricted-project")

        # Add remote
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/test/repo.git"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create src directory and allowed paths
        src_dir = repo_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("print('hello')")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add src"], cwd=repo_path, check=True, capture_output=True
        )

        # Make a change outside allowed_paths
        other_dir = repo_path / "other"
        other_dir.mkdir()
        (other_dir / "file.txt").write_text("outside allowed paths")

        # should_auto_commit with restricted allowed_paths → (False, ...)
        result, reason = should_auto_commit(repo_path, allowed_paths=[src_dir])
        assert result is False
        assert "outside allowed paths" in reason

    def test_auto_commit_allowed_paths_match(self, tmp_path: Path):
        """Changes within allowed_paths should allow auto-commit."""
        repo_path = _create_python_repo(tmp_path / "allowed", "allowed-project")

        # Add remote
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/test/repo.git"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create src directory
        src_dir = repo_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("print('hello')")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add src"], cwd=repo_path, check=True, capture_output=True
        )

        # Make a change within allowed_paths
        (src_dir / "utils.py").write_text("def helper(): pass")

        # should_auto_commit with matching allowed_paths → (True, "")
        result, reason = should_auto_commit(repo_path, allowed_paths=[src_dir])
        assert result is True
        assert reason == ""
