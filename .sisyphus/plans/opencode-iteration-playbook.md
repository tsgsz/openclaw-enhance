# OpenCode Iteration Playbook

## TL;DR
> **Summary**: Create a two-layer, agent-facing documentation system so future OpenCode sessions can immediately understand this repo's hard constraints, current architecture state, durable progress rules, and required pre-read path before planning or implementation.
> **Deliverables**:
> - Repo-root `AGENTS.md` as the mandatory, short entrypoint for future OpenCode sessions
> - `docs/opencode-iteration-handbook.md` as the long-form project memory and iteration handbook
> - Clear separation between durable project memory and session-only `.sisyphus/*` state
> - `docs-check` and doc tests extended to keep the new agent-facing docs from drifting
> **Effort**: Short
> **Parallel**: YES - 2 waves
> **Critical Path**: 1 -> 2 -> 3 -> 5 -> 6

## Context
### Original Request
- Produce a permanent document set that tells future OpenCode sessions what rules this project must follow, what design state has already been reached, where permanent progress should live, and what must be read before design or development starts.

### Interview Summary
- Future OpenCode sessions must see the guidance automatically rather than discovering it manually later.
- The chosen shape is a two-layer system: repo-root `AGENTS.md` as the mandatory entrypoint plus a linked long-form handbook.
- The handbook must cover current architecture state, durable progress recording, iteration workflow, and required reading paths.
- The guidance must distinguish durable project truth from session-local `.sisyphus/*` execution state.

### Metis Review (gaps addressed)
- Resolve the handbook shape now: use a single handbook file rather than a multi-file subtree to avoid early documentation sprawl.
- Resolve the language now: use English for agent-facing docs so future OpenCode sessions and standards-aligned tools can consume them reliably, while leaving the existing Chinese `README.md` in place.
- Resolve the `AGENTS.md` size now: keep it short and operational, target quick-scan length, and forbid long-form architecture narrative there.
- Resolve the durable-progress question now: permanent progress lives in the handbook; `.sisyphus/plans/*.md`, `.sisyphus/boulder.json`, and evidence files remain session/plan tracking only.
- Prevent duplication: existing architecture/install/operations/ADR docs remain the canonical deep references for their topics; the new handbook is a navigation and state layer, not a replacement set.
- Add executable verification so the new docs are enforced by `docs-check` and unit tests rather than social convention only.

## Work Objectives
### Core Objective
- Give future OpenCode sessions a deterministic, repo-local operating contract: read `AGENTS.md` first, follow its required reading order, consult the handbook for durable project memory, then proceed into the existing canonical docs and workspace instructions.

### Deliverables
- Repo-root `AGENTS.md` that defines hard constraints, required read order, source-of-truth precedence, and pre-design/pre-development checks.
- `docs/opencode-iteration-handbook.md` that records current architecture state, permanent progress rules, current milestone status, and update protocol for future agents.
- Minimal discoverability links from existing high-traffic docs so humans and agents do not orphan the new guidance.
- `src/openclaw_enhance/cli.py` / `tests/unit/test_docs_examples.py` updates so the new docs are validated automatically.

### Definition of Done (verifiable conditions with commands)
- `test -f AGENTS.md && grep -q "docs/opencode-iteration-handbook.md" AGENTS.md` exits `0`.
- `test -f docs/opencode-iteration-handbook.md && grep -q "## Current Design Status" docs/opencode-iteration-handbook.md` exits `0`.
- `python -m openclaw_enhance.cli docs-check` exits `0`.
- `pytest tests/unit/test_docs_examples.py -q` exits `0`.
- `python - <<'PY'
from pathlib import Path
agents = Path('AGENTS.md').read_text(encoding='utf-8')
handbook = Path('docs/opencode-iteration-handbook.md').read_text(encoding='utf-8')
assert 'Required Reading Order' in agents
assert 'Source of Truth Map' in agents
assert 'docs/opencode-iteration-handbook.md' in agents
assert 'Current Design Status' in handbook
assert 'Permanent Progress Record' in handbook
assert 'Session State vs Permanent Memory' in handbook
assert 'Update Protocol' in handbook
assert 'router-skill-first-alignment' in handbook
print('opencode-playbook-aligned')
PY` exits `0`.

### Must Have
- `AGENTS.md` must be the mandatory agent-facing entrypoint at repo root.
- `AGENTS.md` must explicitly require reading the handbook before planning or coding, then reading domain-specific docs/workspace `AGENTS.md` as needed.
- The handbook must state the current implemented architecture as: skill-first routing, native `sessions_spawn` / announce execution, main-skill sync during install, symmetric uninstall, docs-check, and workspace role boundaries.
- The handbook must define durable progress rules and explicitly say `.sisyphus/*` is session memory rather than permanent project truth.
- The handbook must include a source-of-truth map so future agents know which file owns which topic.
- `docs-check` and doc tests must validate the new entrypoint docs.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No second README disguised as `AGENTS.md`; keep `AGENTS.md` operational and short.
- No long-form duplication of `docs/architecture.md`, `docs/install.md`, `docs/operations.md`, `docs/troubleshooting.md`, or workspace `AGENTS.md` content.
- No claim that `.sisyphus/boulder.json` or active plans are durable architectural truth.
- No bilingual mirrored handbook/agent docs unless explicitly requested later.
- No new automation beyond documentation validation for this first iteration.
- No changes to runtime architecture, worker topology, or installer behavior; this plan documents and governs the existing system.

## Verification Strategy
> ZERO HUMAN INTERVENTION — all verification is agent-executed.
- Test decision: tests-after, because the work is primarily documentation plus validation coverage.
- QA policy: every task includes command-level verification and one edge/failure-oriented scenario.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`.

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: 1) repo-root `AGENTS.md` entrypoint, 2) handbook core state/source-of-truth sections, 3) handbook durable progress/update protocol

Wave 2: 4) discoverability links in existing docs, 5) `docs-check` + doc tests, 6) final drift review and polish

### Dependency Matrix (full, all tasks)
| Task | Depends On | Blocks |
| --- | --- | --- |
| 1 | none | 4, 5, 6 |
| 2 | none | 3, 4, 5, 6 |
| 3 | 2 | 5, 6 |
| 4 | 1, 2 | 6 |
| 5 | 1, 2, 3 | 6 |
| 6 | 1, 2, 3, 4, 5 | Final Verification |

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 -> 3 tasks -> `writing`, `unspecified-high`
- Wave 2 -> 3 tasks -> `writing`, `quick`, `unspecified-high`
- Final Verification -> 4 tasks -> `oracle`, `unspecified-high`, `deep`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 1. Create repo-root `AGENTS.md` as the mandatory OpenCode entrypoint

  **What to do**: Add a new repo-root `AGENTS.md` that future OpenCode sessions can consume immediately. Keep it short and operational. It must include: project mission, non-invasive boundaries derived from the current project intent, required reading order, source-of-truth precedence, explicit rule that `.sisyphus/*` is not permanent project truth, workspace-specific `AGENTS.md` escalation guidance, and a pre-design / pre-development checklist. Link exact handbook sections rather than re-explaining architecture inline. Keep the file in English and under a quick-scan length budget.
  **Must NOT do**: Do not copy full architecture or workspace rules into `AGENTS.md`. Do not restate every CLI command or ADR narrative there.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: concise, high-signal instruction writing with strict boundary control
  - Skills: [`writing-plans`] — reason about exact sections and verifiable structure
  - Omitted: [`frontend-ui-ux`] — no visual/UI work

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 4, 5, 6 | Blocked By: none

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:3` — project intent as enhancement to OpenClaw
  - Pattern: `README.md:5` — non-invasive rules: no OpenClaw source edits, no runtime-file modifications, CLI-first operations
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md:3` — existing per-workspace AGENTS style and role framing
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md:46` — native subagent dispatch wording already in use
  - Pattern: `workspaces/oe-syshelper/AGENTS.md:30` — explicit guardrail section naming (`Read-Only Guarantee`)
  - Pattern: `workspaces/oe-watchdog/AGENTS.md:168` — narrow-authority framing for hard constraints
  - External: `https://agents.md/` — repo-root AGENTS standard and intent
  - External: `https://open-code.ai/docs/agents/` — agent-facing configuration and role expectations

  **Acceptance Criteria** (agent-executable only):
  - [ ] `test -f AGENTS.md` exits `0`
  - [ ] `grep -q "Required Reading Order" AGENTS.md && grep -q "Source of Truth Map" AGENTS.md` exits `0`
  - [ ] `grep -q "docs/opencode-iteration-handbook.md" AGENTS.md` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
content = Path('AGENTS.md').read_text(encoding='utf-8')
assert len(content.splitlines()) <= 220
assert '.sisyphus' in content and 'not permanent' in content.lower()
print('agents-entrypoint-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: AGENTS entrypoint is short and actionable
    Tool: Bash
    Steps: run the acceptance snippet plus `grep -n "Required Reading Order\|Source of Truth Map\|Pre-Design Checklist" AGENTS.md`
    Expected: all sections exist, handbook link exists, and the file stays within the line budget
    Evidence: .sisyphus/evidence/task-1-agents-entrypoint.txt

  Scenario: AGENTS does not expand into a second handbook
    Tool: Bash
    Steps: run `! grep -q "## Current Design Status" AGENTS.md && ! grep -q "## Permanent Progress Record" AGENTS.md`
    Expected: command exits `0`, proving long-form narrative stayed out of `AGENTS.md`
    Evidence: .sisyphus/evidence/task-1-agents-entrypoint-error.txt
  ```

  **Commit**: YES | Message: `docs(agents): add repo-root opencode entrypoint` | Files: `AGENTS.md`

- [x] 2. Create `docs/opencode-iteration-handbook.md` with current architecture state and source-of-truth map

  **What to do**: Create a single long-form handbook at `docs/opencode-iteration-handbook.md`. Include exact sections: purpose, current design status, source-of-truth map, required reading paths by task type, known invariants/no-go areas, and latest completed milestone. Translate the latest architecture milestone from `.sisyphus/plans/router-skill-first-alignment.md` into plain operational guidance: the repo is now skill-first, native `sessions_spawn` / announce is the only execution path, main-session skills are file-backed and synced into the active workspace, uninstall is symmetric, and `docs-check` enforces doc alignment. Reference existing architecture/install/operations/ADR docs instead of re-explaining them in full.
  **Must NOT do**: Do not replace the existing docs set. Do not rewrite the handbook as a narrative clone of `docs/architecture.md`.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: this is architecture/state writing with precision constraints
  - Skills: [`writing-plans`] — organize sections and references cleanly
  - Omitted: [`brainstorming`] — the document shape is already decided

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 3, 4, 5, 6 | Blocked By: none

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `.sisyphus/plans/router-skill-first-alignment.md:31` — current core objective after the latest completed milestone
  - Pattern: `.sisyphus/plans/router-skill-first-alignment.md:35` — deliverables already implemented
  - Pattern: `docs/architecture.md:122` — existing `Main Session Skills` section to summarize rather than duplicate
  - Pattern: `docs/architecture.md:245` — support matrix already lives in architecture docs
  - Pattern: `docs/install.md:5` — skill-first install wording already reflects current runtime behavior
  - Pattern: `docs/operations.md:15` — operations doc already explains routing behavior and escalation path
  - Pattern: `docs/adr/0002-native-subagent-announce.md:19` — native `sessions_spawn` boundary wording
  - Pattern: `src/openclaw_enhance/install/main_skill_sync.py:20` — installer sync entrypoint
  - Pattern: `src/openclaw_enhance/cli.py:320` — `docs-check` command exists and should be referenced as a validation tool
  - Pattern: `src/openclaw_enhance/skills_catalog.py:178` — file-backed rendering entrypoint for skill contracts

  **Acceptance Criteria** (agent-executable only):
  - [ ] `test -f docs/opencode-iteration-handbook.md` exits `0`
  - [ ] `grep -q "## Current Design Status" docs/opencode-iteration-handbook.md && grep -q "## Source of Truth Map" docs/opencode-iteration-handbook.md` exits `0`
  - [ ] `grep -q "sessions_spawn" docs/opencode-iteration-handbook.md && grep -q "router-skill-first-alignment" docs/opencode-iteration-handbook.md` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
content = Path('docs/opencode-iteration-handbook.md').read_text(encoding='utf-8')
for heading in ['Current Design Status', 'Source of Truth Map', 'Required Reading Paths', 'Known Invariants']:
    assert f'## {heading}' in content
print('handbook-core-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Handbook captures current design state with exact current architecture
    Tool: Bash
    Steps: run `grep -n "skill-first\|sessions_spawn\|main-skill\|docs-check\|workspace AGENTS" docs/opencode-iteration-handbook.md`
    Expected: the handbook references the implemented architecture, validation path, and workspace-level guidance
    Evidence: .sisyphus/evidence/task-2-handbook-core.txt

  Scenario: Handbook is a navigation/state layer rather than a duplicate architecture manual
    Tool: Bash
    Steps: run `grep -n "Source of Truth Map\|Read .*docs/architecture.md\|Read .*docs/operations.md\|Read .*docs/adr/0002-native-subagent-announce.md" docs/opencode-iteration-handbook.md`
    Expected: the handbook points to existing canonical docs instead of restating them wholesale
    Evidence: .sisyphus/evidence/task-2-handbook-core-error.txt
  ```

  **Commit**: YES | Message: `docs(handbook): capture opencode iteration state` | Files: `docs/opencode-iteration-handbook.md`

- [x] 3. Add permanent progress rules and update protocol to the handbook

  **What to do**: Extend `docs/opencode-iteration-handbook.md` with exact sections for `Permanent Progress Record`, `Session State vs Permanent Memory`, and `Update Protocol`. Define that permanent progress means milestone-level or architecture/process-level state that should survive sessions. Record the current durable status as the router-skill-first alignment milestone being complete. Define that `.sisyphus/boulder.json`, active plans, and evidence files are session execution artifacts and may be consulted for detail but are not canonical architectural truth. Define when agents MUST update the handbook (architecture changes, new workflow constraints, new permanent doc locations, completed milestones that change future work) and when they MUST NOT (small code-only changes with no workflow/architecture impact).
  **Must NOT do**: Do not create a second `PROGRESS.md`. Do not make `.sisyphus/*` the permanent memory source.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: policy/rules writing with durability boundaries
  - Skills: [`writing-plans`] — keep update protocol and permanent-memory rules explicit
  - Omitted: [`requesting-code-review`] — this is still plan-stage document authoring

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 5, 6 | Blocked By: 2

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `.sisyphus/boulder.json:2` — active plan pointer example, useful as session-state reference only
  - Pattern: `.sisyphus/plans/router-skill-first-alignment.md:1` — latest completed milestone to summarize durably
  - Pattern: `.sisyphus/plans/router-skill-first-alignment.md:541` — success criteria for the current architecture milestone
  - Pattern: `README.md:5` — non-invasive constraints that must remain durable rules
  - Pattern: `docs/adr/0001-managed-namespace.md:1` — ADRs remain durable decision records, not replaced by the handbook
  - Pattern: `docs/adr/0002-native-subagent-announce.md:19` — durable transport boundary
  - Pattern: `docs/adr/0003-watchdog-authority.md:1` — durable watchdog scope boundary

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -q "## Permanent Progress Record" docs/opencode-iteration-handbook.md && grep -q "## Session State vs Permanent Memory" docs/opencode-iteration-handbook.md` exits `0`
  - [ ] `grep -q ".sisyphus/boulder.json" docs/opencode-iteration-handbook.md && grep -q "not permanent" docs/opencode-iteration-handbook.md` exits `0`
  - [ ] `grep -q "router-skill-first-alignment" docs/opencode-iteration-handbook.md && grep -q "complete" docs/opencode-iteration-handbook.md` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
content = Path('docs/opencode-iteration-handbook.md').read_text(encoding='utf-8')
assert 'Update Protocol' in content
assert 'MUST update' in content or 'must update' in content.lower()
assert 'MUST NOT' in content or 'must not' in content.lower()
print('handbook-progress-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Permanent progress location is explicit and durable
    Tool: Bash
    Steps: run `grep -n "Permanent Progress Record\|router-skill-first-alignment\|current durable status" docs/opencode-iteration-handbook.md`
    Expected: handbook clearly records the current milestone and where future durable status belongs
    Evidence: .sisyphus/evidence/task-3-progress-protocol.txt

  Scenario: Session memory is explicitly demoted from canonical truth
    Tool: Bash
    Steps: run `grep -n ".sisyphus/boulder.json\|session memory\|not permanent" docs/opencode-iteration-handbook.md`
    Expected: the handbook clearly prevents future agents from treating `.sisyphus/*` as the permanent source of truth
    Evidence: .sisyphus/evidence/task-3-progress-protocol-error.txt
  ```

  **Commit**: YES | Message: `docs(handbook): define durable progress protocol` | Files: `docs/opencode-iteration-handbook.md`

- [x] 4. Add minimal discoverability links from existing high-traffic docs

  **What to do**: Update only the high-traffic entrypoints that benefit from discoverability without creating duplication. Add a concise agent-facing pointer in `README.md` saying agent sessions should start from `AGENTS.md`, and add one short note in `docs/architecture.md` or `docs/operations.md` pointing future maintainers to `docs/opencode-iteration-handbook.md` for current-state/project-memory guidance. Keep these notes terse and navigational.
  **Must NOT do**: Do not fan this across every doc page. Do not duplicate the handbook content inside README or architecture docs.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: concise discoverability copy, not broad documentation rewrite
  - Skills: [`writing-plans`] — avoid over-documenting and keep the additions navigational only
  - Omitted: [`frontend-ui-ux`] — markdown only

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 6 | Blocked By: 1, 2

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:3` — project-intent entrypoint already used by humans
  - Pattern: `docs/architecture.md:1` — architecture doc is the current deep technical narrative
  - Pattern: `docs/operations.md:1` — operations doc is the runtime/operator guide if you choose it instead of architecture
  - Pattern: `AGENTS.md` — new repo-root entrypoint from Task 1
  - Pattern: `docs/opencode-iteration-handbook.md` — new handbook from Tasks 2-3

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -q "AGENTS.md" README.md` exits `0`
  - [ ] `grep -q "opencode-iteration-handbook.md" README.md docs/architecture.md docs/operations.md` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
readme = Path('README.md').read_text(encoding='utf-8')
assert 'AGENTS.md' in readme
docs_blob = '\n'.join(
    Path(p).read_text(encoding='utf-8')
    for p in ['docs/architecture.md', 'docs/operations.md']
    if Path(p).exists()
)
assert 'opencode-iteration-handbook.md' in docs_blob
print('discoverability-links-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: High-traffic docs point maintainers to the new agent-facing docs
    Tool: Bash
    Steps: run `grep -n "AGENTS.md\|opencode-iteration-handbook.md" README.md docs/architecture.md docs/operations.md`
    Expected: concise pointer lines exist in the chosen discoverability surfaces
    Evidence: .sisyphus/evidence/task-4-discoverability-links.txt

  Scenario: Discoverability remains terse instead of duplicating the handbook
    Tool: Bash
    Steps: run `! grep -q "## Permanent Progress Record" README.md && ! grep -q "## Current Design Status" README.md`
    Expected: README stays navigational and does not absorb handbook-only sections
    Evidence: .sisyphus/evidence/task-4-discoverability-links-error.txt
  ```

  **Commit**: YES | Message: `docs(readme): link opencode entrypoint docs` | Files: `README.md`, `docs/architecture.md` or `docs/operations.md`

- [x] 5. Extend `docs-check` and doc tests to enforce the new agent-facing docs

  **What to do**: Update `src/openclaw_enhance/cli.py` so `docs-check` also validates `AGENTS.md` and `docs/opencode-iteration-handbook.md`. Preserve the existing `sessions_spawn` and banned-term checks, then add new checks for: handbook link from `AGENTS.md`, required sections in the handbook, and existence of the new files. Extend `tests/unit/test_docs_examples.py` with assertions for the new files and their required sections. Prefer focused section-name checks over brittle whole-file text snapshots.
  **Must NOT do**: Do not create validation that depends on volatile wording or exact line counts beyond the simple `AGENTS.md` quick-scan budget.

  **Recommended Agent Profile**:
  - Category: `quick` — Reason: bounded Python/test updates around an existing validation command
  - Skills: [`test-driven-development`] — lock expected doc invariants in tests before touching validation logic
  - Omitted: [`systematic-debugging`] — no bug triage expected unless validation unexpectedly fails

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 6 | Blocked By: 1, 2, 3

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/cli.py:320` — current `docs-check` command implementation
  - Pattern: `src/openclaw_enhance/cli.py:328` — target file list currently used by docs validation
  - Pattern: `src/openclaw_enhance/cli.py:337` — required terms list currently anchored on `sessions_spawn`
  - Pattern: `src/openclaw_enhance/cli.py:338` — banned terms list already prevents stale router-runtime language
  - Pattern: `tests/unit/test_docs_examples.py:47` — current doc test class organization
  - Pattern: `tests/unit/test_docs_examples.py:241` — CLI docs-check existence/behavior tests already exist
  - Pattern: `tests/unit/test_docs_examples.py:311` — documentation completeness tests already aggregate docs coverage

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  - [ ] `pytest tests/unit/test_docs_examples.py -q` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
from openclaw_enhance.cli import docs_check
assert Path('AGENTS.md').exists()
assert Path('docs/opencode-iteration-handbook.md').exists()
print('docs-check-targets-exist')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: New agent-facing docs are validated automatically
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli docs-check && pytest tests/unit/test_docs_examples.py -q`
    Expected: both commands exit `0`, proving the new docs are covered by automated validation
    Evidence: .sisyphus/evidence/task-5-doc-validation.txt

  Scenario: Validation scope includes AGENTS and handbook specifically
    Tool: Bash
    Steps: run `grep -n "AGENTS.md\|opencode-iteration-handbook.md" src/openclaw_enhance/cli.py tests/unit/test_docs_examples.py`
    Expected: both files are referenced in validation logic and tests
    Evidence: .sisyphus/evidence/task-5-doc-validation-error.txt
  ```

  **Commit**: YES | Message: `test(docs): enforce opencode playbook docs` | Files: `src/openclaw_enhance/cli.py`, `tests/unit/test_docs_examples.py`

- [x] 6. Run final drift review and polish the new guidance against existing canonical docs

  **What to do**: Perform a final pass across `AGENTS.md`, the handbook, README, and the canonical docs they reference. Fix any incorrect precedence, stale terminology, or duplicated content that slipped in. Confirm the guidance tells future agents exactly what to read for: (a) planning a new feature, (b) implementing code, (c) touching orchestrator/worker workspaces, and (d) understanding permanent progress. Make sure the handbook clearly points to the latest completed milestone and that `AGENTS.md` points to the correct handbook sections.
  **Must NOT do**: Do not widen scope into runtime changes, doc redesign, or workspace content rewrites unless drift makes a reference plainly wrong.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: cross-document reconciliation with precision and verification burden
  - Skills: [`verification-before-completion`] — require evidence before claiming the guidance is ready
  - Omitted: [`brainstorming`] — design decisions are already fixed

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: Final Verification | Blocked By: 1, 2, 3, 4, 5

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `AGENTS.md` — final entrypoint to polish after Tasks 1-5
  - Pattern: `docs/opencode-iteration-handbook.md` — final handbook to reconcile after Tasks 2-5
  - Pattern: `README.md:5` — still-authoritative non-invasive constraints
  - Pattern: `docs/architecture.md:122` — main-session skill architecture reference
  - Pattern: `docs/operations.md:15` — routing behavior reference for future operator flows
  - Pattern: `docs/adr/0002-native-subagent-announce.md:19` — execution-boundary wording that must stay consistent
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md:46` — native announce wording for workspace-specific work
  - Pattern: `.sisyphus/plans/router-skill-first-alignment.md:541` — latest success criteria that define current state

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  - [ ] `pytest tests/unit/test_docs_examples.py -q` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
agents = Path('AGENTS.md').read_text(encoding='utf-8')
handbook = Path('docs/opencode-iteration-handbook.md').read_text(encoding='utf-8')
assert 'planning a new feature' in handbook.lower()
assert 'implementing code' in handbook.lower()
assert 'workspace' in handbook.lower()
assert 'router-skill-first-alignment' in handbook
assert 'Required Reading Order' in agents
print('playbook-final-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Future agent can determine exactly what to read before acting
    Tool: Bash
    Steps: run `grep -n "Required Reading Order\|planning a new feature\|implementing code\|workspace-specific" AGENTS.md docs/opencode-iteration-handbook.md`
    Expected: the new guidance covers planning, implementation, and workspace-specific reading paths explicitly
    Evidence: .sisyphus/evidence/task-6-final-polish.txt

  Scenario: Durable progress and current-state guidance remain anchored in the latest milestone
    Tool: Bash
    Steps: run `grep -n "router-skill-first-alignment\|Permanent Progress Record\|Session State vs Permanent Memory" docs/opencode-iteration-handbook.md`
    Expected: the handbook clearly anchors permanent project memory to the latest completed milestone and demotes session-only state appropriately
    Evidence: .sisyphus/evidence/task-6-final-polish-error.txt
  ```

  **Commit**: YES | Message: `docs(playbook): finalize opencode iteration guidance` | Files: `AGENTS.md`, `docs/opencode-iteration-handbook.md`, `README.md`, `docs/architecture.md` or `docs/operations.md`, `src/openclaw_enhance/cli.py`, `tests/unit/test_docs_examples.py`

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [x] F1. Plan Compliance Audit — oracle ✅ All 6 tasks complete, all deliverables present
- [x] F2. Code Quality Review — unspecified-high ✅ 5 new tests pass, docs-check passes, no TODOs
- [x] F3. Real Manual QA — unspecified-high ✅ CLI works, AGENTS.md 80 lines (under budget)
- [x] F4. Scope Fidelity Check — deep ✅ Skill-first architecture documented, session state demoted, no duplication

## Commit Strategy
- One commit per numbered task.
- Use `docs` for new/updated markdown guidance and `test` for validation logic.
- Keep `AGENTS.md` creation separate from handbook creation so the entrypoint and the durable memory evolve in auditable steps.
- Do not mix discoverability-only doc links with validation logic in the same commit.

## Success Criteria
- Future OpenCode sessions can enter the repo, read `AGENTS.md`, and know exactly what to read next before planning or coding.
- The repo has one short mandatory agent entrypoint and one long-form handbook, with a strict topic split and no sprawling duplication.
- Durable project memory is explicitly separated from session-local `.sisyphus/*` state.
- The handbook accurately reflects the current architecture milestone: skill-first routing, native `sessions_spawn` / announce, main-skill sync, symmetric uninstall, docs-check, and workspace boundaries.
- Automated validation fails if `AGENTS.md` or the handbook drift out of required shape.
