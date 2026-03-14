# Repo-Wide Real-Environment Coverage Backfill

## TL;DR
> **Summary**: Backfill real-environment coverage for every shipped capability currently present on this branch by creating a canonical shipped-feature coverage matrix, repairing the live `validate-feature` contract drift, strengthening thin bundle implementations, and generating durable passing reports under `docs/reports/` against one prepared harness-backed `~/.openclaw` target.
> **Deliverables**:
> - Shipped-feature coverage matrix in `docs/testing-playbook.md` mapping every delivered capability to canonical real-environment scenarios and report slugs
> - Normalized `validate-feature` contract (`--feature-class` + `--report-slug`) across CLI, docs, and checks
> - Strengthened validation framework/bundles for install lifecycle, dev install mode, CLI surface, orchestrator/yield routing, recovery worker, and watchdog reminder delivery
> - Harness/integration support that captures deterministic live evidence without creating a second CI system
> - Durable PASS reports in `docs/reports/` for all current-branch shipped capability groups
> **Effort**: XL
> **Parallel**: YES - 3 waves
> **Critical Path**: 1 -> 2 -> 3 -> 4 -> 7 -> 9 -> 10

## Context
### Original Request
- "现在再给之前这个项目开发的所有功能都建立实际环境的测试用例（要完整描述方法）"

### Interview Summary
- Scope is the **full shipped set currently present on this branch**, not only the milestones already recorded in `docs/opencode-iteration-handbook.md`.
- Coverage granularity is a **shipped-feature coverage matrix mapped onto shared executable bundles/reports**, not one report per micro-capability and not only coarse feature-class bundles.
- The first backfill pass must include **full runtime-watchdog reminder delivery proof**, not just state confirmation.
- Existing validation infrastructure (`validate-feature`, harness E2E, `docs/reports/`) must be reused; the work must not turn into a second CI system or an OpenClaw-core change.
- The canonical live target is one prepared harness-backed `~/.openclaw`, because the existing install-lifecycle failure shows arbitrary homes are too unstable for trustworthy first-pass backfill.

### Metis Review (gaps addressed)
- Treat the coverage unit as shipped milestone/capability mapped onto existing feature classes; do not invent a new reporting taxonomy for every sub-behavior.
- Repair contract drift before expanding scope: durable docs currently advertise `validate-feature --class ...`, while the live CLI requires `--feature-class` and `--report-slug`.
- Strengthen thin live bundles instead of assuming the docs are already true. Current `workspace-routing` and `runtime-watchdog` bundles are too shallow to prove shipped behavior.
- Include an explicit harness-readiness step because the current `install-lifecycle` report failed on missing `VERSION` under `~/.openclaw`.
- Resolve the watchdog authority/tool mismatch as part of the first pass because the user chose end-to-end reminder delivery, not state-only proof.

## Work Objectives
### Core Objective
Create a decision-complete, repo-owned real-environment backfill workflow that maps every shipped current-branch capability to one or more exact live scenarios, executes those scenarios through the existing validation framework against a prepared harness-backed `~/.openclaw`, and leaves durable PASS reports under `docs/reports/`.

### Deliverables
- Expanded `docs/testing-playbook.md` with a shipped-feature inventory, coverage matrix, canonical report slugs, exact methods, and evidence expectations
- Contract-aligned docs/examples/checks using `validate-feature --feature-class ... --report-slug ...`
- Validation framework updates that encode milestone-to-scenario mappings, harness readiness, cleanup verification, and stronger bundles
- Strengthened live scenarios for:
  - standard install lifecycle
  - `install --dev` symlink mode
  - CLI surface and validator self-surface
  - orchestrator routing + bounded-loop/yield evidence
  - recovery-worker invocation on a representative real failure
  - watchdog end-to-end reminder delivery
- Durable PASS reports for canonical backfill slugs:
  - `backfill-core-install`
  - `backfill-dev-install`
  - `backfill-cli-surface`
  - `backfill-routing-yield`
  - `backfill-recovery-worker`
  - `backfill-watchdog-reminder`
- Handbook/workflow updates recording the backfill as durable project state

### Definition of Done (verifiable conditions with commands)
- `grep -R "validate-feature --class" AGENTS.md docs tests --include='*.md' --include='*.py'` returns no matches
- `pytest tests/unit/test_real_env_validation.py tests/unit/test_real_env_guardrails.py tests/unit/test_real_env_runner.py tests/unit/test_validation_matrix.py -q` exits `0`
- `pytest tests/integration/test_validation_real_env.py tests/integration/test_install_uninstall.py tests/integration/test_dev_mode_integration.py tests/integration/test_orchestrator_dispatch_contract.py tests/integration/test_timeout_flow.py -q` exits `0`
- `OPENCLAW_HARNESS=1 pytest tests/e2e/test_openclaw_harness.py -k "real_env or recovery or watchdog" -q` exits `0` in a prepared harness environment
- `python -m openclaw_enhance.cli docs-check` exits `0`
- `ls docs/reports/*-backfill-core-install-install-lifecycle.md docs/reports/*-backfill-dev-install-install-lifecycle.md docs/reports/*-backfill-cli-surface-cli-surface.md docs/reports/*-backfill-routing-yield-workspace-routing.md docs/reports/*-backfill-recovery-worker-workspace-routing.md docs/reports/*-backfill-watchdog-reminder-runtime-watchdog.md` exits `0`
- `grep -R "Conclusion: PASS" docs/reports/*-backfill-*.md` returns six matches
- `grep -q "Current branch shipped set" docs/testing-playbook.md` exits `0`

### Must Have
- One canonical shipped-feature inventory covering handbook milestones plus delivered branch capabilities such as `install --dev`
- One prepared harness-backed `~/.openclaw` contract with explicit readiness checks and no OpenClaw core edits
- Existing feature classes retained as the reporting surface; backfill happens by mapping capabilities to those classes
- End-to-end proof for watchdog reminder delivery using observable session/runtime evidence
- Explicit recovery-worker coverage triggered by an actual representative failure path, not mocked failure text
- Cleanup verification actually enforced after install-lifecycle scenarios
- Durable PASS reports committed for every canonical backfill slug

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No new CI system, pytest plugin, or GitHub Actions redesign
- No OpenClaw core code edits or runtime mutation of main OpenClaw docs/config outside supported CLI/install surfaces
- No new feature classes for individual milestones or sub-behaviors
- No placeholder/manual-only scenarios without exact commands, expected proof, and evidence paths
- No watchdog authority expansion beyond what is required to make existing documented reminder delivery real and testable
- No fake coverage via brittle ad-hoc log scraping when an existing session/report/runtime artifact can prove behavior
- No branch-wide OS/version matrix expansion in this pass; use one canonical supported harness environment

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after on top of the existing validator, harness, and pytest suites
- QA policy: every task must update both executable coverage and the durable method description/source-of-truth that explains it
- Evidence:
  - durable validation reports: `docs/reports/*.md`
  - task QA artifacts: `.sisyphus/evidence/task-{N}-{slug}.txt`
  - harness/session artifacts: `.sisyphus/evidence/task-{N}-{slug}.{txt,json,md}` as specified per task

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: contract + matrix foundation (`1`, `2`, `3`, `4`)
Wave 2: bundle-strengthening and runtime proof (`5`, `6`, `7`, `8`, `9`)
Wave 3: harness execution, durable report generation, and workflow state updates (`10`, `11`)

### Dependency Matrix (full, all tasks)
- `1` blocks `2`, `3`, `4`, `10`, `11`
- `2` blocks `3`, `5`, `6`, `7`, `8`, `9`, `10`, `11`
- `3` blocks `4`, `5`, `6`, `7`, `8`, `9`, `10`
- `4` blocks `5`, `6`, `7`, `8`, `9`, `10`
- `5` blocks `10`, `11`
- `6` blocks `10`, `11`
- `7` blocks `8`, `10`, `11`
- `8` blocks `10`, `11`
- `9` blocks `10`, `11`
- `10` blocks `11`, Final Verification
- `11` blocks Final Verification

### Agent Dispatch Summary (wave -> task count -> categories)
- Wave 1 -> 4 tasks -> `writing`, `unspecified-high`, `quick`
- Wave 2 -> 5 tasks -> `unspecified-high`, `writing`
- Wave 3 -> 2 tasks -> `unspecified-high`, `writing`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 1. Normalize the live `validate-feature` contract across CLI, docs, and checks

  **What to do**: Update every durable example, checklist, and verification command to use the real CLI surface: `validate-feature --feature-class <class> --report-slug <slug>`. Add or tighten `docs-check` assertions so `--class` no longer survives in `AGENTS.md`, `docs/install.md`, `docs/operations.md`, or any canonical examples. Ensure all examples also show canonical slugs for the backfill workflow rather than placeholder prose.
  **Must NOT do**: Do not add backward-compatibility aliases for `--class`. Do not leave any durable doc on the old syntax.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: this is mostly contract and source-of-truth repair across durable docs/checks
  - Skills: [`writing-plans`] — why: the command contract must be exact and consistent everywhere
  - Omitted: [`test-driven-development`] — why not needed: the main risk is contract drift, not novel business logic

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2, 3, 4, 10, 11 | Blocked By: none

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/cli.py:436` — live `validate-feature` command signature with `--feature-class` and `--report-slug`
  - Drift: `AGENTS.md:90` — mandatory checklist still references `--class`
  - Drift: `docs/install.md:41` — install verification example still references `--class`
  - Drift: `docs/install.md:374` — install verification checklist still references `--class`
  - Drift: `docs/operations.md:473` — real-environment examples still reference `--class`
  - Test: `tests/unit/test_cli_smoke.py:117` — existing CLI smoke pattern for `validate-feature --help`

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -R "validate-feature --class" AGENTS.md docs tests --include='*.md' --include='*.py'` returns no matches
  - [ ] `python -m openclaw_enhance.cli validate-feature --help | grep -q -- "--feature-class"` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Durable docs use only the live validator contract
    Tool: Bash
    Steps: run `grep -R "validate-feature --class\|validate-feature --feature-class" AGENTS.md docs tests --include='*.md' --include='*.py' > .sisyphus/evidence/task-1-validator-contract.txt`
    Expected: evidence contains only `--feature-class` usages in durable examples and no surviving `--class` contract drift
    Evidence: .sisyphus/evidence/task-1-validator-contract.txt

  Scenario: docs-check enforces the repaired command surface
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli docs-check > .sisyphus/evidence/task-1-docs-check.txt`
    Expected: docs-check passes after the contract repair
    Evidence: .sisyphus/evidence/task-1-docs-check.txt
  ```

  **Commit**: YES | Message: `docs(validation): normalize validate-feature contract` | Files: `AGENTS.md`, `docs/install.md`, `docs/operations.md`, `tests/unit/test_docs_examples.py`, `src/openclaw_enhance/cli.py` (if docs-check needs tightening)

- [x] 2. Expand `docs/testing-playbook.md` into the shipped-feature coverage matrix and method source of truth

  **What to do**: Rewrite the playbook so it no longer stops at feature classes. Add a “Current branch shipped set” inventory that covers the handbook milestones plus delivered branch capabilities like `install --dev`. For each shipped capability/milestone, record: mapped feature class, canonical scenario slug(s), exact commands, required observable proof, report path, and whether the scenario is expected to produce a PASS or EXEMPT report. Explicitly map these canonical slugs: `backfill-core-install`, `backfill-dev-install`, `backfill-cli-surface`, `backfill-routing-yield`, `backfill-recovery-worker`, and `backfill-watchdog-reminder`.
  **Must NOT do**: Do not create new feature classes. Do not keep the matrix only in `.sisyphus/` or only in comments/tests.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: this task establishes the durable inventory and method contract that all execution follows
  - Skills: [`writing-plans`] — why: the matrix must be precise enough that implementers make zero judgment calls
  - Omitted: [`test-driven-development`] — why not needed: the primary output is durable documentation and mapping clarity

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 3, 5, 6, 7, 8, 9, 10, 11 | Blocked By: 1

  **References** (executor has NO interview context — be exhaustive):
  - Source of truth: `docs/opencode-iteration-handbook.md:164` — completed milestones already recorded durably
  - Delivered branch capability: `.sisyphus/plans/dev-install-mode.md:1` — dev install mode exists and must be covered even though not in the handbook yet
  - Current playbook: `docs/testing-playbook.md:5` — existing feature-class-only structure that must be expanded
  - Existing failed evidence: `docs/reports/2026-03-14-harness-test-install-lifecycle.md:41` — shows why harness readiness must be part of the documented method
  - Bundle implementation: `src/openclaw_enhance/validation/types.py:89` — current live bundle definitions are thinner than the documented matrix needs
  - Harness anchor: `tests/e2e/test_openclaw_harness.py:424` — current real-environment smoke already uses `validate-feature`

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -q "Current branch shipped set" docs/testing-playbook.md` exits `0`
  - [ ] `grep -q "backfill-dev-install" docs/testing-playbook.md` exits `0`
  - [ ] `grep -q "backfill-watchdog-reminder" docs/testing-playbook.md` exits `0`
  - [ ] `grep -q "install --dev" docs/testing-playbook.md` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Playbook now maps every shipped capability to canonical scenarios
    Tool: Bash
    Steps: run `grep -n "Current branch shipped set\|backfill-core-install\|backfill-dev-install\|backfill-cli-surface\|backfill-routing-yield\|backfill-recovery-worker\|backfill-watchdog-reminder" docs/testing-playbook.md > .sisyphus/evidence/task-2-coverage-matrix.txt`
    Expected: evidence shows the shipped-set inventory and all six canonical backfill slugs in the playbook
    Evidence: .sisyphus/evidence/task-2-coverage-matrix.txt

  Scenario: Playbook contains exact methods, not vague prose
    Tool: Bash
    Steps: run `grep -n "--feature-class\|docs/reports/\|Observable proof\|Expected conclusion" docs/testing-playbook.md > .sisyphus/evidence/task-2-method-contract.txt`
    Expected: evidence shows concrete commands, report locations, and proof expectations for the matrix
    Evidence: .sisyphus/evidence/task-2-method-contract.txt
  ```

  **Commit**: YES | Message: `docs(testing): add shipped-feature coverage matrix` | Files: `docs/testing-playbook.md`

- [x] 3. Encode the shipped-feature coverage matrix in the validation framework

  **What to do**: Add a focused validation matrix/catalog module that mirrors the playbook in code. It must declare the shipped capability groups, canonical slugs, target feature class, required observable evidence kind, and report expectations. Use it as the single code-side source for the backfill instead of hard-coding bundle behavior only in `types.py`. Add unit coverage that proves every shipped capability maps to at least one canonical scenario and that the documented slugs are complete.
  **Must NOT do**: Do not infer coverage from git diff. Do not create a second unrelated reporting abstraction that disagrees with the playbook.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: this is the code-side source of truth that binds documentation to executable behavior
  - Skills: [`test-driven-development`] — why: matrix completeness and mapping invariants should be pinned before bundle changes land
  - Omitted: [`writing-plans`] — why not needed: this is a Python contract/module task

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 4, 5, 6, 7, 8, 9, 10 | Blocked By: 1, 2

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/validation/types.py:89` — current bundle mapping entry point that will need to delegate or align with a richer catalog
  - Pattern: `src/openclaw_enhance/validation/reporting.py` — durable report schema that the matrix must target
  - Pattern: `src/openclaw_enhance/agent_catalog.py` — existing repo pattern for declarative catalogs/validation
  - Source of truth: `docs/testing-playbook.md` — shipped-feature coverage matrix from Task 2
  - Test style: `tests/unit/test_real_env_validation.py` — validation enums/path-convention test patterns

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_validation_matrix.py -q` exits `0`
  - [ ] `python - <<'PY'
from openclaw_enhance.validation.matrix import SHIPPED_CAPABILITY_MATRIX
required = {
    'backfill-core-install',
    'backfill-dev-install',
    'backfill-cli-surface',
    'backfill-routing-yield',
    'backfill-recovery-worker',
    'backfill-watchdog-reminder',
}
assert required.issubset({item.slug for item in SHIPPED_CAPABILITY_MATRIX})
print('validation-matrix-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Validation matrix covers all canonical backfill slugs
    Tool: Bash
    Steps: run `pytest tests/unit/test_validation_matrix.py -q > .sisyphus/evidence/task-3-validation-matrix-unit.txt`
    Expected: unit tests prove matrix completeness and capability-to-scenario mappings
    Evidence: .sisyphus/evidence/task-3-validation-matrix-unit.txt

  Scenario: Matrix module is importable and exposes the required slug set
    Tool: Bash
    Steps: run the acceptance Python snippet above and save stdout to `.sisyphus/evidence/task-3-validation-matrix-import.txt`
    Expected: snippet prints `validation-matrix-ok`
    Evidence: .sisyphus/evidence/task-3-validation-matrix-import.txt
  ```

  **Commit**: YES | Message: `feat(validation): add shipped-feature coverage matrix` | Files: `src/openclaw_enhance/validation/matrix.py`, `src/openclaw_enhance/validation/__init__.py`, `tests/unit/test_validation_matrix.py`, `src/openclaw_enhance/validation/types.py`

- [x] 4. Upgrade guardrails and runner semantics for canonical harness readiness, cleanup enforcement, and explicit exemptions

  **What to do**: Strengthen the validator so the first-pass backfill can trust its evidence. Add explicit readiness checks for the canonical harness target (`~/.openclaw` VERSION/config/basic OpenClaw home shape), wire the runner to actually use cleanup verification after install-lifecycle scenarios, and make `docs-test-only` semantics explicit by deciding whether it records docs-check evidence while still concluding `EXEMPT`. Ensure failure reports distinguish harness-readiness failures from product failures before any bundle-specific work begins.
  **Must NOT do**: Do not broaden support to arbitrary homes or multi-version matrix testing. Do not leave cleanup verification dormant in `guardrails.py`.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: this is the safety-critical contract that all live scenarios depend on
  - Skills: [`test-driven-development`] — why: readiness and cleanup behavior must be locked down before heavier live scenarios are added
  - Omitted: [`systematic-debugging`] — why not needed: this is contract strengthening, not root-cause triage

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 5, 6, 7, 8, 9, 10 | Blocked By: 1, 3

  **References** (executor has NO interview context — be exhaustive):
  - Risk evidence: `docs/reports/2026-03-14-harness-test-install-lifecycle.md:41` — current install-lifecycle failure from missing VERSION in `~/.openclaw`
  - Pattern: `src/openclaw_enhance/validation/guardrails.py:35` — baseline capture entry point
  - Gap: `src/openclaw_enhance/validation/guardrails.py:149` — cleanup verification exists but is not used by the runner yet
  - Gap: `src/openclaw_enhance/validation/runner.py:84` — `docs-test-only` exits as EXEMPT without recorded docs-check execution
  - Runner: `src/openclaw_enhance/validation/runner.py:67` — orchestration entry point for readiness/cleanup enforcement
  - Integration coverage: `tests/integration/test_validation_real_env.py` — validator integration tests that should pin new semantics

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_real_env_guardrails.py tests/unit/test_real_env_runner.py tests/integration/test_validation_real_env.py -q` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
from openclaw_enhance.validation.guardrails import capture_baseline_state
state = capture_baseline_state(Path.home() / '.openclaw')
assert hasattr(state, 'openclaw_home')
print('guardrails-ready-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Guardrails and runner agree on readiness and cleanup semantics
    Tool: Bash
    Steps: run `pytest tests/unit/test_real_env_guardrails.py tests/unit/test_real_env_runner.py tests/integration/test_validation_real_env.py -q > .sisyphus/evidence/task-4-guardrails-runner.txt`
    Expected: test suites pass with explicit readiness, cleanup, and exemption behavior
    Evidence: .sisyphus/evidence/task-4-guardrails-runner.txt

  Scenario: Canonical harness baseline inspection remains non-mutating
    Tool: Bash
    Steps: run the acceptance Python snippet above and save stdout to `.sisyphus/evidence/task-4-harness-readiness.txt`
    Expected: snippet prints `guardrails-ready-ok`
    Evidence: .sisyphus/evidence/task-4-harness-readiness.txt
  ```

  **Commit**: YES | Message: `feat(validation): enforce harness readiness and cleanup` | Files: `src/openclaw_enhance/validation/guardrails.py`, `src/openclaw_enhance/validation/runner.py`, `tests/unit/test_real_env_guardrails.py`, `tests/unit/test_real_env_runner.py`, `tests/integration/test_validation_real_env.py`

- [x] 5. Expand the install-lifecycle bundle to cover both core install flow and `--dev` symlink mode

  **What to do**: Strengthen the install-lifecycle real-environment bundle so it proves the shipped installer surface, not just a bare install/uninstall smoke. The bundle must cover: standard install, status/doctor after install, main-skill sync visibility, cleanup symmetry, and a dedicated `--dev` subscenario proving symlink-based install behavior. Use the coverage matrix slugs `backfill-core-install` and `backfill-dev-install`; keep them under the existing `install-lifecycle` feature class, not a new class.
  **Must NOT do**: Do not split `--dev` into a new feature class. Do not treat uninstall success alone as proof that install lifecycle is covered.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: install lifecycle touches the canonical live target and must prove both normal and dev flows safely
  - Skills: [`test-driven-development`] — why: install/dev-mode scenario expansion needs strong regression coverage before live execution
  - Omitted: [`systematic-debugging`] — why not needed: this is planned bundle expansion, not a bug hunt

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 10, 11 | Blocked By: 2, 3, 4

  **References** (executor has NO interview context — be exhaustive):
  - Bundle baseline: `src/openclaw_enhance/validation/types.py:92` — current install-lifecycle bundle is too thin for shipped coverage
  - Delivered feature: `.sisyphus/plans/dev-install-mode.md:48` — `--dev` is a delivered install capability that must be backfilled
  - Docs: `docs/install.md:197` — durable dev-mode documentation already exists
  - Existing tests: `tests/integration/test_dev_mode_integration.py` — current integration coverage for dev mode
  - Existing tests: `tests/integration/test_install_uninstall.py` — lifecycle symmetry patterns to mirror in live scenarios
  - Existing failed report: `docs/reports/2026-03-14-harness-test-install-lifecycle.md` — evidence of what the current live bundle misses

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/integration/test_install_uninstall.py tests/integration/test_dev_mode_integration.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class install-lifecycle --report-slug backfill-core-install --openclaw-home "$HOME/.openclaw"` exits `0` in the prepared harness environment
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class install-lifecycle --report-slug backfill-dev-install --openclaw-home "$HOME/.openclaw"` exits `0` in the prepared harness environment

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Core install lifecycle produces a PASS report
    Tool: Bash
    Steps: run the `backfill-core-install` validation command above in the prepared harness environment and save combined output to `.sisyphus/evidence/task-5-core-install.txt`
    Expected: command exits `0` and writes `docs/reports/*-backfill-core-install-install-lifecycle.md` with `Conclusion: PASS`
    Evidence: .sisyphus/evidence/task-5-core-install.txt

  Scenario: Dev install mode proves symlink behavior in real environment
    Tool: Bash
    Steps: run the `backfill-dev-install` validation command above in the prepared harness environment, then inspect the resulting report and managed root layout into `.sisyphus/evidence/task-5-dev-install.txt`
    Expected: report concludes PASS and evidence confirms symlink-based install behavior rather than copied workspaces
    Evidence: .sisyphus/evidence/task-5-dev-install.txt
  ```

  **Commit**: YES | Message: `feat(validation): backfill install lifecycle coverage` | Files: `src/openclaw_enhance/validation/types.py`, `src/openclaw_enhance/validation/matrix.py`, `tests/integration/test_install_uninstall.py`, `tests/integration/test_dev_mode_integration.py`, `docs/testing-playbook.md`

- [x] 6. Expand the CLI-surface bundle to cover the user-facing command surface and validator self-surface

  **What to do**: Strengthen the `cli-surface` bundle so it proves the delivered CLI surface, not just rendering smoke. The real-environment scenario must validate status output, doctor behavior, render commands, docs-check, and at least one validator self-surface check showing that `validate-feature` itself produces the documented report contract. Use canonical slug `backfill-cli-surface` and record explicit output expectations in the playbook/matrix.
  **Must NOT do**: Do not rely on unit smoke tests alone. Do not treat help output as sufficient proof of the shipped CLI surface.

  **Recommended Agent Profile**:
  - Category: `quick` — Reason: mostly command-surface strengthening with existing CLI/test patterns
  - Skills: [`test-driven-development`] — why: command ordering and output expectations should be regression-tested first
  - Omitted: [`writing-plans`] — why not needed: this is executable surface work, not a prose-only task

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 10, 11 | Blocked By: 2, 3, 4

  **References** (executor has NO interview context — be exhaustive):
  - Bundle baseline: `src/openclaw_enhance/validation/types.py:99` — current CLI surface bundle only covers a subset of shipped commands
  - Live CLI: `src/openclaw_enhance/cli.py` — current commands include install/uninstall/doctor/status/render/docs-check/validate-feature
  - Existing tests: `tests/unit/test_cli_smoke.py` — command availability coverage
  - Existing tests: `tests/integration/test_status_command.py` — integration pattern for CLI output checks
  - Docs drift repair: `AGENTS.md:92`, `docs/install.md:41`, `docs/operations.md:473` — now-correct contract examples that the live bundle should match

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_cli_smoke.py tests/integration/test_status_command.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class cli-surface --report-slug backfill-cli-surface --openclaw-home "$HOME/.openclaw"` exits `0` in the prepared harness environment
  - [ ] `grep -q "Conclusion: PASS" docs/reports/*-backfill-cli-surface-cli-surface.md` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: CLI surface bundle proves command outputs in the harness environment
    Tool: Bash
    Steps: run the `backfill-cli-surface` validation command above and save combined output to `.sisyphus/evidence/task-6-cli-surface.txt`
    Expected: command exits `0` and writes a PASS report covering status/doctor/render/docs-check/validator surface expectations
    Evidence: .sisyphus/evidence/task-6-cli-surface.txt

  Scenario: Durable report contains the documented CLI contract sections
    Tool: Bash
    Steps: run `grep -n "Feature Class\|Conclusion\|Command 1\|Command 2" docs/reports/*-backfill-cli-surface-cli-surface.md > .sisyphus/evidence/task-6-cli-report.txt`
    Expected: report contains the required schema and command evidence sections
    Evidence: .sisyphus/evidence/task-6-cli-report.txt
  ```

  **Commit**: YES | Message: `feat(validation): backfill cli surface coverage` | Files: `src/openclaw_enhance/validation/types.py`, `src/openclaw_enhance/validation/matrix.py`, `tests/unit/test_cli_smoke.py`, `tests/integration/test_status_command.py`, `docs/testing-playbook.md`

- [x] 7. Expand workspace-routing coverage to prove worker discovery, orchestrator routing, and bounded-loop/yield behavior

  **What to do**: Strengthen `workspace-routing` so it covers the actual shipped routing stack: worker frontmatter discovery, `oe-orchestrator` selection for complex tasks, and observable proof that bounded orchestration/yield behavior is occurring. Use canonical slug `backfill-routing-yield`. The scenario must prove more than “agent list contains names”; it needs an observable artifact such as session transcript content or durable harness evidence that complex routing reached `oe-orchestrator` and exercised the bounded-loop/yield path.
  **Must NOT do**: Do not introduce undocumented OpenClaw commands. Do not claim `sessions_yield` proof from static docs alone.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: this is the core runtime behavior of the system and needs careful observable proof design
  - Skills: [`test-driven-development`] — why: routing evidence must be pinned in harness/integration tests before live execution
  - Omitted: [`systematic-debugging`] — why not needed: the task is expanding proof depth, not investigating a failure first

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8, 10, 11 | Blocked By: 2, 3, 4

  **References** (executor has NO interview context — be exhaustive):
  - Architecture: `docs/opencode-iteration-handbook.md:11` — bounded multi-round orchestration with native `sessions_yield`
  - Worker source of truth: `docs/opencode-iteration-handbook.md:48` — frontmatter-driven worker discovery
  - Bundle baseline: `src/openclaw_enhance/validation/types.py:105` — current routing bundle is only agent list + chat smoke
  - Orchestrator contract: `workspaces/oe-orchestrator/AGENTS.md:76` — loop/yield behavior described in workspace source of truth
  - Dispatch contract: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md:200` — yield-for-results semantics and recovery branch
  - Existing tests: `tests/integration/test_orchestrator_dispatch_contract.py` — current routing/yield/recovery assertions
  - Existing harness anchor: `tests/e2e/test_openclaw_harness.py:424` — existing real-environment validator smoke entry point

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/integration/test_orchestrator_dispatch_contract.py tests/integration/test_worker_role_boundaries.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class workspace-routing --report-slug backfill-routing-yield --openclaw-home "$HOME/.openclaw"` exits `0` in the prepared harness environment
  - [ ] `grep -q "oe-orchestrator" docs/reports/*-backfill-routing-yield-workspace-routing.md` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Routing/yield bundle proves orchestrator escalation in a real environment
    Tool: Bash
    Steps: run the `backfill-routing-yield` validation command above and save combined output plus any captured session/transcript evidence to `.sisyphus/evidence/task-7-routing-yield.txt`
    Expected: command exits `0`, report concludes PASS, and evidence shows the task escalated to `oe-orchestrator` with bounded-loop/yield proof
    Evidence: .sisyphus/evidence/task-7-routing-yield.txt

  Scenario: Durable report records the observable routing proof source
    Tool: Bash
    Steps: run `grep -n "oe-orchestrator\|sessions_yield\|auto-announced\|Observable proof" docs/reports/*-backfill-routing-yield-workspace-routing.md > .sisyphus/evidence/task-7-routing-report.txt`
    Expected: report explicitly names the routing/yield proof source rather than only listing static commands
    Evidence: .sisyphus/evidence/task-7-routing-report.txt
  ```

  **Commit**: YES | Message: `feat(validation): backfill routing and yield coverage` | Files: `src/openclaw_enhance/validation/types.py`, `src/openclaw_enhance/validation/matrix.py`, `tests/integration/test_orchestrator_dispatch_contract.py`, `tests/e2e/test_openclaw_harness.py`, `docs/testing-playbook.md`

- [x] 8. Add a real-environment recovery-worker scenario that proves `oe-tool-recovery` dispatch on the documented legacy-`websearch` failure

  **What to do**: Add a dedicated canonical scenario `backfill-recovery-worker` under `workspace-routing` that intentionally triggers the documented recovery example where a worker attempts the legacy tool name `websearch` and receives `tool 'websearch' not found`, after which `oe-tool-recovery` recommends `websearch_web_search_exa`. The scenario must prove the orchestrator dispatches `oe-tool-recovery`, waits for the recovery suggestion, and records observable evidence of that recovery path. Prefer this one deterministic, repeatable failure mode over broad combinatorial coverage.
  **Must NOT do**: Do not mock the failure path in the live scenario. Do not test every recovery mode.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: recovery proof needs a careful real failure trigger without destabilizing the harness environment
  - Skills: [`test-driven-development`] — why: deterministic recovery evidence should be codified in tests before live backfill execution
  - Omitted: [`systematic-debugging`] — why not needed: the task intentionally creates a controlled failure path

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 10, 11 | Blocked By: 2, 3, 4, 7

  **References** (executor has NO interview context — be exhaustive):
  - Milestone: `docs/opencode-iteration-handbook.md:177` — tool-failure-recovery-worker completed milestone
  - Recovery contract: `src/openclaw_enhance/runtime/recovery_contract.py` — shared recovery result contract
  - Dispatch contract: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md:231` — documented recovery path
  - Exact failure to use: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md:256` — legacy `websearch` tool-not-found recovery example
  - Existing tests: `tests/integration/test_orchestrator_dispatch_contract.py:340` — current integration assertions for recovery dispatch
  - Routing evidence: `tests/integration/test_worker_role_boundaries.py` — recovery-worker authority boundaries that must remain intact

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/integration/test_orchestrator_dispatch_contract.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class workspace-routing --report-slug backfill-recovery-worker --openclaw-home "$HOME/.openclaw"` exits `0` in the prepared harness environment
  - [ ] `grep -q "oe-tool-recovery" docs/reports/*-backfill-recovery-worker-workspace-routing.md` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Recovery-worker bundle proves real recovery dispatch
    Tool: Bash
    Steps: run the `backfill-recovery-worker` validation command above and save combined output plus session/transcript evidence to `.sisyphus/evidence/task-8-recovery-worker.txt`
    Expected: command exits `0`, report concludes PASS, and evidence contains both the `websearch` tool-not-found signal and the `oe-tool-recovery` correction path
    Evidence: .sisyphus/evidence/task-8-recovery-worker.txt

  Scenario: Durable report records failure trigger and recovery proof
    Tool: Bash
    Steps: run `grep -n "oe-tool-recovery\|Recovered\|tool failure\|Observable proof" docs/reports/*-backfill-recovery-worker-workspace-routing.md > .sisyphus/evidence/task-8-recovery-report.txt`
    Expected: report documents the legacy `websearch` failure trigger and the `websearch_web_search_exa` recovery evidence
    Evidence: .sisyphus/evidence/task-8-recovery-report.txt
  ```

  **Commit**: YES | Message: `feat(validation): backfill recovery worker coverage` | Files: `src/openclaw_enhance/validation/types.py`, `src/openclaw_enhance/validation/matrix.py`, `tests/integration/test_orchestrator_dispatch_contract.py`, `tests/e2e/test_openclaw_harness.py`, `docs/testing-playbook.md`

- [x] 9. Resolve the watchdog contract mismatch and backfill end-to-end reminder delivery coverage

  **What to do**: Align watchdog’s documented authority and actual tool surface so end-to-end reminder delivery is real, testable, and still within project boundaries. If `session_send` is supposed to be available, expose/document it consistently in `oe-watchdog` contracts; if a different repo-owned path is required, make that path explicit and testable. Then add canonical slug `backfill-watchdog-reminder` under `runtime-watchdog`, proving timeout detection, watchdog activation, reminder delivery, and durable evidence of receipt/logging.
  **Must NOT do**: Do not fake reminder delivery with state-only confirmation. Do not broaden watchdog into a general-purpose worker or add OpenClaw core changes.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: this is the highest-risk contract-alignment task and touches runtime authority boundaries
  - Skills: [`test-driven-development`] — why: tool/authority alignment and end-to-end reminder proof must be pinned with tests before live execution
  - Omitted: [`writing-plans`] — why not needed: implementation and proof depth dominate this task

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 10, 11 | Blocked By: 2, 3, 4

  **References** (executor has NO interview context — be exhaustive):
  - Contract mismatch: `workspaces/oe-watchdog/AGENTS.md:41` — watchdog says reminder delivery uses `session_send`
  - Contract mismatch: `workspaces/oe-watchdog/TOOLS.md:180` — watchdog tool surface currently says `session_send` is not available
  - Runtime modules: `src/openclaw_enhance/watchdog/detector.py`, `src/openclaw_enhance/watchdog/notifier.py`, `src/openclaw_enhance/watchdog/state_sync.py` — runtime-side pieces that must remain authoritative
  - Existing tests: `tests/integration/test_timeout_flow.py` — timeout flow coverage to extend
  - Existing harness gate: `tests/e2e/test_openclaw_harness.py` — place for live reminder-delivery proof
  - Bundle baseline: `src/openclaw_enhance/validation/types.py:109` — current runtime-watchdog bundle is only a config grep and is insufficient

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/integration/test_timeout_flow.py tests/integration/test_worker_role_boundaries.py -q` exits `0`
  - [ ] `OPENCLAW_HARNESS=1 pytest tests/e2e/test_openclaw_harness.py -k watchdog -q` exits `0` in the prepared harness environment
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class runtime-watchdog --report-slug backfill-watchdog-reminder --openclaw-home "$HOME/.openclaw"` exits `0` in the prepared harness environment
  - [ ] `grep -q "Conclusion: PASS" docs/reports/*-backfill-watchdog-reminder-runtime-watchdog.md` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Watchdog bundle proves timeout reminder delivery end to end
    Tool: Bash
    Steps: run the `backfill-watchdog-reminder` validation command above in the prepared harness environment and save combined output plus reminder evidence to `.sisyphus/evidence/task-9-watchdog-reminder.txt`
    Expected: command exits `0`, report concludes PASS, and evidence shows the reminder was delivered and logged
    Evidence: .sisyphus/evidence/task-9-watchdog-reminder.txt

  Scenario: Watchdog contracts and tools are aligned after the fix
    Tool: Bash
    Steps: run `grep -n "session_send" workspaces/oe-watchdog/AGENTS.md workspaces/oe-watchdog/TOOLS.md > .sisyphus/evidence/task-9-watchdog-contract.txt`
    Expected: AGENTS and TOOLS agree on the reminder-delivery mechanism used by the live scenario
    Evidence: .sisyphus/evidence/task-9-watchdog-contract.txt
  ```

  **Commit**: YES | Message: `feat(validation): backfill watchdog reminder coverage` | Files: `workspaces/oe-watchdog/AGENTS.md`, `workspaces/oe-watchdog/TOOLS.md`, `src/openclaw_enhance/watchdog/*.py`, `src/openclaw_enhance/validation/types.py`, `src/openclaw_enhance/validation/matrix.py`, `tests/integration/test_timeout_flow.py`, `tests/e2e/test_openclaw_harness.py`, `docs/testing-playbook.md`

- [x] 10. Extend harness/integration support so canonical backfill scenarios capture deterministic live evidence

  **What to do**: Extend the existing harness and integration support to capture the proof artifacts required by the coverage matrix: session transcript snippets, report file assertions, runtime-state evidence, and live reminder/recovery traces. Reuse `OPENCLAW_HARNESS=1` and the existing e2e file instead of inventing a new runner. Add any helper/fixture code needed for deterministic evidence capture, but keep it repo-owned and minimal.
  **Must NOT do**: Do not build a separate backfill orchestration framework. Do not make non-harness test runs flaky or dependent on a live OpenClaw install.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: this is the glue that turns the coverage matrix into repeatable live evidence
  - Skills: [`test-driven-development`] — why: harness helper behavior and evidence capture should be pinned before durable report execution
  - Omitted: [`writing-plans`] — why not needed: this is test/harness engineering, not prose work

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: 11 | Blocked By: 1, 2, 3, 4, 5, 6, 7, 8, 9

  **References** (executor has NO interview context — be exhaustive):
  - Harness gate: `tests/e2e/test_openclaw_harness.py:1` — canonical harness entrypoint and environment gating
  - Existing real-env smoke: `tests/e2e/test_openclaw_harness.py:427` — current install-lifecycle validator smoke
  - Integration harness for validator: `tests/integration/test_validation_real_env.py` — current mocked validator integration file
  - Existing reports schema: `docs/reports/README.md` — durable report contract that evidence capture must satisfy
  - Coverage matrix: `docs/testing-playbook.md` — source of truth for canonical slugs and proof kinds

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/integration/test_validation_real_env.py tests/integration/test_timeout_flow.py tests/integration/test_orchestrator_dispatch_contract.py -q` exits `0`
  - [ ] `OPENCLAW_HARNESS=1 pytest tests/e2e/test_openclaw_harness.py -k "real_env or recovery or watchdog" -q` exits `0` in the prepared harness environment
  - [ ] `pytest tests/e2e/test_openclaw_harness.py -k "real_env or recovery or watchdog" -q` skips cleanly when the harness environment is not available

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Harness subset captures deterministic live evidence when available
    Tool: Bash
    Steps: run `OPENCLAW_HARNESS=1 pytest tests/e2e/test_openclaw_harness.py -k "real_env or recovery or watchdog" -q > .sisyphus/evidence/task-10-harness-live.txt` in the prepared harness environment
    Expected: harness subset passes and writes evidence for routing/recovery/watchdog scenarios without manual intervention
    Evidence: .sisyphus/evidence/task-10-harness-live.txt

  Scenario: Harness subset remains safe outside harness mode
    Tool: Bash
    Steps: run `pytest tests/e2e/test_openclaw_harness.py -k "real_env or recovery or watchdog" -q > .sisyphus/evidence/task-10-harness-skip.txt || true`
    Expected: output indicates clean skip behavior rather than hard failure when `OPENCLAW_HARNESS` is not set
    Evidence: .sisyphus/evidence/task-10-harness-skip.txt
  ```

  **Commit**: YES | Message: `test(e2e): capture live evidence for backfill scenarios` | Files: `tests/e2e/test_openclaw_harness.py`, `tests/integration/test_validation_real_env.py`, `tests/fixtures/__init__.py` (if reusable harness helpers are needed), `docs/testing-playbook.md`

- [ ] 11. Execute the repo-wide backfill and record durable PASS reports plus durable workflow state

  **What to do**: Run the canonical backfill scenarios against the prepared harness-backed `~/.openclaw`, generate and commit the six PASS reports, then update durable workflow state so future work can rely on the backfill. Record the completed backfill milestone in `docs/opencode-iteration-handbook.md`, point durable docs to the coverage matrix/report inventory, and ensure `AGENTS.md`/workflow docs reference the backfilled contract as the default expectation.
  **Must NOT do**: Do not leave the backfill only as uncommitted local evidence. Do not claim completion if any canonical slug is missing or still ends in `PRODUCT_FAILURE` / `ENVIRONMENT_FAILURE`.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: this task combines durable report generation and final durable workflow-state updates
  - Skills: [`writing-plans`] — why: the durable state update must remain precise and aligned with the executed reports
  - Omitted: [`test-driven-development`] — why not needed: by this point execution should rest on already-verified validator/harness behavior

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: Final Verification | Blocked By: 1, 2, 5, 6, 7, 8, 9, 10

  **References** (executor has NO interview context — be exhaustive):
  - Report contract: `docs/reports/README.md` — required durable report schema
  - Existing report examples: `docs/reports/examples/` — formatting and narrative baseline
  - Handbook milestone record: `docs/opencode-iteration-handbook.md:164` — place to record completed durable milestones
  - Workflow checklist: `AGENTS.md:85` — post-development validation checklist that should now point at the backfilled matrix/report inventory
  - Coverage matrix: `docs/testing-playbook.md` — canonical source for the six backfill slugs and proof expectations

  **Acceptance Criteria** (agent-executable only):
  - [ ] `ls docs/reports/*-backfill-core-install-install-lifecycle.md docs/reports/*-backfill-dev-install-install-lifecycle.md docs/reports/*-backfill-cli-surface-cli-surface.md docs/reports/*-backfill-routing-yield-workspace-routing.md docs/reports/*-backfill-recovery-worker-workspace-routing.md docs/reports/*-backfill-watchdog-reminder-runtime-watchdog.md` exits `0`
  - [ ] `grep -R "Conclusion: PASS" docs/reports/*-backfill-*.md` returns six matches
  - [ ] `grep -q "repo-wide-real-env-backfill" docs/opencode-iteration-handbook.md` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Canonical backfill report inventory is complete and passing
    Tool: Bash
    Steps: run `ls docs/reports/*-backfill-*.md && grep -R "Conclusion: PASS" docs/reports/*-backfill-*.md > .sisyphus/evidence/task-11-report-inventory.txt`
    Expected: six canonical backfill reports exist and each records `Conclusion: PASS`
    Evidence: .sisyphus/evidence/task-11-report-inventory.txt

  Scenario: Durable workflow docs now point to the backfilled matrix and reports
    Tool: Bash
    Steps: run `grep -n "backfill-core-install\|docs/reports/\|Current branch shipped set\|repo-wide-real-env-backfill" AGENTS.md docs/opencode-iteration-handbook.md docs/testing-playbook.md docs/install.md docs/operations.md > .sisyphus/evidence/task-11-durable-state.txt`
    Expected: durable docs reference the completed backfill and its report inventory consistently
    Evidence: .sisyphus/evidence/task-11-durable-state.txt
  ```

  **Commit**: YES | Message: `docs(validation): record repo-wide backfill reports` | Files: `docs/reports/*.md`, `docs/opencode-iteration-handbook.md`, `AGENTS.md`, `docs/install.md`, `docs/operations.md`, `docs/testing-playbook.md`

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [ ] F1. Plan Compliance Audit - oracle

  **What to do**: Verify the finished change set matches this plan only: full current-branch shipped-set coverage via a matrix-to-bundle model, repaired validator contract, strengthened existing feature classes (not new ones), six canonical PASS backfill reports, and no CI/OpenClaw-core scope drift.
  **Verification**:
  - [ ] `grep -R "validate-feature --class" AGENTS.md docs tests --include='*.md' --include='*.py'` returns no matches
  - [ ] `grep -q "Current branch shipped set" docs/testing-playbook.md` exits `0`
  - [ ] `ls docs/reports/*-backfill-*.md` lists exactly the canonical backfill report set
  **QA Scenarios**:
  ```
  Scenario: Plan-required coverage surfaces exist and forbidden drift is absent
    Tool: Bash
    Steps: run `grep -R "Current branch shipped set\|backfill-core-install\|backfill-watchdog-reminder\|validate-feature --feature-class" AGENTS.md docs src tests --include='*.md' --include='*.py' > .sisyphus/evidence/f1-backfill-compliance.txt`
    Expected: evidence shows the coverage matrix, canonical slugs, and live CLI contract in expected surfaces
    Evidence: .sisyphus/evidence/f1-backfill-compliance.txt

  Scenario: No accidental scope drift into new feature classes or CI redesign
    Tool: Bash
    Steps: run `! grep -R -- "GitHub Actions\|workflow_dispatch\|new feature class\|matrix build" src docs tests --include='*.md' --include='*.py' > .sisyphus/evidence/f1-backfill-banned.txt 2>/dev/null`
    Expected: implementation stays within the existing validator/reporting model and does not create a second CI system
    Evidence: .sisyphus/evidence/f1-backfill-banned.txt
  ```

  **Pass Condition**: The implementation matches the matrix-based backfill plan, produces canonical reports, and stays within the repo-owned validation scope.

- [ ] F2. Validation Implementation Review - unspecified-high

  **What to do**: Review the validation matrix, runner/guardrails changes, strengthened bundles, and their unit/integration coverage for determinism, cleanup safety, and bundle completeness.
  **Verification**:
  - [ ] `pytest tests/unit/test_real_env_validation.py tests/unit/test_real_env_guardrails.py tests/unit/test_real_env_runner.py tests/unit/test_validation_matrix.py -q` exits `0`
  - [ ] `pytest tests/integration/test_validation_real_env.py tests/integration/test_install_uninstall.py tests/integration/test_dev_mode_integration.py tests/integration/test_orchestrator_dispatch_contract.py tests/integration/test_timeout_flow.py -q` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Validation implementation suites pass together
    Tool: Bash
    Steps: run `pytest tests/unit/test_real_env_validation.py tests/unit/test_real_env_guardrails.py tests/unit/test_real_env_runner.py tests/unit/test_validation_matrix.py tests/integration/test_validation_real_env.py tests/integration/test_install_uninstall.py tests/integration/test_dev_mode_integration.py tests/integration/test_orchestrator_dispatch_contract.py tests/integration/test_timeout_flow.py -q > .sisyphus/evidence/f2-backfill-tests.txt`
    Expected: validation, install/dev, routing/recovery, and watchdog suites pass together without contract drift
    Evidence: .sisyphus/evidence/f2-backfill-tests.txt

  Scenario: Live validator help surface remains stable after backfill
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli validate-feature --help > .sisyphus/evidence/f2-backfill-help.txt`
    Expected: help documents `--feature-class`, `--report-slug`, and the command remains usable after bundle expansion
    Evidence: .sisyphus/evidence/f2-backfill-help.txt
  ```

  **Pass Condition**: The validation implementation is deterministic, fully tested, and safe for canonical harness execution.

- [ ] F3. Real Local Workflow QA - unspecified-high

  **What to do**: Execute the canonical backfill scenarios in the prepared harness environment and confirm that the full report inventory is produced with PASS conclusions and observable proof for routing, recovery, and watchdog reminder delivery.
  **Verification**:
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class install-lifecycle --report-slug backfill-core-install --openclaw-home "$HOME/.openclaw"` exits `0` in the prepared harness environment
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class runtime-watchdog --report-slug backfill-watchdog-reminder --openclaw-home "$HOME/.openclaw"` exits `0` in the prepared harness environment
  - [ ] `grep -R "Conclusion: PASS" docs/reports/*-backfill-*.md` returns six matches
  **QA Scenarios**:
  ```
  Scenario: Canonical backfill scenarios run end to end and write durable reports
    Tool: Bash
    Steps: run the verification commands above plus the remaining canonical backfill slugs, saving combined output to `.sisyphus/evidence/f3-backfill-live.txt`
    Expected: every canonical backfill scenario exits successfully and writes a PASS report under `docs/reports/`
    Evidence: .sisyphus/evidence/f3-backfill-live.txt

  Scenario: Durable reports contain the expected proof sections
    Tool: Bash
    Steps: run `grep -R "Conclusion\|Execution Log\|Observable proof\|Feature Class" docs/reports/*-backfill-*.md > .sisyphus/evidence/f3-backfill-report-scan.txt`
    Expected: every durable backfill report contains the required schema and proof sections
    Evidence: .sisyphus/evidence/f3-backfill-report-scan.txt
  ```

  **Pass Condition**: The backfill works end to end in the canonical harness environment and leaves a complete PASS report inventory.

- [ ] F4. Scope Fidelity Check - deep

  **What to do**: Verify the repo now has a bounded, matrix-driven real-environment backfill for all shipped current-branch capabilities without drifting into OpenClaw-core changes, new feature-class taxonomies, or platform-wide CI work.
  **Verification**:
  - [ ] `python - <<'PY'
from pathlib import Path
blob = '\n'.join([
    Path('AGENTS.md').read_text(encoding='utf-8'),
    Path('docs/testing-playbook.md').read_text(encoding='utf-8'),
    Path('docs/opencode-iteration-handbook.md').read_text(encoding='utf-8'),
])
assert 'Current branch shipped set' in blob
assert 'backfill-core-install' in blob
assert 'backfill-watchdog-reminder' in blob
assert 'No OpenClaw source code edits' in Path('AGENTS.md').read_text(encoding='utf-8')
print('repo-backfill-scope-ok')
PY` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Scope script proves bounded backfill design and durable state alignment
    Tool: Bash
    Steps: run the verification script above and save stdout to `.sisyphus/evidence/f4-backfill-scope.txt`
    Expected: script prints `repo-backfill-scope-ok`
    Evidence: .sisyphus/evidence/f4-backfill-scope.txt

  Scenario: Durable docs still validate after repo-wide backfill updates
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli docs-check > .sisyphus/evidence/f4-backfill-docs-check.txt`
    Expected: docs-check passes after matrix/report/milestone updates
    Evidence: .sisyphus/evidence/f4-backfill-docs-check.txt
  ```

  **Pass Condition**: The completed work stays within the repo-owned, matrix-driven backfill scope and leaves durable docs in sync.

## Commit Strategy
- Keep contract-drift fixes separate from bundle-strengthening code so reviewers can verify the CLI/documentation surface independently.
- Keep matrix/model work separate from live scenario execution so failures in the harness do not hide design drift.
- Keep watchdog contract alignment separate from generic runtime-watchdog scenario work.
- Keep durable report generation/backfill execution separate from earlier code changes so each report commit corresponds to a stable validator state.

## Success Criteria
- Every shipped current-branch capability is explicitly mapped in `docs/testing-playbook.md` to one or more canonical live scenarios and report slugs.
- The repo no longer advertises an invalid `validate-feature --class` contract anywhere in durable docs or checks.
- The validator/harness can produce trustworthy PASS reports for install lifecycle, dev install mode, CLI surface, routing/yield, recovery worker, and watchdog reminder delivery.
- The first pass stays bounded to one canonical supported harness environment and does not create a second CI system.
- Handbook and workflow docs record the backfill as durable project state for future sessions.
