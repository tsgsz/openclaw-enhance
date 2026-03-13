# OpenClaw Enhance Full Blueprint

## TL;DR
> **Summary**: Build `openclaw-enhance` as a non-invasive control-plane package for OpenClaw that adds main-session routing skills, a dedicated Orchestrator, fixed-role worker workspaces, timeout monitoring, and symmetric install/uninstall without editing OpenClaw core.
> **Deliverables**:
> - Python-first CLI and runtime package with idempotent install/uninstall
> - Thin OpenClaw-native hook/extension bridge in TypeScript where the host platform requires it
> - Main enhancement skills plus Orchestrator/worker workspace templates
> - Runtime state store, timeout monitor, watchdog flow, automated tests, and CI
> **Effort**: XL
> **Parallel**: YES - 2 waves
> **Critical Path**: 1 -> 2 -> 6 -> 7 -> 9

## Context
### Original Request
- Design the repository based on `README.md` and cover the full enhancement blueprint.

### Interview Summary
- Use the full README scope, not an MVP slice.
- Keep the repo Python-first, but allow thin TypeScript shims where official OpenClaw hooks/extensions require them.
- Include automated tests and CI in v1.
- Use a control-plane architecture: `main` stays thin; Orchestrator handles deep planning and dispatch.
- Align with official OpenClaw conventions, but treat each agent workspace's actual contents as the primary design surface.
- `main` does not get a full workspace template; it only gets extra skills.
- Subagent behavior must rely on `AGENTS.md`, `TOOLS.md`, and local `skills/`, because full bootstrap files are not reliably loaded for subagents.
- Prefer OpenClaw CLI for agent/hook/config operations; if CLI coverage is missing, read the whole `openclaw.json` into memory as JSON, mutate owned keys only, and save atomically.
- Install/uninstall must be symmetric, namespaced, idempotent, and must not touch user-owned agents, sessions, credentials, or unrelated config.

### Metis Review (gaps addressed)
- Lock all owned assets into a dedicated namespace under `~/.openclaw/openclaw-enhance/` plus prefixed agent IDs/workspaces to make uninstall deterministic.
- Make OpenClaw's native subagent announce chain the only Orchestrator-worker communication protocol; do not introduce a parallel queue or shared-file RPC.
- Restrict `watchdog` authority to timeout confirmation, reminder delivery, and writes to the enhancement-owned runtime state store.
- Pin v1 support to OpenClaw `2026.3.x` on macOS and Linux and fail closed outside that matrix.
- Treat local plugin path registration and tool policy changes as JSON-object fallback operations, never ad-hoc text edits.

## Work Objectives
### Core Objective
- Deliver an installable enhancement repo that augments OpenClaw multitasking, long-running-task handling, and operational visibility entirely through skills, hooks, extensions, scripts, and agent workspaces.

### Deliverables
- Python package `src/openclaw_enhance/` with CLI, installer/uninstaller, runtime store, ownership utilities, watchdog logic, and monitor entrypoints.
- Root `skills/` containing the three main-session enhancement skills.
- Dedicated worker workspace templates under `workspaces/` for `oe-orchestrator`, `oe-searcher`, `oe-syshelper`, `oe-script-coder`, and `oe-watchdog`.
- OpenClaw-native bridge surfaces under `hooks/` and `extensions/` for spawn-event enrichment and extension registration.
- Managed namespace assets under `~/.openclaw/openclaw-enhance/` with install manifest, locks, backups, and runtime state.
- Automated unit/integration/E2E tests plus CI and operator documentation.

### Definition of Done (verifiable conditions with commands)
- `python -m openclaw_enhance.cli doctor --openclaw-home "$HOME/.openclaw"` exits `0` and prints the detected OpenClaw version, active profile, and support verdict.
- `python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --dry-run` exits `0` and lists only namespaced assets and owned config keys.
- `python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw"` followed by `python -m openclaw_enhance.cli status --openclaw-home "$HOME/.openclaw"` shows `oe-orchestrator`, all worker agents, installed skills, enabled hooks, and runtime store path.
- `pytest tests/unit tests/integration -q` exits `0`.
- `pytest tests/e2e -q` exits `0` in the supported OpenClaw harness.
- `python -m openclaw_enhance.cli uninstall --openclaw-home "$HOME/.openclaw"` exits `0`, removes enhancement-owned assets, and leaves unrelated config untouched.

### Must Have
- Managed namespace root: `~/.openclaw/openclaw-enhance/` with `install-manifest.json`, `state/runtime-state.json`, `locks/install.lock`, `backups/openclaw.json.bak`, and installer logs.
- Agent IDs prefixed `oe-`: `oe-orchestrator`, `oe-searcher`, `oe-syshelper`, `oe-script-coder`, `oe-watchdog`.
- Worker workspaces at `~/.openclaw/workspace-openclaw-enhance-<role>` (for example `~/.openclaw/workspace-openclaw-enhance-orchestrator`).
- Main-session skills installed as direct child directories under the active main workspace `skills/` with IDs `oe-eta-estimator`, `oe-toolcall-router`, and `oe-timeout-state-sync`.
- OpenClaw config fallback limited to one owned top-level namespace plus explicit owned entries in `agents.list`, `hooks.internal.entries`, and `plugins.load.paths`.
- Support matrix guard: macOS/Linux only, OpenClaw `>=2026.3.11 <2026.4.0`.
- Native subagent announce chain for all Orchestrator-worker communication.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No edits to OpenClaw source files, bundled runtime files, or user-owned workspace files outside the enhancement namespace.
- No direct text editing of `openclaw.json`; JSON parse-modify-write only, with backup and ownership checks.
- No recursive orchestration beyond `main -> oe-orchestrator -> worker`.
- No watchdog authority to kill processes, edit user repos, rewrite task queues, or mutate non-owned config.
- No Windows/WSL support in v1.
- No generic scheduler, cron manager, or queueing platform beyond the README's timeout monitor requirement.

## Verification Strategy
> ZERO HUMAN INTERVENTION — all verification is agent-executed.
- Test decision: tests-after with `pytest` for Python, `vitest` for TypeScript hook/extension shims, and OpenClaw-backed integration/E2E harnesses.
- QA policy: Every task includes agent-executed happy-path and failure-path scenarios.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: 1) repo + toolchain scaffold, 2) managed namespace/runtime contracts, 3) main skills, 4) Orchestrator workspace, 5) worker workspaces

Wave 2: 6) hook/extension bridge, 7) installer/uninstaller lifecycle, 8) timeout monitor + watchdog flow, 9) automated tests + CI, 10) operator docs + ADRs

### Dependency Matrix (full, all tasks)
| Task | Depends On | Blocks |
| --- | --- | --- |
| 1 | none | 2, 3, 4, 5, 6, 7, 9, 10 |
| 2 | 1 | 6, 7, 8, 9, 10 |
| 3 | 1 | 7, 9, 10 |
| 4 | 1 | 6, 7, 9, 10 |
| 5 | 1 | 7, 8, 9, 10 |
| 6 | 1, 2, 4 | 7, 8, 9, 10 |
| 7 | 1, 2, 3, 4, 5, 6 | 8, 9, 10 |
| 8 | 2, 5, 6, 7 | 9, 10 |
| 9 | 1, 2, 3, 4, 5, 6, 7, 8 | 10 |
| 10 | 1, 2, 3, 4, 5, 6, 7, 8, 9 | Final Verification |

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 -> 5 tasks -> `unspecified-high`, `quick`, `writing`
- Wave 2 -> 5 tasks -> `unspecified-high`, `deep`, `writing`
- Final Verification -> 4 tasks -> `oracle`, `unspecified-high`, `deep`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Scaffold the hybrid repo and local developer toolchains

  **What to do**: Create the baseline Python package plus the minimal Node/TypeScript toolchain needed for OpenClaw-native hooks and extensions. Add `pyproject.toml`, a root `package.json`, `tsconfig.json`, `src/openclaw_enhance/__init__.py`, `src/openclaw_enhance/cli.py`, `src/openclaw_enhance/constants.py`, `tests/unit/test_cli_smoke.py`, `tests/integration/test_repo_layout.py`, and `.gitignore` additions for local build artifacts. Keep the root layout explicit: `skills/`, `workspaces/`, `hooks/`, `extensions/`, `scripts/`, `src/`, `tests/`, `docs/`.
  **Must NOT do**: Do not implement install logic, runtime state, or agent behavior in this task. Do not assume TypeScript is the primary runtime.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: cross-toolchain scaffolding with exact file layout decisions
  - Skills: [`test-driven-development`] — enforce smoke tests before filling in CLI/package code
  - Omitted: [`frontend-ui-ux`] — no UI surface exists

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2, 3, 4, 5, 6, 7, 9, 10 | Blocked By: none

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:3` — project is an enhancement layer, not an OpenClaw fork
  - Pattern: `README.md:5` — do not modify OpenClaw source code
  - Pattern: `README.md:7` — install/uninstall must be one-click and symmetric
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/agent-workspace.md` — official workspace shape and what belongs outside the workspace
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/creating-skills.md` — skill directory layout and discovery behavior
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/automation/hooks.md` — hook format and TypeScript handler expectations

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m openclaw_enhance.cli --help` exits `0`
  - [ ] `pytest tests/unit/test_cli_smoke.py -q` exits `0`
  - [ ] `npm run typecheck -- --pretty false` exits `0`
  - [ ] `pytest tests/integration/test_repo_layout.py -q` verifies the planned top-level directories exist in the repo

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Happy path scaffold works
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli --help && pytest tests/unit/test_cli_smoke.py -q && npm run typecheck -- --pretty false`
    Expected: all commands exit 0; help output includes `install`, `uninstall`, `doctor`, and `status`
    Evidence: .sisyphus/evidence/task-1-scaffold.txt

  Scenario: Invalid CLI command fails cleanly
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli not-a-command`
    Expected: non-zero exit with argparse/Typer usage text; no files are created outside standard caches
    Evidence: .sisyphus/evidence/task-1-scaffold-error.txt
  ```

  **Commit**: YES | Message: `build(scaffold): initialize hybrid openclaw-enhance repo` | Files: `pyproject.toml`, `package.json`, `tsconfig.json`, `src/openclaw_enhance/`, `tests/`

- [ ] 2. Define the managed namespace, ownership contracts, and config round-trip utilities

  **What to do**: Implement the enhancement-owned filesystem/config contract under `src/openclaw_enhance/paths.py`, `src/openclaw_enhance/runtime/schema.py`, `src/openclaw_enhance/runtime/store.py`, `src/openclaw_enhance/runtime/ownership.py`, `src/openclaw_enhance/runtime/config_patch.py`, and `src/openclaw_enhance/runtime/support_matrix.py`. The design is fixed: all persistent enhancement state lives under `~/.openclaw/openclaw-enhance/`; config fallback edits are limited to owned keys only; OpenClaw `2026.3.x` on macOS/Linux is the only supported matrix.
  **Must NOT do**: Do not write installer orchestration yet. Do not directly edit JSON text or infer ownership from unprefixed names.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: this task defines the safety envelope for every later mutation
  - Skills: [`test-driven-development`] — encode support matrix, ownership, and round-trip rules in tests first
  - Omitted: [`brainstorming`] — architectural decisions are already fixed

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 6, 7, 8, 9, 10 | Blocked By: 1

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:5` — all capability must come from plugins/hooks/skills/agents definitions
  - Pattern: `README.md:8` — prefer OpenClaw CLI over direct config edits
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/agent-workspace.md` — separates workspace content from `~/.openclaw/` config/session storage
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/cli/agents.md` — official agent registration/binding surface to mirror in ownership rules
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/subagents.md` — subagent depth/concurrency/timeouts and announce behavior

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_paths.py tests/unit/test_support_matrix.py tests/unit/test_config_patch.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli doctor --openclaw-home /tmp/oe-missing` exits non-zero with an explicit unsupported/missing-home error
  - [ ] `pytest tests/integration/test_config_roundtrip.py -q` proves owned-key-only mutation and atomic backup/restore behavior

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Supported matrix and namespace are enforced
    Tool: Bash
    Steps: run `pytest tests/unit/test_paths.py tests/unit/test_support_matrix.py tests/unit/test_config_patch.py -q`
    Expected: tests pass and assert `~/.openclaw/openclaw-enhance/` paths, version guard, and owned-key filtering
    Evidence: .sisyphus/evidence/task-2-contracts.txt

  Scenario: Invalid OpenClaw home is rejected
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli doctor --openclaw-home /tmp/oe-missing`
    Expected: non-zero exit with a namespaced error message; no config or state directories are created
    Evidence: .sisyphus/evidence/task-2-contracts-error.txt
  ```

  **Commit**: YES | Message: `feat(runtime): add ownership and config safety contracts` | Files: `src/openclaw_enhance/runtime/`, `tests/unit/test_paths.py`, `tests/unit/test_support_matrix.py`, `tests/integration/test_config_roundtrip.py`

- [ ] 3. Add the three main-session enhancement skills and their routing heuristics

  **What to do**: Create `skills/oe-eta-estimator/SKILL.md`, `skills/oe-toolcall-router/SKILL.md`, and `skills/oe-timeout-state-sync/SKILL.md`, plus any helper Python modules/tests needed to render deterministic prompts and heuristics (`src/openclaw_enhance/skills_catalog.py`, `tests/unit/test_main_skills.py`, `tests/integration/test_main_skill_sync.py`). The router must keep `main` thin: simple tasks stay local; heavy-tool, parallel, or long-running tasks escalate to `oe-orchestrator` using the native subagent path.
  **Must NOT do**: Do not create a full `main` workspace template. Do not route directly to workers from `main`.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: mixed Markdown skill authoring and deterministic routing helpers
  - Skills: [`test-driven-development`] — route heuristics and sync logic must be test-locked
  - Omitted: [`frontend-ui-ux`] — no visual surface

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 7, 9, 10 | Blocked By: 1

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:21` — Orchestrator should be `main`-strength and always plan before acting
  - Pattern: `README.md:22` — `main` needs ETA estimation
  - Pattern: `README.md:23` — `main` should route tasks with TOOLCALL > 2 to Orchestrator
  - Pattern: `README.md:29` — timeout-state behavior is shared between `main` and Orchestrator
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/creating-skills.md` — official `SKILL.md` format
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/subagents.md` — native spawn and announce constraints that the router must respect
  - API/Type: `src/openclaw_enhance/runtime/schema.py` — ownership and runtime event contracts from Task 2

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_main_skills.py -q` exits `0`
  - [ ] `pytest tests/integration/test_main_skill_sync.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-skill oe-toolcall-router` prints the expected route/escalate contract without unresolved placeholders

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Complex task escalates to Orchestrator contract
    Tool: Bash
    Steps: run `pytest tests/unit/test_main_skills.py -q -k complex_route`
    Expected: the test asserts TOOLCALL-heavy input selects `oe-orchestrator` and includes ETA + reason fields
    Evidence: .sisyphus/evidence/task-3-main-skills.txt

  Scenario: Simple task stays on main
    Tool: Bash
    Steps: run `pytest tests/unit/test_main_skills.py -q -k simple_route`
    Expected: the test asserts no worker/orchestrator escalation is emitted for a simple request
    Evidence: .sisyphus/evidence/task-3-main-skills-error.txt
  ```

  **Commit**: YES | Message: `feat(skills): add main session routing and timeout skills` | Files: `skills/oe-eta-estimator/`, `skills/oe-toolcall-router/`, `skills/oe-timeout-state-sync/`, `src/openclaw_enhance/skills_catalog.py`, `tests/unit/test_main_skills.py`

- [ ] 4. Create the Orchestrator workspace template and local orchestration skills

  **What to do**: Create `workspaces/oe-orchestrator/AGENTS.md`, `workspaces/oe-orchestrator/TOOLS.md`, and local skills under `workspaces/oe-orchestrator/skills/`: `oe-project-registry`, `oe-worker-dispatch`, `oe-agentos-practice`, and `oe-git-context`. Encode the exact responsibilities already decided: project discovery, workspace selection, task splitting, worker dispatch, child-result synthesis through native announce, and project-level git context injection.
  **Must NOT do**: Do not give Orchestrator direct user-channel delivery powers beyond the native announce path. Do not introduce another Orchestrator tier.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: most of the work is precise workspace instructions and skill contracts
  - Skills: [`test-driven-development`] — validate template rendering and route rules with snapshot/integration tests
  - Omitted: [`brainstorming`] — the design is already approved

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 6, 7, 9, 10 | Blocked By: 1

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:21` — Orchestrator is the same class of agent as main and always plans with files/superpowers
  - Pattern: `README.md:25` — Orchestrator must manage projects and workspace selection
  - Pattern: `README.md:26` — Orchestrator must dispatch tasks to specific subagents
  - Pattern: `README.md:27` — Orchestrator must support agentos practice for coding tasks
  - Pattern: `README.md:28` — Orchestrator must inject project-level git history context
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/agent-workspace.md` — workspace files and what subagents reliably load
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/subagents.md` — native announce chain, `maxSpawnDepth`, and worker management model
  - Test: `tests/integration/test_repo_layout.py` — follow the Task 1 workspace directory pattern

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_orchestrator_workspace.py -q` exits `0`
  - [ ] `pytest tests/integration/test_orchestrator_dispatch_contract.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-workspace oe-orchestrator` outputs `AGENTS.md`, `TOOLS.md`, and all local skill IDs

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Orchestrator template renders complete local context
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli render-workspace oe-orchestrator && pytest tests/unit/test_orchestrator_workspace.py -q`
    Expected: rendered output contains `AGENTS.md`, `TOOLS.md`, and the four local skill directories with no unresolved template markers
    Evidence: .sisyphus/evidence/task-4-orchestrator.txt

  Scenario: Unsupported worker target is rejected
    Tool: Bash
    Steps: run `pytest tests/integration/test_orchestrator_dispatch_contract.py -q -k invalid_worker`
    Expected: the test asserts Orchestrator refuses unknown worker IDs and emits a bounded error contract instead of retry loops
    Evidence: .sisyphus/evidence/task-4-orchestrator-error.txt
  ```

  **Commit**: YES | Message: `feat(orchestrator): add workspace template and dispatch skills` | Files: `workspaces/oe-orchestrator/`, `tests/unit/test_orchestrator_workspace.py`, `tests/integration/test_orchestrator_dispatch_contract.py`

- [ ] 5. Create the fixed-role worker workspace templates and lock their tool boundaries

  **What to do**: Create worker workspaces for `oe-searcher`, `oe-syshelper`, `oe-script-coder`, and `oe-watchdog` under `workspaces/`. Each workspace must include `AGENTS.md`, `TOOLS.md`, and only the local skills that its role needs. Add `tests/unit/test_worker_workspaces.py` and `tests/integration/test_worker_role_boundaries.py`. Explicitly do **not** create an `oe-acp` workspace; ACP remains an Orchestrator dispatch target, not a separately templated OpenClaw agent.
  **Must NOT do**: Do not duplicate Orchestrator logic inside workers. Do not give `oe-watchdog` general write access or repo-edit instructions.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: this task is mostly role-contract documentation with bounded local skills
  - Skills: [`test-driven-development`] — prevent role drift with snapshot and contract tests
  - Omitted: [`frontend-ui-ux`] — no UI

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 7, 8, 9, 10 | Blocked By: 1

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:35` — `searcher` does search and research work
  - Pattern: `README.md:36` — `syshelper` is system-search/read-only focused
  - Pattern: `README.md:37` — `script_coder` handles scripts and tests
  - Pattern: `README.md:38` — `watchdog` handles session status/timeout judgment and has `session_send`
  - Pattern: `README.md:41` — ACP is represented through Orchestrator dispatch logic, not a dedicated agent here
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/agent-workspace.md` — workers should center on `AGENTS.md`, `TOOLS.md`, and local `skills/`
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/subagents.md` — worker sessions are leaf subagents with no extra session tools except the approved watchdog path
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md` — worker prompts must complement, not duplicate, Orchestrator responsibilities

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_worker_workspaces.py -q` exits `0`
  - [ ] `pytest tests/integration/test_worker_role_boundaries.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-workspace oe-watchdog` shows only watchdog-specific context and local skills

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Worker templates stay role-specific
    Tool: Bash
    Steps: run `pytest tests/unit/test_worker_workspaces.py -q`
    Expected: tests assert each worker workspace contains only its approved local skills and excludes Orchestrator-only instructions
    Evidence: .sisyphus/evidence/task-5-workers.txt

  Scenario: Watchdog authority stays narrow
    Tool: Bash
    Steps: run `pytest tests/integration/test_worker_role_boundaries.py -q -k watchdog`
    Expected: tests assert `oe-watchdog` can confirm timeout and send reminders but cannot edit repos or mutate non-owned config
    Evidence: .sisyphus/evidence/task-5-workers-error.txt
  ```

  **Commit**: YES | Message: `feat(workspaces): add fixed-role worker templates` | Files: `workspaces/oe-searcher/`, `workspaces/oe-syshelper/`, `workspaces/oe-script-coder/`, `workspaces/oe-watchdog/`, `tests/unit/test_worker_workspaces.py`

- [ ] 6. Implement the OpenClaw-native hook and extension bridge surfaces

  **What to do**: Create `hooks/oe-subagent-spawn-enrich/HOOK.md` and `hooks/oe-subagent-spawn-enrich/handler.ts` to enrich `subagent_spawning` with task ID, project, parent session, ETA bucket, and dedupe key. Create `extensions/openclaw-enhance-runtime/package.json`, `extensions/openclaw-enhance-runtime/openclaw.plugin.json`, `extensions/openclaw-enhance-runtime/index.ts`, `extensions/openclaw-enhance-runtime/src/runtime-bridge.ts`, and `extensions/openclaw-enhance-runtime/src/runtime-bridge.test.ts` to provide the minimum plugin surface needed for namespaced runtime integration. Keep the extension thin; the native subagent announce chain remains the only worker communication path.
  **Must NOT do**: Do not add a custom queue, HTTP service, or file-polling protocol between Orchestrator and workers. Do not put business logic in the hook beyond event normalization.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: mixed hook/plugin TypeScript surfaces with strict OpenClaw compatibility constraints
  - Skills: [`test-driven-development`] — encode event payload contracts before implementation
  - Omitted: [`brainstorming`] — no new architecture choices remain

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 7, 8, 9, 10 | Blocked By: 1, 2, 4

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:45` — `subagent_spawning` must record extra task info, including project and ETA
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/automation/hooks.md` — official hook directory structure, CLI lifecycle, and event metadata
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/plugin.md` — plugin/extension registration model and local path considerations
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/subagents.md` — announce chain and spawn metadata constraints
  - API/Type: `src/openclaw_enhance/runtime/schema.py` — namespaced runtime event fields
  - Pattern: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` — upstream consumer of spawn-event enrichment

  **Acceptance Criteria** (agent-executable only):
  - [ ] `npm test -- --runInBand --filter openclaw-enhance-runtime` exits `0`
  - [ ] `pytest tests/integration/test_spawn_event_contract.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-hook oe-subagent-spawn-enrich` prints the expected event subscriptions and payload keys

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Spawn hook emits normalized payload
    Tool: Bash
    Steps: run `npm test -- --runInBand --filter openclaw-enhance-runtime && pytest tests/integration/test_spawn_event_contract.py -q`
    Expected: tests prove `subagent_spawning` payloads include project, ETA bucket, parent session, task ID, and dedupe key under the enhancement namespace
    Evidence: .sisyphus/evidence/task-6-hook-bridge.txt

  Scenario: Unknown event payload is ignored safely
    Tool: Bash
    Steps: run `pytest tests/integration/test_spawn_event_contract.py -q -k malformed_event`
    Expected: malformed or incomplete hook input is dropped with a bounded warning; no runtime store mutation occurs
    Evidence: .sisyphus/evidence/task-6-hook-bridge-error.txt
  ```

  **Commit**: YES | Message: `feat(bridge): add hook and extension runtime bridge` | Files: `hooks/oe-subagent-spawn-enrich/`, `extensions/openclaw-enhance-runtime/`, `tests/integration/test_spawn_event_contract.py`

- [ ] 7. Implement the install, uninstall, status, and rollback lifecycle

  **What to do**: Implement `src/openclaw_enhance/install/openclaw_cli.py`, `src/openclaw_enhance/install/workspace_sync.py`, `src/openclaw_enhance/install/manifest.py`, `src/openclaw_enhance/install/lock.py`, `src/openclaw_enhance/install/installer.py`, `src/openclaw_enhance/install/uninstaller.py`, and wire them into `src/openclaw_enhance/cli.py`. The lifecycle is fixed: preflight support-matrix check, acquire install lock, create/update enhancement namespace, sync worker workspaces, copy main skills into the active main workspace, register agents with OpenClaw CLI, enable/install hooks via CLI, and only then apply JSON-object fallback for owned config keys such as local plugin load paths and tool policy entries. Uninstall reverses that exact order and preserves user-owned state.
  **Must NOT do**: Do not shell out to `sed`/string replacement against `openclaw.json`. Do not uninstall anything that is missing from the enhancement-owned install manifest.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: high-risk lifecycle and rollback logic with external tool coordination
  - Skills: [`test-driven-development`] — installer idempotency and rollback need locked tests first
  - Omitted: [`frontend-ui-ux`] — no UI

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 8, 9, 10 | Blocked By: 1, 2, 3, 4, 5, 6

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:7` — one-click deploy/uninstall requirement
  - Pattern: `README.md:8` — use OpenClaw CLI first
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/cli/agents.md` — agent add/bind/delete commands and workspace targeting
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/automation/hooks.md` — hook install/enable/disable CLI flow
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/agent-workspace.md` — workspace paths and what remains outside managed workspaces
  - API/Type: `src/openclaw_enhance/runtime/ownership.py` — owned keys and manifest safety rules
  - Pattern: `skills/oe-eta-estimator/SKILL.md` — main-skill source directories that must be copied into the active main workspace
  - Pattern: `workspaces/oe-orchestrator/` — source workspace tree to sync into `~/.openclaw/workspace-openclaw-enhance-orchestrator`

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/integration/test_install_uninstall.py -q` exits `0`
  - [ ] `pytest tests/integration/test_install_idempotency.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --dry-run` exits `0`
  - [ ] `python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" && python -m openclaw_enhance.cli status --openclaw-home "$HOME/.openclaw" && python -m openclaw_enhance.cli uninstall --openclaw-home "$HOME/.openclaw"` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Install -> status -> uninstall is symmetric
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" && python -m openclaw_enhance.cli status --openclaw-home "$HOME/.openclaw" && python -m openclaw_enhance.cli uninstall --openclaw-home "$HOME/.openclaw"`
    Expected: install registers only `oe-*` assets, status reports them, uninstall removes them and leaves unrelated config untouched
    Evidence: .sisyphus/evidence/task-7-lifecycle.txt

  Scenario: Partial install rolls back safely
    Tool: Bash
    Steps: run `pytest tests/integration/test_install_idempotency.py -q -k partial_failure`
    Expected: simulated mid-install failure restores backed-up config, preserves manifest correctness, and allows a clean retry
    Evidence: .sisyphus/evidence/task-7-lifecycle-error.txt
  ```

  **Commit**: YES | Message: `feat(installer): add managed lifecycle and rollback support` | Files: `src/openclaw_enhance/install/`, `src/openclaw_enhance/cli.py`, `tests/integration/test_install_uninstall.py`, `tests/integration/test_install_idempotency.py`

- [ ] 8. Implement the timeout monitor, watchdog policy, and runtime-state transitions

  **What to do**: Create `scripts/monitor_runtime.py`, `src/openclaw_enhance/watchdog/detector.py`, `src/openclaw_enhance/watchdog/policy.py`, `src/openclaw_enhance/watchdog/notifier.py`, `src/openclaw_enhance/watchdog/state_sync.py`, `tests/unit/test_watchdog_policy.py`, and `tests/integration/test_timeout_flow.py`. The monitor script runs every minute, emits only `timeout_suspected` events into the managed namespace, and never messages sessions directly. `oe-watchdog` confirms or rejects suspicion, updates only the namespaced runtime store, and when confirmed uses the approved reminder path plus `oe-timeout-state-sync`.
  **Must NOT do**: Do not let the monitor script or watchdog kill processes, mutate task queues, or write outside `~/.openclaw/openclaw-enhance/`.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: this task defines failure handling, race control, and authority limits
  - Skills: [`test-driven-development`] — timeout races and false positives must be locked by tests
  - Omitted: [`systematic-debugging`] — no live bug exists yet; this is greenfield policy work

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 9, 10 | Blocked By: 2, 5, 6, 7

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:29` — `main` and Orchestrator both need timeout-state updates
  - Pattern: `README.md:38` — `watchdog` handles session diagnosis and `session_send`
  - Pattern: `README.md:39` — `watchdog` must notify the original session when timeout is detected
  - Pattern: `README.md:40` — `watchdog` must learn how to judge session state
  - Pattern: `README.md:49` — monitor runtime every minute and let watchdog make the final decision
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/subagents.md` — timeout fields, child-session metadata, and announce/status semantics
  - API/Type: `src/openclaw_enhance/runtime/store.py` — enhancement-owned runtime state persistence
  - Pattern: `workspaces/oe-watchdog/AGENTS.md` — role boundary that must match the policy code

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_watchdog_policy.py -q` exits `0`
  - [ ] `pytest tests/integration/test_timeout_flow.py -q` exits `0`
  - [ ] `python scripts/monitor_runtime.py --once --openclaw-home "$HOME/.openclaw" --state-root "$HOME/.openclaw/openclaw-enhance"` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Suspicion -> confirmation -> reminder flow succeeds
    Tool: Bash
    Steps: run `pytest tests/integration/test_timeout_flow.py -q -k confirmed_timeout`
    Expected: the test asserts the monitor emits `timeout_suspected`, `oe-watchdog` confirms it, runtime state updates to `timeout_confirmed`, and the reminder path is invoked once
    Evidence: .sisyphus/evidence/task-8-watchdog.txt

  Scenario: Healthy long-running task does not false-positive
    Tool: Bash
    Steps: run `pytest tests/integration/test_timeout_flow.py -q -k false_positive`
    Expected: the test asserts a long but healthy session stays below `timeout_confirmed`, sends no reminder, and records the rejection reason
    Evidence: .sisyphus/evidence/task-8-watchdog-error.txt
  ```

  **Commit**: YES | Message: `feat(watchdog): add timeout monitoring and state sync flow` | Files: `scripts/monitor_runtime.py`, `src/openclaw_enhance/watchdog/`, `tests/unit/test_watchdog_policy.py`, `tests/integration/test_timeout_flow.py`

- [ ] 9. Build the automated test harness and CI pipeline

  **What to do**: Add `.github/workflows/ci.yml`, `tests/unit/test_support_matrix.py` refinements, `tests/integration/test_subagent_routing.py`, `tests/integration/test_status_command.py`, `tests/e2e/test_openclaw_harness.py`, and any fixtures under `tests/fixtures/`. CI must run Python unit/integration suites, TypeScript tests, lint/typecheck, and the install/uninstall/status smoke flow on the supported matrix. E2E should be opt-in or gated on the OpenClaw harness being present, but still executable in CI when configured.
  **Must NOT do**: Do not make CI mutate a real user OpenClaw home. Do not mark flaky timeouts as acceptable.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: combines Python tests, TS tests, CI orchestration, and harness gating
  - Skills: [`test-driven-development`] — test harness and CI expectations should be written before workflow glue
  - Omitted: [`frontend-ui-ux`] — no UI

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 10 | Blocked By: 1, 2, 3, 4, 5, 6, 7, 8

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:13` — multitasking quality regression is a core problem to verify against
  - Pattern: `README.md:14` — long tool-call sequences should stop blocking the main agent
  - Pattern: `README.md:16` — users need ETA/expectation visibility and subagent failure handling
  - Pattern: `README.md:17` — file-writing behavior must be more deterministic and manageable
  - Test: `tests/integration/test_install_uninstall.py` — lifecycle smoke path to include in CI
  - Test: `tests/integration/test_timeout_flow.py` — timeout regression suite to include in CI
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/subagents.md` — concurrency and depth limits to encode in harness fixtures

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit tests/integration -q` exits `0`
  - [ ] `npm test -- --runInBand` exits `0`
  - [ ] `pytest tests/e2e/test_openclaw_harness.py -q` exits `0` when the harness is available and skips cleanly otherwise
  - [ ] `python - <<'PY'
import pathlib, yaml
yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text())
print('ci-workflow-valid')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Full local test matrix passes
    Tool: Bash
    Steps: run `pytest tests/unit tests/integration -q && npm test -- --runInBand`
    Expected: all local unit/integration/TypeScript suites pass with no skipped critical tests
    Evidence: .sisyphus/evidence/task-9-ci.txt

  Scenario: E2E harness absence is handled cleanly
    Tool: Bash
    Steps: run `pytest tests/e2e/test_openclaw_harness.py -q`
    Expected: when the OpenClaw harness is missing, the test suite reports explicit skips instead of failures or hangs; when present, it passes
    Evidence: .sisyphus/evidence/task-9-ci-error.txt
  ```

  **Commit**: YES | Message: `test(ci): add automated verification pipeline` | Files: `.github/workflows/ci.yml`, `tests/integration/test_subagent_routing.py`, `tests/e2e/test_openclaw_harness.py`

- [ ] 10. Write operator documentation, ADRs, and repository usage guides

  **What to do**: Create `docs/architecture.md`, `docs/install.md`, `docs/operations.md`, `docs/troubleshooting.md`, `docs/adr/0001-managed-namespace.md`, `docs/adr/0002-native-subagent-announce.md`, `docs/adr/0003-watchdog-authority.md`, and update `README.md` with a concise quickstart pointing to those docs. Document the exact support matrix, install/uninstall flow, owned asset namespace, config fallback policy, worker roles, and how to inspect state during incidents.
  **Must NOT do**: Do not rewrite `README.md` into a product-marketing page. Do not document unsupported Windows/WSL flows as if they are supported.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: precise operator-facing docs and architecture records
  - Skills: [`writing-plans`] — keep documentation aligned with the implementation plan and acceptance criteria
  - Omitted: [`frontend-ui-ux`] — documentation only

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: Final Verification | Blocked By: 1, 2, 3, 4, 5, 6, 7, 8, 9

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:3` — project goal: improve OpenClaw intelligence and stability
  - Pattern: `README.md:5` — all capability must stay non-invasive
  - Pattern: `README.md:7` — one-click deploy/uninstall requirement
  - Pattern: `README.md:19` — multi-task solution overview to preserve in the architecture doc
  - Pattern: `README.md:31` — worker-agent definitions to reflect in operations docs
  - Pattern: `README.md:43` — hook requirement for spawn enrichment
  - Pattern: `README.md:47` — script requirement for runtime monitoring
  - Pattern: `docs/architecture.md` — canonical architecture narrative created in this task

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  - [ ] `pytest tests/unit/test_docs_examples.py -q` exits `0`
  - [ ] `grep -R "openclaw-enhance" docs README.md` shows quickstart, support matrix, install, uninstall, watchdog, and runtime-state references

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Documentation examples stay executable
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli docs-check && pytest tests/unit/test_docs_examples.py -q`
    Expected: docs-check validates fenced commands and tests confirm copied examples still parse or execute in the harness
    Evidence: .sisyphus/evidence/task-10-docs.txt

  Scenario: Unsupported matrix is documented as unsupported
    Tool: Bash
    Steps: run `pytest tests/unit/test_docs_examples.py -q -k support_matrix`
    Expected: docs tests assert the docs mention macOS/Linux + OpenClaw 2026.3.x only, and do not advertise Windows/WSL support
    Evidence: .sisyphus/evidence/task-10-docs-error.txt
  ```

  **Commit**: YES | Message: `docs(operations): add architecture and support docs` | Files: `docs/`, `README.md`, `tests/unit/test_docs_examples.py`

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Use one commit per numbered task.
- Commit prefixes: `build`, `feat`, `fix`, `test`, `docs`, as specified in each task.
- Never mix installer/config-state changes with unrelated workspace content changes in the same commit.

## Success Criteria
- The repo can install and uninstall its enhancement layer without human file editing.
- Complex tasks route from `main` to `oe-orchestrator` and, when needed, to a fixed worker role without blocking `main`.
- Timeout suspicion, confirmation, reminder, and state synchronization follow a deterministic, namespaced flow.
- All enhancement-owned assets are discoverable, auditable, and removable.
- The plan is executable without additional architectural judgment.
