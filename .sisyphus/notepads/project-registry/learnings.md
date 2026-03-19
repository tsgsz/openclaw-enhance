

## 2026-03-19 Task 11: End-to-End Context Flow Integration Tests

### Test Coverage
Created 11 integration tests covering:
1. Full end-to-end context flow (detect → register → set active → build context)
2. Context override with explicit path
3. Permanent project occupancy prevents concurrent access
4. Temporary project has no lock (multiple orch can acquire)
5. Resolution chain precedence (explicit > active_project > detect from cwd > default)
6. Stale detection and re-detect
7. Git context in dispatch (3 commits, branch, clean status)
8. Git context dirty repo detection
9. Auto-commit behavior for clean repo
10. Auto-commit restricted by allowed_paths
11. Auto-commit allowed within allowed_paths

### Implementation Notes
- Project modules created: detector.py, registry.py, context.py, git_ops.py
- RuntimeState extended with active_project and active_project_path fields
- Project detection returns None for directories without project files (not UNKNOWN type)
- Stale detection uses config file mtime (pyproject.toml, etc.) not directory mtime
- Registry uses atomic writes with fcntl.flock for process-level locking
- Schema version 2 with dict-based projects keyed by canonical path

### Test Patterns
- Used tmp_path fixture exclusively for isolated test directories
- Real git subprocess calls for authentic git context tests
- Helper function _create_python_repo reduces boilerplate
- Tests independent with no shared state

### Key Findings
- detect_project must return None (not UNKNOWN type) for fallback to "default" to work
- Git context gathering requires proper git config (user.email, user.name)
- Stale detection must track config file mtime, not directory mtime
- Temporary projects skip occupancy locking entirely
