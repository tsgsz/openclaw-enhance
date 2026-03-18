# Main-to-Orchestrator Escalation Repair

## TL;DR
> **Summary**: Add a runtime-backed `main -> oe-orchestrator` escalation proof for heavy main-session requests, use that proof to drive any required main-workspace skill sync/path fixes, and only then align the routing contract and durable docs.
> **Deliverables**:
> - New `workspace-routing` live probe and canonical slug for main-session escalation
> - Validation bundle, matrix, and test coverage for the new probe
> - Expanded main-workspace resolution and main-skill sync coverage
> - Targeted sync/path repair, conditional router-contract tightening, and updated docs/reports
> **Effort**: Large
> **Parallel**: YES - 3 waves plus final verification
> **Critical Path**: Task 1 -> Task 2 -> Task 3 -> Task 5 -> Task 7 -> Task 8

## Context
### Original Request
- User asked for a detailed overall repair plan before implementation, after creating issues `#9`, `#10`, and `#11` and opening worktree `fix-main-orch-routing-gaps`.

### Interview Summary
- Scope is the combined repair of:
  - `#9`: heavy PPT/research request stayed on `main` instead of escalating to `oe-orchestrator`
  - `#10`: likely design/implementation gap where routing depends on passive markdown skills and/or mis-synced main workspace state
  - `#11`: missing real integration validation that proves a heavy request entering `main` actually escalates
- Current worktree baseline:
  - `npm test` passes
  - `python3 -m pytest` has one pre-existing environment-sensitive failure in `tests/integration/test_status_command.py::TestStatusInstallTime::test_status_shows_na_for_missing_install_time`; this is out of scope for the routing repair and must not block targeted routing verification
- Architecture constraints from `AGENTS.md`, `docs/adr/0002-native-subagent-announce.md`, and `docs/opencode-iteration-handbook.md` remain in force: no OpenClaw core edits, no runtime wrappers around `sessions_spawn`, skills remain file-backed markdown contracts.

### Metis Review (gaps addressed)
- Gap categories explicitly covered in this plan:
  - main-session entrypoint ambiguity for real-environment validation
  - separation of direct orchestrator proof vs main-escalation proof
  - workspace-resolution and skill-sync edge cases (`agent.workspace`, `agents.defaults.workspace`, profile fallback, `openclaw.json` preference, `--dev` installs)
  - stale troubleshooting guidance that still points to `workspace-default*`
  - requirement that the new proof fail when heavy requests stay entirely in `main`

## Work Objectives
### Core Objective
- Make `openclaw-enhance` prove and preserve the documented behavior that clearly heavy main-session requests escalate to `oe-orchestrator`, without violating the native `sessions_spawn` skill-first architecture.

### Deliverables
- New live probe command in `src/openclaw_enhance/validation/live_probes.py` for heavy main-session escalation
- New canonical slug `backfill-main-escalation` under `workspace-routing`
- Validation bundle wiring in `src/openclaw_enhance/validation/types.py` and `src/openclaw_enhance/validation/matrix.py`
- Expanded tests in `tests/unit/test_live_probes_model_pin.py`, `tests/integration/test_validation_real_env.py`, `tests/unit/test_validation_matrix.py`, `tests/unit/test_paths.py`, `tests/integration/test_main_skill_sync.py`, and, if needed, `tests/unit/test_main_skills.py` / `tests/integration/test_subagent_routing.py`
- Sync/path correction in `src/openclaw_enhance/install/main_skill_sync.py` and/or `src/openclaw_enhance/paths.py` if the red proof identifies the defect there
- Durable docs updates in `docs/testing-playbook.md`, `docs/operations.md`, `docs/troubleshooting.md`, and canonical report inventory/report updates under `docs/reports/`

### Definition of Done (verifiable conditions with commands)
- `npm test`
- `python3 -m pytest tests/unit/test_live_probes_model_pin.py tests/integration/test_validation_real_env.py tests/unit/test_validation_matrix.py tests/unit/test_paths.py tests/integration/test_main_skill_sync.py tests/unit/test_main_skills.py tests/integration/test_subagent_routing.py -q`
- `python -m openclaw_enhance.cli docs-check`
- `python -m openclaw_enhance.validation.live_probes main-escalation --openclaw-home "$OPENCLAW_HOME" --message "我26号要参加一个aws的亚太igaming的会，要演讲……先设计一个20页左右的PPT大纲（包含内容，数据和讲稿），并保证数据真实可追溯"`
- `python -m openclaw_enhance.cli validate-feature --feature-class workspace-routing --report-slug backfill-main-escalation`
- `python -m openclaw_enhance.cli validate-feature --feature-class workspace-routing --report-slug backfill-routing-yield`

### Must Have
- New proof uses a real main-session entrypoint, not direct `--agent oe-orchestrator`
- New proof captures main-session and orchestrator-session evidence separately
- Existing `backfill-routing-yield` remains intact as direct orchestrator runtime proof
- Any sync/path fix respects file-backed skill and native-execution invariants
- Targeted tests cover main workspace resolution, install-time sync, and validation bundle wiring

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- Must NOT edit OpenClaw core source or runtime-managed main `AGENTS.md` / `TOOLS.md`
- Must NOT introduce a Python/router wrapper around `sessions_spawn`
- Must NOT replace `backfill-routing-yield` with the new proof
- Must NOT broaden this into a heuristic redesign unless the new proof and sync/path evidence prove that necessary
- Must NOT fold in unrelated `status` output cleanup from `tests/integration/test_status_command.py`

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after + targeted RED/GREEN loops for validation, path, and skill-contract surfaces
- QA policy: every task includes executable happy-path and failure/edge scenarios
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: Task 1 (main-entrypoint probe contract), Task 4 (workspace-resolution and sync coverage)
Wave 2: Task 2 (main-escalation probe)
Wave 3: Task 3 (validation bundle/matrix wiring), Task 5 (sync/path repair)
Wave 4: Task 6 (conditional router-contract tightening), Task 7 (docs alignment)
Wave 5: Task 8 (runtime validation report + inventory)

### Dependency Matrix (full, all tasks)
| Task | Depends On | Notes |
|------|------------|-------|
| 1 | none | Discover and codify a supported main-session CLI path for probes |
| 2 | 1 | Probe must use the supported main-session entrypoint from Task 1 |
| 3 | 2 | Bundle wiring should target the actual probe command name and canonical slug |
| 4 | none | Can expand path/sync coverage before any code fix |
| 5 | 2, 4 | Use the red probe plus expanded tests to drive the sync/path fix |
| 6 | 5 | Execute only if Task 5 leaves the new proof red while sync/path tests are green |
| 7 | 3, 5 | Durable docs must match the actual proof and repaired runtime behavior |
| 8 | 3, 5, 7 | Canonical report depends on implemented proof + docs alignment; include Task 6 if executed |

### Agent Dispatch Summary (wave -> task count -> categories)
- Wave 1 -> 2 tasks -> `deep`, `unspecified-high`
- Wave 2 -> 1 task -> `deep`
- Wave 3 -> 2 tasks -> `unspecified-high`, `deep`
- Wave 4 -> 2 tasks -> `deep`, `writing`
- Wave 5 -> 1 task -> `unspecified-high`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Lock the supported main-session probe contract

  **What to do**: Determine the supported CLI entrypoint for a normal main session, then codify that choice in reusable probe helpers before adding a new runtime proof. Treat current `chat`-wording as stale until the real CLI contract is verified in the live environment. Add failing tests first for both the supported-path selection and the unsupported-path machine-readable failure.
  **Must NOT do**: Do not guess the main entrypoint from old docs/examples. Do not hardcode `openclaw chat` if the installed CLI does not support it. Do not touch `routing-yield` yet.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: this task resolves the main runtime entrypoint ambiguity that every later routing proof depends on.
  - Skills: [`test-driven-development`] - establish helper selection/failure tests before editing the probe implementation.
  - Omitted: [`using-git-worktrees`] - already operating inside the dedicated worktree.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 2, 3, 8 | Blocked By: none

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `src/openclaw_enhance/validation/live_probes.py:57` - JSON extraction helper already used by existing probes.
  - Pattern: `src/openclaw_enhance/validation/live_probes.py:121` - transcript lookup pattern for runtime session proof.
  - Pattern: `src/openclaw_enhance/validation/live_probes.py:183` - bootstrap preparation for runtime probe safety.
  - Pattern: `src/openclaw_enhance/validation/live_probes.py:241` - existing `routing-yield` command shape and model-pinning pattern.
  - Test: `tests/unit/test_live_probes_model_pin.py:32` - expected mocking style for probe subprocess/model-pin tests.
  - Evidence: `docs/reports/2026-03-15-harness-routing-test-workspace-routing.md:19` - stale runtime proof previously failed with `unknown command 'chat'`.
  - Evidence: `docs/reports/examples/workspace-routing-example.md:40` - example still advertises `openclaw chat --message`, so docs/examples cannot be trusted without re-verification.

  **Acceptance Criteria** (agent-executable only):
  - [ ] A reusable helper or equivalent probe path in `src/openclaw_enhance/validation/live_probes.py` selects the supported main-session CLI command without assuming `chat` exists.
  - [ ] A targeted test proves the supported command path is used when available.
  - [ ] A targeted test proves the probe exits with a machine-readable unsupported-entrypoint failure when no valid main-session CLI path exists.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Main entrypoint helper selects the supported CLI path
    Tool: Bash
    Steps: Run `python3 -m pytest tests/unit/test_live_probes_helpers.py -k main_entrypoint -q`
    Expected: PASS; helper test confirms the chosen main-session command path and no stale `chat` fallback is required.
    Evidence: .sisyphus/evidence/task-1-main-entrypoint.txt

  Scenario: Unsupported main entrypoint fails cleanly
    Tool: Bash
    Steps: Run `python3 -m pytest tests/unit/test_live_probes_helpers.py -k unsupported_main_entrypoint -q`
    Expected: PASS; the test asserts a deterministic machine-readable failure such as `main_entrypoint_unsupported` rather than an uncaught exception.
    Evidence: .sisyphus/evidence/task-1-main-entrypoint-error.txt
  ```

  **Commit**: YES | Message: `test(validation): codify main session probe entrypoint` | Files: `src/openclaw_enhance/validation/live_probes.py`, `tests/unit/test_live_probes_helpers.py`

- [ ] 2. Add the `main-escalation` live probe

  **What to do**: Add a new `workspace-routing` live probe command in `src/openclaw_enhance/validation/live_probes.py` named `main-escalation`. The probe must send a clearly heavy issue-`#9`-class prompt to a normal main session, capture the main-session metadata, and prove handoff to `oe-orchestrator` using observable session/transcript evidence. Use this exact prompt seed unless the supported main-session CLI requires escaping adjustments: `搜索 2025 年整个东南亚 iGaming 行业现状，给出 2026 年判断，并先设计一个 20 页左右的 PPT 大纲（包含内容、数据和讲稿），保证数据真实可追溯。` Emit a dedicated success marker (for example `PROBE_MAIN_ESCALATION_OK`) and deterministic failure reasons for missing main session id, missing orchestrator handoff, or missing transcript evidence.
  **Must NOT do**: Do not point this probe directly at `--agent oe-orchestrator`. Do not declare success from prompt text alone. Do not remove or weaken `routing-yield`.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: the probe is the new runtime truth source for issues `#9` and `#11`.
  - Skills: [`test-driven-development`] - add mocked success and failure tests before probe implementation is considered done.
  - Omitted: [`systematic-debugging`] - this task creates the proof surface; deeper debugging happens only after the proof is red.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 3, 5, 6, 8 | Blocked By: 1

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `src/openclaw_enhance/validation/live_probes.py:241` - existing command declaration, pinned model handling, and proof payload format.
  - Pattern: `src/openclaw_enhance/validation/live_probes.py:300` - tool-surface validation pattern used by `routing-yield`.
  - Pattern: `src/openclaw_enhance/validation/live_probes.py:324` - JSON emission shape for successful probe payloads.
  - Pattern: `src/openclaw_enhance/validation/live_probes.py:341` - second probe command (`recovery-worker`) shows how to reuse the same helper stack.
  - Contract: `skills/oe-toolcall-router/SKILL.md:39` - heavy tasks (`> 2` toolcalls, research, multi-file, complex) must escalate.
  - Contract: `docs/operations.md:21` - documented activation rules for orchestrator escalation.
  - Test: `tests/unit/test_live_probes_model_pin.py:32` - established unit-test pattern for probe subprocess calls and pinned-model assertions.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `src/openclaw_enhance/validation/live_probes.py` exposes a `main-escalation` command with pinned-model behavior matching the other live probes.
  - [ ] Success payload includes both main-session and orchestrator-session evidence fields (session id and transcript path, or equivalent metadata already used elsewhere in the validation system).
  - [ ] Failure tests prove the probe returns a machine-readable failure when a heavy request stays entirely in `main`.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Probe emits success payload on mocked main-to-orchestrator handoff
    Tool: Bash
    Steps: Run `python3 -m pytest tests/unit/test_live_probes_model_pin.py -k main_escalation -q`
    Expected: PASS; the probe preserves model pinning and emits a success marker with both session evidence fields.
    Evidence: .sisyphus/evidence/task-2-main-escalation.txt

  Scenario: Probe rejects a heavy request that never leaves main
    Tool: Bash
    Steps: Run `python3 -m pytest tests/unit/test_live_probes_helpers.py -k orchestrator_handoff_missing -q`
    Expected: PASS; the failure path asserts a deterministic machine-readable reason such as `orchestrator_handoff_missing`.
    Evidence: .sisyphus/evidence/task-2-main-escalation-error.txt
  ```

  **Commit**: YES | Message: `test(validation): add main escalation live probe` | Files: `src/openclaw_enhance/validation/live_probes.py`, `tests/unit/test_live_probes_helpers.py`, `tests/unit/test_live_probes_model_pin.py`

- [ ] 3. Wire the canonical validation slug and bundle for `backfill-main-escalation`

  **What to do**: Add a new canonical slug `backfill-main-escalation` under `FeatureClass.WORKSPACE_ROUTING`. Update validation command generation, shipped-feature matrix, integration tests, and harness coverage so the new proof is first-class and separate from `backfill-routing-yield` and `backfill-recovery-worker`.
  **Must NOT do**: Do not overload `backfill-routing-yield`. Do not create a new feature class. Do not let matrix tests silently accept the old slug set.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: this is controlled validation plumbing with multiple contract surfaces but limited algorithmic risk.
  - Skills: [`test-driven-development`] - bundle command and matrix tests should fail first before the wiring is added.
  - Omitted: [`writing-plans`] - this is direct implementation/test wiring, not a new planning session.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 7, 8 | Blocked By: 2

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `src/openclaw_enhance/validation/types.py:89` - bundle command dispatch by feature class/slug.
  - Pattern: `src/openclaw_enhance/validation/types.py:128` - current `workspace-routing` slug branching for `routing-yield` vs `recovery-worker`.
  - Pattern: `src/openclaw_enhance/validation/matrix.py:5` - canonical slug list and proof expectations.
  - Test: `tests/integration/test_validation_real_env.py:200` - routing bundle command-order assertions.
  - Test: `tests/unit/test_validation_matrix.py:7` - canonical slug-set assertion.
  - Test: `tests/e2e/test_openclaw_harness.py:589` - harness-level validation feature-class checks already exercise `workspace-routing`.
  - Contract: `docs/testing-playbook.md:53` - current bundle definition that must gain a separate main-escalation proof.
  - Inventory: `docs/reports/INVENTORY.md:5` - canonical current-branch backfill table that must retain existing slugs while adding the new one later.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `get_bundle_commands(FeatureClass.WORKSPACE_ROUTING, "backfill-main-escalation")` returns exactly one `main-escalation` probe command.
  - [ ] `SHIPPED_FEATURES` includes `backfill-main-escalation` without removing `backfill-routing-yield` or `backfill-recovery-worker`.
  - [ ] Validation CLI integration tests cover the new slug and still pass for the legacy routing slugs.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: New workspace-routing slug is wired into validation bundles
    Tool: Bash
    Steps: Run `python3 -m pytest tests/integration/test_validation_real_env.py -k main_escalation -q`
    Expected: PASS; the new slug resolves to the `main-escalation` probe command and keeps existing slug behavior intact.
    Evidence: .sisyphus/evidence/task-3-validation-bundle.txt

  Scenario: Canonical slug table rejects missing routing proof entries
    Tool: Bash
    Steps: Run `python3 -m pytest tests/unit/test_validation_matrix.py -q`
    Expected: PASS; the canonical slug-set test includes `backfill-main-escalation` and still requires the legacy routing slugs.
    Evidence: .sisyphus/evidence/task-3-validation-bundle-error.txt
  ```

  **Commit**: YES | Message: `test(validation): wire main escalation routing bundle` | Files: `src/openclaw_enhance/validation/types.py`, `src/openclaw_enhance/validation/matrix.py`, `tests/integration/test_validation_real_env.py`, `tests/unit/test_validation_matrix.py`, `tests/e2e/test_openclaw_harness.py`

- [ ] 4. Expand main-workspace resolution and main-skill sync coverage

  **What to do**: Add failing tests that define the supported runtime workspace-resolution contract and install-time skill sync behavior for main-session skills. Cover `agent.workspace`, `agents.defaults.workspace`, non-default `OPENCLAW_PROFILE`, default/no-profile fallback, `openclaw.json` preference, and `--dev` install shape. Use these tests to narrow whether issue `#9` is a sync/path problem before changing runtime code.
  **Must NOT do**: Do not patch runtime code in this task. Do not stop at the two existing sync cases. Do not leave profile-based or `openclaw.json`-based behavior untested.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: this is focused test design around path/sync contract coverage.
  - Skills: [`test-driven-development`] - coverage must go red before any sync/path code changes occur.
  - Omitted: [`systematic-debugging`] - these are targeted contract tests, not exploratory bug-fixing yet.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 5 | Blocked By: none

  **References** (executor has NO interview context - be exhaustive):
  - API/Type: `src/openclaw_enhance/paths.py:29` - config-derived workspace resolution helper.
  - API/Type: `src/openclaw_enhance/paths.py:47` - `resolve_main_workspace()` decision path.
  - API/Type: `src/openclaw_enhance/paths.py:67` - `openclaw.json` preference helper.
  - Pattern: `tests/unit/test_paths.py:36` - existing main-workspace resolution tests.
  - Pattern: `tests/unit/test_paths.py:97` - config-path preference tests.
  - Pattern: `tests/integration/test_main_skill_sync.py:44` - current install-time sync assertions for config-defined workspace and default fallback only.
  - Contract: `docs/troubleshooting.md:108` - current troubleshooting guidance still assumes `workspace-default*`, which the expanded tests should help correct.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `tests/unit/test_paths.py` covers `agent.workspace`, `agents.defaults.workspace`, non-default profile fallback, default/no-profile fallback, and `openclaw.json` preference.
  - [ ] `tests/integration/test_main_skill_sync.py` covers install-time sync for config-defined workspace, defaults workspace, profile-based workspace, and `--dev`-compatible expectations where relevant.
  - [ ] At least one of the new tests fails before Task 5 if the current runtime workspace mapping is wrong.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Path-resolution contract is fully covered
    Tool: Bash
    Steps: Run `python3 -m pytest tests/unit/test_paths.py -q`
    Expected: PASS; all new path-resolution cases are asserted, including profile and config precedence.
    Evidence: .sisyphus/evidence/task-4-path-resolution.txt

  Scenario: Main skill sync covers non-default runtime workspace shapes
    Tool: Bash
    Steps: Run `python3 -m pytest tests/integration/test_main_skill_sync.py -q`
    Expected: PASS; the suite verifies skill placement for config-defined, defaults-derived, and profile-derived workspaces.
    Evidence: .sisyphus/evidence/task-4-path-resolution-error.txt
  ```

  **Commit**: YES | Message: `test(sync): expand main workspace resolution coverage` | Files: `tests/unit/test_paths.py`, `tests/integration/test_main_skill_sync.py`

- [ ] 5. Repair main skill sync to the actual runtime workspace

  **What to do**: Use the red `main-escalation` proof plus the new path/sync tests to repair main-skill delivery only where the evidence demands it. Primary fix surface is `src/openclaw_enhance/paths.py` and `src/openclaw_enhance/install/main_skill_sync.py`. Ensure install-time sync lands `oe-eta-estimator`, `oe-toolcall-router`, and `oe-timeout-state-sync` in the same workspace the live main session actually loads. Preserve copy installs, `--dev` symlink installs, and manifest/uninstall symmetry.
  **Must NOT do**: Do not add a custom router wrapper. Do not move skills into multiple workspaces to "cover all bases." Do not edit worker workspace contracts. Do not patch around the issue in docs only.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: this is the most likely runtime defect surface and must be fixed without violating the skill-first architecture.
  - Skills: [`test-driven-development`, `systematic-debugging`] - use the new failing proof/tests to isolate whether the mismatch is config, profile, or install-path related.
  - Omitted: [`using-git-worktrees`] - the executor is already in the dedicated repair worktree.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 6, 7, 8 | Blocked By: 2, 4

  **References** (executor has NO interview context - be exhaustive):
  - API/Type: `src/openclaw_enhance/install/main_skill_sync.py:20` - current main-skill sync entrypoint and file copy/symlink behavior.
  - API/Type: `src/openclaw_enhance/install/main_skill_sync.py:38` - target skill path is currently `skills/<skill_id>/SKILL.md` under the resolved main workspace.
  - API/Type: `src/openclaw_enhance/paths.py:47` - runtime main-workspace resolution logic.
  - Contract: `docs/opencode-iteration-handbook.md:130` - native execution only, file-backed skill invariants, symmetric lifecycle.
  - Test: `tests/unit/test_paths.py:36` - expanded path-resolution assertions from Task 4.
  - Test: `tests/integration/test_main_skill_sync.py:44` - install-time sync test scaffold.
  - Evidence: `docs/troubleshooting.md:108` - current symptom/diagnosis area that should only change after the runtime fix is understood.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Install-time sync places main routing skills into the runtime-resolved main workspace for normal copy installs.
  - [ ] `--dev` installs preserve the same runtime-resolved placement semantics via symlinks where applicable.
  - [ ] Targeted path/sync tests pass after the fix.
  - [ ] The `main-escalation` probe no longer fails because the router skill is missing or synced to the wrong workspace.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Runtime-resolved workspace receives the synced main skills
    Tool: Bash
    Steps: Run `python3 -m pytest tests/unit/test_paths.py tests/integration/test_main_skill_sync.py -q`
    Expected: PASS; runtime workspace resolution and installer-side skill placement match across config/default/profile cases.
    Evidence: .sisyphus/evidence/task-5-skill-sync.txt

  Scenario: Missing-skill / wrong-workspace regression is prevented
    Tool: Bash
    Steps: Run `python3 -m pytest tests/unit/test_live_probes_helpers.py -k missing_skill_or_wrong_workspace -q`
    Expected: PASS; the regression test proves the repaired logic no longer leaves the probe in a missing-router-skill state.
    Evidence: .sisyphus/evidence/task-5-skill-sync-error.txt
  ```

  **Commit**: YES | Message: `fix(install): align main skill sync with active workspace` | Files: `src/openclaw_enhance/paths.py`, `src/openclaw_enhance/install/main_skill_sync.py`, `tests/unit/test_paths.py`, `tests/integration/test_main_skill_sync.py`

- [ ] 6. Tighten the heavy-research routing contract only if the repaired sync path still leaves the probe red

  **What to do**: Execute this task only if Task 5 leaves `main-escalation` red while the path/sync tests are green. In that case, strengthen the markdown contract in `skills/oe-toolcall-router/SKILL.md` to include an explicit heavy PPT/research + traceable-data example matching issue `#9`, and update the related skill-rendering tests. Keep thresholds unchanged unless the red probe specifically proves a threshold mismatch.
  **Must NOT do**: Do not change thresholds speculatively. Do not duplicate skill text into Python strings. Do not route main directly to workers.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: only execute this if runtime evidence shows the delivered contract still under-specifies the heavy-task decision.
  - Skills: [`test-driven-development`] - update contract assertions first, then revise the markdown.
  - Omitted: [`systematic-debugging`] - this task is contract refinement after sync debugging has already been completed.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: 7, 8 | Blocked By: 5

  **References** (executor has NO interview context - be exhaustive):
  - Contract: `skills/oe-toolcall-router/SKILL.md:22` - current stay-local vs escalate philosophy.
  - Contract: `skills/oe-toolcall-router/SKILL.md:39` - current heavy-task heuristic table.
  - Contract: `skills/oe-toolcall-router/SKILL.md:110` - current simple/complex/research examples.
  - Test: `tests/unit/test_main_skills.py:103` - registry/router heuristic tests.
  - Test: `tests/unit/test_main_skills.py:119` - exact contract-render assertions.
  - Test: `tests/integration/test_subagent_routing.py:20` - contract rendering/integration expectations for the file-backed skill model.
  - Contract: `docs/adr/0002-native-subagent-announce.md:19` - skills define when/why; native `sessions_spawn` executes.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `skills/oe-toolcall-router/SKILL.md` contains an explicit heavy research/PPT example that maps issue `#9`-class prompts to `oe-orchestrator`.
  - [ ] Threshold numbers remain unchanged unless the failing probe evidence explicitly justifies changing them.
  - [ ] Skill-rendering tests assert the new contract language and still preserve the native-execution/no-wrapper rules.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Updated router contract renders the new heavy-task example
    Tool: Bash
    Steps: Run `python3 -m pytest tests/unit/test_main_skills.py -k toolcall_router -q`
    Expected: PASS; contract-render tests assert the issue-#9-class heavy-task example and the existing no-wrapper rule.
    Evidence: .sisyphus/evidence/task-6-router-contract.txt

  Scenario: File-backed integration still treats the router skill as the source of truth
    Tool: Bash
    Steps: Run `python3 -m pytest tests/integration/test_subagent_routing.py -q`
    Expected: PASS; integration tests still validate file-backed skill loading after the contract update.
    Evidence: .sisyphus/evidence/task-6-router-contract-error.txt
  ```

  **Commit**: YES | Message: `docs(router): tighten heavy research escalation contract` | Files: `skills/oe-toolcall-router/SKILL.md`, `tests/unit/test_main_skills.py`, `tests/integration/test_subagent_routing.py`

- [ ] 7. Align durable docs with the new proof model and repaired runtime behavior

  **What to do**: Update the durable docs so they distinguish three separate routing proofs: direct orchestrator runtime surface, recovery-worker runtime surface, and main-session escalation runtime surface. Fix stale main-workspace troubleshooting guidance and stale examples that still reference `openclaw chat` or `workspace-default*`. Update the handbook only if the new proof becomes a permanent canonical workflow rule rather than a one-off repair note.
  **Must NOT do**: Do not claim the new proof exists before Task 8 passes. Do not remove existing routing/recovery report references. Do not leave stale `chat` examples in examples/docs if the verified main entrypoint differs.

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: this task is documentation alignment across multiple canonical docs after the implementation path is settled.
  - Skills: [`verification-before-completion`] - run `docs-check` and confirm the updated docs are internally consistent before calling the task done.
  - Omitted: [`test-driven-development`] - this task is documentation-driven, not new runtime logic.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 8 | Blocked By: 3, 5

  **References** (executor has NO interview context - be exhaustive):
  - Contract: `docs/operations.md:7` - current "complex tasks automatically escalate" language and routing overview.
  - Contract: `docs/testing-playbook.md:53` - current `workspace-routing` bundle definition and canonical slug table.
  - Contract: `docs/troubleshooting.md:106` - stale `workspace-default*` routing diagnosis.
  - Contract: `docs/opencode-iteration-handbook.md:126` - architecture invariants and durable-status section.
  - Example: `docs/reports/examples/workspace-routing-example.md:40` - stale `openclaw chat` usage that must match the verified CLI path.
  - Inventory pattern: `docs/reports/INVENTORY.md:5` - canonical/superseded report structure to preserve in Task 8.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `docs/testing-playbook.md` defines `backfill-main-escalation` separately from `backfill-routing-yield` and `backfill-recovery-worker`.
  - [ ] `docs/operations.md` and `docs/troubleshooting.md` point at the repaired proof/workspace model rather than stale `workspace-default*` or `chat` assumptions.
  - [ ] `python -m openclaw_enhance.cli docs-check` passes after the doc edits.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Durable docs align with the repaired proof model
    Tool: Bash
    Steps: Run `python -m openclaw_enhance.cli docs-check`
    Expected: PASS; all canonical docs, playbook text, and inventory structure remain aligned.
    Evidence: .sisyphus/evidence/task-7-docs-alignment.txt

  Scenario: Example/report docs no longer rely on stale main-session commands
    Tool: Bash
    Steps: Run `python3 -m pytest tests/e2e/test_openclaw_harness.py -k routing -q`
    Expected: PASS; harness/docs-facing routing coverage still passes after replacing stale example assumptions.
    Evidence: .sisyphus/evidence/task-7-docs-alignment-error.txt
  ```

  **Commit**: YES | Message: `docs(validation): add main escalation routing proof` | Files: `docs/testing-playbook.md`, `docs/operations.md`, `docs/troubleshooting.md`, `docs/opencode-iteration-handbook.md`, `docs/reports/examples/workspace-routing-example.md`

- [ ] 8. Generate the canonical `backfill-main-escalation` runtime report and update inventory

  **What to do**: Run the repaired `workspace-routing` validation bundle in the real environment and save the canonical PASS report as `docs/reports/YYYY-MM-DD-backfill-main-escalation-workspace-routing.md`. The report must capture the heavy main-session prompt, the main-session id, the orchestrator-session id, transcript-path evidence for both, and the final conclusion. Update `docs/reports/INVENTORY.md` to add the new canonical slug entry without disturbing the existing routing and recovery report rows.
  **Must NOT do**: Do not mark this task complete with mocked/unit evidence only. Do not overwrite `backfill-routing-yield`. Do not update inventory before the report file exists.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: this is the real-environment merge-gate proof for the routing repair.
  - Skills: [`verification-before-completion`] - the final report and inventory update must be backed by observed command output.
  - Omitted: [`systematic-debugging`] - by this point the red proof should already be resolved; this task is final runtime verification.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: Final Verification Wave | Blocked By: 3, 5, 7

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `docs/reports/2026-03-15-backfill-routing-yield-workspace-routing.md:1` - canonical report format for a `workspace-routing` PASS report.
  - Pattern: `docs/reports/template.md:1` - required report schema.
  - Inventory: `docs/reports/INVENTORY.md:5` - canonical inventory table that must gain the new slug row.
  - Bundle: `docs/testing-playbook.md:53` - repaired `workspace-routing` bundle definition from Task 7.
  - Command wiring: `src/openclaw_enhance/validation/types.py:128` - bundle command generation path used by `validate-feature`.
  - Probe: `src/openclaw_enhance/validation/live_probes.py` - `main-escalation` command implementation from Task 2.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class workspace-routing --report-slug backfill-main-escalation` exits successfully and produces a PASS report file.
  - [ ] The generated report includes both main-session and orchestrator-session evidence fields.
  - [ ] `docs/reports/INVENTORY.md` includes the new canonical slug row for `backfill-main-escalation`.
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class workspace-routing --report-slug backfill-routing-yield` still passes after the new slug lands.

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: New canonical main-escalation proof passes in the real environment
    Tool: Bash
    Steps: Run `python -m openclaw_enhance.cli validate-feature --feature-class workspace-routing --report-slug backfill-main-escalation`
    Expected: PASS report is generated under `docs/reports/` and includes both main and orchestrator transcript evidence.
    Evidence: .sisyphus/evidence/task-8-main-escalation-report.txt

  Scenario: Legacy direct orchestrator proof still passes
    Tool: Bash
    Steps: Run `python -m openclaw_enhance.cli validate-feature --feature-class workspace-routing --report-slug backfill-routing-yield`
    Expected: PASS; the repaired main-escalation proof does not regress the existing direct orchestrator runtime-surface proof.
    Evidence: .sisyphus/evidence/task-8-main-escalation-report-error.txt
  ```

  **Commit**: YES | Message: `test(validation): record main escalation runtime proof` | Files: `docs/reports/YYYY-MM-DD-backfill-main-escalation-workspace-routing.md`, `docs/reports/INVENTORY.md`

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [ ] F1. Plan Compliance Audit - oracle
  - Tool: Bash
  - Steps: Run `git diff --name-only $(git merge-base HEAD main)..HEAD`; compare the changed-file set against Tasks 1-8; run `python -m openclaw_enhance.cli render-skill oe-toolcall-router` and confirm the final contract still routes heavy tasks to `oe-orchestrator` without introducing wrapper instructions.
  - Expected: Every changed file maps to a planned task, no unplanned scope appears, and no wrapper-based routing language is introduced.
  - Evidence: `.sisyphus/evidence/f1-plan-compliance.txt`
- [ ] F2. Code Quality Review - unspecified-high
  - Tool: Bash
  - Steps: Run `npm test`; run `python3 -m pytest tests/unit/test_live_probes_model_pin.py tests/integration/test_validation_real_env.py tests/unit/test_validation_matrix.py tests/unit/test_paths.py tests/integration/test_main_skill_sync.py tests/unit/test_main_skills.py tests/integration/test_subagent_routing.py -q`; run `python -m openclaw_enhance.cli docs-check`.
  - Expected: All targeted tests and docs-check pass; no duplicate slug wiring, broken path-resolution logic, or invalid skill-render assertions remain.
  - Evidence: `.sisyphus/evidence/f2-code-quality.txt`
- [ ] F3. Runtime QA Replay - unspecified-high
  - Tool: Bash
  - Steps: Run `python -m openclaw_enhance.validation.live_probes main-escalation --openclaw-home "$OPENCLAW_HOME" --message "搜索 2025 年整个东南亚 iGaming 行业现状，给出 2026 年判断，并先设计一个 20 页左右的 PPT 大纲（包含内容、数据和讲稿），保证数据真实可追溯。"`; then run `python -m openclaw_enhance.cli validate-feature --feature-class workspace-routing --report-slug backfill-main-escalation`; open the generated report and confirm it contains both the main-session and orchestrator-session evidence fields.
  - Expected: The direct probe succeeds, the canonical validation report is PASS, and the report records both session/transcript evidence sets.
  - Evidence: `.sisyphus/evidence/f3-real-qa.txt`
- [ ] F4. Scope Fidelity Check - deep
  - Tool: Bash
  - Steps: Run `git diff --name-only $(git merge-base HEAD main)..HEAD`; verify no files outside the planned routing/validation/docs surfaces changed; run `python -m openclaw_enhance.cli validate-feature --feature-class workspace-routing --report-slug backfill-routing-yield` to confirm the legacy direct-orchestrator proof still passes.
  - Expected: No OpenClaw core edits, no unrelated `status`-test cleanup, and no regression of the existing `backfill-routing-yield` proof.
  - Evidence: `.sisyphus/evidence/f4-scope-fidelity.txt`

## Commit Strategy
- Commit 1: `test(validation): scaffold main escalation probe contract`
- Commit 2: `test(sync): expand main workspace resolution coverage`
- Commit 3: `fix(install): align main skill sync with runtime workspace`
- Commit 4: `docs(router): add main escalation validation contract`
- Commit 5: `test(validation): record main escalation runtime proof`
- Conditional Commit 6: `docs(router): tighten heavy research escalation examples` (only if Task 6 executes)

## Success Criteria
- Heavy issue-`#9`-class prompts entering `main` produce observable `oe-orchestrator` handoff evidence instead of staying fully local
- `backfill-main-escalation` becomes a distinct canonical `workspace-routing` proof alongside `backfill-routing-yield` and `backfill-recovery-worker`
- Main skill sync/path tests cover the actual runtime workspace resolution contract used by live main sessions
- Docs and troubleshooting guidance point to the same workspace/proof model used by the repaired validation path
- `docs-check`, targeted Python tests, `npm test`, and both routing validation slugs pass
