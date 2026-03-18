## 2026-03-18 Task: T3 - Git Ops Module

### Patterns
- `git rev-parse --is-inside-work-tree` is the reliable way to check if a path is inside a git repo
- `git symbolic-ref HEAD` returns non-zero in detached HEAD state — good detection mechanism
- `git diff --cached --quiet` returns 0 if no staged changes, non-zero if there are staged changes — use for "nothing to commit" detection
- `git status --porcelain` output format: first 2 chars are status codes, char 3 is space, rest is filename. For renames: `XY old -> new`
- `git log --oneline` format: `{hash} {message}`, split on first space

### Test Infrastructure
- `git init -b main` ensures consistent branch name across environments (some default to "master")
- Must set `git config user.email` and `user.name` before commits in tmp repos
- Mocking `subprocess.run` selectively (only for `gh` commands) requires saving `original_run` and checking `args[0]`
- Tests with real git repos in `tmp_path` are fast (~1s for 8 tests)

### Design Decisions
- `gather_git_context` returns `None` (not empty dict) for non-git paths — clear signal vs "empty context"
- `gh` CLI failure is graceful: `gh_available=False`, `open_prs=[]` — never blocks context gathering
- `should_auto_commit` returns tuple `(bool, str)` — reason string for logging/debugging
- `auto_commit` uses `git diff --cached --quiet` after staging to detect "nothing to commit" rather than parsing porcelain output
- `allowed_paths` check uses `Path.resolve()` + parent traversal for robust containment check
## [2026-03-18] Task: T1
- Implemented project data model and detector.
- Used `tomllib` with fallback to `tomli` for parsing `pyproject.toml`.
- Implemented lazy parsers for `pyproject.toml` and `package.json` to extract project name and metadata.
- `find_project_root` prioritizes `.git` but also falls back to project indicators.
- Verified with 9 unit tests covering various project types and root finding scenarios.

## 2026-03-18 Task: T4 - Project Context Builder

### Patterns
- Resolution chain: explicit path -> active_project -> auto-detect -> default fallback.
- Auto-registration: resolve_project_context() automatically registers detected projects as "temporary" if not already in registry.
- JSON-serializable: All Path objects converted to str() in context dict for downstream consumption (hooks/handlers).

### Design Decisions
- build_project_context() handles three levels: registered, detected-but-unregistered, and ultimate fallback.
- git_context is included in all levels (even "default") if the path happens to be a git repo.
- project_id is the canonical path string for registered/detected projects, but "default" for the ultimate fallback.
- metadata is always a dict, even if empty, to ensure consumer consistency.

### Test Infrastructure
- tmp_path fixture used to create mock project structures (pyproject.toml).
- Evidence generation integrated into tests to capture real-world context shapes.

## 2026-03-18 Task: T5 - Project CLI Command Group

### Patterns
- Click `@cli.group()` for sub-command grouping; `@group.command("name")` for sub-commands.
- Registry path isolation via `OE_REGISTRY_PATH` env var, read in `_resolve_registry_path()`.
- `CliRunner(env={"OE_REGISTRY_PATH": str(path)})` provides per-test isolation without monkeypatching.
- Click's newer versions removed `mix_stderr` from `CliRunner.__init__()` — don't use it.
- `sys.exit(N)` from Click commands results in `result.exit_code == N` in CliRunner.

### Design Decisions
- Exit codes: 0=success, 1=not found/not in registry, 2=error (path missing etc.)
- `project create` falls back to `ProjectInfo(type=unknown)` when `detect_project()` returns None.
- `project list --json` outputs JSON array (not object) for easy piping.
- `project scan` without `--register` is read-only; `--register` persists to registry.

### Test Infrastructure
- Worktree uses `pip install -e .` from worktree dir to override main repo's editable install for CLI testing.
- Must restore main repo editable install after testing to avoid breaking other worktrees.
- 10 integration tests covering: empty list, create+list, scan detection, scan+register, info registered/unregistered, kind filtering, github-remote.

## 2026-03-18 Task: T7 - Project Occupancy Lock Bridge

### Patterns
- `acquire_for_work` and `release_after_work` bridge registry (knows kind) with project_state (manages occupancy).
- Temporary projects bypass locking entirely — always return `(True, None)`.
- Permanent projects delegate to `acquire_project`/`release_project`/`get_project_owner` in `project_state.py`.
- Imports are lazy (inside method body) to avoid circular imports between project and runtime modules.

### Design Decisions
- Return type `tuple[bool, str | None]` encodes three states: success, blocked-by-owner, not-registered.
- `release_after_work` returns `True` for unregistered/temporary — nothing to release is success.
- `_FakeProjectInfo` dataclass in tests avoids importing real `ProjectInfo` which needs detector module.

### Test Infrastructure
- 5 integration tests using `tmp_path` for both registry and user_home isolation.
- Evidence files: `task-7-permanent-lock.txt` (blocking test) and `task-7-temp-no-lock.txt` (no-lock test).
- Full suite: 366 tests pass (up from 361 baseline).
