# Session Yield Orchestrator Loop

## TL;DR
> **Summary**: Redesign `oe-orchestrator` from a one-shot fan-out/fan-in dispatcher into a bounded, semi-visible multi-round loop that uses native `sessions_spawn` for worker execution and `sessions_yield` as the orchestrator's round-boundary synchronization primitive.
> **Deliverables**:
> - Updated orchestrator contract (`workspaces/oe-orchestrator/AGENTS.md` + `oe-worker-dispatch/SKILL.md`) for round-based orchestration
> - Native-primitives ADR/docs updates describing `sessions_yield` vs `sessions_spawn`
> - Bounded loop state/termination design documented and encoded in tests/contracts
> - Integration tests for dispatch -> yield -> collect -> re-dispatch behavior and checkpoint visibility
> **Effort**: Medium
> **Parallel**: YES - 2 waves
> **Critical Path**: 1 -> 2 -> 3 -> 5

## Context
### Original Request
- Consider the new OpenClaw `sessions_yield` tool.
- Upgrade the orchestrator so it can do `dispatch -> collect -> continue dispatching until complete`, not only a one-shot dispatch.

### Interview Summary
- User explicitly wants the new design to incorporate `sessions_yield`.
- Research confirms `sessions_yield` is not a replacement for `sessions_spawn`; it is a turn-ending synchronization primitive so auto-announce can deliver child results on the next message.
- User chose a **semi-visible** model: main should see milestone-level checkpoints, not every internal round.
- Risk-driven design was prioritized: state drift, duplicate dispatch, infinite loops, blocker escalation, and visibility control are all first-class requirements.

### Metis Review (gaps addressed)
- Worker sessions remain single-round in v1; only the orchestrator owns loop state.
- State ownership is explicit and bounded: the plan fixes one orchestrator-owned round-state schema instead of ad hoc memory.
- Termination is deterministic: no open-ended “keep trying until it feels done” behavior.
- Checkpoint policy is explicit: only `started`, `meaningful_progress`, `blocked`, and terminal states are visible to main.
- The plan keeps the native-primitives model intact: `sessions_spawn`/announce stay the only worker execution path and `sessions_yield` is only a round boundary.
- Docs/ADR drift is treated as part of the architecture change, not left as follow-up.

## Work Objectives
### Core Objective
- Introduce a bounded orchestrator loop where `oe-orchestrator` can dispatch workers, yield its turn, collect auto-announced results on the next turn, evaluate progress, and decide whether to re-dispatch or terminate.

### Deliverables
- Round-based orchestrator workflow and guardrails in `workspaces/oe-orchestrator/AGENTS.md`.
- Iterative dispatch contract, round result schema, duplicate-dispatch rules, and checkpoint policy in `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`.
- Native transport documentation updated to include `sessions_yield` semantics in `docs/adr/0002-native-subagent-announce.md`, `docs/architecture.md`, `docs/operations.md`, and `docs/opencode-iteration-handbook.md`.
- Tests covering round-state transitions, max-round protection, duplicate-dispatch guards, checkpoint visibility, and “no polling/history while waiting” behavior.

### Definition of Done (verifiable conditions with commands)
- `pytest tests/integration/test_orchestrator_dispatch_contract.py -q` exits `0`.
- `pytest tests/unit/test_orchestrator_workspace.py -q` exits `0`.
- `pytest tests/unit/test_docs_examples.py -q` exits `0`.
- `python -m openclaw_enhance.cli docs-check` exits `0`.
- `python - <<'PY'
from pathlib import Path
paths = [
    Path('workspaces/oe-orchestrator/AGENTS.md'),
    Path('workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md'),
    Path('docs/adr/0002-native-subagent-announce.md'),
    Path('docs/operations.md'),
    Path('docs/architecture.md'),
    Path('docs/opencode-iteration-handbook.md'),
]
blob = '\n'.join(p.read_text(encoding='utf-8') for p in paths)
assert 'sessions_yield' in blob
assert 'max_rounds' in blob or 'max rounds' in blob.lower()
assert 'meaningful_progress' in blob or 'meaningful progress' in blob.lower()
assert 'blocked' in blob.lower()
print('session-yield-loop-docs-aligned')
PY` exits `0`.

### Must Have
- `sessions_spawn` / announce remain the only worker execution path.
- `sessions_yield` is documented and used only as an orchestrator round-boundary primitive.
- Workers remain single-round executors in v1.
- Orchestrator loop state must include round index, pending/received dispatches, blocker list, dedupe identities, and termination reason.
- Max-round protection and duplicate-dispatch guards must be explicit.
- Main visibility stays semi-visible: milestone checkpoints only.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No worker-level `sessions_yield` in v1.
- No polling-based `sessions_history` / ad hoc waiting loops after dispatch.
- No custom runtime or queue around native primitives.
- No free-form recursive orchestration DAGs.
- No fully transparent every-round chatter to main.
- No changes that weaken existing worker boundary rules.

## Verification Strategy
> ZERO HUMAN INTERVENTION — all verification is agent-executed.
- Test decision: tests-after with targeted contract tests first, because the work is architecture/spec/contract heavy.
- QA policy: every task includes an executable happy-path and edge/failure scenario.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`.

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: 1) orchestrator loop contract foundation

Wave 2: 2) iterative worker-dispatch contract, 3) round-state / termination test scaffolding

Wave 3: 4) ADR + architecture/operations docs, 5) handbook/agent guidance and checkpoint policy

Wave 4: 6) final drift review + integrated tests

### Dependency Matrix (full, all tasks)
| Task | Depends On | Blocks |
| --- | --- | --- |
| 1 | none | 2, 3, 4, 5, 6 |
| 2 | 1 | 4, 5, 6 |
| 3 | 1, 2 | 6 |
| 4 | 1, 2 | 6 |
| 5 | 1, 2 | 6 |
| 6 | 1, 2, 3, 4, 5 | Final Verification |

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 -> 3 tasks -> `writing`, `unspecified-high`, `quick`
- Wave 2 -> 3 tasks -> `writing`, `unspecified-high`
- Final Verification -> 4 tasks -> `oracle`, `unspecified-high`, `deep`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 1. Redefine orchestrator workflow as a bounded round-based loop in `workspaces/oe-orchestrator/AGENTS.md`

  **What to do**: Replace the current linear task flow in `workspaces/oe-orchestrator/AGENTS.md` with a bounded loop lifecycle. The new workflow must explicitly define: `Assess`, `PlanRound`, `DispatchRound`, `YieldForResults`, `CollectResults`, `EvaluateProgress`, `Complete/Blocked/Exhausted/Escalated`. Add orchestrator-owned state requirements: `task_id`, `round_index`, `max_rounds`, `pending_dispatches`, `received_results`, `blocked_items`, `dedupe_keys`, `termination_state`, `termination_reason`. Set defaults: `max_rounds=3` with hard cap `5`; one orchestrator `sessions_yield` per round; checkpoints to main only on `started`, `meaningful_progress`, `blocked`, and terminal events.
  **Must NOT do**: Do not give workers loop ownership. Do not describe polling/history-based waiting. Do not change worker boundary sections outside what is needed to explain orchestrator ownership.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: architecture contract rewrite with strict language
  - Skills: [`writing-plans`] — keep workflow/state/guardrails decision-complete
  - Omitted: [`brainstorming`] — design decisions already fixed

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 2, 3, 4, 5, 6 | Blocked By: none

  **References**:
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md:7` — current orchestrator role summary to rewrite
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md:61` — current linear `Standard Task Flow`
  - Pattern: `docs/opencode-iteration-handbook.md:13` — current native-primitives wording to preserve
  - Pattern: `docs/opencode-iteration-handbook.md:111` — current invariant that execution stays native
  - Pattern: `docs/adr/0003-watchdog-authority.md` — watchdog boundary constraints that loop states must not violate
  - External: OpenClaw PR semantics for `sessions_yield` — turn-ending synchronization primitive, not transport replacement

  **Acceptance Criteria**:
  - [ ] `grep -q "YieldForResults" workspaces/oe-orchestrator/AGENTS.md && grep -q "CollectResults" workspaces/oe-orchestrator/AGENTS.md` exits `0`
  - [ ] `grep -q "max_rounds" workspaces/oe-orchestrator/AGENTS.md && grep -q "meaningful_progress" workspaces/oe-orchestrator/AGENTS.md` exits `0`
  - [ ] `grep -q "sessions_yield" workspaces/oe-orchestrator/AGENTS.md && ! grep -q "workers use sessions_yield" workspaces/oe-orchestrator/AGENTS.md` exits `0`

  **QA Scenarios**:
  ```
  Scenario: Orchestrator workflow is explicitly multi-round and bounded
    Tool: Bash
    Steps: run `grep -n "PlanRound\|DispatchRound\|YieldForResults\|CollectResults\|EvaluateProgress\|Complete" workspaces/oe-orchestrator/AGENTS.md`
    Expected: all round-state phases are present in the orchestrator workflow
    Evidence: .sisyphus/evidence/task-1-orchestrator-loop-contract.txt

  Scenario: Loop control guardrails are explicit
    Tool: Bash
    Steps: run `grep -n "max_rounds\|hard cap\|dedupe\|blocked\|termination" workspaces/oe-orchestrator/AGENTS.md`
    Expected: the contract contains explicit round ceilings, dedupe, and termination states
    Evidence: .sisyphus/evidence/task-1-orchestrator-loop-contract-error.txt
  ```

  **Commit**: YES | Message: `docs(orchestrator): define bounded session-yield loop` | Files: `workspaces/oe-orchestrator/AGENTS.md`

- [x] 2. Redesign `oe-worker-dispatch` contract for iterative rounds and semi-visible checkpoints

  **What to do**: Update `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` so it no longer describes only one-pass dispatch patterns. Add an explicit iterative pattern with: round planning, dispatch identity, expected result slots, duplicate-dispatch guard, failure classification (`retriable`, `reroutable`, `escalated`), and checkpoint policy. Define that workers return structured round results and never own the loop. Define the `semi-visible` checkpoint contract to main: expose only `started`, `meaningful_progress`, `blocked`, and terminal updates. Explicitly state that `sessions_yield` is called once after a round's dispatch set is closed and that no `sessions_history` polling should occur while waiting.
  **Must NOT do**: Do not introduce worker-level yield loops or arbitrary recursive trees.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: contract/spec update for dispatch behavior
  - Skills: [`writing-plans`] — keep result schemas and checkpoint policy concrete
  - Omitted: [`dispatching-parallel-agents`] — this is about protocol, not execution

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 3, 4, 5, 6 | Blocked By: 1

  **References**:
  - Pattern: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` — current dispatch skill contract
  - Pattern: `docs/adr/0002-native-subagent-announce.md` — current request/response wording to expand carefully
  - Pattern: `docs/operations.md` — current one-shot orchestration wording
  - Pattern: `hooks/oe-subagent-spawn-enrich/HOOK.md` — existing `task_id`, `parent_session`, `dedupe_key` enrichment fields to reuse conceptually
  - Pattern: `docs/architecture.md` — current dedupe and transport terminology to stay aligned with

  **Acceptance Criteria**:
  - [ ] `grep -q "sessions_yield" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` exits `0`
  - [ ] `grep -q "meaningful_progress" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md && grep -q "blocked" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` exits `0`
  - [ ] `! grep -q "sessions_history" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` exits `0`

  **QA Scenarios**:
  ```
  Scenario: Worker dispatch contract includes iterative round semantics
    Tool: Bash
    Steps: run `grep -n "round\|dedupe\|retriable\|reroutable\|escalated\|sessions_yield" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`
    Expected: iterative dispatch, failure classes, and yield semantics are all present
    Evidence: .sisyphus/evidence/task-2-worker-dispatch-iterative.txt

  Scenario: Contract explicitly bans polling-based waiting
    Tool: Bash
    Steps: run `grep -n "Do NOT poll\|no polling\|sessions_history" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`
    Expected: the contract makes polling-style waiting clearly forbidden or absent
    Evidence: .sisyphus/evidence/task-2-worker-dispatch-iterative-error.txt
  ```

  **Commit**: YES | Message: `docs(dispatch): add iterative round contract` | Files: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`

- [x] 3. Add test/contracts for bounded loop controls and checkpoint behavior

  **What to do**: Extend orchestrator-related tests so the new architecture is enforceable. Add/adjust tests in `tests/integration/test_orchestrator_dispatch_contract.py`, `tests/unit/test_orchestrator_workspace.py`, and any narrow companion file if needed. Cover: round-state phases present in orchestrator docs, `sessions_yield` referenced in orchestrator/dispatch contracts, max-round and hard-cap wording present, checkpoint visibility terms present, duplicate-dispatch guard terms present, and polling/history absence where required. Use documentation/contract tests if runtime code is not yet changed; keep them specific enough that later implementers cannot claim vague compliance.
  **Must NOT do**: Do not add fake placeholder tests or broad snapshot-style assertions that hide missing semantics.

  **Recommended Agent Profile**:
  - Category: `quick` — Reason: bounded contract-test expansion around existing orchestrator docs/tests
  - Skills: [`test-driven-development`] — lock architecture invariants explicitly in tests
  - Omitted: [`systematic-debugging`] — not a debugging task

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 6 | Blocked By: 1, 2

  **References**:
  - Test: `tests/integration/test_orchestrator_dispatch_contract.py` — current orchestrator dispatch contract tests
  - Test: `tests/unit/test_orchestrator_workspace.py` — current workspace-level orchestrator expectations
  - Pattern: `tests/unit/test_docs_examples.py` — existing docs contract style if needed
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md` and `oe-worker-dispatch/SKILL.md` after Tasks 1-2

  **Acceptance Criteria**:
  - [ ] `pytest tests/integration/test_orchestrator_dispatch_contract.py -q` exits `0`
  - [ ] `pytest tests/unit/test_orchestrator_workspace.py -q` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
blob = '\n'.join([
    Path('tests/integration/test_orchestrator_dispatch_contract.py').read_text(encoding='utf-8'),
    Path('tests/unit/test_orchestrator_workspace.py').read_text(encoding='utf-8'),
])
for token in ['sessions_yield', 'max_rounds', 'meaningful_progress', 'blocked']:
    assert token in blob
print('orchestrator-loop-tests-aligned')
PY` exits `0`

  **QA Scenarios**:
  ```
  Scenario: Contract tests lock bounded loop behavior
    Tool: Bash
    Steps: run `pytest tests/integration/test_orchestrator_dispatch_contract.py tests/unit/test_orchestrator_workspace.py -q`
    Expected: orchestrator tests pass and enforce session_yield, bounded rounds, and checkpoint semantics
    Evidence: .sisyphus/evidence/task-3-orchestrator-loop-tests.txt

  Scenario: Tests specifically guard against regression to one-shot-only wording
    Tool: Bash
    Steps: run `grep -n "sessions_yield\|max_rounds\|meaningful_progress\|blocked" tests/integration/test_orchestrator_dispatch_contract.py tests/unit/test_orchestrator_workspace.py`
    Expected: tests contain direct assertions for loop semantics instead of vague string checks
    Evidence: .sisyphus/evidence/task-3-orchestrator-loop-tests-error.txt
  ```

  **Commit**: YES | Message: `test(orchestrator): lock session-yield loop contracts` | Files: `tests/integration/test_orchestrator_dispatch_contract.py`, `tests/unit/test_orchestrator_workspace.py`, related test files if needed

- [x] 4. Update ADR and deep docs so native-primitives architecture includes `sessions_yield`

  **What to do**: Update `docs/adr/0002-native-subagent-announce.md`, `docs/architecture.md`, and `docs/operations.md` so they describe `sessions_yield` correctly. The ADR must say `sessions_spawn` / announce remain the only worker execution path and `sessions_yield` is the orchestrator's turn-yield synchronization primitive. `docs/architecture.md` must replace the purely linear orchestrator diagram/wording with a bounded loop view. `docs/operations.md` must describe the real operational lifecycle: dispatch a round, yield, collect auto-announced results, evaluate, optionally re-dispatch, or terminate.
  **Must NOT do**: Do not describe `sessions_yield` as a result transport, and do not create worker-level yield semantics.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: cross-document architecture alignment
  - Skills: [`writing-plans`] — keep the transport boundary precise across docs
  - Omitted: [`frontend-ui-ux`] — docs only

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 6 | Blocked By: 1, 2

  **References**:
  - Pattern: `docs/adr/0002-native-subagent-announce.md` — current native announce ADR
  - Pattern: `docs/architecture.md` — current linear control-flow narrative
  - Pattern: `docs/operations.md` — current one-shot operations guide
  - Pattern: `docs/opencode-iteration-handbook.md:13` — current native execution wording to preserve
  - External: high-signal `sessions_yield` semantics from merged OpenClaw PR research

  **Acceptance Criteria**:
  - [ ] `grep -q "sessions_yield" docs/adr/0002-native-subagent-announce.md docs/architecture.md docs/operations.md` exits `0`
  - [ ] `grep -q "dispatch -> yield -> collect" docs/operations.md || grep -q "YieldForResults" docs/operations.md` exits `0`
  - [ ] `! grep -q "sessions_yield.*worker" docs/adr/0002-native-subagent-announce.md` exits `0`

  **QA Scenarios**:
  ```
  Scenario: Deep docs explain session_yield as orchestrator round boundary
    Tool: Bash
    Steps: run `grep -n "sessions_yield\|turn-ending\|round boundary\|dispatch -> yield -> collect" docs/adr/0002-native-subagent-announce.md docs/architecture.md docs/operations.md`
    Expected: all deep docs consistently describe session_yield as an orchestrator synchronization primitive
    Evidence: .sisyphus/evidence/task-4-native-docs-yield.txt

  Scenario: Docs preserve native execution boundary
    Tool: Bash
    Steps: run `grep -n "only execution path\|sessions_spawn\|announce" docs/adr/0002-native-subagent-announce.md docs/architecture.md docs/operations.md`
    Expected: docs still make clear that worker execution remains native `sessions_spawn` / announce based
    Evidence: .sisyphus/evidence/task-4-native-docs-yield-error.txt
  ```

  **Commit**: YES | Message: `docs(adr): add session-yield orchestration model` | Files: `docs/adr/0002-native-subagent-announce.md`, `docs/architecture.md`, `docs/operations.md`

- [x] 5. Update durable project memory and entrypoint docs for the new orchestration model

  **What to do**: Update `docs/opencode-iteration-handbook.md` and `AGENTS.md` so future sessions know the repo no longer assumes one-shot orchestrator behavior. Add a new durable milestone entry describing the `session-yield-orchestrator-loop` design state once docs/contracts are updated. Update reading/checklist guidance so future design/development work touching orchestration must read the yield-loop sections and respect bounded-loop controls. Keep `AGENTS.md` short; put the detailed state/risks in the handbook.
  **Must NOT do**: Do not turn `AGENTS.md` into a deep architecture document.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: durable project-memory update and entrypoint alignment
  - Skills: [`writing-plans`] — preserve topic split between entrypoint and handbook
  - Omitted: [`brainstorming`] — decisions are already set

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 6 | Blocked By: 1, 2

  **References**:
  - Pattern: `AGENTS.md` — current repo entrypoint boundaries and required reading order
  - Pattern: `docs/opencode-iteration-handbook.md:7` — current design status section to update
  - Pattern: `docs/opencode-iteration-handbook.md:142` — current durable progress record
  - Pattern: `docs/opencode-iteration-handbook.md:203` — update protocol

  **Acceptance Criteria**:
  - [ ] `grep -q "sessions_yield" docs/opencode-iteration-handbook.md && grep -q "bounded" docs/opencode-iteration-handbook.md` exits `0`
  - [ ] `grep -q "orchestration" AGENTS.md && grep -q "opencode-iteration-handbook.md" AGENTS.md` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
agents = Path('AGENTS.md').read_text(encoding='utf-8')
handbook = Path('docs/opencode-iteration-handbook.md').read_text(encoding='utf-8')
assert 'session-yield-orchestrator-loop' in handbook
assert 'sessions_yield' in handbook
assert len(agents.splitlines()) <= 220
print('entrypoint-handbook-loop-aligned')
PY` exits `0`

  **QA Scenarios**:
  ```
  Scenario: Durable project memory records the new orchestration milestone
    Tool: Bash
    Steps: run `grep -n "session-yield-orchestrator-loop\|sessions_yield\|bounded loop" docs/opencode-iteration-handbook.md`
    Expected: the handbook records the new orchestration model and its durable rules
    Evidence: .sisyphus/evidence/task-5-handbook-loop-milestone.txt

  Scenario: Repo entrypoint still stays concise while pointing to the new model
    Tool: Bash
    Steps: run `wc -l AGENTS.md && grep -n "orchestrator\|handbook" AGENTS.md`
    Expected: AGENTS stays under the line budget and points future sessions to the handbook/orchestration guidance
    Evidence: .sisyphus/evidence/task-5-handbook-loop-milestone-error.txt
  ```

  **Commit**: YES | Message: `docs(handbook): record session-yield orchestration model` | Files: `AGENTS.md`, `docs/opencode-iteration-handbook.md`

- [x] 6. Run final drift review across contracts, docs, and tests for the bounded-loop model

  **What to do**: Perform a final reconciliation pass across orchestrator docs/contracts/tests. Confirm the repo now consistently says: worker execution remains native `sessions_spawn` / announce, orchestrator may run multiple bounded rounds, `sessions_yield` is only an orchestrator turn boundary, main visibility is semi-visible milestones only, and loop termination is explicit. Fix any stale one-shot wording, missing `max_rounds` / blocker terminology, or accidental worker-yield language. Re-run the focused test suite and `docs-check`.
  **Must NOT do**: Do not expand scope into runtime implementation beyond contracts/docs/tests.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: cross-file reconciliation with high regression risk
  - Skills: [`verification-before-completion`] — evidence-first final pass
  - Omitted: [`brainstorming`] — architecture already approved

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: Final Verification | Blocked By: 1, 2, 3, 4, 5

  **References**:
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md`
  - Pattern: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`
  - Pattern: `docs/adr/0002-native-subagent-announce.md`
  - Pattern: `docs/architecture.md`
  - Pattern: `docs/operations.md`
  - Pattern: `docs/opencode-iteration-handbook.md`
  - Test: `tests/integration/test_orchestrator_dispatch_contract.py`
  - Test: `tests/unit/test_orchestrator_workspace.py`
  - Test: `tests/unit/test_docs_examples.py`

  **Acceptance Criteria**:
  - [ ] `pytest tests/integration/test_orchestrator_dispatch_contract.py tests/unit/test_orchestrator_workspace.py tests/unit/test_docs_examples.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
blob = '\n'.join([
    Path('workspaces/oe-orchestrator/AGENTS.md').read_text(encoding='utf-8'),
    Path('workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md').read_text(encoding='utf-8'),
    Path('docs/adr/0002-native-subagent-announce.md').read_text(encoding='utf-8'),
    Path('docs/operations.md').read_text(encoding='utf-8'),
    Path('docs/architecture.md').read_text(encoding='utf-8'),
    Path('docs/opencode-iteration-handbook.md').read_text(encoding='utf-8'),
])
assert 'sessions_yield' in blob
assert 'max_rounds' in blob or 'max rounds' in blob.lower()
assert 'meaningful_progress' in blob or 'meaningful progress' in blob.lower()
assert 'blocked' in blob.lower()
assert 'worker-level' not in blob.lower() or 'no worker-level' in blob.lower()
print('bounded-loop-final-alignment-ok')
PY` exits `0`

  **QA Scenarios**:
  ```
  Scenario: Repo-wide contracts and docs agree on the same bounded-loop model
    Tool: Bash
    Steps: run the final focused test suite plus `python -m openclaw_enhance.cli docs-check`
    Expected: tests and docs validation pass with no stale one-shot-only contradictions
    Evidence: .sisyphus/evidence/task-6-bounded-loop-final.txt

  Scenario: Repo-wide wording forbids worker-level yield and polling waits
    Tool: Bash
    Steps: run `grep -R "sessions_history\|worker.*sessions_yield\|polling" workspaces/oe-orchestrator docs tests --include='*.md' --include='*.py'`
    Expected: no stale polling-based wait guidance and no accidental worker-level yield instructions remain
    Evidence: .sisyphus/evidence/task-6-bounded-loop-final-error.txt
  ```

  **Commit**: YES | Message: `docs(orchestrator): finalize bounded session-yield model` | Files: orchestrator docs/contracts/tests and related handbook/docs files

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [x] F1. Plan Compliance Audit — oracle

  **What to do**: Audit the executed work against this plan only. Confirm every numbered task was completed in the intended dependency order, no worker-level yield semantics were introduced, and no polling/history waiting patterns were reintroduced.
  **Verification**:
  - [ ] `grep -n "sessions_yield\|max_rounds\|meaningful_progress\|blocked" workspaces/oe-orchestrator/AGENTS.md workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md docs/adr/0002-native-subagent-announce.md docs/operations.md docs/architecture.md docs/opencode-iteration-handbook.md` exits `0`
  - [ ] `! grep -R "sessions_history" workspaces/oe-orchestrator docs tests --include='*.md' --include='*.py'` exits `0`
  **Pass Condition**: Every planned surface was updated and no forbidden polling guidance exists.

- [x] F2. Code Quality Review — unspecified-high

  **What to do**: Review the changed tests/docs/contracts for internal consistency and stale wording.
  **Verification**:
  - [ ] `pytest tests/integration/test_orchestrator_dispatch_contract.py tests/unit/test_orchestrator_workspace.py tests/unit/test_docs_examples.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  **Pass Condition**: Focused test suite passes and documentation validation is clean.

- [x] F3. Real Manual QA — unspecified-high

  **What to do**: Manually inspect rendered contract/docs outputs to verify a future agent would understand the bounded-loop model.
  **Verification**:
  - [ ] `python -m openclaw_enhance.cli render-workspace oe-orchestrator` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-skill oe-toolcall-router` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-skill oe-timeout-state-sync` exits `0`
  **Pass Condition**: Rendered outputs are coherent, mention native execution, and do not imply one-shot-only orchestration where changed.

- [x] F4. Scope Fidelity Check — deep

  **What to do**: Verify v1 stayed narrow: orchestrator-only yield, bounded rounds, milestone checkpoints, no recursive worker orchestration or custom runtime.
  **Verification**:
  - [ ] `python - <<'PY'
from pathlib import Path
blob = '\n'.join([
    Path('workspaces/oe-orchestrator/AGENTS.md').read_text(encoding='utf-8'),
    Path('workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md').read_text(encoding='utf-8'),
    Path('docs/adr/0002-native-subagent-announce.md').read_text(encoding='utf-8'),
])
assert 'sessions_yield' in blob
assert 'worker-level' not in blob.lower() or 'no worker-level' in blob.lower()
assert 'max_rounds' in blob or 'max rounds' in blob.lower()
print('scope-fidelity-ok')
PY` exits `0`
  **Pass Condition**: The implemented design remains bounded, orchestrator-owned, and compatible with the native-primitives model.

## Commit Strategy
- Keep orchestrator workflow and worker-dispatch contract in separate commits so the loop controller and dispatch protocol evolve independently.
- Keep tests in their own commit so bounded-loop requirements are auditable.
- Keep ADR/deep docs separate from handbook/entrypoint docs.
- Final drift review commit should only reconcile wording or test/doc drift, not introduce new contract scope.

## Success Criteria
- The repo no longer describes `oe-orchestrator` as a purely linear one-shot dispatcher.
- `sessions_yield` is documented as an orchestrator-only round-boundary primitive, not as a transport or worker feature.
- Future implementers have explicit loop state, max-round, duplicate-dispatch, blocker, and checkpoint rules to follow without improvisation.
- Main visibility is intentionally semi-visible: milestone checkpoints only.
- Tests and documentation together lock the new orchestration model and guard against regression to polling or one-shot-only semantics.
