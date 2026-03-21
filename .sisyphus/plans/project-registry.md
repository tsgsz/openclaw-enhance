# Project Registry: Lifecycle Management, Git Workflow, and Context Injection

## TL;DR

> **Quick Summary**: 实现项目注册系统，支持永久/临时项目的创建和管理，worker dispatch 时自动注入项目上下文，orchestrator 完成任务后 auto-commit 并在开始前通过 gh 获取 git 上下文。
> 
> **Deliverables**:
> - `src/openclaw_enhance/project/` Python 模块（detector, registry, context, git_ops）
> - CLI 命令：`project list/scan/info/create`
> - Hook 修改：spawn-enrich 从 registry 读取项目上下文
> - runtime-state.json 扩展：active_project + 永久项目占用锁
> - oe-project-registry SKILL.md 更新
> - PLAYBOOK.md 更新
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 → Task 2 → Task 4 → Task 7 → Task 9 → Task 11 → F1-F4

---

## Context

### Original Request
README.md 第 46-51 行设计意图：orchestrator 通过技能决定在哪个项目，项目分永久和临时两种，dispatch 子任务时指定项目子目录为 worker 工作目录。追加需求：orch 完成任务后 commit，进入任务前通过 gh 检查 commit 状态获取上下文。

### Interview Summary
**Key Discussions**:
- 永久项目同时只允许一个 orch 操作，新任务路由到已占用的 orch
- 临时项目 per-task，互不冲突
- gh status before task: `git log + git status + gh pr list`，gh 不可用 fallback 纯 git
- Auto-commit: orch 自行判断，dirty tree 时 skip
- v1 不做 branch/PR/merge 除非用户明确要求

**Research Findings**:
- spawn-enrich hook 已有 project 字段，defaults to "default"
- sessions_spawn 只传 task/agentId/label
- runtime-state.json 极简，无 project 追踪
- project-registry.json 存在但为空

### Metis Review
**Identified Gaps** (addressed):
- active_project scope → per-task for temp, occupancy lock for permanent
- git safety → orch 自行判断，skip on ambiguity
- registry concurrency → atomic write + lock file
- nested project ambiguity → deterministic precedence（.git 最近优先）
- contract drift → skill + PLAYBOOK 同步更新

---

## Work Objectives

### Core Objective
为 openclaw-enhance 实现完整的项目注册系统，使 orchestrator 能识别/管理项目，dispatch worker 时注入项目上下文，并在任务前后执行 git 工作流。

### Concrete Deliverables
- `src/openclaw_enhance/project/__init__.py`
- `src/openclaw_enhance/project/detector.py`
- `src/openclaw_enhance/project/registry.py`
- `src/openclaw_enhance/project/context.py`
- `src/openclaw_enhance/project/git_ops.py`
- CLI `project` 命令组
- 更新 `hooks/oe-subagent-spawn-enrich/handler.ts`
- 更新 `src/openclaw_enhance/runtime/schema.py`
- 更新 `workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md`
- 更新 `PLAYBOOK.md`

### Definition of Done
- [ ] `python -m pytest tests/unit/test_project*.py` — all pass
- [ ] `python -m pytest tests/integration/test_project*.py` — all pass
- [ ] `python -m openclaw_enhance.cli project list` — exits 0
- [ ] `python -m openclaw_enhance.cli project scan /some/path` — detects project type
- [ ] `python -m openclaw_enhance.cli docs-check` — passes

### Must Have
- 永久/临时项目区分
- 永久项目占用锁（同时只有一个 orch）
- 项目类型自动检测（pyproject.toml, package.json, Cargo.toml, go.mod 等）
- 持久化注册表 with atomic writes
- Git 上下文获取（git log + status + gh pr list）
- Auto-commit 判断逻辑
- worker dispatch 时注入项目上下文
- runtime-state.json 向后兼容

### Must NOT Have (Guardrails)
- 不修改 OpenClaw 核心代码
- 不创建 branch/PR/merge 除非用户明确要求
- 不 auto-commit 项目目录外的文件
- 不在 dirty tree 或 detached HEAD 时强制 commit
- 不做后台扫描/monorepo 子包追踪/registry 删除重命名
- 不让 GitHub 不可用成为 hard blocker（fallback 到纯 git）
- 不做临时项目自动清理
- 不做 GitHub API 写入

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: YES (tests-after per module)
- **Framework**: pytest + Click CliRunner

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Python modules**: Use Bash (pytest) — run targeted test, assert pass
- **CLI**: Use Bash (CliRunner or direct invocation) — assert exit code + output
- **Integration**: Use Bash — assert spawn context contains project info

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — data model + core modules):
├── Task 1: Project data model + detector [quick]
├── Task 2: Registry persistence (atomic read/write/lock) [unspecified-high]
├── Task 3: Git ops module (context gathering + auto-commit logic) [unspecified-high]

Wave 2 (Integration — context + CLI + runtime):
├── Task 4: Context builder (project → dispatch context) [quick] (depends: 1, 2, 3)
├── Task 5: CLI project commands [unspecified-high] (depends: 1, 2, 3)
├── Task 6: Runtime state schema extension [quick] (depends: 1, 2)
├── Task 7: Permanent project occupancy lock [unspecified-high] (depends: 2, 6)

Wave 3 (Wiring — hook + skill + docs):
├── Task 8: Spawn-enrich hook modification [unspecified-high] (depends: 4, 6)
├── Task 9: oe-project-registry SKILL.md rewrite [writing] (depends: 1-7)
├── Task 10: PLAYBOOK.md + AGENTS.md update [writing] (depends: 1-8)
├── Task 11: Integration tests for full context flow [deep] (depends: 3, 4, 7, 8)

Wave FINAL (After ALL tasks):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real QA (unspecified-high)
├── F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay

Critical Path: T1 → T2 → T4 → T7 → T8 → T11 → F1-F4
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 3 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 | — | 2, 3, 4, 5, 6, 7, 9 |
| 2 | 1 | 4, 5, 6, 7, 8, 9 |
| 3 | 1 | 4, 5, 9, 11 |
| 4 | 1, 2, 3 | 8, 11 |
| 5 | 1, 2, 3 | 10 |
| 6 | 1, 2 | 7, 8 |
| 7 | 2, 6 | 9, 11 |
| 8 | 4, 6 | 10, 11 |
| 9 | 1-7 | — |
| 10 | 1-8 | — |
| 11 | 3, 4, 7, 8 | — |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 `quick`, T2 `unspecified-high`, T3 `unspecified-high`
- **Wave 2**: 4 tasks — T4 `quick`, T5 `unspecified-high`, T6 `quick`, T7 `unspecified-high`
- **Wave 3**: 4 tasks — T8 `unspecified-high`, T9 `writing`, T10 `writing`, T11 `deep`
- **FINAL**: 4 tasks — F1 `oracle`, F2 `unspecified-high`, F3 `unspecified-high`, F4 `deep`

---

## TODOs

- [x] 1. Project Data Model + Detector

  **What to do**:
  - Create `src/openclaw_enhance/project/__init__.py` with exports
  - Create `src/openclaw_enhance/project/detector.py`:
    - `ProjectType` enum: `python`, `nodejs`, `rust`, `go`, `java`, `ruby`, `php`, `cpp`, `unknown`
    - `ProjectKind` enum: `permanent`, `temporary`
    - `ProjectInfo` dataclass: `path`, `name`, `type`, `subtype`, `kind`, `indicator_file`, `indicator_mtime`, `metadata` dict
    - `INDICATOR_MAP`: dict mapping filename → (ProjectType, subtype, lazy_parser)
    - `detect_project(path: Path) -> ProjectInfo | None`: stat indicator files in priority order, lazy parse first match
    - `find_project_root(path: Path) -> Path | None`: walk up from path, find `.git` or indicator file
    - Indicator files: `pyproject.toml` → python (parse for poetry/setuptools), `package.json` → nodejs, `Cargo.toml` → rust, `go.mod` → go, `pom.xml` → java-maven, `build.gradle` → java-gradle, `Gemfile` → ruby, `composer.json` → php, `Makefile`/`CMakeLists.txt` → cpp
    - Lazy parsers: only `pyproject.toml` (tomllib) and `package.json` (json) need parsing for metadata
    - Nested project: closest `.git` wins, then closest indicator file
  - Create `tests/unit/test_project_detector.py`:
    - Test each indicator file detection
    - Test mixed markers (pyproject.toml + package.json → python wins by priority)
    - Test no markers → None
    - Test nested projects → closest wins
    - Test find_project_root walks up correctly
    - Test manual override precedence (future-proof: if ProjectInfo.type is explicitly set, skip detection)

  **Must NOT do**:
  - Do NOT parse entire pyproject.toml/package.json — only extract name, version, test framework
  - Do NOT do framework detection (django vs fastapi)
  - Do NOT do background scanning

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 2, 3, 4, 5, 6, 7, 9
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `src/openclaw_enhance/runtime/ownership.py` — dataclass pattern used in the project
  - `src/openclaw_enhance/workspaces.py:list_workspaces()` — directory scanning pattern

  **API/Type References**:
  - `src/openclaw_enhance/paths.py:managed_root()` — where registry file lives

  **Test References**:
  - `tests/unit/test_main_skills.py` — unit test patterns in this project

  **WHY Each Reference Matters**:
  - ownership.py shows the project's dataclass convention (frozen, slots, etc.)
  - workspaces.py shows how directory iteration is done in this codebase
  - paths.py is needed for registry file location

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/unit/test_project_detector.py -q` → PASS (≥8 tests)
  - [ ] `from openclaw_enhance.project.detector import detect_project, find_project_root, ProjectInfo` → no import error

  **QA Scenarios**:
  ```
  Scenario: Detect Python project from pyproject.toml
    Tool: Bash (pytest)
    Preconditions: tmp directory with pyproject.toml containing [tool.poetry] section
    Steps:
      1. Create tmp dir with pyproject.toml
      2. Call detect_project(tmp_dir)
      3. Assert result.type == ProjectType.python
      4. Assert result.subtype == "poetry"
    Expected Result: ProjectInfo with type=python, subtype=poetry
    Evidence: .sisyphus/evidence/task-1-detect-python.txt

  Scenario: No markers returns None
    Tool: Bash (pytest)
    Preconditions: Empty tmp directory
    Steps:
      1. Create empty tmp dir
      2. Call detect_project(tmp_dir)
      3. Assert result is None
    Expected Result: None returned
    Evidence: .sisyphus/evidence/task-1-no-markers.txt
  ```

  **Commit**: YES (group: 1)
  - Message: `feat(project): add data model and detector`
  - Files: `src/openclaw_enhance/project/__init__.py`, `src/openclaw_enhance/project/detector.py`, `tests/unit/test_project_detector.py`
  - Pre-commit: `pytest tests/unit/test_project_detector.py`

- [x] 2. Registry Persistence with Atomic Writes

  **What to do**:
  - Create `src/openclaw_enhance/project/registry.py`:
    - `REGISTRY_FILENAME = "project-registry.json"`
    - `REGISTRY_SCHEMA_VERSION = 2` (v1 was the empty shell)
    - `ProjectRegistry` class:
      - `__init__(self, registry_path: Path)`: load from file or create empty
      - `load() -> dict`: read JSON, migrate from v1 if needed, handle missing/corrupt file
      - `save()`: atomic write (write to .tmp, rename) with fcntl lock
      - `register(project: ProjectInfo, kind: ProjectKind, github_remote: str | None) -> str`: add/update project, return canonical path as key
      - `unregister(path: Path)`: remove project (not in v1 scope but trivial)
      - `get(path: Path) -> ProjectInfo | None`: lookup by canonical path
      - `list_projects(kind: ProjectKind | None = None) -> list[ProjectInfo]`: list all or filter by kind
      - `scan(root: Path, kind: ProjectKind = ProjectKind.permanent) -> list[ProjectInfo]`: scan directory, detect, register all found
      - `update_last_accessed(path: Path)`: touch last_accessed timestamp
      - `is_stale(path: Path) -> bool`: check indicator mtime vs stored mtime
    - Canonical path: `Path.resolve()` to handle symlinks and relative paths
    - Schema migration: v1 `{"version":"1.0.0","projects":[]}` → v2 `{"schema_version":2,"projects":{}}`
    - Atomic write pattern: write to `{path}.tmp`, then `os.replace()` (atomic on POSIX)
    - File lock: `fcntl.flock` on `.lock` file during write
  - Create `tests/unit/test_project_registry.py`:
    - Test register/get/list/scan
    - Test atomic write survives crash (write .tmp, verify .tmp cleanup)
    - Test canonical path dedup (register same project via relative and absolute path)
    - Test v1 → v2 migration
    - Test corrupt file recovery (create malformed JSON, verify graceful fallback to empty)
    - Test deleted-path handling (registered project whose path no longer exists)

  **Must NOT do**:
  - Do NOT use database — single JSON file
  - Do NOT implement delete/rename in v1

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Tasks 4, 5, 6, 7, 8, 9
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `src/openclaw_enhance/install/manifest.py` — JSON persistence pattern with schema versioning
  - `src/openclaw_enhance/install/lock.py:InstallLock` — file locking pattern

  **API/Type References**:
  - `src/openclaw_enhance/project/detector.py:ProjectInfo` — the data model from Task 1
  - `src/openclaw_enhance/paths.py:managed_root()` — registry file location

  **Test References**:
  - `tests/integration/test_install_uninstall.py` — isolated install test patterns with tmp_path

  **WHY Each Reference Matters**:
  - manifest.py shows how this project handles JSON schema versioning and migration
  - lock.py shows the locking convention used in this codebase
  - detector.py is the source of ProjectInfo being persisted

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/unit/test_project_registry.py -q` → PASS (≥8 tests)
  - [ ] Registry survives v1 → v2 migration without data loss

  **QA Scenarios**:
  ```
  Scenario: Register and retrieve a project
    Tool: Bash (pytest)
    Preconditions: tmp directory with pyproject.toml, fresh registry
    Steps:
      1. Create ProjectRegistry with tmp registry path
      2. Detect project from tmp dir
      3. Register detected project
      4. Get project by path
      5. Assert returned project matches registered one
    Expected Result: Registered project retrieved by path
    Evidence: .sisyphus/evidence/task-2-register-retrieve.txt

  Scenario: Corrupt registry file recovery
    Tool: Bash (pytest)
    Preconditions: registry file with invalid JSON
    Steps:
      1. Write "{{invalid json" to registry file
      2. Create ProjectRegistry
      3. Assert load succeeds with empty projects
    Expected Result: Graceful fallback to empty registry
    Evidence: .sisyphus/evidence/task-2-corrupt-recovery.txt
  ```

  **Commit**: YES (group: 2)
  - Message: `feat(project): add registry persistence with atomic writes`
  - Files: `src/openclaw_enhance/project/registry.py`, `tests/unit/test_project_registry.py`
  - Pre-commit: `pytest tests/unit/test_project_registry.py`

- [x] 3. Git Ops Module

  **What to do**:
  - Create `src/openclaw_enhance/project/git_ops.py`:
    - `gather_git_context(project_path: Path) -> dict`: run git commands, return structured context
      - `git log --oneline -5` → recent commits
      - `git status --porcelain` → working tree status
      - `git branch --show-current` → current branch
      - `git remote get-url origin` → remote URL (if exists)
      - `gh pr list --state open --limit 5 --json number,title,headRefName` → open PRs (fallback to empty if gh unavailable)
      - `gh pr status --json currentBranch` → current branch PR info (fallback)
      - Returns: `{"recent_commits": [...], "branch": "...", "status": "clean|dirty", "remote": "...", "open_prs": [...], "gh_available": bool}`
    - `should_auto_commit(project_path: Path, allowed_paths: list[Path] | None) -> tuple[bool, str]`: check preconditions
      - Returns (True, "") if: branch exists, not detached HEAD, has remote, only changed files in allowed_paths (or all if None)
      - Returns (False, reason) otherwise
    - `auto_commit(project_path: Path, message: str, allowed_paths: list[Path] | None) -> bool`: execute commit
      - Call should_auto_commit first
      - `git add` only files in allowed_paths
      - `git commit -m message`
      - Return True if committed, False if skipped
    - All subprocess calls with timeout=10s, capture stderr
    - `gh` commands with fallback: catch FileNotFoundError and subprocess errors
  - Create `tests/unit/test_project_git_ops.py`:
    - Test gather_git_context on a real tmp git repo (git init + commit)
    - Test gather_git_context with no git → returns None/empty
    - Test should_auto_commit: clean repo → True
    - Test should_auto_commit: detached HEAD → False
    - Test should_auto_commit: dirty with unrelated files → False
    - Test auto_commit: successful commit
    - Test auto_commit: skip on dirty tree
    - Mock `gh` as unavailable → fallback to empty PRs

  **Must NOT do**:
  - Do NOT push to remote
  - Do NOT create branches or PRs
  - Do NOT modify files outside project path
  - Do NOT make gh availability a hard blocker

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Tasks 9, 11
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `src/openclaw_enhance/install/installer.py:_run_openclaw_cli()` — subprocess wrapper pattern with error handling

  **API/Type References**:
  - `src/openclaw_enhance/project/detector.py:ProjectInfo` — project path comes from here

  **WHY Each Reference Matters**:
  - _run_openclaw_cli shows how this project wraps subprocess calls (timeout, capture, error handling)

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/unit/test_project_git_ops.py -q` → PASS (≥7 tests)
  - [ ] gather_git_context returns structured dict even when gh is unavailable

  **QA Scenarios**:
  ```
  Scenario: Gather git context from real repo
    Tool: Bash (pytest)
    Preconditions: tmp git repo with 3 commits
    Steps:
      1. Create tmp dir, git init, make 3 commits
      2. Call gather_git_context(tmp_dir)
      3. Assert "recent_commits" has 3 entries
      4. Assert "branch" is "main" or "master"
      5. Assert "status" is "clean"
    Expected Result: Structured git context dict
    Evidence: .sisyphus/evidence/task-3-git-context.txt

  Scenario: gh unavailable falls back gracefully
    Tool: Bash (pytest)
    Preconditions: tmp git repo, gh mocked as unavailable (PATH without gh)
    Steps:
      1. Create tmp dir, git init
      2. Mock gh as FileNotFoundError
      3. Call gather_git_context(tmp_dir)
      4. Assert "gh_available" is False
      5. Assert "open_prs" is empty list
    Expected Result: Fallback context without gh data
    Evidence: .sisyphus/evidence/task-3-gh-fallback.txt
  ```

  **Commit**: YES (group: 3)
  - Message: `feat(project): add git ops module`
  - Files: `src/openclaw_enhance/project/git_ops.py`, `tests/unit/test_project_git_ops.py`
  - Pre-commit: `pytest tests/unit/test_project_git_ops.py`

- [x] 4. Context Builder for Dispatch Injection

  **What to do**:
  - Create `src/openclaw_enhance/project/context.py`:
    - `build_project_context(project_path: Path, registry: ProjectRegistry) -> dict`: build dispatch context
      - Lookup project in registry
      - Call `gather_git_context(project_path)` for git info
      - Return: `{"project_id": str(canonical_path), "project_name": name, "project_type": type, "project_subtype": subtype, "project_kind": permanent|temporary, "working_dir": str(path), "git_context": {...}, "metadata": {...}}`
    - `resolve_project_context(path: Path, registry: ProjectRegistry, active_project: str | None = None) -> dict`: canonical resolution chain
      - Priority: explicit path → active_project from runtime state → detect_project from cwd → `"default"` fallback
      - If detected but not registered: auto-register as temporary
    - Context format must be JSON-serializable for hook injection
  - Create `tests/unit/test_project_context.py`:
    - Test build_project_context with registered project → full context
    - Test resolve_project_context priority chain
    - Test auto-register as temporary when detected but not registered
    - Test fallback to "default" for unknown directory

  **Must NOT do**:
  - Do NOT make network calls — git_ops handles that
  - Do NOT cache aggressively — mtime check is sufficient

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7)
  - **Blocks**: Tasks 8, 11
  - **Blocked By**: Tasks 1, 2, 3

  **References**:

  **Pattern References**:
  - `hooks/oe-subagent-spawn-enrich/handler.ts:enrichSpawnEvent()` — the consumer of this context

  **API/Type References**:
  - `src/openclaw_enhance/project/detector.py:ProjectInfo`
  - `src/openclaw_enhance/project/registry.py:ProjectRegistry`
  - `src/openclaw_enhance/project/git_ops.py:gather_git_context()`

  **WHY Each Reference Matters**:
  - handler.ts shows what shape the enrichment hook expects for `context.project`
  - The three modules from Tasks 1-3 are this task's inputs

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/unit/test_project_context.py -q` → PASS (≥4 tests)

  **QA Scenarios**:
  ```
  Scenario: Full context for registered project
    Tool: Bash (pytest)
    Preconditions: tmp git repo with pyproject.toml, registered in registry
    Steps:
      1. Create project, register it
      2. Call build_project_context
      3. Assert all fields present: project_id, project_name, project_type, git_context
    Expected Result: Complete context dict
    Evidence: .sisyphus/evidence/task-4-full-context.txt

  Scenario: Unknown directory falls back to default
    Tool: Bash (pytest)
    Preconditions: tmp directory with no indicators, empty registry
    Steps:
      1. Call resolve_project_context on empty dir
      2. Assert project_id is "default"
    Expected Result: Default fallback context
    Evidence: .sisyphus/evidence/task-4-fallback-default.txt
  ```

  **Commit**: YES (group: 4)
  - Message: `feat(project): add context builder for dispatch injection`
  - Files: `src/openclaw_enhance/project/context.py`, `tests/unit/test_project_context.py`
  - Pre-commit: `pytest tests/unit/test_project_context.py`

- [x] 5. CLI Project Commands

  **What to do**:
  - Add `project` command group to `src/openclaw_enhance/cli.py`:
    - `project list [--kind permanent|temporary|all] [--json]`: list registered projects
    - `project scan <path> [--kind permanent] [--register]`: scan directory, detect projects, optionally register
    - `project info <path>`: show project details + git context
    - `project create <path> --name <name> --kind permanent|temporary [--github-remote <url>]`: manually register a project
  - Use Click command group pattern (existing in cli.py)
  - JSON output for `--json` flag, human-readable table otherwise
  - Exit codes: 0 success, 1 not found, 2 error
  - Create `tests/integration/test_project_cli.py`:
    - Test `project list` on empty registry → exit 0, empty output
    - Test `project create` + `project list` → shows created project
    - Test `project scan` on tmp dir with pyproject.toml → detects python
    - Test `project info` on registered project → shows details
    - Test `project info` on unregistered path → exit 1

  **Must NOT do**:
  - Do NOT add `project delete` or `project rename` in v1
  - Do NOT make `--github-remote` required

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 6, 7)
  - **Blocks**: Task 10
  - **Blocked By**: Tasks 1, 2, 3

  **References**:

  **Pattern References**:
  - `src/openclaw_enhance/cli.py` — existing Click CLI structure, command registration pattern

  **Test References**:
  - `tests/integration/test_status_command.py` — CLI testing pattern with CliRunner

  **WHY Each Reference Matters**:
  - cli.py is where the command group will be added; follow its import and registration pattern
  - test_status_command.py shows the CliRunner invocation pattern used in this project

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/integration/test_project_cli.py -q` → PASS (≥5 tests)
  - [ ] `python -m openclaw_enhance.cli project list` → exit 0

  **QA Scenarios**:
  ```
  Scenario: Create and list a project via CLI
    Tool: Bash (CliRunner)
    Preconditions: empty registry
    Steps:
      1. Invoke `project create /tmp/test-proj --name test --kind permanent`
      2. Assert exit code 0
      3. Invoke `project list --json`
      4. Assert output contains "test"
    Expected Result: Created project appears in list
    Evidence: .sisyphus/evidence/task-5-cli-create-list.txt

  Scenario: Scan detects Python project
    Tool: Bash (CliRunner)
    Preconditions: tmp dir with pyproject.toml
    Steps:
      1. Create tmp dir with pyproject.toml
      2. Invoke `project scan <tmp_dir>`
      3. Assert exit code 0
      4. Assert output contains "python"
    Expected Result: Python project detected
    Evidence: .sisyphus/evidence/task-5-cli-scan.txt
  ```

  **Commit**: YES (group: 5)
  - Message: `feat(cli): add project command group`
  - Files: `src/openclaw_enhance/cli.py`, `tests/integration/test_project_cli.py`
  - Pre-commit: `pytest tests/integration/test_project_cli.py`

- [x] 6. Runtime State Schema Extension

  **What to do**:
  - Extend `src/openclaw_enhance/runtime/schema.py`:
    - Add `active_project: str | None` field (canonical path of current project)
    - Add `project_occupancy: dict[str, str]` field (permanent project path → orchestrator session id)
    - Backward compatible: existing runtime-state.json without these fields loads with defaults (None, {})
  - Extend `src/openclaw_enhance/runtime/store.py` (if exists) or the appropriate state management:
    - `set_active_project(path: str | None)`
    - `get_active_project() -> str | None`
    - `acquire_project(path: str, session_id: str) -> bool`: try to occupy a permanent project
    - `release_project(path: str, session_id: str) -> bool`: release occupation
    - `get_project_owner(path: str) -> str | None`: who owns this project
  - Create `tests/unit/test_runtime_project_state.py`:
    - Test loading old runtime-state.json without active_project → defaults to None
    - Test set/get active_project
    - Test acquire/release project occupancy
    - Test acquire fails if already occupied by different session

  **Must NOT do**:
  - Do NOT break existing runtime-state.json loading
  - Do NOT remove existing fields

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 7)
  - **Blocks**: Tasks 7, 8
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `src/openclaw_enhance/runtime/schema.py` — existing runtime state schema
  - `src/openclaw_enhance/runtime/store.py` — existing state persistence (if exists)

  **API/Type References**:
  - `src/openclaw_enhance/watchdog/state_sync.py` — reads/writes runtime state, must remain compatible

  **WHY Each Reference Matters**:
  - schema.py is the file being extended; must maintain backward compatibility
  - state_sync.py is a consumer of runtime state; changes must not break it

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/unit/test_runtime_project_state.py -q` → PASS (≥4 tests)
  - [ ] Loading existing runtime-state.json (without new fields) → no error, defaults to None/{}

  **QA Scenarios**:
  ```
  Scenario: Backward-compatible load
    Tool: Bash (pytest)
    Preconditions: runtime-state.json with only schema_version and last_updated_utc
    Steps:
      1. Load runtime state from old-format file
      2. Assert active_project is None
      3. Assert project_occupancy is {}
    Expected Result: Graceful default values
    Evidence: .sisyphus/evidence/task-6-backward-compat.txt

  Scenario: Permanent project occupancy lock
    Tool: Bash (pytest)
    Preconditions: fresh runtime state
    Steps:
      1. acquire_project("/path/a", "session-1") → True
      2. acquire_project("/path/a", "session-2") → False
      3. get_project_owner("/path/a") → "session-1"
      4. release_project("/path/a", "session-1") → True
      5. acquire_project("/path/a", "session-2") → True
    Expected Result: Lock prevents concurrent access
    Evidence: .sisyphus/evidence/task-6-occupancy-lock.txt
  ```

  **Commit**: YES (group: 6)
  - Message: `feat(runtime): extend schema with active_project and occupancy`
  - Files: `src/openclaw_enhance/runtime/schema.py`, `tests/unit/test_runtime_project_state.py`
  - Pre-commit: `pytest tests/unit/test_runtime_project_state.py`

- [x] 7. Permanent Project Occupancy Lock Integration

  **What to do**:
  - Extend `src/openclaw_enhance/project/registry.py`:
    - `acquire_for_work(path: Path, session_id: str) -> tuple[bool, str | None]`: check registry kind=permanent, then acquire via runtime state. Returns (True, None) or (False, owning_session_id)
    - `release_after_work(path: Path, session_id: str) -> bool`: release lock
  - This bridges registry (knows project kind) with runtime state (manages locks)
  - Create `tests/integration/test_project_occupancy.py`:
    - Test acquire permanent project → success
    - Test acquire already-occupied permanent project → fail with owner info
    - Test acquire temporary project → always succeeds (no lock)
    - Test release + re-acquire

  **Must NOT do**:
  - Do NOT deadlock — always use try/finally for lock release
  - Do NOT block indefinitely — acquire returns immediately

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6)
  - **Blocks**: Tasks 9, 11
  - **Blocked By**: Tasks 2, 6

  **References**:

  **Pattern References**:
  - `src/openclaw_enhance/install/lock.py:InstallLock` — locking pattern

  **API/Type References**:
  - `src/openclaw_enhance/project/registry.py:ProjectRegistry` — from Task 2
  - `src/openclaw_enhance/runtime/schema.py` — extended in Task 6

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/integration/test_project_occupancy.py -q` → PASS (≥4 tests)

  **QA Scenarios**:
  ```
  Scenario: Permanent project locked by first orchestrator
    Tool: Bash (pytest)
    Steps:
      1. Register permanent project
      2. acquire_for_work(path, "orch-1") → (True, None)
      3. acquire_for_work(path, "orch-2") → (False, "orch-1")
    Expected Result: Second orchestrator is told who owns the project
    Evidence: .sisyphus/evidence/task-7-permanent-lock.txt

  Scenario: Temporary project has no lock
    Tool: Bash (pytest)
    Steps:
      1. Register temporary project
      2. acquire_for_work(path, "orch-1") → (True, None)
      3. acquire_for_work(path, "orch-2") → (True, None)
    Expected Result: Both succeed, no lock for temp projects
    Evidence: .sisyphus/evidence/task-7-temp-no-lock.txt
  ```

  **Commit**: YES (group: 7)
  - Message: `feat(project): add permanent project occupancy lock`
  - Files: `src/openclaw_enhance/project/registry.py` (extend), `tests/integration/test_project_occupancy.py`
  - Pre-commit: `pytest tests/integration/test_project_occupancy.py`

- [x] 8. Spawn-Enrich Hook Modification

  **What to do**:
  - Modify `hooks/oe-subagent-spawn-enrich/handler.ts`:
    - Read project-registry.json to resolve project context
    - Read runtime-state.json for active_project
    - Resolution chain (canonical, matches context.py): `context.project` (if explicitly set) → active_project from runtime state → detect_project from cwd → `"default"`
    - Inject full project context into enriched payload (not just project name, but type, kind, working_dir)
    - Add `project_context` field to `SpawnEnrichOutput.enriched_payload`
  - Update `hooks/oe-subagent-spawn-enrich/HOOK.md` to document new fields
  - Create `tests/integration/test_spawn_project_context.py`:
    - Test that with active_project set, spawn enrichment uses it
    - Test that without active_project, fallback to "default"
    - Test that explicit context.project overrides active_project
  - Note: TypeScript changes may need `npm run build` in the hooks directory

  **Must NOT do**:
  - Do NOT modify the SpawnEnrichInput interface (backward compatible)
  - Do NOT make registry read a hard dependency (fallback gracefully if file missing)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 10, 11)
  - **Blocks**: Tasks 10, 11
  - **Blocked By**: Tasks 4, 6

  **References**:

  **Pattern References**:
  - `hooks/oe-subagent-spawn-enrich/handler.ts` — the file being modified
  - `hooks/oe-subagent-spawn-enrich/HOOK.md` — documentation to update

  **API/Type References**:
  - `src/openclaw_enhance/project/context.py:build_project_context()` — Python side context builder
  - Runtime state file: `~/.openclaw/openclaw-enhance/runtime-state.json`
  - Registry file: `~/.openclaw/openclaw-enhance/project-registry.json`

  **WHY Each Reference Matters**:
  - handler.ts is the file being modified; must understand current enrichment shape
  - context.py defines what the Python side produces; hook must match

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/integration/test_spawn_project_context.py -q` → PASS (≥3 tests)
  - [ ] Hook gracefully handles missing registry file

  **QA Scenarios**:
  ```
  Scenario: Spawn enrichment with active project
    Tool: Bash (pytest)
    Preconditions: registry with project registered, runtime state with active_project set
    Steps:
      1. Set up registry and runtime state files in tmp
      2. Invoke enrichSpawnEvent with empty context.project
      3. Assert enriched_payload.project matches active_project
    Expected Result: Active project used instead of "default"
    Evidence: .sisyphus/evidence/task-8-enrich-active-project.txt

  Scenario: Missing registry graceful fallback
    Tool: Bash (pytest)
    Preconditions: no registry file, no runtime state
    Steps:
      1. Invoke enrichSpawnEvent
      2. Assert enriched_payload.project is "default"
    Expected Result: Fallback to "default" without error
    Evidence: .sisyphus/evidence/task-8-enrich-fallback.txt
  ```

  **Commit**: YES (group: 8)
  - Message: `feat(hooks): wire spawn-enrich to read project from registry`
  - Files: `hooks/oe-subagent-spawn-enrich/handler.ts`, `hooks/oe-subagent-spawn-enrich/HOOK.md`, `tests/integration/test_spawn_project_context.py`
  - Pre-commit: `pytest tests/integration/test_spawn_project_context.py`

- [x] 9. oe-project-registry SKILL.md Rewrite

  **What to do**:
  - Rewrite `workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md` to match actual implementation:
    - Remove pseudocode Python examples (old spec)
    - Document actual CLI commands: `project list`, `project scan`, `project info`, `project create`
    - Document project types and detection logic
    - Document permanent vs temporary project lifecycle
    - Document occupancy lock behavior for permanent projects
    - Document git workflow: gather context before task, auto-commit after task
    - Document resolution chain: explicit → active_project → detect → default
    - Keep frontmatter metadata updated

  **Must NOT do**:
  - Do NOT include implementation details (file paths, line numbers)
  - Do NOT promise features not in v1

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 8, 10, 11)
  - **Blocks**: None
  - **Blocked By**: Tasks 1-7

  **References**:
  - `workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md` — current file to rewrite
  - `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` — style reference for skill docs

  **Acceptance Criteria**:
  - [ ] SKILL.md documents all v1 features accurately
  - [ ] `python -m openclaw_enhance.cli docs-check` → passes

  **QA Scenarios**:
  ```
  Scenario: SKILL.md contains all v1 features
    Tool: Bash (grep)
    Preconditions: SKILL.md rewritten
    Steps:
      1. grep "project list" workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md → found
      2. grep "project scan" workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md → found
      3. grep "permanent" workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md → found
      4. grep "temporary" workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md → found
      5. grep "occupancy" workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md → found
      6. grep "auto-commit\|auto_commit" workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md → found
      7. python -m openclaw_enhance.cli docs-check → exit 0
    Expected Result: All v1 features documented, docs-check passes
    Failure Indicators: Any grep returns empty, docs-check exit != 0
    Evidence: .sisyphus/evidence/task-9-skill-content.txt

  Scenario: Old pseudocode removed
    Tool: Bash (grep)
    Preconditions: SKILL.md rewritten
    Steps:
      1. grep "discover_projects\|register_project\|get_project\|select_workspace" workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md → NOT found
    Expected Result: No old Python pseudocode API references
    Failure Indicators: grep returns matches
    Evidence: .sisyphus/evidence/task-9-old-pseudocode-removed.txt
  ```

  **Commit**: YES (group: 9)
  - Message: `docs(skill): rewrite oe-project-registry SKILL.md to match implementation`
  - Files: `workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md`
  - Pre-commit: `docs-check`

- [x] 10. PLAYBOOK.md + AGENTS.md Update

  **What to do**:
  - Update `PLAYBOOK.md`:
    - Add "项目注册系统" section documenting project registry capabilities
    - Add `project-registry.json` to 安装产物清单
    - Add CLI project commands to CLI 命令速查
  - Update `AGENTS.md`:
    - Add `project-registry.json` to Source of Truth Map
  - Sync deployed PLAYBOOK.md to `~/.openclaw/openclaw-enhance/PLAYBOOK.md`

  **Must NOT do**:
  - Do NOT duplicate SKILL.md content — reference it

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 8, 9, 11)
  - **Blocks**: None
  - **Blocked By**: Tasks 1-8

  **Acceptance Criteria**:
  - [ ] `python -m openclaw_enhance.cli docs-check` → passes
  - [ ] PLAYBOOK.md contains project registry section

  **QA Scenarios**:
  ```
  Scenario: PLAYBOOK.md updated with project registry
    Tool: Bash (grep)
    Preconditions: PLAYBOOK.md updated
    Steps:
      1. grep "project-registry.json" PLAYBOOK.md → found in 安装产物清单
      2. grep "project list" PLAYBOOK.md → found in CLI 命令速查
      3. grep "project scan" PLAYBOOK.md → found in CLI 命令速查
      4. grep "项目注册" PLAYBOOK.md → found as section header
      5. python -m openclaw_enhance.cli docs-check → exit 0
    Expected Result: All project registry content present, docs-check passes
    Failure Indicators: Any grep returns empty, docs-check exit != 0
    Evidence: .sisyphus/evidence/task-10-playbook-updated.txt

  Scenario: AGENTS.md Source of Truth Map updated
    Tool: Bash (grep)
    Preconditions: AGENTS.md updated
    Steps:
      1. grep "project-registry" AGENTS.md → found in Source of Truth Map
    Expected Result: project-registry.json referenced
    Failure Indicators: grep returns empty
    Evidence: .sisyphus/evidence/task-10-agents-updated.txt
  ```

  **Commit**: YES (group: 10)
  - Message: `docs: update PLAYBOOK.md and AGENTS.md for project registry`
  - Files: `PLAYBOOK.md`, `AGENTS.md`
  - Pre-commit: `docs-check`

- [x] 11. Integration Tests for Full Context Flow

  **What to do**:
  - Create `tests/integration/test_project_context_flow.py`:
    - End-to-end test: create project → register → set active → verify spawn enrichment has project context
    - Test permanent project occupancy: orch-1 occupies → orch-2 rejected → orch-1 releases → orch-2 succeeds
    - Test temporary project: multiple orchs can work simultaneously
    - Test git context flow: create repo with commits → gather context → verify recent_commits in dispatch context
    - Test resolution chain precedence: explicit > active > detect > default
    - Test stale detection: modify pyproject.toml → registry marks stale → re-detect updates metadata
  - All tests use tmp directories and isolated registries

  **Must NOT do**:
  - Do NOT test against real installed openclaw
  - Do NOT test real GitHub API

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after T8)
  - **Blocks**: None
  - **Blocked By**: Tasks 3, 4, 7, 8

  **References**:
  - All `src/openclaw_enhance/project/` modules
  - `tests/integration/conftest.py` — global CLI mock fixture

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/integration/test_project_context_flow.py -q` → PASS (≥6 tests)

  **QA Scenarios**:
  ```
  Scenario: Full end-to-end project context flow
    Tool: Bash (pytest)
    Preconditions: tmp git repo with pyproject.toml, isolated registry and runtime state
    Steps:
      1. detect_project → returns python project
      2. registry.register → stores project
      3. runtime state set active_project
      4. build_project_context → returns full context
      5. Assert context has: project_id, project_type=python, git_context with commits
    Expected Result: Complete context with all fields populated
    Evidence: .sisyphus/evidence/task-11-e2e-context.txt

  Scenario: Permanent project occupancy prevents concurrent access
    Tool: Bash (pytest)
    Preconditions: registered permanent project
    Steps:
      1. acquire_for_work(path, "orch-1") → True
      2. acquire_for_work(path, "orch-2") → False
      3. release + re-acquire → True
    Expected Result: Occupancy lock works correctly
    Evidence: .sisyphus/evidence/task-11-occupancy-e2e.txt
  ```

  **Commit**: YES (group: 11)
  - Message: `test(integration): add full context flow integration tests`
  - Files: `tests/integration/test_project_context_flow.py`
  - Pre-commit: `pytest tests/integration/test_project_context_flow.py`

---

## Final Verification Wave (MANDATORY)

- [x] F1. **Plan Compliance Audit** — `oracle`

  **QA Scenario**:
  ```
  Scenario: All Must Haves implemented, all Must NOT Haves absent
    Tool: Bash (grep + pytest)
    Steps:
      1. grep -r "class ProjectRegistry" src/openclaw_enhance/project/ → found
      2. grep -r "def detect_project" src/openclaw_enhance/project/ → found
      3. grep -r "def gather_git_context" src/openclaw_enhance/project/ → found
      4. grep -r "def build_project_context" src/openclaw_enhance/project/ → found
      5. grep -r "permanent\|temporary" src/openclaw_enhance/project/detector.py → found (ProjectKind)
      6. grep -r "acquire_for_work" src/openclaw_enhance/project/registry.py → found
      7. python -m openclaw_enhance.cli project list --help → exit 0
      8. python -m openclaw_enhance.cli project scan --help → exit 0
      9. grep -r "git push" src/openclaw_enhance/project/ → NOT found (must not push)
      10. grep -r "gh pr create" src/openclaw_enhance/project/ → NOT found (must not create PRs)
      11. ls .sisyphus/evidence/task-*.txt | wc -l → ≥ 11 evidence files
    Expected Result: All Must Haves found, no forbidden patterns, evidence files exist
    Evidence: .sisyphus/evidence/F1-compliance.txt
  ```

- [x] F2. **Code Quality Review** — `unspecified-high`

  **QA Scenario**:
  ```
  Scenario: Tests pass, lint clean, no quality issues
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -q → all pass, 0 failures
      2. ruff check src/openclaw_enhance/project/ → no errors
      3. ruff check tests/unit/test_project*.py tests/integration/test_project*.py → no errors
      4. grep -rn "as any\|@ts-ignore\|console\.log" src/openclaw_enhance/project/ → NOT found
      5. grep -rn "# TODO\|# FIXME\|# HACK" src/openclaw_enhance/project/ → NOT found or documented
    Expected Result: All tests pass, zero lint errors, no quality anti-patterns
    Evidence: .sisyphus/evidence/F2-quality.txt
  ```

- [x] F3. **Full QA Pass** — `unspecified-high`

  **QA Scenario**:
  ```
  Scenario: Execute all task QA scenarios end-to-end
    Tool: Bash (pytest + CLI)
    Steps:
      1. python -m pytest tests/unit/test_project_detector.py -v → all pass
      2. python -m pytest tests/unit/test_project_registry.py -v → all pass
      3. python -m pytest tests/unit/test_project_git_ops.py -v → all pass
      4. python -m pytest tests/unit/test_project_context.py -v → all pass
      5. python -m pytest tests/integration/test_project_cli.py -v → all pass
      6. python -m pytest tests/unit/test_runtime_project_state.py -v → all pass
      7. python -m pytest tests/integration/test_project_occupancy.py -v → all pass
      8. python -m pytest tests/integration/test_spawn_project_context.py -v → all pass
      9. python -m pytest tests/integration/test_project_context_flow.py -v → all pass
      10. python -m openclaw_enhance.cli project list → exit 0
      11. python -m openclaw_enhance.cli docs-check → exit 0
    Expected Result: All 9 test files pass, CLI works, docs valid
    Evidence: .sisyphus/evidence/final-qa/
  ```

- [x] F4. **Scope Fidelity + Real-Environment Validation** — `deep`

  **QA Scenario**:
  ```
  Scenario: Scope check + repo merge gate validation
    Tool: Bash (git + validate-feature)
    Steps:
      1. git diff main --name-only → only expected files changed (src/openclaw_enhance/project/*, tests/*, cli.py, runtime/schema.py, hooks/*, PLAYBOOK.md, AGENTS.md, SKILL.md)
      2. git diff main --name-only | grep -v "project\|test_project\|test_runtime_project\|test_spawn_project\|cli.py\|schema.py\|PLAYBOOK\|AGENTS\|SKILL\|hook\|conftest" → empty (no unaccounted files)
      3. python -m openclaw_enhance.cli validate-feature --feature-class cli-surface --report-slug project-registry-cli → generates report
      4. python -m openclaw_enhance.cli validate-feature --feature-class workspace-routing --report-slug project-registry-routing → generates report (covers hook + runtime changes)
      5. ls docs/reports/*project-registry* → ≥2 report files exist
    Expected Result: Only expected files changed, no scope creep, validation report generated
    Evidence: .sisyphus/evidence/F4-scope-fidelity.txt
  ```

---

## Commit Strategy

| Commit | Scope | Files | Pre-commit check |
|--------|-------|-------|-----------------|
| 1 | `feat(project): add data model and detector` | `src/openclaw_enhance/project/__init__.py`, `detector.py`, `tests/unit/test_project_detector.py` | `pytest tests/unit/test_project_detector.py` |
| 2 | `feat(project): add registry persistence with atomic writes` | `registry.py`, `tests/unit/test_project_registry.py` | `pytest tests/unit/test_project_registry.py` |
| 3 | `feat(project): add git ops module` | `git_ops.py`, `tests/unit/test_project_git_ops.py` | `pytest tests/unit/test_project_git_ops.py` |
| 4 | `feat(project): add context builder for dispatch injection` | `context.py`, `tests/unit/test_project_context.py` | `pytest tests/unit/test_project_context.py` |
| 5 | `feat(cli): add project command group` | `src/openclaw_enhance/cli.py`, `tests/integration/test_project_cli.py` | `pytest tests/integration/test_project_cli.py` |
| 6 | `feat(runtime): extend schema with active_project and occupancy` | `src/openclaw_enhance/runtime/schema.py`, `tests/unit/test_runtime_project_state.py` | `pytest tests/unit/test_runtime_project_state.py` |
| 7 | `feat(project): add permanent project occupancy lock` | `registry.py` (extend), `tests/integration/test_project_occupancy.py` | `pytest tests/integration/test_project_occupancy.py` |
| 8 | `feat(hooks): wire spawn-enrich to read project from registry` | `hooks/oe-subagent-spawn-enrich/handler.ts`, `tests/integration/test_spawn_project_context.py` | `pytest tests/integration/test_spawn_project_context.py` |
| 9 | `docs(skill): rewrite oe-project-registry SKILL.md to match implementation` | `workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md` | `docs-check` |
| 10 | `docs: update PLAYBOOK.md and AGENTS.md for project registry` | `PLAYBOOK.md`, `AGENTS.md` | `docs-check` |
| 11 | `test(integration): add full context flow integration tests` | `tests/integration/test_project_context_flow.py` | `pytest tests/integration/test_project_context_flow.py` |

---

## Success Criteria

### Verification Commands
```bash
python -m pytest tests/unit/test_project*.py -q                    # Expected: all pass
python -m pytest tests/integration/test_project*.py -q             # Expected: all pass
python -m openclaw_enhance.cli project list                        # Expected: exit 0
python -m openclaw_enhance.cli project scan .                      # Expected: detects project type
python -m openclaw_enhance.cli docs-check                          # Expected: passes
ruff check src/openclaw_enhance/project/                           # Expected: no errors
python -m openclaw_enhance.cli validate-feature --feature-class cli-surface --report-slug project-registry-cli             # Expected: report generated
python -m openclaw_enhance.cli validate-feature --feature-class workspace-routing --report-slug project-registry-routing  # Expected: report generated
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] PLAYBOOK.md updated
- [ ] oe-project-registry SKILL.md matches implementation
