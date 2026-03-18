"""Git operations for project context gathering and auto-commit."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

_TIMEOUT = 10


def _run_git(
    args: list[str], project_path: Path, *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(project_path),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
        check=check,
    )


def _is_git_repo(project_path: Path) -> bool:
    result = _run_git(["rev-parse", "--is-inside-work-tree"], project_path, check=False)
    return result.returncode == 0


def _parse_log_lines(raw: str) -> list[dict[str, str]]:
    commits: list[dict[str, str]] = []
    for line in raw.strip().splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2:
            commits.append({"hash": parts[0], "message": parts[1]})
    return commits


def _fetch_open_prs(project_path: Path) -> tuple[list[dict], bool]:
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--limit",
                "5",
                "--json",
                "number,title,headRefName",
            ],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            check=True,
        )
        return json.loads(result.stdout), True
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError):
        return [], False


def gather_git_context(project_path: Path) -> dict | None:
    """Gather git context from a project directory.

    Returns None if project_path is not a git repo. Returns a structured
    dict with recent commits, branch, status, remote, open PRs, and gh
    availability even when ``gh`` CLI is absent.
    """
    if not _is_git_repo(project_path):
        return None

    log_result = _run_git(["log", "--oneline", "-5"], project_path, check=False)
    recent_commits = _parse_log_lines(log_result.stdout) if log_result.returncode == 0 else []

    status_result = _run_git(["status", "--porcelain"], project_path, check=False)
    status = "clean" if not status_result.stdout.strip() else "dirty"

    branch_result = _run_git(["branch", "--show-current"], project_path, check=False)
    branch = branch_result.stdout.strip()

    remote_result = _run_git(["remote", "get-url", "origin"], project_path, check=False)
    remote = remote_result.stdout.strip() if remote_result.returncode == 0 else ""

    open_prs, gh_available = _fetch_open_prs(project_path)

    return {
        "recent_commits": recent_commits,
        "branch": branch,
        "status": status,
        "remote": remote,
        "open_prs": open_prs,
        "gh_available": gh_available,
    }


def should_auto_commit(
    project_path: Path, allowed_paths: list[Path] | None = None
) -> tuple[bool, str]:
    """Check whether auto-commit is safe for the given project.

    Returns ``(True, "")`` when safe, or ``(False, reason)`` explaining
    why auto-commit should be skipped.
    """
    if not _is_git_repo(project_path):
        return False, "not a git repository"

    head_check = _run_git(["symbolic-ref", "HEAD"], project_path, check=False)
    if head_check.returncode != 0:
        return False, "detached HEAD state"

    remote_check = _run_git(["remote", "get-url", "origin"], project_path, check=False)
    if remote_check.returncode != 0:
        return False, "no remote configured"

    if allowed_paths is not None:
        status_result = _run_git(["status", "--porcelain"], project_path, check=False)
        for line in status_result.stdout.strip().splitlines():
            if not line.strip():
                continue
            # porcelain format: XY filename  (or XY -> renamed)
            file_rel = line[3:].split(" -> ")[-1]
            file_abs = (project_path / file_rel).resolve()
            inside = any(
                file_abs == ap or ap in file_abs.parents
                for ap in (p.resolve() for p in allowed_paths)
            )
            if not inside:
                return False, f"changed file outside allowed paths: {file_rel}"

    return True, ""


def auto_commit(project_path: Path, message: str, allowed_paths: list[Path] | None = None) -> bool:
    """Auto-commit changes in the project directory.

    Returns True if a commit was created, False if skipped (pre-check
    failed or nothing to commit).
    """
    ok, _ = should_auto_commit(project_path, allowed_paths)
    if not ok:
        return False

    if allowed_paths is not None:
        for ap in allowed_paths:
            _run_git(["add", str(ap)], project_path, check=False)
    else:
        _run_git(["add", "."], project_path, check=False)

    # check if there are staged changes
    diff_result = _run_git(["diff", "--cached", "--quiet"], project_path, check=False)
    if diff_result.returncode == 0:
        return False

    _run_git(["commit", "-m", message], project_path)
    return True
