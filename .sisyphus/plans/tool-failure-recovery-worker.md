# Tool Failure Recovery Worker

## TL;DR
> **Summary**: Add a dedicated `oe-tool-recovery` worker so tool-call failures inside orchestrator rounds can be diagnosed and recovered without weakening `oe-syshelper`'s read-only contract.
> **Deliverables**:
> - new `oe-tool-recovery` workspace contract and skill
> - orchestrator recovery dispatch + `recovered_method` handoff rules
> - installer/registry/render support for the new workspace
> - worker-boundary, dispatch-contract, and recovery-schema tests
> - handbook/architecture/operations updates for the recovery flow
> **Effort**: Large
> **Parallel**: YES - 3 waves
> **Critical Path**: Task 1 -> Task 3 -> Task 4 -> Task 7 -> Final Verification Wave

## Context
### Original Request
User wants failures from orchestrator or worker tool calls to trigger a recovery flow: inspect the failed tool usage, test safe variants, check docs and alternatives, then return a working method so orchestrator can continue or retry.

### Interview Summary
- `oe-syshelper` must remain strictly read-only.
- User selected a separate narrow worker rather than broadening `oe-syshelper`.
- Chosen design: add `oe-tool-recovery` as a dedicated recovery specialist.
- Recovery remains inside the native bounded loop using `sessions_spawn` / `announce` / `sessions_yield`.
- Recovery worker returns a `recovered_method`; orchestrator alone decides retry, reroute, or escalation.
- Each failed step may receive at most one recovery-assisted retry.

### Metis Review (gaps addressed)
- Guard against scope creep: recovery worker must not become a general execution worker.
- Make recovery worker a leaf node: no subagent spawning, no worker-to-worker handoff.
- Define explicit fallback if recovery itself fails.
- Add tests for retry limit, contract validation, and boundary enforcement.

## Work Objectives
### Core Objective
Introduce a dedicated tool-failure recovery path that preserves native subagent execution, keeps `oe-syshelper` read-only, and gives orchestrator structured recovery evidence for exactly one bounded retry per failed step.

### Deliverables
- `workspaces/oe-tool-recovery/AGENTS.md`
- `workspaces/oe-tool-recovery/TOOLS.md`
- `workspaces/oe-tool-recovery/skills/oe-tool-recovery/SKILL.md`
- orchestrator contract updates in `workspaces/oe-orchestrator/AGENTS.md` and `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`
- workspace registration/render/install updates in `src/openclaw_enhance/install/installer.py` and related discovery tests/docs
- recovery boundary, schema, and integration tests
- handbook/architecture/operations documentation updates

### Definition of Done (verifiable conditions with commands)
- `pytest tests/integration/test_worker_role_boundaries.py tests/integration/test_orchestrator_dispatch_contract.py tests/unit/test_worker_workspaces.py tests/unit/test_docs_examples.py -q` exits `0`
- `python -m openclaw_enhance.cli render-workspace oe-tool-recovery` exits `0`
- `python -m openclaw_enhance.cli docs-check` exits `0`
- `grep -q "oe-tool-recovery" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md docs/architecture.md docs/opencode-iteration-handbook.md` exits `0`

### Must Have
- New `oe-tool-recovery` worker with narrow authority and explicit prohibited operations
- Recovery dispatch only for tool-usage failures, not generic business-task failures
- `recovered_method` contract with required fields and validation
- Orchestrator tracking for one recovery-assisted retry per failed step
- Recovery-worker failure path that escalates instead of looping
- No weakening of `oe-syshelper`'s read-only constraints

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No custom runtime or transport outside native `sessions_spawn` / `announce` / `sessions_yield`
- No worker-to-worker direct communication
- No recovery worker takeover of the original business task
- No repeated recovery retries with unchanged evidence
- No broadening `oe-syshelper` into write-capable, decision-making, or web-research roles

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after + focused integration/unit suite in existing pytest framework
- QA policy: Every task includes agent-executed scenarios
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: workspace contract foundation + installer/discovery mapping + recovery schema/test scaffolding
Wave 2: orchestrator recovery flow + dispatch contract + worker-boundary tests/docs
Wave 3: integration QA + durable docs alignment + drift cleanup

### Dependency Matrix (full, all tasks)
- Task 1 blocks Tasks 3, 4, 6, 7
- Task 2 blocks Task 5 and supports Task 6
- Task 3 blocks Tasks 4 and 7
- Task 4 blocks Task 7
- Task 5 blocks Task 6 and Task 8
- Task 6 blocks Task 8
- Task 7 blocks Final Verification Wave
- Task 8 blocks Final Verification Wave

### Agent Dispatch Summary (wave -> task count -> categories)
- Wave 1 -> 3 tasks -> writing, unspecified-high
- Wave 2 -> 3 tasks -> writing, unspecified-high
- Wave 3 -> 2 tasks -> writing, unspecified-high

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 1. Define the new `oe-tool-recovery` workspace contract and narrow authority boundary

  **What to do**: Create `workspaces/oe-tool-recovery/AGENTS.md`, `workspaces/oe-tool-recovery/TOOLS.md`, and `workspaces/oe-tool-recovery/skills/oe-tool-recovery/SKILL.md`. Follow the workspace structure used by existing workers, but make this worker a leaf-node recovery specialist. It must diagnose tool-call failures, inspect local tool contracts, look up external docs if explicitly allowed by tools, and return a structured `recovered_method`. It must not modify project files, take over business tasks, or spawn agents.
  **Must NOT do**: Do not broaden `oe-syshelper`; do not give `oe-tool-recovery` file-edit authority; do not let it own loop state or retry decisions.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: worker contract docs must be precise and boundary-heavy
  - Skills: [`writing-plans`] — why: keeps authority rules decision-complete and explicit
  - Omitted: [`brainstorming`] — why not needed: boundary design is already decided

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 3, 4, 6, 7 | Blocked By: none

  **References**:
  - Pattern: `workspaces/oe-syshelper/AGENTS.md` — read-only worker contract style and collaboration wording
  - Pattern: `workspaces/oe-watchdog/AGENTS.md` — narrow-authority worker with explicit ALLOWED/PROHIBITED sections
  - Pattern: `workspaces/oe-searcher/AGENTS.md` — external docs/research capability language to reuse narrowly
  - Pattern: `workspaces/oe-syshelper/TOOLS.md` — tool documentation layout for worker-scoped tools
  - Pattern: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` — current worker naming, failure handling terms, native dispatch wording
  - Test: `tests/integration/test_worker_role_boundaries.py` — existing worker boundary assertions to extend

  **Acceptance Criteria** (agent-executable only):
  - [ ] `test -f workspaces/oe-tool-recovery/AGENTS.md && test -f workspaces/oe-tool-recovery/TOOLS.md && test -f workspaces/oe-tool-recovery/skills/oe-tool-recovery/SKILL.md` exits `0`
  - [ ] `grep -q "oe-tool-recovery" workspaces/oe-tool-recovery/AGENTS.md && grep -q "PROHIBITED" workspaces/oe-tool-recovery/AGENTS.md` exits `0`
  - [ ] `! grep -q "spawn subagents" workspaces/oe-tool-recovery/TOOLS.md || grep -q "Cannot spawn" workspaces/oe-tool-recovery/AGENTS.md` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Recovery workspace renders with explicit narrow boundary
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli render-workspace oe-tool-recovery > .sisyphus/evidence/task-1-recovery-worker-render.txt`
    Expected: rendered output includes oe-tool-recovery role, prohibited operations, and recovery-specific skill
    Evidence: .sisyphus/evidence/task-1-recovery-worker-render.txt

  Scenario: Recovery workspace does not claim ownership of business execution
    Tool: Bash
    Steps: run `grep -n "business task\|take over\|spawn" workspaces/oe-tool-recovery/AGENTS.md workspaces/oe-tool-recovery/skills/oe-tool-recovery/SKILL.md > .sisyphus/evidence/task-1-recovery-worker-boundary-scan.txt`
    Expected: any match is framed as a prohibition or boundary, not an allowed behavior
    Evidence: .sisyphus/evidence/task-1-recovery-worker-boundary-scan.txt
  ```

  **Commit**: YES | Message: `feat(recovery): add tool recovery workspace contract` | Files: `workspaces/oe-tool-recovery/**`

- [x] 2. Register and surface `oe-tool-recovery` in install/discovery/render paths

  **What to do**: Update workspace discovery/installation surfaces so the new worker is discoverable, installable, and renderable through existing CLI paths. At minimum update `src/openclaw_enhance/install/installer.py` agent registry entry and any tests/docs that assert known worker sets. Verify `render-workspace oe-tool-recovery` works without special cases.
  **Must NOT do**: Do not introduce a custom registry outside existing installer/discovery mechanisms; do not rename existing workers.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: touches code + tests but remains bounded and mechanical
  - Skills: [`test-driven-development`] — why: new worker registration should be locked by tests first
  - Omitted: [`systematic-debugging`] — why not needed: this is additive registration work, not failure triage

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 5, 8 | Blocked By: none

  **References**:
  - Pattern: `src/openclaw_enhance/install/installer.py` — agent registry patch structure
  - Pattern: `src/openclaw_enhance/workspaces.py` — generic workspace discovery and render path
  - Test: `tests/unit/test_worker_workspaces.py` — worker metadata/render assertions to extend
  - Test: `tests/integration/test_orchestrator_dispatch_contract.py` — workspace render integration patterns

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m openclaw_enhance.cli render-workspace oe-tool-recovery` exits `0`
  - [ ] `grep -q "oe-tool-recovery" src/openclaw_enhance/install/installer.py` exits `0`
  - [ ] `pytest tests/unit/test_worker_workspaces.py -q` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: CLI renders the new workspace without special-case failure
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli render-workspace oe-tool-recovery > .sisyphus/evidence/task-2-recovery-workspace-cli.txt`
    Expected: command exits 0 and output includes AGENTS, TOOLS, and oe-tool-recovery skill sections
    Evidence: .sisyphus/evidence/task-2-recovery-workspace-cli.txt

  Scenario: Installer registry includes the new worker entry
    Tool: Bash
    Steps: run `grep -n "oe-tool-recovery" src/openclaw_enhance/install/installer.py > .sisyphus/evidence/task-2-recovery-installer-entry.txt`
    Expected: installer contains exactly one registry entry for oe-tool-recovery with workspace and description
    Evidence: .sisyphus/evidence/task-2-recovery-installer-entry.txt
  ```

  **Commit**: YES | Message: `feat(recovery): register tool recovery workspace` | Files: `src/openclaw_enhance/install/installer.py`, `tests/unit/test_worker_workspaces.py`, related discovery files

- [x] 3. Define the `recovered_method` contract and recovery-worker output validation

  **What to do**: Add a single source of truth for the recovery result contract used by orchestrator and `oe-tool-recovery`. The contract must require fields for failed step identity, tool name, failure reason, exact invocation shape, preconditions, optional fallback tool, evidence source, confidence, and retry owner. Add unit tests that validate both required fields and forbidden ambiguity (for example, missing retry owner, unbounded retry counts, or free-form-only output).
  **Must NOT do**: Do not invent a second transport; do not let the contract make final execution decisions on behalf of orchestrator.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: schema + tests + contract integration need precision
  - Skills: [`test-driven-development`] — why: schema-first test lock prevents output drift
  - Omitted: [`writing-plans`] — why not needed: this is concrete contract/test work

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 4, 7 | Blocked By: 1

  **References**:
  - Pattern: `docs/adr/0002-native-subagent-announce.md` — existing structured worker-result framing and native announce boundary
  - Pattern: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` — failure classification and retry terminology
  - Test: `tests/unit/test_docs_examples.py` — documentation/content validation style
  - Test: `tests/integration/test_orchestrator_dispatch_contract.py` — current contract assertions for orchestrator worker dispatch

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_recovery_contract.py -q` exits `0`
  - [ ] `grep -q "recovered_method" workspaces/oe-tool-recovery/skills/oe-tool-recovery/SKILL.md` exits `0`
  - [ ] `grep -q "retry_owner" workspaces/oe-tool-recovery/skills/oe-tool-recovery/SKILL.md` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Recovery contract rejects underspecified outputs
    Tool: Bash
    Steps: run `pytest tests/unit/test_recovery_contract.py -q > .sisyphus/evidence/task-3-recovery-contract-tests.txt`
    Expected: tests prove missing required fields or invalid enum values are rejected
    Evidence: .sisyphus/evidence/task-3-recovery-contract-tests.txt

  Scenario: Recovery skill documents required handoff fields
    Tool: Bash
    Steps: run `grep -n "failed_step\|tool_name\|failure_reason\|retry_owner\|confidence" workspaces/oe-tool-recovery/skills/oe-tool-recovery/SKILL.md > .sisyphus/evidence/task-3-recovery-contract-fields.txt`
    Expected: all required contract fields are present in the recovery skill documentation
    Evidence: .sisyphus/evidence/task-3-recovery-contract-fields.txt
  ```

  **Commit**: YES | Message: `feat(recovery): define recovered method contract` | Files: contract/schema files, `tests/unit/test_recovery_contract.py`, `workspaces/oe-tool-recovery/skills/oe-tool-recovery/SKILL.md`

- [x] 4. Extend orchestrator loop state and decision rules for tool-failure recovery

  **What to do**: Update `workspaces/oe-orchestrator/AGENTS.md` so the bounded loop explicitly supports a tool-recovery branch inside `EvaluateProgress`. Define the decision trigger for tool-usage failures, add loop-state fields needed to track per-step recovery attempts and recovered methods, and lock the rule that recovery dispatch does not create worker-to-worker handoff or unlimited retries. Document that recovery-worker failure escalates rather than re-enters recovery.
  **Must NOT do**: Do not make recovery a new transport; do not let the orchestrator bypass `sessions_yield`; do not weaken the current `blocked` / `escalated` semantics.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: loop-state and decision rules are architectural contract changes
  - Skills: [`writing-plans`] — why: preserves precision in state and guardrail language
  - Omitted: [`test-driven-development`] — why not needed: AGENTS contract text is the source artifact here

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 7, 8 | Blocked By: 1, 3

  **References**:
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md` — existing bounded loop lifecycle and loop-state table
  - Pattern: `docs/opencode-iteration-handbook.md` — durable bounded-loop invariants and worker boundary language
  - Pattern: `tests/unit/test_orchestrator_workspace.py` — orchestrator documentation assertions for loop state and checkpoints
  - Pattern: `tests/integration/test_orchestrator_dispatch_contract.py` — dispatch contract integration expectations

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -q "oe-tool-recovery" workspaces/oe-orchestrator/AGENTS.md && grep -q "recovery-assisted retry" workspaces/oe-orchestrator/AGENTS.md` exits `0`
  - [ ] `grep -q "recovery_attempts" workspaces/oe-orchestrator/AGENTS.md || grep -q "recovered_methods" workspaces/oe-orchestrator/AGENTS.md` exits `0`
  - [ ] `pytest tests/unit/test_orchestrator_workspace.py -q` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Orchestrator contract documents recovery branch inside EvaluateProgress
    Tool: Bash
    Steps: run `grep -n "EvaluateProgress\|oe-tool-recovery\|recovery-assisted retry\|escalated" workspaces/oe-orchestrator/AGENTS.md > .sisyphus/evidence/task-4-orchestrator-recovery-contract.txt`
    Expected: orchestrator contract explicitly describes recovery trigger, retry cap, and escalation on recovery failure
    Evidence: .sisyphus/evidence/task-4-orchestrator-recovery-contract.txt

  Scenario: Recovery does not bypass bounded loop guardrails
    Tool: Bash
    Steps: run `grep -n "max_rounds\|blocked\|sessions_yield\|announce" workspaces/oe-orchestrator/AGENTS.md > .sisyphus/evidence/task-4-orchestrator-guardrails.txt`
    Expected: native loop guardrails remain present alongside recovery language
    Evidence: .sisyphus/evidence/task-4-orchestrator-guardrails.txt
  ```

  **Commit**: YES | Message: `docs(orchestrator): add tool recovery loop rules` | Files: `workspaces/oe-orchestrator/AGENTS.md`, `tests/unit/test_orchestrator_workspace.py`

- [x] 5. Update worker-dispatch routing rules for recovery classification and handoff

  **What to do**: Extend `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` so it distinguishes generic retriable failures from tool-usage failures that should route to `oe-tool-recovery`. Add dispatch instructions for the recovery worker, document the exact failure context passed in, state how `recovered_method` re-enters the orchestrator retry flow, and explicitly forbid direct worker-to-worker retry handoff.
  **Must NOT do**: Do not tell workers to call each other; do not create a second retry loop inside `oe-tool-recovery`; do not weaken existing `reroutable` and `escalated` meanings.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: dispatch contract and routing heuristics are documentation contracts
  - Skills: [`writing-plans`] — why: keeps classification and retry rules explicit and decision-complete
  - Omitted: [`brainstorming`] — why not needed: routing choice has already been made

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 7, 8 | Blocked By: 1, 2, 3

  **References**:
  - Pattern: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` — existing failure classes and native dispatch examples
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md` — bounded loop checkpoints and ownership model
  - Pattern: `docs/operations.md` — worker-role operational descriptions
  - Test: `tests/integration/test_orchestrator_dispatch_contract.py` — dispatch skill assertions to extend

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -q "oe-tool-recovery" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` exits `0`
  - [ ] `grep -q "tool-usage failure" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md && grep -q "recovered_method" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` exits `0`
  - [ ] `! grep -q "worker-to-worker" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md || grep -q "forbid" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Dispatch contract identifies when to route to recovery worker
    Tool: Bash
    Steps: run `grep -n "tool-usage failure\|oe-tool-recovery\|retry_owner\|one recovery-assisted retry" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md > .sisyphus/evidence/task-5-dispatch-recovery-routing.txt`
    Expected: dispatch skill includes tool-failure trigger, recovery worker routing, handoff fields, and retry cap
    Evidence: .sisyphus/evidence/task-5-dispatch-recovery-routing.txt

  Scenario: Dispatch contract still preserves native execution path
    Tool: Bash
    Steps: run `grep -n "sessions_spawn\|sessions_yield\|announce" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md > .sisyphus/evidence/task-5-dispatch-native-path.txt`
    Expected: recovery routing remains within native sessions_spawn/announce/sessions_yield wording
    Evidence: .sisyphus/evidence/task-5-dispatch-native-path.txt
  ```

  **Commit**: YES | Message: `docs(dispatch): add recovery worker routing rules` | Files: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`, related contract tests

- [x] 6. Add worker-boundary and workspace tests for `oe-tool-recovery`

  **What to do**: Extend worker boundary coverage so the new worker's authority is enforced the same way `oe-syshelper` and `oe-watchdog` are enforced today. Add tests for allowed operations, prohibited operations, render coverage, skill presence, and the rule that recovery worker recommends but does not execute or decide. Update any worker metadata tests to include `oe-tool-recovery`.
  **Must NOT do**: Do not rely on documentation-only assertions if an existing test pattern can make the boundary more explicit; do not alter `oe-syshelper` tests except to preserve its unchanged contract.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: multiple test files + boundary reasoning + workspace discovery
  - Skills: [`test-driven-development`] — why: tests should fail before worker contract is finalized
  - Omitted: [`systematic-debugging`] — why not needed: this is proactive contract coverage, not failure triage

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 7 | Blocked By: 1, 2, 3

  **References**:
  - Pattern: `tests/integration/test_worker_role_boundaries.py` — worker-boundary class structure
  - Pattern: `tests/unit/test_worker_workspaces.py` — workspace metadata/render expectations
  - Pattern: `workspaces/oe-watchdog/AGENTS.md` — narrow authority language worth asserting against
  - Pattern: `workspaces/oe-tool-recovery/AGENTS.md` and `workspaces/oe-tool-recovery/TOOLS.md` — newly added boundary source files

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/integration/test_worker_role_boundaries.py tests/unit/test_worker_workspaces.py -q` exits `0`
  - [ ] `grep -q "oe-tool-recovery" tests/integration/test_worker_role_boundaries.py` exits `0`
  - [ ] `grep -q "oe-tool-recovery" tests/unit/test_worker_workspaces.py` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Boundary tests enforce recovery worker narrow authority
    Tool: Bash
    Steps: run `pytest tests/integration/test_worker_role_boundaries.py -q > .sisyphus/evidence/task-6-recovery-boundary-tests.txt`
    Expected: tests pass and include oe-tool-recovery-specific assertions for no file edits, no spawn, and recommendation-only behavior
    Evidence: .sisyphus/evidence/task-6-recovery-boundary-tests.txt

  Scenario: Workspace tests include render/metadata coverage for recovery worker
    Tool: Bash
    Steps: run `pytest tests/unit/test_worker_workspaces.py -q > .sisyphus/evidence/task-6-recovery-workspace-tests.txt`
    Expected: recovery workspace is discoverable and renderable via the same mechanisms as existing workers
    Evidence: .sisyphus/evidence/task-6-recovery-workspace-tests.txt
  ```

  **Commit**: YES | Message: `test(recovery): enforce recovery worker boundaries` | Files: `tests/integration/test_worker_role_boundaries.py`, `tests/unit/test_worker_workspaces.py`

- [ ] 7. Add orchestrator recovery-flow integration tests and retry-limit coverage

  **What to do**: Extend integration coverage so orchestrator dispatches `oe-tool-recovery` when tool-usage failures occur, consumes a valid `recovered_method`, retries exactly once with new evidence, and escalates if recovery or the assisted retry fails. Add explicit tests for tool-not-found, invalid-parameter, retry-limit, and recovery-worker-failure cases. Keep them contract-level if runtime implementation is still documentation-driven, but make assertions specific enough to prevent ambiguous future behavior.
  **Must NOT do**: Do not write trivial placeholder tests; do not hide missing behavior behind broad string-matching only; do not allow tests to imply infinite retries.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: multi-scenario integration coverage with bounded-loop semantics
  - Skills: [`test-driven-development`] — why: scenario-first coverage should define the intended flow before implementation details drift
  - Omitted: [`systematic-debugging`] — why not needed: we are specifying known scenarios, not exploring unknown failures

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: Final Verification Wave | Blocked By: 3, 4, 5, 6

  **References**:
  - Pattern: `tests/integration/test_orchestrator_dispatch_contract.py` — current dispatch contract integration style
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md` — loop-state and blocked/escalated semantics
  - Pattern: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` — failure classification and retry wording
  - Pattern: `docs/operations.md` — operational narrative for orchestration rounds and worker roles

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/integration/test_orchestrator_dispatch_contract.py -q` exits `0`
  - [ ] `grep -q "oe-tool-recovery" tests/integration/test_orchestrator_dispatch_contract.py` exits `0`
  - [ ] `grep -q "one recovery-assisted retry" tests/integration/test_orchestrator_dispatch_contract.py || grep -q "retry limit" tests/integration/test_orchestrator_dispatch_contract.py` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Tool-not-found failure routes through recovery and returns retry guidance
    Tool: Bash
    Steps: run `pytest tests/integration/test_orchestrator_dispatch_contract.py -q -k "tool_not_found or recovery" > .sisyphus/evidence/task-7-tool-not-found-recovery.txt`
    Expected: tests prove orchestrator dispatches oe-tool-recovery, consumes recovered_method, and limits retry to one assisted attempt
    Evidence: .sisyphus/evidence/task-7-tool-not-found-recovery.txt

  Scenario: Recovery failure escalates instead of looping
    Tool: Bash
    Steps: run `pytest tests/integration/test_orchestrator_dispatch_contract.py -q -k "recovery_failure or retry_limit" > .sisyphus/evidence/task-7-recovery-failure-escalation.txt`
    Expected: tests prove recovery failure or second failure leads to blocked/escalated handling without re-entering recovery
    Evidence: .sisyphus/evidence/task-7-recovery-failure-escalation.txt
  ```

  **Commit**: YES | Message: `test(orchestrator): cover tool recovery flow` | Files: `tests/integration/test_orchestrator_dispatch_contract.py`, related integration test files

- [ ] 8. Update durable docs and architecture memory for the recovery worker model

  **What to do**: Update durable project memory so future sessions understand why `oe-tool-recovery` exists, how it differs from `oe-syshelper`, and how tool-failure recovery fits into the bounded loop. Update `docs/opencode-iteration-handbook.md`, `docs/architecture.md`, `docs/operations.md`, and any concise entrypoint docs that list worker roles. If needed, add a focused ADR or extend an existing ADR only at the decision level - avoid reintroducing implementation-heavy pseudocode.
  **Must NOT do**: Do not blur `oe-tool-recovery` and `oe-syshelper`; do not imply worker-to-worker direct messaging; do not add custom runtime components.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: this is durable architecture memory and operational guidance
  - Skills: [`writing-plans`] — why: keeps docs aligned with the chosen bounded-loop design and worker boundaries
  - Omitted: [`brainstorming`] — why not needed: architecture decisions are already approved

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: Final Verification Wave | Blocked By: 2, 4, 5

  **References**:
  - Pattern: `docs/opencode-iteration-handbook.md` — durable state + worker-boundary source of truth
  - Pattern: `docs/architecture.md` — system overview and worker-role matrix
  - Pattern: `docs/operations.md` — operational bounded-loop narrative
  - Pattern: `AGENTS.md` — top-level role pointers to worker-specific docs
  - Pattern: `docs/adr/0002-native-subagent-announce.md` — decision-level native transport boundary wording

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -q "oe-tool-recovery" docs/opencode-iteration-handbook.md docs/architecture.md docs/operations.md AGENTS.md` exits `0`
  - [ ] `grep -q "one recovery-assisted retry" docs/operations.md docs/opencode-iteration-handbook.md` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Durable docs distinguish syshelper from recovery worker
    Tool: Bash
    Steps: run `grep -n "oe-syshelper\|oe-tool-recovery" docs/opencode-iteration-handbook.md docs/architecture.md docs/operations.md > .sisyphus/evidence/task-8-worker-role-docs.txt`
    Expected: docs clearly show syshelper remains read-only while oe-tool-recovery owns tool-failure recovery
    Evidence: .sisyphus/evidence/task-8-worker-role-docs.txt

  Scenario: Documentation remains aligned with native transport rules
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli docs-check > .sisyphus/evidence/task-8-docs-check.txt`
    Expected: docs-check passes and no custom runtime or wrapper-dispatch drift is introduced
    Evidence: .sisyphus/evidence/task-8-docs-check.txt
  ```

  **Commit**: YES | Message: `docs(recovery): document tool recovery worker model` | Files: `docs/opencode-iteration-handbook.md`, `docs/architecture.md`, `docs/operations.md`, `AGENTS.md`, related ADR/docs files

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [ ] F1. Plan Compliance Audit - oracle

  **What to do**: Audit the delivered changes against this plan only. Confirm that the new worker exists, `oe-syshelper` stayed read-only, orchestrator owns all retry decisions, and each numbered task delivered the promised surfaces without adding worker-to-worker handoff or custom transport.
  **Verification**:
  - [ ] `grep -q "oe-tool-recovery" workspaces/oe-tool-recovery/AGENTS.md workspaces/oe-orchestrator/AGENTS.md workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` exits `0`
  - [ ] `grep -q "strictly read-only" workspaces/oe-syshelper/AGENTS.md && ! grep -q "oe-tool-recovery" workspaces/oe-syshelper/AGENTS.md` exits `0`
  - [ ] `! grep -R "worker-to-worker" workspaces docs tests --include='*.md' --include='*.py' || grep -R "forbid\|prohibit\|must not" workspaces docs tests --include='*.md' --include='*.py'` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Compliance scan across all planned surfaces
    Tool: Bash
    Steps: run `grep -n "oe-tool-recovery\|recovery-assisted retry\|retry_owner\|strictly read-only" workspaces/oe-tool-recovery/AGENTS.md workspaces/oe-orchestrator/AGENTS.md workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md workspaces/oe-syshelper/AGENTS.md > .sisyphus/evidence/f1-plan-compliance-scan.txt`
    Expected: all required recovery surfaces are present and syshelper remains explicitly read-only
    Evidence: .sisyphus/evidence/f1-plan-compliance-scan.txt

  Scenario: No forbidden transport drift was introduced
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli docs-check > .sisyphus/evidence/f1-plan-compliance-docs-check.txt`
    Expected: docs-check passes, confirming native transport wording still holds
    Evidence: .sisyphus/evidence/f1-plan-compliance-docs-check.txt
  ```

  **Pass Condition**: Every planned surface is present and no forbidden transport/worker-boundary drift is found.

- [ ] F2. Code Quality Review - unspecified-high

  **What to do**: Review worker contracts, registration changes, and tests for internal consistency, duplicate logic, invalid references, and missing assertions around retry limits or recommendation-only behavior.
  **Verification**:
  - [ ] `pytest tests/integration/test_worker_role_boundaries.py tests/integration/test_orchestrator_dispatch_contract.py tests/unit/test_worker_workspaces.py tests/unit/test_recovery_contract.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-workspace oe-tool-recovery` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Focused quality suite passes together
    Tool: Bash
    Steps: run `pytest tests/integration/test_worker_role_boundaries.py tests/integration/test_orchestrator_dispatch_contract.py tests/unit/test_worker_workspaces.py tests/unit/test_recovery_contract.py -q > .sisyphus/evidence/f2-quality-suite.txt`
    Expected: all focused recovery tests pass in one run without fixture or naming conflicts
    Evidence: .sisyphus/evidence/f2-quality-suite.txt

  Scenario: Recovery workspace renders cleanly after all changes
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli render-workspace oe-tool-recovery > .sisyphus/evidence/f2-recovery-render.txt`
    Expected: rendered workspace includes AGENTS, TOOLS, and skill content with no missing files or broken metadata
    Evidence: .sisyphus/evidence/f2-recovery-render.txt
  ```

  **Pass Condition**: The focused test suite and render path both succeed, and the review finds no contract inconsistencies.

- [ ] F3. Agent-Executed Render QA - unspecified-high

  **What to do**: Perform agent-executed inspection of rendered docs/workspaces to verify the recovery model is understandable from user-facing outputs without human intervention.
  **Verification**:
  - [ ] `python -m openclaw_enhance.cli render-workspace oe-orchestrator` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-workspace oe-tool-recovery` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Rendered orchestrator output shows recovery branch and bounded retry language
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli render-workspace oe-orchestrator > .sisyphus/evidence/f3-orchestrator-render.txt && grep -n "oe-tool-recovery\|recovery-assisted retry\|blocked\|sessions_yield" .sisyphus/evidence/f3-orchestrator-render.txt > .sisyphus/evidence/f3-orchestrator-render-scan.txt`
    Expected: rendered orchestrator workspace clearly exposes the recovery branch, retry cap, and native loop wording
    Evidence: .sisyphus/evidence/f3-orchestrator-render-scan.txt

  Scenario: Rendered recovery worker output shows recommendation-only role
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli render-workspace oe-tool-recovery > .sisyphus/evidence/f3-recovery-render.txt && grep -n "recommend\|must not\|cannot spawn\|cannot modify" .sisyphus/evidence/f3-recovery-render.txt > .sisyphus/evidence/f3-recovery-render-scan.txt`
    Expected: rendered recovery workspace presents recommendation-only behavior and explicit prohibitions
    Evidence: .sisyphus/evidence/f3-recovery-render-scan.txt
  ```

  **Pass Condition**: Agent-executed render inspection shows the recovery model is coherent and policy-aligned without manual review.

- [ ] F4. Scope Fidelity Check - deep

  **What to do**: Verify the finished design stayed narrow: `oe-syshelper` unchanged in role, `oe-tool-recovery` remains a leaf node, orchestrator still owns retry decisions, and the system still relies only on native dispatch primitives.
  **Verification**:
  - [ ] `python - <<'PY'
from pathlib import Path
blob = '\n'.join([
    Path('workspaces/oe-syshelper/AGENTS.md').read_text(encoding='utf-8'),
    Path('workspaces/oe-tool-recovery/AGENTS.md').read_text(encoding='utf-8'),
    Path('workspaces/oe-orchestrator/AGENTS.md').read_text(encoding='utf-8'),
    Path('workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md').read_text(encoding='utf-8'),
])
assert 'strictly read-only' in Path('workspaces/oe-syshelper/AGENTS.md').read_text(encoding='utf-8').lower()
assert 'oe-tool-recovery' in blob
assert 'sessions_spawn' in blob and 'sessions_yield' in blob and 'announce' in blob
assert 'one recovery-assisted retry' in blob or 'recovery-assisted retry' in blob
assert 'cannot spawn' in Path('workspaces/oe-tool-recovery/AGENTS.md').read_text(encoding='utf-8').lower()
print('scope-fidelity-ok')
PY` exits `0`
  - [ ] `pytest tests/integration/test_worker_role_boundaries.py -q` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Scope fidelity script proves narrow worker boundaries remain intact
    Tool: Bash
    Steps: run the verification script above and save stdout to `.sisyphus/evidence/f4-scope-fidelity.txt`
    Expected: script prints `scope-fidelity-ok`
    Evidence: .sisyphus/evidence/f4-scope-fidelity.txt

  Scenario: Boundary suite still passes for all workers
    Tool: Bash
    Steps: run `pytest tests/integration/test_worker_role_boundaries.py -q > .sisyphus/evidence/f4-boundary-suite.txt`
    Expected: worker boundary tests pass, proving syshelper stayed read-only and recovery worker stayed narrow
    Evidence: .sisyphus/evidence/f4-boundary-suite.txt
  ```

  **Pass Condition**: The finished design remains native, bounded, leaf-node for recovery, and fully compatible with existing worker-boundary rules.

## Commit Strategy
- Keep recovery worker workspace introduction separate from orchestrator loop contract changes.
- Keep installer/discovery updates separate from worker contract docs when practical.
- Keep tests in at least two auditable units: worker boundaries/schema and orchestrator recovery flow.
- Keep durable docs updates after contracts/tests stabilize.

## Success Criteria
- The repository documents a dedicated `oe-tool-recovery` worker without weakening `oe-syshelper`.
- Orchestrator can route tool-usage failures into a bounded recovery path and consume a validated `recovered_method`.
- Recovery is native, leaf-node, and limited to one assisted retry per failed step.
- Tests and docs together prevent drift toward worker-to-worker handoff, custom transport, or recovery loops.
