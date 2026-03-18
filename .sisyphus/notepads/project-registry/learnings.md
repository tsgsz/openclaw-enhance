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
