# Router Skill-First Alignment

## TL;DR
> **Summary**: Refactor `oe-toolcall-router` so the routing contract is owned by markdown skills and executed through OpenClaw's native `sessions_spawn` / announce path, while removing the current Python-first router API. Fix installer/test/doc drift so the main session actually receives the synced skills that the repo claims to provide.
> **Deliverables**:
> - File-backed main-skill contract loading/rendering sourced from real `skills/*/SKILL.md` files
> - Clean-break removal of `SkillRouter` / `TaskAssessment` / `RoutingDecision` / `should_escalate_to_orchestrator`
> - Installer/uninstaller support for syncing main-session skills into the resolved active workspace
> - Contract-based tests and docs aligned to native `sessions_spawn` / announce semantics
> **Effort**: Medium
> **Parallel**: YES - 2 waves
> **Critical Path**: 1 -> 2 -> 4 -> 6 -> 8

## Context
### Original Request
- Produce a complete modification plan for the current implementation so `oe-toolcall-router` follows a `skill + thin helper` model and actual execution reuses native `session_spawn` / announce.

### Interview Summary
- The router must only decide whether work stays in `main` or escalates to `oe-orchestrator`.
- Actual execution must reuse native `session_spawn` / subagent announce flow; no custom router runtime or wrapper executor is allowed.
- Thin helper support is still allowed for rule constants, render/debug support, and tests.
- The existing Python router API is intentionally allowed to break; no compatibility shim is required.

### Metis Review (gaps addressed)
- Validate and fix main-skill sync instead of assuming the current installer already copies skills into the active main workspace.
- Replace Python-API-centric tests before removing the old router surface so behavior remains covered.
- Treat the real `skills/*/SKILL.md` files as the runtime contract source of truth and eliminate duplicated embedded markdown in Python.
- Preserve orchestrator-worker topology and native announce semantics; this refactor changes contract ownership, not transport design.

## Work Objectives
### Core Objective
- Make the main-session routing story internally consistent: markdown skills define routing behavior, OpenClaw native subagent/session tools execute it, Python only supports packaging/rendering/sync/validation.

### Deliverables
- `src/openclaw_enhance/skills_catalog.py` slimmed to file-backed main-skill registry/rendering and no router runtime classes/functions.
- `skills/oe-toolcall-router/SKILL.md` rewritten as the authoritative routing contract, with companion updates to any neighboring skill/docs that still present wrapper-style dispatch.
- `src/openclaw_enhance/paths.py` and installer lifecycle code updated to resolve the active main workspace and sync/remove enhancement-owned main skills.
- Updated tests in `tests/unit/`, `tests/integration/`, `tests/e2e/`, and `tests/fixtures/` that verify contract loading, main-skill sync, and absence of the removed Python router API.
- Documentation updates across `README.md`, `docs/install.md`, `docs/operations.md`, `docs/architecture.md`, `docs/troubleshooting.md`, and `docs/adr/0002-native-subagent-announce.md`.

### Definition of Done (verifiable conditions with commands)
- `python -m openclaw_enhance.cli render-skill oe-toolcall-router` exits `0` and renders the file-backed skill contract without embedded-Python drift.
- `pytest tests/unit/test_main_skills.py tests/unit/test_paths.py -q` exits `0`.
- `pytest tests/integration/test_main_skill_sync.py tests/integration/test_subagent_routing.py tests/integration/test_install_uninstall.py -q` exits `0`.
- `python - <<'PY'
from pathlib import Path
from openclaw_enhance.skills_catalog import render_skill_contract
disk = Path('skills/oe-toolcall-router/SKILL.md').read_text(encoding='utf-8').strip()
rendered = render_skill_contract('oe-toolcall-router').strip()
assert rendered == disk
print('router-contract-in-sync')
PY` exits `0`.
- `! grep -R "class SkillRouter\|class TaskAssessment\|class RoutingDecision\|def should_escalate_to_orchestrator" src/openclaw_enhance tests` exits `0` (no matches).

### Must Have
- Main-skill contract source of truth is the on-disk markdown under `skills/` rather than duplicated Python string literals.
- Active main workspace resolution uses OpenClaw workspace rules: explicit config workspace first, profile-aware default fallback second, plain `~/.openclaw/workspace` fallback last.
- Installer/uninstaller track synced main skills as enhancement-owned components and remove only those directories.
- Router docs and skill examples explicitly say: router decides, native `sessions_spawn` / announce executes.
- Orchestrator-side skill examples stop advertising pseudo helper wrappers such as `dispatch_task(...)` if those helpers do not exist.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No new wrapper runtime over `sessions_spawn`, `subagent.announce`, or announce delivery.
- No changes to orchestrator-worker topology, worker roles, hook payload schema, or watchdog authority.
- No compatibility shim preserving `SkillRouter`-style runtime routing as a first-class API.
- No dependence on unpublished root-repo paths at runtime without a packaged fallback for installed distributions.
- No doc language that suggests `main` routes directly to workers.

## Verification Strategy
> ZERO HUMAN INTERVENTION — all verification is agent-executed.
- Test decision: tests-after, with focused rewrites before removal so contract coverage replaces API coverage immediately.
- QA policy: every task includes command-level verification plus at least one failure/edge case.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`.

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: 1) workspace/main-skill path resolution, 2) file-backed main-skill registry, 3) router contract rewrite, 4) clean-break API removal

Wave 2: 5) installer main-skill sync, 6) uninstall/status symmetry, 7) test suite realignment, 8) docs/ADR/README alignment

### Dependency Matrix (full, all tasks)
| Task | Depends On | Blocks |
| --- | --- | --- |
| 1 | none | 5, 6, 7, 8 |
| 2 | none | 4, 6, 7, 8 |
| 3 | 2 | 4, 6, 7, 8 |
| 4 | 2, 3 | 6, 7, 8 |
| 5 | 1, 2 | 6, 7, 8 |
| 6 | 2, 3, 4, 5 | 7, 8 |
| 7 | 2, 3, 5, 6 | 8 |
| 8 | 1, 2, 3, 4, 5, 6, 7 | Final Verification |

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 -> 4 tasks -> `deep`, `writing`, `unspecified-high`
- Wave 2 -> 4 tasks -> `deep`, `writing`, `unspecified-high`
- Final Verification -> 4 tasks -> `oracle`, `unspecified-high`, `deep`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 1. Add active main-workspace resolution utilities for main-skill sync

  **What to do**: Extend `src/openclaw_enhance/paths.py` so installer code can resolve the active main workspace deterministically before copying skills. Implement exact precedence: `(1)` `agent.workspace` from the OpenClaw config object, `(2)` `agents.defaults.workspace` if present, `(3)` `OPENCLAW_PROFILE`-aware fallback to `~/.openclaw/workspace-<profile>` when the profile is set and not `default`, `(4)` plain `~/.openclaw/workspace`. Add a helper that returns the `skills/` directory under that workspace without creating it. Update `tests/unit/test_paths.py` to cover all precedence branches and non-creating behavior.
  **Must NOT do**: Do not create or mutate workspaces in the path-resolution helper. Do not guess alternate config keys beyond the explicit precedence above.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: path resolution defines installer behavior and must be exact
  - Skills: [`test-driven-development`] — lock resolution order in tests before adding the helper
  - Omitted: [`brainstorming`] — routing strategy is already decided

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 5, 6, 8 | Blocked By: none

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/paths.py:9` — current path helpers stop at managed-root/runtime files and have no workspace resolution
  - Test: `tests/unit/test_paths.py:6` — existing path-test style to extend rather than replace
  - Pattern: `README.md:56` — main receives enhancement skills as part of the multitask design
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/agent-workspace.md` — active workspace defaults, profile-aware fallback, and `skills/` location inside the workspace

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_paths.py -q` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
from openclaw_enhance.paths import resolve_main_workspace, main_workspace_skills_dir
cfg = {"agent": {"workspace": "~/custom-ws"}}
ws = resolve_main_workspace(Path('/tmp/.openclaw'), config=cfg, env={})
assert str(ws).endswith('custom-ws')
assert main_workspace_skills_dir(ws).name == 'skills'
print('workspace-resolution-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Config-defined workspace wins
    Tool: Bash
    Steps: run `pytest tests/unit/test_paths.py -q -k workspace`
    Expected: tests prove `agent.workspace` and `agents.defaults.workspace` override profile/default fallbacks
    Evidence: .sisyphus/evidence/task-1-workspace-resolution.txt

  Scenario: Helper does not create directories
    Tool: Bash
    Steps: run `python - <<'PY'
from pathlib import Path
from openclaw_enhance.paths import resolve_main_workspace
target = resolve_main_workspace(Path('/tmp/nonexistent-openclaw'), config={}, env={})
assert not target.exists()
print(target)
PY`
    Expected: command exits 0 and prints the resolved path without creating it on disk
    Evidence: .sisyphus/evidence/task-1-workspace-resolution-error.txt
  ```

  **Commit**: YES | Message: `feat(paths): resolve active main workspace for skill sync` | Files: `src/openclaw_enhance/paths.py`, `tests/unit/test_paths.py`

- [x] 2. Make on-disk main-skill markdown the single contract source of truth

  **What to do**: Refactor `src/openclaw_enhance/skills_catalog.py` so `render_skill_contract()` and any skill-listing helpers read real `skills/<name>/SKILL.md` files instead of the embedded `SKILL_CONTRACTS` dict. Keep the module as the CLI-facing registry surface, but convert it into a file-backed loader with this exact resolution order: repo-root `skills/` when present in a source checkout, otherwise bundled package data under `openclaw_enhance/_bundled_skills/` inside the installed wheel. Update `pyproject.toml` so the root `skills/` tree is included in wheel builds at that bundled fallback path. Add/reshape unit coverage so `render-skill` returns byte-for-byte file content from the markdown source.
  **Must NOT do**: Do not keep duplicated router markdown strings in Python. Do not add a YAML/frontmatter dependency just to parse or render the file-backed contract.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: packaging and runtime resource lookup must work both in editable installs and built wheels
  - Skills: [`test-driven-development`] — prove file-backed rendering before deleting embedded contracts
  - Omitted: [`frontend-ui-ux`] — no UI surface exists

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 3, 4, 5, 7, 8 | Blocked By: none

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/skills_catalog.py:95` — embedded skill-contract dict to remove as the runtime source of truth
  - Pattern: `src/openclaw_enhance/skills_catalog.py:401` — current render helper to preserve as the public CLI-facing entry point
  - Pattern: `src/openclaw_enhance/cli.py:162` — `render-skill` already depends on `skills_catalog` rather than reading files directly
  - Pattern: `skills/oe-toolcall-router/SKILL.md:1` — actual skill markdown already exists on disk
  - Pattern: `pyproject.toml:39` — current build config only packages `src/openclaw_enhance` and misses root `skills/`

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_main_skills.py -q -k render` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
from openclaw_enhance.skills_catalog import render_skill_contract
assert render_skill_contract('oe-toolcall-router').strip() == Path('skills/oe-toolcall-router/SKILL.md').read_text(encoding='utf-8').strip()
print('router-contract-in-sync')
PY` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-skill oe-toolcall-router` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Rendered contract matches disk source
    Tool: Bash
    Steps: run `python - <<'PY'
from pathlib import Path
from openclaw_enhance.skills_catalog import render_skill_contract
for skill in ['oe-eta-estimator', 'oe-toolcall-router', 'oe-timeout-state-sync']:
    disk = Path(f'skills/{skill}/SKILL.md').read_text(encoding='utf-8').strip()
    rendered = render_skill_contract(skill).strip()
    assert rendered == disk, skill
print('all-skill-contracts-match')
PY`
    Expected: command exits 0 and confirms all rendered contracts match the markdown files exactly
    Evidence: .sisyphus/evidence/task-2-file-backed-contracts.txt

  Scenario: Unknown skill still fails cleanly
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli render-skill does-not-exist`
    Expected: non-zero exit with an unknown-skill message and a list of available main skills
    Evidence: .sisyphus/evidence/task-2-file-backed-contracts-error.txt
  ```

  **Commit**: YES | Message: `refactor(skills): load main skill contracts from markdown files` | Files: `src/openclaw_enhance/skills_catalog.py`, `src/openclaw_enhance/cli.py`, `pyproject.toml`, `tests/unit/test_main_skills.py`

- [x] 3. Rewrite router and orchestrator skill contracts to use native session primitives only

  **What to do**: Update `skills/oe-toolcall-router/SKILL.md` so it no longer presents Python import/use examples built around `SkillRouter`; the skill should instead describe a decision-only contract and explicitly instruct escalation through native `sessions_spawn` to `oe-orchestrator`, never direct worker routing. Update `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` so its examples stop advertising fictional helper wrappers like `dispatch_task(...)`, `dispatch_parallel(...)`, or `dispatch_with_watchdog(...)` and instead show native `sessions_spawn` / announce-oriented patterns that match OpenClaw docs and the existing orchestrator AGENTS contract.
  **Must NOT do**: Do not invent a new JSON protocol or helper API for dispatch. Do not change agent roles or worker topology.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: this task is authoritative contract writing, not runtime implementation
  - Skills: [`writing-plans`] — keep the skill language operational and unambiguous
  - Omitted: [`brainstorming`] — the design is already approved

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 4, 7, 8 | Blocked By: 2

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `skills/oe-toolcall-router/SKILL.md:71` — current router contract still teaches Python import/use examples that must be removed
  - Pattern: `skills/oe-toolcall-router/SKILL.md:109` — already states `main` must never route directly to workers
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md:24` — orchestrator contract already says native announce is the dispatch mechanism
  - Pattern: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md:130` — current pseudo helper examples to replace with native session-tool examples
  - Pattern: `docs/adr/0002-native-subagent-announce.md:21` — repo ADR already anchors native announce as the only communication protocol
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/subagents.md` — official `sessions_spawn` semantics and announce-chain constraints

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m openclaw_enhance.cli render-skill oe-toolcall-router` exits `0` and contains `sessions_spawn`
  - [ ] `python - <<'PY'
from pathlib import Path
router = Path('skills/oe-toolcall-router/SKILL.md').read_text(encoding='utf-8')
dispatch = Path('workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md').read_text(encoding='utf-8')
assert 'SkillRouter' not in router
assert 'TaskAssessment' not in router
assert 'dispatch_task(' not in dispatch
assert 'dispatch_parallel(' not in dispatch
assert 'dispatch_with_watchdog(' not in dispatch
assert 'sessions_spawn' in router or 'sessions_spawn' in dispatch
print('native-primitives-only')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Router skill teaches decision-only escalation
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli render-skill oe-toolcall-router`
    Expected: output describes staying in `main` vs escalating to `oe-orchestrator`, mentions native `sessions_spawn`, and does not mention `SkillRouter`/`TaskAssessment`
    Evidence: .sisyphus/evidence/task-3-router-contract.txt

  Scenario: Orchestrator dispatch skill no longer advertises wrapper APIs
    Tool: Bash
    Steps: run `python - <<'PY'
from pathlib import Path
text = Path('workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md').read_text(encoding='utf-8')
for banned in ['dispatch_task(', 'dispatch_parallel(', 'dispatch_with_watchdog(']:
    assert banned not in text, banned
print('no-wrapper-examples')
PY`
    Expected: command exits 0 and confirms all wrapper-style examples are gone
    Evidence: .sisyphus/evidence/task-3-router-contract-error.txt
  ```

  **Commit**: YES | Message: `docs(skills): align router contracts to native session primitives` | Files: `skills/oe-toolcall-router/SKILL.md`, `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`

- [x] 4. Remove the Python-first router runtime API from the codebase

  **What to do**: Delete `SkillRouter`, `TaskAssessment`, `RoutingDecision`, and `should_escalate_to_orchestrator` from `src/openclaw_enhance/skills_catalog.py`. Keep only the pieces still justified by the approved architecture: file-backed main-skill discovery/rendering, shared skill metadata if still needed by CLI/tests, `estimate_task_duration` only if it remains the support surface for `oe-eta-estimator`, and timeout sync helpers unrelated to router execution. Rewrite direct Python-API tests in `tests/unit/test_main_skills.py`, `tests/integration/test_subagent_routing.py`, and the `skill_router` fixture in `tests/fixtures/__init__.py` so they validate the contract-based behavior instead of instantiating a router object.
  **Must NOT do**: Do not reintroduce a compatibility shim that preserves runtime routing under a new name. Do not remove ETA or timeout helpers unless they are proven unused and unrelated to their own skills.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: this is a breaking API removal with coordinated test updates
  - Skills: [`test-driven-development`] — replace coverage before deleting the old surface
  - Omitted: [`systematic-debugging`] — this is planned refactoring, not bug chasing

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 7, 8 | Blocked By: 2, 3

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/skills_catalog.py:282` — `SkillRouter` class to remove
  - Pattern: `src/openclaw_enhance/skills_catalog.py:376` — boolean escalation helper to remove
  - Test: `tests/unit/test_main_skills.py:178` — current unit tests instantiate `SkillRouter`
  - Test: `tests/integration/test_subagent_routing.py:21` — current integration suite is dominated by Python routing decisions
  - Test: `tests/fixtures/__init__.py:156` — fixture currently constructs a `SkillRouter`
  - Pattern: `README.md:58` — router is supposed to be a skill used by main, not a Python service API

  **Acceptance Criteria** (agent-executable only):
  - [ ] `! grep -R "class SkillRouter\|class TaskAssessment\|class RoutingDecision\|def should_escalate_to_orchestrator" src/openclaw_enhance tests` exits `0`
  - [ ] `pytest tests/unit/test_main_skills.py tests/integration/test_subagent_routing.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-skill oe-toolcall-router` still exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Removed router API stays removed
    Tool: Bash
    Steps: run `grep -R "class SkillRouter\|class TaskAssessment\|class RoutingDecision\|def should_escalate_to_orchestrator" src/openclaw_enhance tests`
    Expected: command returns exit code 1 with no matches
    Evidence: .sisyphus/evidence/task-4-router-api-removal.txt

  Scenario: Contract-based tests replace object-instantiation tests
    Tool: Bash
    Steps: run `pytest tests/unit/test_main_skills.py tests/integration/test_subagent_routing.py -q`
    Expected: suites pass without importing or constructing the removed router classes/functions
    Evidence: .sisyphus/evidence/task-4-router-api-removal-error.txt
  ```

  **Commit**: YES | Message: `refactor(router): remove python-first routing api` | Files: `src/openclaw_enhance/skills_catalog.py`, `tests/unit/test_main_skills.py`, `tests/integration/test_subagent_routing.py`, `tests/fixtures/__init__.py`

- [x] 5. Sync enhancement-owned main skills into the resolved active workspace during install

  **What to do**: Extend the install lifecycle so the three main-session skills are actually copied into the resolved active main workspace under `skills/<skill-id>/SKILL.md`. Implement this in a dedicated helper module (for example `src/openclaw_enhance/install/main_skill_sync.py`) rather than burying copy logic directly in `installer.py`. The copy source must use the same resolved file-backed skill loader from Task 2. Installer behavior is fixed: ensure the main workspace exists, ensure its `skills/` directory exists, copy only `oe-eta-estimator`, `oe-toolcall-router`, and `oe-timeout-state-sync`, and register them in the manifest as `main-skill:<skill-id>` components. Update integration tests to verify config-defined workspaces and default fallbacks both receive the synced skills.
  **Must NOT do**: Do not copy non-enhancement skills. Do not overwrite unrelated sibling skill directories. Do not rely on CLI `render-skill` output as the copy source; copy the markdown tree directly.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: installer mutations must be deterministic, symmetric, and ownership-safe
  - Skills: [`test-driven-development`] — write failing workspace-sync tests before adding installer code
  - Omitted: [`brainstorming`] — the sync policy is already decided

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 6, 7, 8 | Blocked By: 1, 2

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/install/installer.py:396` — current install flow syncs workspaces, agents, hooks, runtime state, but never main-session skills
  - Pattern: `src/openclaw_enhance/paths.py:9` — managed-root utilities to extend rather than duplicate
  - Pattern: `tests/integration/test_main_skill_sync.py:21` — existing integration suite to repurpose toward actual workspace sync verification
  - Pattern: `README.md:56` — main-session skill requirement from the original design
  - Pattern: `docs/install.md:79` — docs already claim main skills are part of the install flow
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/agent-workspace.md` — workspace-local `skills/` is where main-session overrides live

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/integration/test_main_skill_sync.py -q -k install` exits `0`
  - [ ] `pytest tests/integration/test_install_uninstall.py -q -k registers_components` exits `0`
  - [ ] `python - <<'PY'
import json
from pathlib import Path
from openclaw_enhance.install import install

tmp = Path('tmp-router-install-check')
openclaw_home = tmp / '.openclaw'
workspace = tmp / '.openclaw' / 'workspace-custom'
openclaw_home.mkdir(parents=True, exist_ok=True)
(openclaw_home / 'VERSION').write_text('2026.3.11\n', encoding='utf-8')
(openclaw_home / 'config.json').write_text(json.dumps({'agent': {'workspace': str(workspace)}}) + '\n', encoding='utf-8')
result = install(openclaw_home, user_home=tmp)
assert result.success, result
for skill in ['oe-eta-estimator', 'oe-toolcall-router', 'oe-timeout-state-sync']:
    assert (workspace / 'skills' / skill / 'SKILL.md').exists(), skill
print('main-skill-sync-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Config-defined main workspace receives all main skills
    Tool: Bash
    Steps: run `pytest tests/integration/test_main_skill_sync.py -q -k custom_workspace`
    Expected: tests prove installer copies the three `oe-*` main skills into the configured workspace `skills/` directory
    Evidence: .sisyphus/evidence/task-5-main-skill-install.txt

  Scenario: Existing user skill directories survive enhancement install
    Tool: Bash
    Steps: run `pytest tests/integration/test_main_skill_sync.py -q -k preserves_user_skills`
    Expected: installer leaves unrelated skill directories untouched while refreshing only enhancement-owned skill folders
    Evidence: .sisyphus/evidence/task-5-main-skill-install-error.txt
  ```

  **Commit**: YES | Message: `feat(installer): sync main-session skills into active workspace` | Files: `src/openclaw_enhance/install/main_skill_sync.py`, `src/openclaw_enhance/install/installer.py`, `tests/integration/test_main_skill_sync.py`

- [x] 6. Remove synced main skills symmetrically on uninstall and expose them in status output

  **What to do**: Extend uninstall/status handling so enhancement-owned main skills are removed from the resolved active workspace based on manifest ownership, not by deleting the whole workspace or `skills/` directory. Update uninstall logic to remove only `main-skill:*` components and leave unrelated user skills untouched. Ensure install/uninstall/status tests assert that `status --json` lists the main-skill components after install and reports a clean component set after uninstall.
  **Must NOT do**: Do not delete the user's entire workspace or `skills/` directory. Do not infer ownership from name alone when the manifest has the authoritative record.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: uninstall symmetry and ownership safety are high-risk lifecycle behavior
  - Skills: [`test-driven-development`] — prove clean removal of only enhancement-owned skills
  - Omitted: [`systematic-debugging`] — this is planned lifecycle work

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 7, 8 | Blocked By: 1, 5

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/install/uninstaller.py:54` — current uninstall path only removes hooks, agents, workspaces, runtime state, and namespace artifacts
  - Pattern: `tests/integration/test_install_uninstall.py:118` — lifecycle tests to strengthen for main-skill removal symmetry
  - Pattern: `tests/integration/test_install_idempotency.py:43` — idempotency tests to keep stable after adding main-skill components
  - Pattern: `tests/integration/test_status_command.py:148` — status tests already check component reporting and should now include main-skill components
  - Pattern: `docs/install.md:149` — docs promise enhancement-owned artifacts are removable while user state is preserved

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/integration/test_install_uninstall.py tests/integration/test_install_idempotency.py tests/integration/test_status_command.py -q` exits `0`
  - [ ] `python - <<'PY'
import json
from pathlib import Path
from openclaw_enhance.install import install, uninstall, get_install_status

tmp = Path('tmp-router-uninstall-check')
openclaw_home = tmp / '.openclaw'
workspace = tmp / '.openclaw' / 'workspace'
openclaw_home.mkdir(parents=True, exist_ok=True)
(openclaw_home / 'VERSION').write_text('2026.3.11\n', encoding='utf-8')
(openclaw_home / 'config.json').write_text(json.dumps({'agent': {'workspace': str(workspace)}}) + '\n', encoding='utf-8')
(workspace / 'skills' / 'user-custom-skill').mkdir(parents=True, exist_ok=True)
(workspace / 'skills' / 'user-custom-skill' / 'SKILL.md').write_text('user skill', encoding='utf-8')
assert install(openclaw_home, user_home=tmp).success
status = get_install_status(user_home=tmp)
assert any(c.startswith('main-skill:oe-toolcall-router') for c in status['components'])
assert uninstall(openclaw_home=openclaw_home, user_home=tmp).success
assert (workspace / 'skills' / 'user-custom-skill' / 'SKILL.md').exists()
assert not (workspace / 'skills' / 'oe-toolcall-router').exists()
print('main-skill-uninstall-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Uninstall removes only enhancement-owned main skills
    Tool: Bash
    Steps: run `pytest tests/integration/test_install_uninstall.py -q -k main_skill`
    Expected: tests prove `oe-*` main skill directories are removed while unrelated user skills remain
    Evidence: .sisyphus/evidence/task-6-main-skill-uninstall.txt

  Scenario: Status reflects main-skill components accurately
    Tool: Bash
    Steps: run `pytest tests/integration/test_status_command.py -q -k components`
    Expected: status reports `main-skill:*` entries after install and no stale entries after uninstall
    Evidence: .sisyphus/evidence/task-6-main-skill-uninstall-error.txt
  ```

  **Commit**: YES | Message: `feat(uninstall): remove synced main skills symmetrically` | Files: `src/openclaw_enhance/install/uninstaller.py`, `tests/integration/test_install_uninstall.py`, `tests/integration/test_install_idempotency.py`, `tests/integration/test_status_command.py`

- [x] 7. Replace router-object tests with contract, sync, and harness verification

  **What to do**: Rebuild the remaining routing-related test surface around the new contract model. `tests/unit/test_main_skills.py` should validate file-backed discovery, frontmatter/metadata extraction, and `render_skill_contract()` behavior. `tests/integration/test_subagent_routing.py` should assert the router contract language encodes the expected decision semantics (`main` vs `oe-orchestrator`, never direct worker routing, native `sessions_spawn`). `tests/e2e/test_openclaw_harness.py` should keep the existing gated harness behavior but verify the clean-break surface: `render-skill` still works, and an installed harness workspace contains the synced main skills when installation is exercised. Update `tests/fixtures/__init__.py` to provide workspace/config fixtures instead of a `SkillRouter` object fixture.
  **Must NOT do**: Do not keep tests whose only purpose is instantiating removed Python router classes. Do not add brittle assertions against exact prose outside the core contract guarantees.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: this is a broad test migration across unit, integration, fixtures, and E2E gates
  - Skills: [`test-driven-development`] — replacement tests are the safety net for the breaking change
  - Omitted: [`brainstorming`] — testing strategy is already fixed by the plan

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 2, 3, 4, 5, 6

  **References** (executor has NO interview context — be exhaustive):
  - Test: `tests/unit/test_main_skills.py:1` — current unit suite is router-object-centric and must be rewritten
  - Test: `tests/integration/test_subagent_routing.py:21` — current integration suite hard-codes old routing classes and thresholds
  - Test: `tests/integration/test_main_skill_sync.py:21` — installer/sync integration suite to expand rather than duplicate elsewhere
  - Test: `tests/e2e/test_openclaw_harness.py:149` — existing harness rendering tests to preserve and extend
  - Test: `tests/fixtures/__init__.py:118` — sample task-assessment and `skill_router` fixtures to remove/replace
  - Pattern: `skills/oe-toolcall-router/SKILL.md:101` — contract sections the new tests should anchor to instead of Python API objects

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_main_skills.py tests/integration/test_subagent_routing.py tests/integration/test_main_skill_sync.py -q` exits `0`
  - [ ] `pytest tests/e2e/test_openclaw_harness.py -q` exits `0` when `OPENCLAW_HARNESS=1` and skips cleanly otherwise
  - [ ] `! grep -R "skill_router()\|TaskAssessment\|RoutingDecision\|SkillRouter" tests/fixtures tests/unit/test_main_skills.py tests/integration/test_subagent_routing.py` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Contract-focused suites pass without old router objects
    Tool: Bash
    Steps: run `pytest tests/unit/test_main_skills.py tests/integration/test_subagent_routing.py -q`
    Expected: tests pass while validating markdown contracts, render output, and main-vs-orchestrator semantics without importing removed router classes
    Evidence: .sisyphus/evidence/task-7-contract-tests.txt

  Scenario: Harness gate remains clean
    Tool: Bash
    Steps: run `pytest tests/e2e/test_openclaw_harness.py -q`
    Expected: suite explicitly skips when the harness is absent and does not fail due to removed Python routing classes
    Evidence: .sisyphus/evidence/task-7-contract-tests-error.txt
  ```

  **Commit**: YES | Message: `test(router): migrate routing coverage to skill contracts` | Files: `tests/unit/test_main_skills.py`, `tests/integration/test_subagent_routing.py`, `tests/integration/test_main_skill_sync.py`, `tests/e2e/test_openclaw_harness.py`, `tests/fixtures/__init__.py`

- [x] 8. Realign docs and ADRs to the new skill-first contract and verified install path

  **What to do**: Update the operator/docs surface so it stops describing a Python router object model and instead explains the actual post-refactor system: the markdown skill decides, native `sessions_spawn` / announce executes, and install syncs enhancement-owned main skills into the resolved active workspace. Update `README.md`, `docs/architecture.md`, `docs/install.md`, `docs/operations.md`, `docs/troubleshooting.md`, and `docs/adr/0002-native-subagent-announce.md`. Keep ADR 0002 focused on transport, but add explicit wording that skills should teach when/why to spawn rather than wrapping `sessions_spawn`. If any docs mention direct worker routing from `main` or wrapper helpers, remove that wording.
  **Must NOT do**: Do not reopen transport decisions or describe unsupported runtime wrappers. Do not document Windows/WSL as supported.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: this is primarily architecture/operations/ADR cleanup after the contract shift
  - Skills: [`writing-plans`] — keep the wording operational, precise, and consistent with the code changes
  - Omitted: [`frontend-ui-ux`] — documentation only

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: none | Blocked By: 1, 2, 3, 5, 6, 7

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:56` — original project requirement that `main` gets a router skill for TOOLCALL-based escalation
  - Pattern: `docs/architecture.md:122` — current docs describe `oe-toolcall-router` as a component but not the new file-backed/skill-first source-of-truth model
  - Pattern: `docs/install.md:79` — install flow section to update with real main-skill sync behavior
  - Pattern: `docs/operations.md:19` — routing activation and task-flow sections to rewrite around the skill-first contract
  - Pattern: `docs/troubleshooting.md:88` — router-related troubleshooting to update for synced workspace skills instead of Python router internals
  - Pattern: `docs/adr/0002-native-subagent-announce.md:146` — implementation notes to clarify skill-vs-runtime boundaries
  - External: `https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/subagents.md` — official statement that `sessions_spawn` is the native orchestration primitive and should not be wrapped

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  - [ ] `pytest tests/unit/test_docs_examples.py -q` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
targets = [
    Path('README.md'),
    Path('docs/architecture.md'),
    Path('docs/install.md'),
    Path('docs/operations.md'),
    Path('docs/troubleshooting.md'),
    Path('docs/adr/0002-native-subagent-announce.md'),
]
blob = '\n'.join(path.read_text(encoding='utf-8') for path in targets)
assert 'sessions_spawn' in blob
assert 'SkillRouter' not in blob
assert 'dispatch_task(' not in blob
print('docs-aligned')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Docs reflect skill-first routing and native execution
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli docs-check && pytest tests/unit/test_docs_examples.py -q`
    Expected: docs validation passes and examples/tests reference native `sessions_spawn` / announce semantics without Python router classes
    Evidence: .sisyphus/evidence/task-8-docs-alignment.txt

  Scenario: No stale wrapper-language remains in docs
    Tool: Bash
    Steps: run `grep -R "SkillRouter\|dispatch_task(\|dispatch_parallel(\|dispatch_with_watchdog(" README.md docs`
    Expected: command returns exit code 1 with no matches
    Evidence: .sisyphus/evidence/task-8-docs-alignment-error.txt
  ```

  **Commit**: YES | Message: `docs(router): document skill-first routing and native execution` | Files: `README.md`, `docs/architecture.md`, `docs/install.md`, `docs/operations.md`, `docs/troubleshooting.md`, `docs/adr/0002-native-subagent-announce.md`

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [x] F1. Plan Compliance Audit — oracle ✅ All 8 tasks complete, no router API, docs-check passes
- [x] F2. Code Quality Review — unspecified-high ✅ 77 tests pass, no TODOs in critical files
- [x] F3. Real Manual QA — unspecified-high ✅ CLI commands work, contract rendering verified
- [x] F4. Scope Fidelity Check — deep ✅ Skill-first model, file-backed skills, native sessions_spawn only

## Commit Strategy
- One commit per numbered task.
- Use `refactor`, `feat`, `test`, or `docs` prefixes as indicated in each task.
- Do not mix packaging/installer changes with unrelated doc-only edits in the same commit.

## Success Criteria
- The repo has no Python-first router runtime that competes with the skill contract.
- `oe-toolcall-router` is authored and rendered from markdown as the authoritative contract.
- Main-session skills are actually synced into the resolved active workspace during install and removed symmetrically during uninstall.
- Tests validate contract loading and skill sync instead of the removed Python router API.
- Docs, ADRs, and workspace skills consistently describe native `sessions_spawn` / announce as the only execution path.
