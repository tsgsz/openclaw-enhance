## 2026-03-18 Task: T2 — Registry Persistence with Atomic Writes

### Patterns Used
- `fcntl.flock` on a separate `.lock` file for process-level locking during writes
- `os.replace()` for atomic file swap (POSIX guarantee: same filesystem)
- Write to `.tmp` then replace — ensures no partial writes on crash
- `TYPE_CHECKING` guard for `ProjectInfo` import to avoid circular dependency with parallel Task 1

### Schema Migration
- v1 format: `{"version": "1.0.0", "projects": []}` (list)
- v2 format: `{"schema_version": 2, "last_scan": null, "projects": {}}` (dict keyed by canonical path)
- Migration handles both `version` → `schema_version` rename and `projects` list → dict conversion

### Canonical Path Resolution
- All paths stored as `str(Path(path).resolve())` — handles symlinks, relative paths, deduplication
- Key in projects dict = canonical path string

### Test Conventions
- Use `tmp_path` fixture exclusively for isolated test directories
- No docstrings in tests, clear function names describe behavior
- Helper functions `_make_project_dir` and `_make_project_info` to reduce boilerplate
- 9 tests covering: roundtrip, list, filter, dedup, migration, corrupt recovery, staleness, atomic save cleanup, missing file

### Gotchas
- `time.sleep(0.05)` needed in `test_is_stale` to ensure mtime actually changes on fast filesystems
- Lock file and tmp file both need cleanup in error paths
- `detector.py` stub created for parallel task independence — will be replaced by Task 1
