# Dynamic Agent Discovery Routing

## TL;DR
> **Summary**: Replace orchestrator's static worker descriptions with discovery-first routing driven by structured frontmatter embedded in each worker `AGENTS.md`, while keeping `oe-worker-dispatch` as the deterministic policy layer. Add schema validation, least-privilege ranking, TDD coverage, and docs updates without introducing a new manifest file or transport.
> **Deliverables**:
> - Worker `AGENTS.md` frontmatter schema and built-in worker metadata
> - Catalog parsing/validation utilities for workspace metadata and tests
> - Discovery-first `oe-worker-dispatch` contract and aligned orchestrator docs
> - Unit/integration/docs-check coverage for schema, ranking, render, and drift prevention
> **Effort**: Medium
> **Parallel**: YES - 3 waves
> **Critical Path**: 1 -> 2 -> 5 -> 8 -> 9

## Context
### Original Request
- "orch分配sub的skill要先发现agents去看他们是干啥的，再进行分配，这样可以根据AGENTS.md中的描述来动态调配agent，这里可能需要AGENTS.md中有对应的描述"

### Interview Summary
- Current workspace discovery is dynamic at the filesystem level via `src/openclaw_enhance/workspaces.py`, but worker selection remains static prose inside `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`.
- The user wants orchestrator dispatch to discover workers first, understand what each worker is for, and route dynamically from `AGENTS.md` instead of relying on hardcoded worker descriptions.
- The chosen source of truth is `AGENTS.md` frontmatter, not a separate manifest file.
- The approved metadata shape is richer than simple capability tags: it includes capability, constraint, scheduling, and abstract tool-class signals, but does not duplicate exact tool inventories from `TOOLS.md`.
- The approved runtime model is a per-orchestration in-memory catalog, no persistent cache, TDD-first rollout.

### Metis Review (gaps addressed)
- Keep routing logic in skill contracts; do not introduce a new Python routing runtime that bypasses `SKILL.md`.
- Add a closed schema and validator; do not let "rich metadata" become an open-ended DSL.
- Frontmatter must never expand authority beyond `TOOLS.md` and prose boundaries in worker `AGENTS.md`.
- Ranking must be deterministic and least-privilege-first.
- Update docs/render/tests together so frontmatter-bearing `AGENTS.md` files do not break current render and text-coupled assertions.

### Oracle Review (guardrails incorporated)
- Keep exact tools authoritative in `TOOLS.md`; frontmatter stores only routing abstractions.
- Treat install registry descriptions as non-authoritative and minimize drift against worker manifests.
- Make built-in worker manifest compliance testable; invalid or conflicting metadata makes a worker ineligible.
- Preserve native `sessions_spawn` / `sessions_yield` / `announce` flow and do not add persistent cache invalidation complexity.

## Work Objectives
### Core Objective
Make `oe-orchestrator` discover worker capabilities from worker `AGENTS.md` frontmatter before dispatch so worker selection is driven by machine-readable capability metadata instead of static prose lists.

### Deliverables
- Closed frontmatter schema for worker routing metadata embedded in every built-in worker `AGENTS.md`
- Catalog parsing/validation utilities that surface routing metadata without changing native transport behavior
- Discovery-first dispatch contract in `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`
- Updated orchestrator and durable docs reflecting discovery-first routing and source-of-truth boundaries
- TDD coverage for schema parsing, catalog loading, deterministic ranking, invalid metadata handling, render behavior, and docs-check guardrails

### Definition of Done (verifiable conditions with commands)
- `pytest tests/unit/test_agent_catalog.py -q` exits `0`
- `pytest tests/unit/test_worker_workspaces.py tests/unit/test_orchestrator_workspace.py tests/unit/test_docs_examples.py -q` exits `0`
- `pytest tests/integration/test_orchestrator_dispatch_contract.py tests/integration/test_worker_role_boundaries.py -q` exits `0`
- `python -m openclaw_enhance.cli render-workspace oe-orchestrator` exits `0`
- `python -m openclaw_enhance.cli render-workspace oe-searcher` exits `0`
- `python -m openclaw_enhance.cli docs-check` exits `0`
- `grep -q "schema_version:" workspaces/oe-searcher/AGENTS.md workspaces/oe-syshelper/AGENTS.md workspaces/oe-script_coder/AGENTS.md workspaces/oe-watchdog/AGENTS.md workspaces/oe-tool-recovery/AGENTS.md` exits `0`
- `grep -q "discover worker manifests" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` exits `0`

### Must Have
- `AGENTS.md` frontmatter as the routing source of truth for built-in worker capability metadata
- Deterministic, least-privilege-first ranking rules documented in `oe-worker-dispatch`
- Frontmatter schema validation with explicit ineligible behavior on conflict
- TDD for parser, validator, and dispatch contract updates
- Docs/render/test updates that keep frontmatter human-readable and machine-parseable

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No separate `agent-manifest.yaml/json` file
- No new transport, runtime dispatcher, or worker-to-worker handoff
- No persistent disk cache for agent catalogs
- No exact tool names copied into frontmatter; those remain authoritative in `TOOLS.md`
- No expansion of worker authority beyond existing `AGENTS.md` / `TOOLS.md` constraints
- No main-session direct routing to workers; main still escalates only to `oe-orchestrator`
- No heuristic mini-DSL with arbitrary weights or free-form ranking scripts in frontmatter

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: TDD + pytest
- QA policy: Every task includes agent-executed happy-path and failure/edge scenarios
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.txt`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: schema and catalog foundation (`1`, `2`, `3`, `4`)
Wave 2: discovery-driven dispatch contracts and regression coverage (`5`, `6`, `7`, `8`)
Wave 3: docs and non-authoritative registry alignment (`9`, `10`)

### Dependency Matrix (full, all tasks)
- `1` blocks `2`, `3`, `4`, `5`, `7`
- `2` blocks `5`, `6`, `8`, `9`
- `3` blocks `4`, `7`, `10`
- `4` blocks `9`
- `5` blocks `6`, `8`, `9`
- `6` blocks `8`, `9`
- `7` blocks `8`, `10`
- `8` blocks Final Verification
- `9` blocks Final Verification
- `10` blocks Final Verification

### Agent Dispatch Summary
- Wave 1 -> 4 tasks -> `unspecified-high`, `writing`
- Wave 2 -> 4 tasks -> `writing`, `unspecified-high`
- Wave 3 -> 2 tasks -> `writing`, `quick`
- Final Verification -> 4 tasks -> `oracle`, `unspecified-high`, `unspecified-high`, `deep`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 1. Define the worker-routing frontmatter schema and parser foundation

  **What to do**: Add a dedicated catalog/parsing module that reads YAML frontmatter from worker `AGENTS.md` files and validates a closed routing schema. Lock the schema to routing-only metadata: identity, capability, constraint, scheduling, and abstract tool classes. Add explicit invalid/ineligible outcomes for unknown enum values, missing required fields, and malformed frontmatter. Keep exact tools out of the schema.
  **Must NOT do**: Do not implement a new dispatcher runtime; do not parse arbitrary prose for capability decisions; do not put exact tool names or prompt text into the schema.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: new parser/validator design with repo-wide downstream impact
  - Skills: [`test-driven-development`] — why: schema and parser should be driven by failing tests first
  - Omitted: [`systematic-debugging`] — why not needed: this is greenfield validation work, not root-cause analysis

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2, 3, 4, 5, 7 | Blocked By: none

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/workspaces.py` — existing workspace discovery and render entrypoints that the new parser must complement, not replace
  - Pattern: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md:1` — existing YAML frontmatter precedent in repo markdown contracts
  - Pattern: `skills/oe-toolcall-router/SKILL.md:1` — example of richer frontmatter with nested metadata already accepted in this repo
  - API/Type: `src/openclaw_enhance/skills_catalog.py:19` — simple metadata dataclass pattern worth mirroring for parsed catalog objects
  - Test: `tests/unit/test_worker_workspaces.py` — current workspace metadata/render expectations that will need compatible evolution
  - External: `https://code.claude.com/docs/en/sub-agents` — agent descriptions should be clear enough to guide delegation decisions

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_agent_catalog.py -q` exits `0`
  - [ ] `python - <<'PY'
from openclaw_enhance.agent_catalog import parse_agent_manifest
print(parse_agent_manifest('---\nschema_version: 1\nagent_id: oe-demo\nworkspace: oe-demo\nrouting:\n  description: demo\n  capabilities: [code_search]\n  accepts: [find symbol]\n  rejects: [modify files]\n  output_kind: introspection_report\n  mutation_mode: read_only\n  can_spawn: false\n  requires_tests: false\n  session_access: none\n  network_access: none\n  repo_scope: selected_files\n  cost_tier: cheap\n  model_tier: fast\n  duration_band: short\n  parallel_safe: true\n  priority_boost: 0\n  tool_classes: [code_search]\n---\n# Demo\n').agent_id)
PY` prints `oe-demo`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Valid frontmatter parses into a catalog object
    Tool: Bash
    Steps: run `pytest tests/unit/test_agent_catalog.py -q -k "parse or schema" > .sisyphus/evidence/task-1-agent-catalog-parse.txt`
    Expected: parser/schema tests pass and prove valid frontmatter becomes a typed routing manifest
    Evidence: .sisyphus/evidence/task-1-agent-catalog-parse.txt

  Scenario: Invalid frontmatter becomes ineligible instead of silently accepted
    Tool: Bash
    Steps: run `pytest tests/unit/test_agent_catalog.py -q -k "invalid or missing or enum" > .sisyphus/evidence/task-1-agent-catalog-invalid.txt`
    Expected: tests prove malformed or conflicting metadata is rejected deterministically
    Evidence: .sisyphus/evidence/task-1-agent-catalog-invalid.txt
  ```

  **Commit**: YES | Message: `feat(orchestrator): add agent manifest parser` | Files: `src/openclaw_enhance/agent_catalog.py`, `tests/unit/test_agent_catalog.py`

- [ ] 2. Add closed frontmatter manifests to all built-in worker AGENTS files

  **What to do**: Add the approved frontmatter block to every built-in worker `AGENTS.md`: `oe-searcher`, `oe-syshelper`, `oe-script_coder`, `oe-watchdog`, and `oe-tool-recovery`. Each manifest must encode only routing-relevant abstractions and must match the worker's existing prose boundaries and tool authority. Preserve all current human-readable sections below the frontmatter.
  **Must NOT do**: Do not add frontmatter to root `AGENTS.md`; do not duplicate exact tool names from `TOOLS.md`; do not change worker authority or remove human-readable boundary prose.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: mostly contract editing with boundary precision
  - Skills: [`writing-plans`] — why: helps keep repeated manifest blocks consistent across workers
  - Omitted: [`brainstorming`] — why not needed: schema and metadata shape are already decided

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 5, 6, 8, 9 | Blocked By: 1

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `workspaces/oe-searcher/AGENTS.md` — research worker scope and constraints
  - Pattern: `workspaces/oe-syshelper/AGENTS.md:30` — explicit read-only guarantee that metadata must not contradict
  - Pattern: `workspaces/oe-script_coder/AGENTS.md` — worker with repo-write and test responsibility
  - Pattern: `workspaces/oe-watchdog/AGENTS.md` — runtime-only/narrow-authority worker
  - Pattern: `workspaces/oe-tool-recovery/AGENTS.md` — leaf-node recovery specialist with recovery-only scope
  - Pattern: `skills/oe-toolcall-router/SKILL.md:1` — nested frontmatter formatting precedent
  - Test: `tests/integration/test_worker_role_boundaries.py` — prose boundary assertions that must remain true after frontmatter insertion

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -q "schema_version:" workspaces/oe-searcher/AGENTS.md workspaces/oe-syshelper/AGENTS.md workspaces/oe-script_coder/AGENTS.md workspaces/oe-watchdog/AGENTS.md workspaces/oe-tool-recovery/AGENTS.md` exits `0`
  - [ ] `pytest tests/integration/test_worker_role_boundaries.py -q` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: All built-in workers expose required frontmatter
    Tool: Bash
    Steps: run `grep -n "schema_version:\|routing:" workspaces/oe-searcher/AGENTS.md workspaces/oe-syshelper/AGENTS.md workspaces/oe-script_coder/AGENTS.md workspaces/oe-watchdog/AGENTS.md workspaces/oe-tool-recovery/AGENTS.md > .sisyphus/evidence/task-2-worker-frontmatter.txt`
    Expected: each built-in worker AGENTS file contains frontmatter and routing metadata headings
    Evidence: .sisyphus/evidence/task-2-worker-frontmatter.txt

  Scenario: Existing worker-boundary prose still passes enforcement tests
    Tool: Bash
    Steps: run `pytest tests/integration/test_worker_role_boundaries.py -q > .sisyphus/evidence/task-2-worker-boundaries.txt`
    Expected: boundary suite still passes, proving frontmatter did not weaken worker constraints
    Evidence: .sisyphus/evidence/task-2-worker-boundaries.txt
  ```

  **Commit**: YES | Message: `docs(workers): add routing frontmatter to worker manifests` | Files: `workspaces/oe-searcher/AGENTS.md`, `workspaces/oe-syshelper/AGENTS.md`, `workspaces/oe-script_coder/AGENTS.md`, `workspaces/oe-watchdog/AGENTS.md`, `workspaces/oe-tool-recovery/AGENTS.md`

- [ ] 3. Extend workspace metadata and render helpers to surface parsed worker routing metadata

  **What to do**: Integrate the new parser into workspace helper APIs so tests and CLI rendering can inspect worker manifests without changing the native routing architecture. Add metadata accessors that expose parsed frontmatter for worker workspaces, and preserve `render-workspace` readability by intentionally rendering the raw frontmatter plus the existing markdown body.
  **Must NOT do**: Do not hide or strip frontmatter silently; do not turn `render_workspace()` into a routing engine; do not break existing metadata keys used by current tests.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: touches shared workspace helper API and CLI-facing render behavior
  - Skills: [`test-driven-development`] — why: render/metadata compatibility should be pinned by regression tests
  - Omitted: [`frontend-ui-ux`] — why not needed: this is markdown/CLI rendering, not UI styling

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 4, 7, 10 | Blocked By: 1

  **References** (executor has NO interview context — be exhaustive):
  - API/Type: `src/openclaw_enhance/workspaces.py:28` — list/get/render workspace helper surface
  - API/Type: `src/openclaw_enhance/cli.py:174` — CLI render-workspace command
  - Test: `tests/unit/test_worker_workspaces.py:146` — render expectations for built-in workers
  - Test: `tests/unit/test_orchestrator_workspace.py:254` — CLI render contract assertions
  - Pattern: `src/openclaw_enhance/skills_catalog.py:178` — file-backed render helper pattern

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_worker_workspaces.py tests/unit/test_orchestrator_workspace.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-workspace oe-searcher` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Workspace helpers expose parsed routing metadata without breaking old keys
    Tool: Bash
    Steps: run `pytest tests/unit/test_worker_workspaces.py -q -k "metadata or render" > .sisyphus/evidence/task-3-workspace-metadata.txt`
    Expected: metadata/render tests pass and prove parsed frontmatter is available alongside legacy workspace info
    Evidence: .sisyphus/evidence/task-3-workspace-metadata.txt

  Scenario: CLI render preserves frontmatter and human-readable AGENTS body
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli render-workspace oe-searcher > .sisyphus/evidence/task-3-workspace-render.txt && grep -n "schema_version:\|## Role\|## Constraints" .sisyphus/evidence/task-3-workspace-render.txt > .sisyphus/evidence/task-3-workspace-render-scan.txt`
    Expected: rendered output includes both machine-readable frontmatter and worker prose sections
    Evidence: .sisyphus/evidence/task-3-workspace-render-scan.txt
  ```

  **Commit**: YES | Message: `feat(workspaces): expose parsed worker routing metadata` | Files: `src/openclaw_enhance/workspaces.py`, `src/openclaw_enhance/cli.py`, `tests/unit/test_worker_workspaces.py`, `tests/unit/test_orchestrator_workspace.py`

- [ ] 4. Add docs-check and validation guardrails for manifest drift

  **What to do**: Extend validation tooling so built-in worker manifests are checked for schema presence, enum validity, and drift against existing worker authority boundaries. Enforce the no-exact-tool-names rule in frontmatter, and make conflicting metadata render a worker ineligible. Wire the check into `docs-check` or an adjacent validation path used by `docs-check` so repo health catches drift early.
  **Must NOT do**: Do not make docs-check depend on live network access; do not make exact tool names mandatory in frontmatter; do not let conflicting metadata pass as warnings only.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: validation rules affect repo-wide CI/documentation health
  - Skills: [`test-driven-development`] — why: validator behavior should be captured before implementation
  - Omitted: [`systematic-debugging`] — why not needed: guardrail addition is proactive, not reactive

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 9 | Blocked By: 1, 3

  **References** (executor has NO interview context — be exhaustive):
  - API/Type: `src/openclaw_enhance/cli.py:320` — current `docs-check` implementation and scope
  - Test: `tests/unit/test_docs_examples.py` — existing docs-related validation patterns
  - Pattern: `tests/unit/test_recovery_contract.py` — closed-schema/enum validation test style already present in repo
  - Pattern: `workspaces/oe-syshelper/AGENTS.md:30` — worker prose boundary that metadata must not contradict
  - Pattern: `workspaces/oe-tool-recovery/AGENTS.md` — example of narrow authority that must stay represented consistently

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  - [ ] `pytest tests/unit/test_docs_examples.py tests/unit/test_agent_catalog.py -q` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Docs/manifest validation passes for compliant built-in workers
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli docs-check > .sisyphus/evidence/task-4-docs-check.txt`
    Expected: docs-check passes after adding manifest-specific validation rules
    Evidence: .sisyphus/evidence/task-4-docs-check.txt

  Scenario: Validator rejects tool-detail duplication and enum drift
    Tool: Bash
    Steps: run `pytest tests/unit/test_agent_catalog.py -q -k "tool_names or enum or conflict" > .sisyphus/evidence/task-4-manifest-guardrails.txt`
    Expected: tests prove frontmatter cannot duplicate exact tools or carry invalid enum values
    Evidence: .sisyphus/evidence/task-4-manifest-guardrails.txt
  ```

  **Commit**: YES | Message: `test(docs): enforce worker manifest guardrails` | Files: `src/openclaw_enhance/cli.py`, `tests/unit/test_docs_examples.py`, `tests/unit/test_agent_catalog.py`

- [ ] 5. Rewrite `oe-worker-dispatch` as a discovery-first routing contract

  **What to do**: Replace the static worker-description section in `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` with an explicit discovery-first workflow. The contract must require orchestrator to enumerate worker `AGENTS.md` files, parse frontmatter, build a candidate catalog, hard-filter by constraints, rank by deterministic least-privilege rules, and dispatch only then. Keep special-case branches for `oe-tool-recovery` and `oe-watchdog` explicit and separate from ordinary scoring.
  **Must NOT do**: Do not reintroduce hardcoded authoritative worker descriptions; do not allow main to route directly to workers; do not add custom transport or worker-to-worker handoff.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: the source of truth for dispatch behavior is the markdown skill contract
  - Skills: [`writing-plans`] — why: helps preserve deterministic, stepwise routing language
  - Omitted: [`brainstorming`] — why not needed: the routing design and guardrails are already approved

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 6, 8, 9 | Blocked By: 1, 2

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md:31` — current static worker taxonomy that must be demoted from source of truth
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md:87` — EvaluateProgress / recovery flow language that dispatch contract must stay compatible with
  - Pattern: `skills/oe-toolcall-router/SKILL.md:104` — main must still escalate only to orchestrator
  - Pattern: `workspaces/oe-tool-recovery/AGENTS.md` — dedicated recovery branch authority and exclusions
  - Test: `tests/integration/test_orchestrator_dispatch_contract.py` — current contract-level assertions to evolve from static wording to discovery-first wording
  - External: `https://code.claude.com/docs/en/sub-agents` — description-based delegation rationale

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -q "discover worker manifests" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` exits `0`
  - [ ] `grep -q "least-privilege" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Dispatch contract documents discovery-first workflow
    Tool: Bash
    Steps: run `grep -n "discover worker manifests\|candidate catalog\|hard filter\|least-privilege" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md > .sisyphus/evidence/task-5-discovery-first-dispatch.txt`
    Expected: dispatch contract explicitly instructs orchestrator to discover and rank workers from AGENTS manifests before dispatch
    Evidence: .sisyphus/evidence/task-5-discovery-first-dispatch.txt

  Scenario: Special-case routing remains explicit and bounded
    Tool: Bash
    Steps: run `grep -n "oe-tool-recovery\|oe-watchdog\|worker-to-worker\|sessions_spawn" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md > .sisyphus/evidence/task-5-special-routing.txt`
    Expected: recovery/watchdog branches remain explicit and no forbidden handoff/custom transport language appears
    Evidence: .sisyphus/evidence/task-5-special-routing.txt
  ```

  **Commit**: YES | Message: `docs(dispatch): make worker routing discovery-first` | Files: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`

- [ ] 6. Align orchestrator contract with catalog-driven worker selection

  **What to do**: Update `workspaces/oe-orchestrator/AGENTS.md` so worker selection is described as catalog-driven rather than a static supported-agent list. Preserve orchestrator ownership of dispatch, recovery, and checkpointing, but demote the static agent-type bullets into non-authoritative examples. Make it explicit that built-in workers are discovered from manifest-bearing workspaces and validated before selection.
  **Must NOT do**: Do not remove native transport wording; do not imply arbitrary third-party workers are automatically trusted; do not weaken orchestrator ownership of dispatch/retry decisions.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: orchestrator behavior is documented primarily in AGENTS contract prose
  - Skills: [`writing-plans`] — why: keeps architecture wording precise and non-duplicative
  - Omitted: [`receiving-code-review`] — why not needed: this is proactive contract alignment, not feedback response

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8, 9 | Blocked By: 2, 5

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md:35` — current static supported agent types section
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md:62` — bounded round-based orchestration loop that must remain intact
  - Pattern: `docs/opencode-iteration-handbook.md:57` — router decisions stay in skill contracts
  - Pattern: `docs/operations.md:15` — current orchestration narrative and main-to-orchestrator routing boundary
  - Test: `tests/unit/test_orchestrator_workspace.py` — text-coupled orchestrator contract assertions that must be updated intentionally

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -q "candidate catalog" workspaces/oe-orchestrator/AGENTS.md` exits `0`
  - [ ] `grep -q "non-authoritative examples" workspaces/oe-orchestrator/AGENTS.md || grep -q "examples" workspaces/oe-orchestrator/AGENTS.md` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Orchestrator contract no longer treats static worker list as truth source
    Tool: Bash
    Steps: run `grep -n "candidate catalog\|manifest-bearing workspaces\|examples" workspaces/oe-orchestrator/AGENTS.md > .sisyphus/evidence/task-6-orchestrator-catalog.txt`
    Expected: AGENTS contract describes catalog-driven worker selection and static worker mentions only as examples
    Evidence: .sisyphus/evidence/task-6-orchestrator-catalog.txt

  Scenario: Native loop and recovery semantics remain intact
    Tool: Bash
    Steps: run `grep -n "sessions_spawn\|sessions_yield\|oe-tool-recovery\|meaningful_progress" workspaces/oe-orchestrator/AGENTS.md > .sisyphus/evidence/task-6-orchestrator-loop.txt`
    Expected: catalog-driven wording coexists with bounded loop, recovery, and checkpoint semantics
    Evidence: .sisyphus/evidence/task-6-orchestrator-loop.txt
  ```

  **Commit**: YES | Message: `docs(orchestrator): align worker selection to manifests` | Files: `workspaces/oe-orchestrator/AGENTS.md`, `tests/unit/test_orchestrator_workspace.py`

- [ ] 7. Add unit coverage for catalog loading, ranking inputs, and render compatibility

  **What to do**: Extend unit coverage so catalog objects, workspace metadata helpers, and render output all reflect the new manifest-bearing worker model. Add tests for deterministic field extraction, legacy metadata compatibility, frontmatter-preserving renders, and ineligible-worker handling when metadata conflicts with declared boundaries.
  **Must NOT do**: Do not rely on brittle snapshot dumps for the whole render output; do not leave ranking inputs untested; do not assert prose wording when a semantic assertion is possible.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: shared regression coverage across parser, helpers, and rendering
  - Skills: [`test-driven-development`] — why: unit contracts should pin the intended semantics tightly
  - Omitted: [`systematic-debugging`] — why not needed: tests define new behavior rather than diagnose unknown failures

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8, 10 | Blocked By: 1, 3

  **References** (executor has NO interview context — be exhaustive):
  - Test: `tests/unit/test_worker_workspaces.py` — current helper/render coverage
  - Test: `tests/unit/test_orchestrator_workspace.py` — current orchestrator render/help coverage
  - Test: `tests/unit/test_recovery_contract.py` — style precedent for enum/validation-focused unit tests
  - API/Type: `src/openclaw_enhance/workspaces.py` — metadata/render helper surface
  - API/Type: `src/openclaw_enhance/agent_catalog.py` — new parser/catalog surface from task 1

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_agent_catalog.py tests/unit/test_worker_workspaces.py tests/unit/test_orchestrator_workspace.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-workspace oe-tool-recovery` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Unit suite proves catalog extraction and ineligible handling
    Tool: Bash
    Steps: run `pytest tests/unit/test_agent_catalog.py tests/unit/test_worker_workspaces.py -q > .sisyphus/evidence/task-7-catalog-units.txt`
    Expected: unit tests pass and demonstrate deterministic extraction plus invalid/ineligible handling
    Evidence: .sisyphus/evidence/task-7-catalog-units.txt

  Scenario: CLI and render behavior stay compatible with frontmatter-bearing AGENTS files
    Tool: Bash
    Steps: run `pytest tests/unit/test_orchestrator_workspace.py -q > .sisyphus/evidence/task-7-render-units.txt`
    Expected: render/help-related unit tests pass after frontmatter-aware changes
    Evidence: .sisyphus/evidence/task-7-render-units.txt
  ```

  **Commit**: YES | Message: `test(workspaces): cover manifest-driven catalog helpers` | Files: `tests/unit/test_agent_catalog.py`, `tests/unit/test_worker_workspaces.py`, `tests/unit/test_orchestrator_workspace.py`

- [ ] 8. Add integration tests for discovery-first dispatch and least-privilege ranking

  **What to do**: Upgrade dispatch contract integration coverage so it asserts manifest discovery before worker selection, deterministic ranking, special-case routing for recovery/watchdog, and conflict handling that marks workers ineligible rather than silently eligible. Include representative tasks that should prefer `oe-syshelper` over `oe-script_coder` for read-only work and `oe-searcher` over broader workers for pure research work.
  **Must NOT do**: Do not keep the tests coupled only to static worker-description prose; do not encode arbitrary weighted scoring not present in the approved design; do not allow invalid metadata to fall through to a random worker.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: multi-scenario contract coverage with orchestration semantics
  - Skills: [`test-driven-development`] — why: integration coverage should define the intended behavior before implementation wording drifts
  - Omitted: [`systematic-debugging`] — why not needed: the scenarios are known and design-approved

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: Final Verification | Blocked By: 2, 5, 6, 7

  **References** (executor has NO interview context — be exhaustive):
  - Test: `tests/integration/test_orchestrator_dispatch_contract.py` — current contract-level dispatch assertions
  - Test: `tests/integration/test_worker_role_boundaries.py` — worker-boundary expectations used to mark conflicts/ineligibility
  - Pattern: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` — target discovery-first dispatch contract
  - Pattern: `workspaces/oe-orchestrator/AGENTS.md` — orchestrator ownership and bounded loop semantics
  - Pattern: `workspaces/oe-tool-recovery/AGENTS.md` — special-case routing branch that must remain direct, not scored normally

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/integration/test_orchestrator_dispatch_contract.py -q` exits `0`
  - [ ] `grep -q "discover worker manifests" tests/integration/test_orchestrator_dispatch_contract.py || grep -q "candidate catalog" tests/integration/test_orchestrator_dispatch_contract.py` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Read-only work prefers the narrowest eligible worker
    Tool: Bash
    Steps: run `pytest tests/integration/test_orchestrator_dispatch_contract.py -q -k "least_privilege or read_only" > .sisyphus/evidence/task-8-least-privilege.txt`
    Expected: tests prove read-only exploration routes to a narrow worker before broader code-writing workers
    Evidence: .sisyphus/evidence/task-8-least-privilege.txt

  Scenario: Invalid metadata or special-case branches do not use ordinary scoring
    Tool: Bash
    Steps: run `pytest tests/integration/test_orchestrator_dispatch_contract.py -q -k "ineligible or recovery or watchdog" > .sisyphus/evidence/task-8-special-branches.txt`
    Expected: tests prove invalid workers are excluded and recovery/watchdog routing remains explicit
    Evidence: .sisyphus/evidence/task-8-special-branches.txt
  ```

  **Commit**: YES | Message: `test(dispatch): cover manifest-driven worker selection` | Files: `tests/integration/test_orchestrator_dispatch_contract.py`, `tests/integration/test_worker_role_boundaries.py`

- [ ] 9. Update durable docs to explain manifest-driven worker discovery

  **What to do**: Update durable docs so future sessions understand that built-in worker routing metadata now lives in worker `AGENTS.md` frontmatter, while `oe-worker-dispatch` stays the policy layer and `TOOLS.md` stays exact-tool truth. Update architecture, operations, handbook, and root guidance where worker roles or source-of-truth rules are mentioned.
  **Must NOT do**: Do not imply a new manifest file exists; do not imply exact tool lists moved into frontmatter; do not blur main-router responsibilities with orchestrator worker selection.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: durable architecture memory and operational guidance update
  - Skills: [`writing-plans`] — why: keeps docs aligned with approved source-of-truth boundaries
  - Omitted: [`brainstorming`] — why not needed: design choices are already approved and fixed

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: Final Verification | Blocked By: 2, 4, 5, 6

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `docs/opencode-iteration-handbook.md` — durable state and source-of-truth map
  - Pattern: `docs/architecture.md` — system overview and worker routing diagrams
  - Pattern: `docs/operations.md` — operational routing narrative and worker roles
  - Pattern: `AGENTS.md` — top-level worker-role pointers and required reading order
  - Pattern: `docs/adr/0002-native-subagent-announce.md` — native transport boundary wording that must remain unchanged

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -q "AGENTS.md frontmatter" docs/opencode-iteration-handbook.md docs/architecture.md docs/operations.md AGENTS.md` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Durable docs explain frontmatter as routing source of truth
    Tool: Bash
    Steps: run `grep -n "AGENTS.md frontmatter\|source of truth\|TOOLS.md" docs/opencode-iteration-handbook.md docs/architecture.md docs/operations.md AGENTS.md > .sisyphus/evidence/task-9-durable-docs.txt`
    Expected: docs clearly describe frontmatter-driven discovery and TOOLS.md authority boundary
    Evidence: .sisyphus/evidence/task-9-durable-docs.txt

  Scenario: Documentation stays aligned with native transport and render checks
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli docs-check > .sisyphus/evidence/task-9-docs-check.txt`
    Expected: docs-check passes with no banned transport/runtime drift
    Evidence: .sisyphus/evidence/task-9-docs-check.txt
  ```

  **Commit**: YES | Message: `docs(routing): describe manifest-driven worker discovery` | Files: `docs/opencode-iteration-handbook.md`, `docs/architecture.md`, `docs/operations.md`, `AGENTS.md`

- [ ] 10. Demote installer registry descriptions to non-authoritative metadata and update regression coverage

  **What to do**: Keep installer registry descriptions minimal and explicitly non-authoritative so they do not compete with worker `AGENTS.md` manifests. Update any tests/fixtures that assume worker descriptions live only in static registry or prose lists, and add one regression proving built-in workspaces remain discoverable even though capability truth moved to manifests.
  **Must NOT do**: Do not make installer registry parse frontmatter at install time; do not create a second routing schema in config; do not let tests reintroduce installer descriptions as dispatch truth.

  **Recommended Agent Profile**:
  - Category: `quick` — Reason: narrow alignment task across config descriptions and regression expectations
  - Skills: [`test-driven-development`] — why: one regression should pin non-authoritative installer behavior
  - Omitted: [`writing-plans`] — why not needed: this is short code/test alignment, not broad doc restructuring

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: Final Verification | Blocked By: 3, 7

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/install/installer.py:230` — current agent registry descriptions
  - Pattern: `src/openclaw_enhance/workspaces.py:75` — workspace metadata helper that should remain the discovery entrypoint for tests
  - Test: `tests/unit/test_worker_workspaces.py` — built-in workspace discoverability assertions
  - Test: `tests/unit/test_docs_examples.py` — doc/example alignment style
  - Pattern: `docs/install.md` — installer behavior explanations if registry wording becomes user-visible

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_worker_workspaces.py -q` exits `0`
  - [ ] `grep -q "non-authoritative" src/openclaw_enhance/install/installer.py docs/install.md || grep -q "routing source of truth" docs/install.md` exits `0`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Workspace discoverability remains intact after registry demotion
    Tool: Bash
    Steps: run `pytest tests/unit/test_worker_workspaces.py -q > .sisyphus/evidence/task-10-workspace-discoverability.txt`
    Expected: worker workspace discovery/render tests still pass after installer description alignment
    Evidence: .sisyphus/evidence/task-10-workspace-discoverability.txt

  Scenario: Installer/docs no longer imply registry descriptions are routing truth
    Tool: Bash
    Steps: run `grep -n "description\|source of truth\|non-authoritative" src/openclaw_enhance/install/installer.py docs/install.md > .sisyphus/evidence/task-10-installer-alignment.txt`
    Expected: installer/docs language is minimal and does not claim dispatch authority over worker manifests
    Evidence: .sisyphus/evidence/task-10-installer-alignment.txt
  ```

  **Commit**: YES | Message: `chore(install): demote registry descriptions from routing truth` | Files: `src/openclaw_enhance/install/installer.py`, `docs/install.md`, `tests/unit/test_worker_workspaces.py`

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [ ] F1. Plan Compliance Audit - oracle

  **What to do**: Verify the final change set matches this plan only: frontmatter lives in worker `AGENTS.md`, discovery stays orchestrator-local, `oe-worker-dispatch` becomes discovery-first, `TOOLS.md` remains exact-tool truth, and no new manifest or transport is introduced.
  **Verification**:
  - [ ] `grep -q "schema_version:" workspaces/oe-searcher/AGENTS.md workspaces/oe-syshelper/AGENTS.md workspaces/oe-script_coder/AGENTS.md workspaces/oe-watchdog/AGENTS.md workspaces/oe-tool-recovery/AGENTS.md` exits `0`
  - [ ] `grep -q "discover worker manifests" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` exits `0`
  - [ ] `! grep -R "agent-manifest" workspaces src docs tests --include='*.md' --include='*.py'` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Compliance scan across worker manifests and dispatch contract
    Tool: Bash
    Steps: run `grep -n "schema_version:\|routing:\|discover worker manifests\|least-privilege" workspaces/oe-*/AGENTS.md workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md > .sisyphus/evidence/f1-dynamic-discovery-compliance.txt`
    Expected: built-in workers expose frontmatter and dispatch contract documents discovery-first ranking
    Evidence: .sisyphus/evidence/f1-dynamic-discovery-compliance.txt

  Scenario: Forbidden manifest drift was not introduced
    Tool: Bash
    Steps: run `! grep -R "agent-manifest\|dispatch_task(" workspaces src docs tests --include='*.md' --include='*.py' > .sisyphus/evidence/f1-dynamic-discovery-banned.txt`
    Expected: no separate manifest file pattern and no banned custom dispatcher references appear
    Evidence: .sisyphus/evidence/f1-dynamic-discovery-banned.txt
  ```

  **Pass Condition**: Plan surfaces exist, worker discovery is frontmatter-driven, and no forbidden routing/runtime drift appears.

- [ ] F2. Code Quality Review - unspecified-high

  **What to do**: Review schema/parser utilities, worker manifest edits, dispatch-contract changes, and tests for determinism, least-privilege behavior, and drift prevention.
  **Verification**:
  - [ ] `pytest tests/unit/test_agent_catalog.py tests/unit/test_worker_workspaces.py tests/integration/test_orchestrator_dispatch_contract.py tests/integration/test_worker_role_boundaries.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-workspace oe-tool-recovery` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Focused quality suite passes together
    Tool: Bash
    Steps: run `pytest tests/unit/test_agent_catalog.py tests/unit/test_worker_workspaces.py tests/integration/test_orchestrator_dispatch_contract.py tests/integration/test_worker_role_boundaries.py -q > .sisyphus/evidence/f2-dynamic-discovery-quality.txt`
    Expected: parser, render, boundary, and dispatch tests pass without fixture or wording conflicts
    Evidence: .sisyphus/evidence/f2-dynamic-discovery-quality.txt

  Scenario: Render path still works with frontmatter-bearing AGENTS files
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli render-workspace oe-tool-recovery > .sisyphus/evidence/f2-dynamic-discovery-render.txt`
    Expected: rendered workspace includes frontmatter and body content without parse or formatting failures
    Evidence: .sisyphus/evidence/f2-dynamic-discovery-render.txt
  ```

  **Pass Condition**: Tests pass, frontmatter-rich workspaces render correctly, and no ranking/authority contradictions remain.

- [ ] F3. Agent-Executed Render QA - unspecified-high

  **What to do**: Inspect rendered orchestrator and worker workspaces to confirm discovery-first routing is understandable from user-facing output and that frontmatter remains readable.
  **Verification**:
  - [ ] `python -m openclaw_enhance.cli render-workspace oe-orchestrator` exits `0`
  - [ ] `python -m openclaw_enhance.cli render-workspace oe-searcher` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Orchestrator render exposes discovery-first dispatch
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli render-workspace oe-orchestrator > .sisyphus/evidence/f3-dynamic-discovery-orchestrator.txt && grep -n "discover worker manifests\|least-privilege\|catalog\|ineligible" .sisyphus/evidence/f3-dynamic-discovery-orchestrator.txt > .sisyphus/evidence/f3-dynamic-discovery-orchestrator-scan.txt`
    Expected: render clearly shows discovery-first dispatch flow and deterministic ranking rules
    Evidence: .sisyphus/evidence/f3-dynamic-discovery-orchestrator-scan.txt

  Scenario: Worker render exposes frontmatter without hiding human-readable boundaries
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli render-workspace oe-searcher > .sisyphus/evidence/f3-dynamic-discovery-worker.txt && grep -n "schema_version:\|routing:\|## Role\|## Constraints" .sisyphus/evidence/f3-dynamic-discovery-worker.txt > .sisyphus/evidence/f3-dynamic-discovery-worker-scan.txt`
    Expected: both machine-readable frontmatter and human-readable boundary sections are visible
    Evidence: .sisyphus/evidence/f3-dynamic-discovery-worker-scan.txt
  ```

  **Pass Condition**: Rendered outputs communicate the new routing model clearly and preserve worker boundary readability.

- [ ] F4. Scope Fidelity Check - deep

  **What to do**: Verify the design stayed narrow: no new manifest file, no persistent cache, no transport/runtime rewrite, no worker authority expansion, and main routing still escalates only to orchestrator.
  **Verification**:
  - [ ] `python - <<'PY'
from pathlib import Path
blob = '\n'.join([
    Path('skills/oe-toolcall-router/SKILL.md').read_text(encoding='utf-8'),
    Path('workspaces/oe-orchestrator/AGENTS.md').read_text(encoding='utf-8'),
    Path('workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md').read_text(encoding='utf-8'),
])
assert 'oe-orchestrator' in blob
assert 'sessions_spawn' in blob and 'announce' in blob
assert 'agent-manifest' not in blob
assert 'persistent cache' not in blob.lower()
print('dynamic-discovery-scope-ok')
PY` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Scope script proves no architecture drift
    Tool: Bash
    Steps: run the verification script above and save stdout to `.sisyphus/evidence/f4-dynamic-discovery-scope.txt`
    Expected: script prints `dynamic-discovery-scope-ok`
    Evidence: .sisyphus/evidence/f4-dynamic-discovery-scope.txt

  Scenario: Docs alignment still passes after source-of-truth shift
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli docs-check > .sisyphus/evidence/f4-dynamic-discovery-docs-check.txt`
    Expected: docs-check passes with no banned transport/runtime terminology
    Evidence: .sisyphus/evidence/f4-dynamic-discovery-docs-check.txt
  ```

  **Pass Condition**: The finished design remains skill-first, native, bounded, and least-privilege, with no new manifest or cache subsystem.

## Commit Strategy
- Keep schema/parser foundation separate from worker manifest population.
- Keep dispatch-contract changes separate from parser utilities so behavior shifts are reviewable.
- Keep docs-check/validator guardrails separate from durable docs wording when practical.
- Keep final docs and registry-alignment updates after contract/tests stabilize.

## Success Criteria
- Built-in workers advertise routing metadata from `AGENTS.md` frontmatter and pass schema validation.
- Orchestrator dispatch contract explicitly discovers worker manifests before ranking candidates.
- Least-privilege deterministic ranking is documented and regression-tested.
- `TOOLS.md` remains exact-tool truth; frontmatter remains routing-only abstraction.
- Docs, render behavior, and validation commands stay aligned with the new source-of-truth model.
