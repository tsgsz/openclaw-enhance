from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from openclaw_enhance.project.git_ops import (
    auto_commit,
    gather_git_context,
    should_auto_commit,
)


def _init_git_repo(path: Path, *, commits: int = 0) -> None:
    def run(args):
        return subprocess.run(args, cwd=str(path), capture_output=True, text=True, check=True)

    run(["git", "init", "-b", "main"])
    run(["git", "config", "user.email", "test@test.com"])
    run(["git", "config", "user.name", "Test"])
    for i in range(commits):
        (path / f"file{i}.txt").write_text(f"content {i}")
        run(["git", "add", "."])
        run(["git", "commit", "-m", f"commit {i}"])


def _add_remote(path: Path, url: str = "https://github.com/test/repo.git") -> None:
    subprocess.run(
        ["git", "remote", "add", "origin", url],
        cwd=str(path),
        capture_output=True,
        text=True,
        check=True,
    )


def test_gather_git_context_real_repo(tmp_path: Path) -> None:
    _init_git_repo(tmp_path, commits=3)

    ctx = gather_git_context(tmp_path)

    assert ctx is not None
    assert len(ctx["recent_commits"]) == 3
    assert ctx["branch"] in ("main", "master")
    assert ctx["status"] == "clean"
    assert all("hash" in c and "message" in c for c in ctx["recent_commits"])


def test_gather_git_context_not_a_repo(tmp_path: Path) -> None:
    assert gather_git_context(tmp_path) is None


def test_gather_git_context_gh_fallback(tmp_path: Path) -> None:
    _init_git_repo(tmp_path, commits=1)

    original_run = subprocess.run

    def _mock_run(args, **kwargs):
        if args[0] == "gh":
            raise FileNotFoundError("gh not found")
        return original_run(args, **kwargs)

    with patch("subprocess.run", side_effect=_mock_run):
        ctx = gather_git_context(tmp_path)

    assert ctx is not None
    assert ctx["gh_available"] is False
    assert ctx["open_prs"] == []


def test_should_auto_commit_clean_repo_with_remote(tmp_path: Path) -> None:
    _init_git_repo(tmp_path, commits=1)
    _add_remote(tmp_path)

    ok, reason = should_auto_commit(tmp_path)

    assert ok is True
    assert reason == ""


def test_should_auto_commit_detached_head(tmp_path: Path) -> None:
    _init_git_repo(tmp_path, commits=2)
    _add_remote(tmp_path)

    # detach HEAD
    subprocess.run(
        ["git", "checkout", "--detach"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )

    ok, reason = should_auto_commit(tmp_path)

    assert ok is False
    assert "detach" in reason.lower()


def test_should_auto_commit_file_outside_allowed_paths(tmp_path: Path) -> None:
    _init_git_repo(tmp_path, commits=1)
    _add_remote(tmp_path)

    # create changes outside allowed paths
    (tmp_path / "outside.txt").write_text("rogue change")
    subprocess.run(
        ["git", "add", "outside.txt"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )

    allowed = [tmp_path / "src"]
    ok, reason = should_auto_commit(tmp_path, allowed_paths=allowed)

    assert ok is False
    assert "outside" in reason.lower() or "allowed" in reason.lower()


def test_auto_commit_with_changes(tmp_path: Path) -> None:
    _init_git_repo(tmp_path, commits=1)
    _add_remote(tmp_path)

    (tmp_path / "new.txt").write_text("new content")

    result = auto_commit(tmp_path, "test commit")

    assert result is True

    # verify commit exists
    log = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "test commit" in log.stdout


def test_auto_commit_no_changes(tmp_path: Path) -> None:
    _init_git_repo(tmp_path, commits=1)
    _add_remote(tmp_path)

    result = auto_commit(tmp_path, "nothing to commit")

    assert result is False
