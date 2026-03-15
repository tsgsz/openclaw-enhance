# OpenClaw CLI Real-Environment Testing Loop

## TL;DR
> **Summary**: Replace the current generic testing guidance with a decision-complete real-environment validation loop that runs against the developer's default `~/.openclaw`, uses OpenClaw CLI plus `openclaw_enhance` CLI commands, records durable reports in `docs/reports/`, and becomes a mandatory post-development gate.
> **Deliverables**:
> - Feature-class matrix with exact real-environment scenarios and cleanup guardrails
> - Reusable validation runner/reporting implementation inside the repo
> - Durable `docs/testing-playbook.md` + `docs/reports/` reporting contract
> - Test coverage spanning unit, integration, and harness/E2E validation of the loop
> - Workflow enforcement updates in durable project docs/checklists
> **Effort**: Large
> **Parallel**: YES - 3 waves
> **Critical Path**: 1 -> 2 -> 4 -> 6 -> 8

## Context
### Original Request
- "我是希望为这个项目设计出来完整的实测闭环，能够在开发时引入真实环境进行测试进行最终开发的调整，因此需要提前调研设计出用真实环境测试的方案，并且落实到当前的开发流程中去"
- "要给 opencode 建立一个使用 openclaw cli 进行测试的 playbook，并且约定在开发完成新功能之后要使用 openclaw cli 进行效果实测。"

### Interview Summary
- The desired outcome is a complete real-environment loop, not a one-off shell script.
- Mandatory validation must target the developer's default `~/.openclaw` rather than a dedicated profile.
- Validation strength should vary by feature class rather than forcing one identical script for every change.
- Durable evidence must be committed under `docs/reports/`, not left only in session-local state.

### Metis Review (gaps addressed)
- Avoid turning the solution into a vague checklist; encode exact phases, commands, and expected outputs.
- Separate feature classes so docs/test-only work is not forced through the same flow as install/routing/runtime changes.
- Add guardrails for running against default `~/.openclaw`: baseline capture, owned-state verification, cleanup, and explicit failure classification.
- Keep the scope focused on local developer workflow and durable repo process; do not turn this into a broad CI platform redesign.

### Oracle Review (guardrails incorporated)
- Treat current `tests/e2e/test_openclaw_harness.py` as complementary harness coverage, not the full real-world loop.
- Use current documented OpenClaw CLI surfaces (`openclaw agent`, `openclaw agents list`, `openclaw status`, `openclaw doctor`) instead of outdated ad-hoc commands.
- Because the target is default `~/.openclaw`, implementation must prevent cross-run pollution and detect preexisting non-owned state before mutating anything.

## Work Objectives
### Core Objective
Create a decision-complete, repo-owned real-environment testing workflow that developers run after feature development to validate behavior in a real local OpenClaw environment using CLI commands and durable reports.

### Deliverables
- `docs/testing-playbook.md` rewritten as a feature-class-based, exact-command playbook
- `docs/reports/README.md` plus committed report template/examples for mandatory evidence
- Validation implementation that runs deterministic real-environment scenarios and writes reports to `docs/reports/`
- Tests for scenario selection, report generation, cleanup safeguards, and harness/E2E compatibility
- Workflow updates in durable docs/checklists so work cannot be called complete without a matching real-environment report when applicable

### Definition of Done (verifiable conditions with commands)
- `pytest tests/unit/test_real_env_validation.py -q` exits `0`
- `pytest tests/integration/test_real_env_validation.py -q` exits `0`
- `OPENCLAW_HARNESS=1 pytest tests/e2e/test_openclaw_harness.py -k real_env -q` exits `0` when the harness environment is available
- `python -m openclaw_enhance.cli docs-check` exits `0`
- `python -m openclaw_enhance.cli validate-feature --feature-class install-lifecycle --report-slug smoke --openclaw-home "$HOME/.openclaw"` exits `0` in a prepared local OpenClaw environment
- `test -f docs/reports/README.md` exits `0`
- `grep -q "OpenClaw CLI real-world testing" AGENTS.md docs/testing-playbook.md` exits `0`

### Must Have
- Exact feature-class matrix that determines which real-environment scenario must run
- Default `~/.openclaw` targeting with baseline capture, owned-state verification, and cleanup guardrails
- Exact OpenClaw CLI + `openclaw_enhance` CLI command bundles for each applicable feature class
- Durable report generation under `docs/reports/` with a stable schema/template
- Explicit differentiation between environment failure, product failure, and skipped/exempt classes
- Integration into current developer workflow via project docs/checklists

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No OpenClaw core code edits
- No assumption that `tests/e2e/test_openclaw_harness.py` alone satisfies the real-world loop
- No vague "run some manual checks" steps without exact commands and pass/fail criteria
- No silent mutation of preexisting `~/.openclaw` state without baseline capture and cleanup verification
- No storing mandatory evidence only in `.sisyphus/`
- No repo-wide CI redesign beyond what is necessary to anchor the local workflow

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after using existing pytest + harness patterns
- QA policy: every task includes exact CLI or pytest scenarios, with durable or session evidence paths
- Evidence: local validation reports go to `docs/reports/`; task execution artifacts go to `.sisyphus/evidence/task-{N}-{slug}.txt`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: validation contract foundation (`1`, `2`, `3`)
Wave 2: runner/CLI/test implementation (`4`, `5`, `6`, `7`)
Wave 3: durable workflow integration and examples (`8`, `9`)

### Dependency Matrix (full, all tasks)
- `1` blocks `2`, `3`, `4`, `8`
- `2` blocks `4`, `5`, `6`
- `3` blocks `4`, `6`, `8`
- `4` blocks `5`, `6`, `7`, `8`, `9`
- `5` blocks `7`
- `6` blocks Final Verification
- `7` blocks Final Verification
- `8` blocks Final Verification
- `9` blocks Final Verification

### Agent Dispatch Summary (wave -> task count -> categories)
- Wave 1 -> 3 tasks -> `writing`, `unspecified-high`, `quick`
- Wave 2 -> 4 tasks -> `unspecified-high`, `quick`, `writing`
- Wave 3 -> 2 tasks -> `writing`, `quick`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Rewrite the testing playbook into a decision-complete real-environment contract

  **What to do**: Replace the current generic `docs/testing-playbook.md` with an exact workflow that defines the phase order, the feature-class matrix, the required command bundles per class, the exemption policy for docs/test-only changes, the report location under `docs/reports/`, and the cleanup rules for running against default `~/.openclaw`. Update wording that currently relies on vague/manual steps or outdated OpenClaw CLI command assumptions.
  **Must NOT do**: Do not leave any step as “manual verification” without exact commands and expected outcomes. Do not require a dedicated profile; this contract must target default `~/.openclaw` because that decision is already fixed.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: the repo needs a durable, exact workflow contract before code can implement it safely
  - Skills: [`writing-plans`] — why: the file needs decision-complete operational detail, not high-level guidance
  - Omitted: [`test-driven-development`] — why not needed: this task defines the contract rather than implementation behavior

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2, 3, 4, 8 | Blocked By: none

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `docs/testing-playbook.md` — current generic playbook that must be tightened
  - Pattern: `AGENTS.md` — existing mandatory post-development checklist that the playbook must satisfy
  - Pattern: `tests/e2e/test_openclaw_harness.py` — current harness coverage boundaries to describe accurately
  - External: `https://docs.openclaw.ai/cli` — current command surface including `agent`, `agents list`, `status`, `doctor`, `--profile`, `--dev`

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -q "install-lifecycle" docs/testing-playbook.md` exits `0`
  - [ ] `grep -q "docs/reports/" docs/testing-playbook.md` exits `0`
  - [ ] `grep -q "~/.openclaw" docs/testing-playbook.md` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Playbook exposes feature-class matrix and exact real-environment flow
    Tool: Bash
    Steps: run `grep -n "install-lifecycle\|workspace-routing\|runtime-watchdog\|docs-test-only\|docs/reports" docs/testing-playbook.md > .sisyphus/evidence/task-1-playbook-matrix.txt`
    Expected: the rewritten playbook includes exact feature classes, report location, and durable flow anchors
    Evidence: .sisyphus/evidence/task-1-playbook-matrix.txt

  Scenario: Playbook still validates in repo docs checks
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli docs-check > .sisyphus/evidence/task-1-docs-check.txt`
    Expected: docs-check passes after rewriting the playbook
    Evidence: .sisyphus/evidence/task-1-docs-check.txt
  ```

  **Commit**: YES | Message: `docs(testing): define real-environment validation contract` | Files: `docs/testing-playbook.md`

- [ ] 2. Add validation types for feature classes, report schema, and failure taxonomy

  **What to do**: Create a focused validation module that encodes the real-environment contract in code. Add enums/dataclasses for feature classes, validation phases, report structure, result categories (`pass`, `product_failure`, `environment_failure`, `exempt`), and exact report path conventions. The implementation must be small and explicit; feature-class selection is manual via CLI argument, not inferred automatically from git diff.
  **Must NOT do**: Do not add auto-classification from changed files in this plan. Do not make report format open-ended or free-form.

  **Recommended Agent Profile**:
  - Category: `quick` — Reason: small focused Python module with deterministic types and tests
  - Skills: [`test-driven-development`] — why: schema/taxonomy behavior should be pinned before the runner is added
  - Omitted: [`writing-plans`] — why not needed: code contract task, not a workflow prose task

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 4, 5, 6 | Blocked By: 1

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/install/manifest.py` — existing dataclass serialization style
  - Pattern: `src/openclaw_enhance/runtime/schema.py` — simple schema-bearing module style
  - Test: `tests/unit/test_agent_catalog.py` — enum/schema validation test style
  - Pattern: `docs/testing-playbook.md` — source of truth for the feature-class matrix and report requirements

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_real_env_validation.py -q` exits `0`
  - [ ] `python - <<'PY'
from openclaw_enhance.validation.types import FeatureClass, ValidationConclusion
assert FeatureClass.INSTALL_LIFECYCLE.value == 'install-lifecycle'
assert ValidationConclusion.PASS.value == 'pass'
print('real-env-types-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Validation schema round-trips deterministically
    Tool: Bash
    Steps: run `pytest tests/unit/test_real_env_validation.py -q > .sisyphus/evidence/task-2-real-env-unit.txt`
    Expected: all validation-type tests pass and pin report semantics
    Evidence: .sisyphus/evidence/task-2-real-env-unit.txt

  Scenario: CLI-visible enums and report semantics are importable
    Tool: Bash
    Steps: run the acceptance Python snippet above and save stdout to `.sisyphus/evidence/task-2-real-env-import.txt`
    Expected: snippet prints `real-env-types-ok`
    Evidence: .sisyphus/evidence/task-2-real-env-import.txt
  ```

  **Commit**: YES | Message: `feat(validation): add real-environment validation types` | Files: `src/openclaw_enhance/validation/types.py`, `src/openclaw_enhance/validation/__init__.py`, `tests/unit/test_real_env_validation.py`

- [ ] 3. Implement baseline capture and cleanup guardrails for default `~/.openclaw`

  **What to do**: Add helper code that captures baseline state before validation and verifies cleanup afterward. It must record whether `openclaw-enhance` is already installed, whether the current target home appears to belong to the current checkout, the current `config.json` state for owned keys, and the managed-root state. It must refuse to mutate obviously foreign/preexisting enhance state and must verify uninstall removes owned state at the end of applicable scenarios.
  **Must NOT do**: Do not snapshot-restore the entire `~/.openclaw` tree. Do not silently proceed when a foreign/preexisting installation is detected.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: safety-sensitive state handling against a real default environment
  - Skills: [`test-driven-development`] — why: cleanup guardrails need exact regression coverage
  - Omitted: [`systematic-debugging`] — why not needed: this is greenfield safety logic, not failure triage

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 4, 6 | Blocked By: 1

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/paths.py` — managed root and workspace path conventions
  - Pattern: `src/openclaw_enhance/install/installer.py` — install/status data available to inspect
  - Pattern: `src/openclaw_enhance/install/uninstaller.py` — cleanup semantics that post-validation must verify
  - Test Fixture: `tests/fixtures/__init__.py` — isolated user-home fixture patterns
  - Test: `tests/integration/test_install_uninstall.py` — lifecycle symmetry assertions to mirror

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_real_env_guardrails.py -q` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
from openclaw_enhance.validation.guardrails import capture_baseline_state
state = capture_baseline_state(Path.home() / '.openclaw')
assert hasattr(state, 'openclaw_home') and state.openclaw_home.name == '.openclaw'
print('baseline-capture-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Guardrails reject unsafe starting state and accept clean state
    Tool: Bash
    Steps: run `pytest tests/unit/test_real_env_guardrails.py -q > .sisyphus/evidence/task-3-guardrails-unit.txt`
    Expected: unit tests prove baseline capture and foreign-state rejection behavior
    Evidence: .sisyphus/evidence/task-3-guardrails-unit.txt

  Scenario: Baseline capture can inspect the developer default home shape without mutating it
    Tool: Bash
    Steps: run the acceptance Python snippet above and save stdout to `.sisyphus/evidence/task-3-baseline-capture.txt`
    Expected: snippet prints `baseline-capture-ok`
    Evidence: .sisyphus/evidence/task-3-baseline-capture.txt
  ```

  **Commit**: YES | Message: `feat(validation): add baseline and cleanup guardrails` | Files: `src/openclaw_enhance/validation/guardrails.py`, `tests/unit/test_real_env_guardrails.py`

- [ ] 4. Implement deterministic real-environment scenarios and durable report generation

  **What to do**: Add the reusable runner layer that maps each supported feature class to an exact ordered command bundle, executes commands, captures stdout/stderr/exit codes, and emits a markdown report to `docs/reports/YYYY-MM-DD-<slug>-<feature-class>.md`. The scenarios must cover at minimum: `install-lifecycle`, `cli-surface`, `workspace-routing`, `runtime-watchdog`, and `docs-test-only` (exempt path that records why no real-environment run was required). Use current OpenClaw CLI commands (`openclaw doctor`, `openclaw status`, `openclaw agents list`, `openclaw agent --message`) plus `python -m openclaw_enhance.cli` commands where appropriate.
  **Must NOT do**: Do not shell out to undocumented `openclaw chat` flows. Do not let scenarios differ from the matrix defined in `docs/testing-playbook.md`.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: this is the core reusable behavior that turns docs into an executable validation loop
  - Skills: [`test-driven-development`] — why: scenario/report behavior must be pinned before workflow integration
  - Omitted: [`writing-plans`] — why not needed: implementation task, not planning prose

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 5, 6, 7, 8, 9 | Blocked By: 2, 3

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/install/installer.py` — subprocess invocation style for external CLI calls
  - Pattern: `src/openclaw_enhance/cli.py` — click command wiring and JSON/plain output behavior
  - Pattern: `tests/e2e/test_openclaw_harness.py` — subprocess-based harness assertions for real-environment style commands
  - External: `https://docs.openclaw.ai/cli` — current OpenClaw CLI command surface
  - Contract: `docs/testing-playbook.md` — exact feature-class matrix to implement

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_real_env_runner.py -q` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
from openclaw_enhance.validation.runner import build_report_path
path = build_report_path(Path('docs/reports'), 'smoke', 'install-lifecycle')
assert path.parent.as_posix() == 'docs/reports'
assert path.name.endswith('-smoke-install-lifecycle.md')
print('real-env-runner-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Scenario catalog and report path behavior are deterministic
    Tool: Bash
    Steps: run `pytest tests/unit/test_real_env_runner.py -q > .sisyphus/evidence/task-4-runner-unit.txt`
    Expected: scenario catalog and report rendering tests pass
    Evidence: .sisyphus/evidence/task-4-runner-unit.txt

  Scenario: Report path generation matches the durable docs contract
    Tool: Bash
    Steps: run the acceptance Python snippet above and save stdout to `.sisyphus/evidence/task-4-report-path.txt`
    Expected: snippet prints `real-env-runner-ok`
    Evidence: .sisyphus/evidence/task-4-report-path.txt
  ```

  **Commit**: YES | Message: `feat(validation): add real-environment scenarios and reports` | Files: `src/openclaw_enhance/validation/runner.py`, `src/openclaw_enhance/validation/reporting.py`, `tests/unit/test_real_env_runner.py`

- [ ] 5. Expose the validation loop through a dedicated CLI command

  **What to do**: Add `python -m openclaw_enhance.cli validate-feature` as the repo-owned entrypoint for developers. The command must require `--feature-class` and `--report-slug`, default `--openclaw-home` to `~/.openclaw`, call the guardrails + runner layers, and print the final report path plus pass/fail conclusion. The CLI contract must not guess feature class from changed files.
  **Must NOT do**: Do not introduce interactive prompts. Do not silently downgrade failures to warnings.

  **Recommended Agent Profile**:
  - Category: `quick` — Reason: focused Click command wiring on top of the runner
  - Skills: [`test-driven-development`] — why: CLI UX should be pinned with command-level tests
  - Omitted: [`systematic-debugging`] — why not needed: deterministic command addition

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 6, 8 | Blocked By: 4

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/cli.py` — existing command definitions and option conventions
  - Test: `tests/unit/test_cli_smoke.py` — CLI presence/help test style
  - Test: `tests/integration/test_status_command.py` — Click runner integration style
  - Contract: `docs/testing-playbook.md` — command should line up with the documented workflow

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m openclaw_enhance.cli validate-feature --help` exits `0`
  - [ ] `python -m openclaw_enhance.cli validate-feature --help | grep -q -- "--feature-class"` exits `0`
  - [ ] `pytest tests/unit/test_cli_smoke.py -k validate_feature -q` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: CLI exposes validate-feature with required options
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli validate-feature --help > .sisyphus/evidence/task-5-validate-help.txt`
    Expected: help output documents `--feature-class`, `--report-slug`, and `--openclaw-home`
    Evidence: .sisyphus/evidence/task-5-validate-help.txt

  Scenario: CLI smoke tests pin command availability
    Tool: Bash
    Steps: run `pytest tests/unit/test_cli_smoke.py -k validate_feature -q > .sisyphus/evidence/task-5-cli-smoke.txt`
    Expected: validate-feature command is covered by CLI smoke tests
    Evidence: .sisyphus/evidence/task-5-cli-smoke.txt
  ```

  **Commit**: YES | Message: `feat(cli): add validate-feature command` | Files: `src/openclaw_enhance/cli.py`, `tests/unit/test_cli_smoke.py`

- [ ] 6. Add integration tests for local validation runner behavior and report writing

  **What to do**: Add integration tests that exercise `validate-feature` with isolated `HOME`/`openclaw_home` fixtures and a mocked OpenClaw CLI subprocess surface. Verify report creation, command ordering, exemption handling, cleanup verification, and failure classification. These tests must prove the runner writes into `docs/reports/` and does not mutate unrelated test fixtures when scenarios fail.
  **Must NOT do**: Do not make these tests depend on a real installed OpenClaw binary. Real binary coverage belongs to the harness/E2E task.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: integration behavior spans CLI, runner, report writing, and safety guards
  - Skills: [`test-driven-development`] — why: exact command ordering and failure semantics need regression coverage
  - Omitted: [`writing-plans`] — why not needed: implementation-facing test task

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: Final Verification | Blocked By: 4, 5

  **References** (executor has NO interview context — be exhaustive):
  - Fixture: `tests/fixtures/__init__.py` — isolated user-home/openclaw-home fixture patterns
  - Pattern: `tests/integration/test_status_command.py` — command-level integration style
  - Pattern: `tests/integration/test_install_uninstall.py` — lifecycle symmetry and cleanup checks
  - Contract: `docs/reports/` naming and schema from Task 4

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/integration/test_real_env_validation.py -q` exits `0`
  - [ ] `python -m pytest tests/integration/test_real_env_validation.py -k report -q` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Integration tests verify report generation and command ordering
    Tool: Bash
    Steps: run `pytest tests/integration/test_real_env_validation.py -q > .sisyphus/evidence/task-6-real-env-integration.txt`
    Expected: integration tests pass and cover report writing, cleanup, and failure taxonomy
    Evidence: .sisyphus/evidence/task-6-real-env-integration.txt

  Scenario: Report-focused integration subset passes independently
    Tool: Bash
    Steps: run `python -m pytest tests/integration/test_real_env_validation.py -k report -q > .sisyphus/evidence/task-6-real-env-report-subset.txt`
    Expected: report-generation subset passes in isolation
    Evidence: .sisyphus/evidence/task-6-real-env-report-subset.txt
  ```

  **Commit**: YES | Message: `test(validation): cover real-environment runner integration` | Files: `tests/integration/test_real_env_validation.py`

- [ ] 7. Extend the harness E2E suite to validate the real-environment loop contract

  **What to do**: Extend `tests/e2e/test_openclaw_harness.py` so harness runs can exercise at least one real-environment validation path through the new runner/CLI entrypoint. The harness coverage must prove that the loop works with an actual OpenClaw environment when `OPENCLAW_HARNESS=1`, while still skipping cleanly when the harness is unavailable.
  **Must NOT do**: Do not replace the existing harness file or remove current install/status/doctor/render checks. Do not make non-harness test runs flaky.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: e2e coverage must align with an actual OpenClaw environment and existing harness conventions
  - Skills: [`test-driven-development`] — why: harness behavior should be expanded with explicit skip/pass assertions
  - Omitted: [`systematic-debugging`] — why not needed: this is extending a known harness pattern

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: Final Verification | Blocked By: 4

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `tests/e2e/test_openclaw_harness.py` — harness gating and subprocess style
  - Contract: `docs/testing-playbook.md` — which feature class and scenario the harness should mirror
  - External: `https://docs.openclaw.ai/cli` — OpenClaw commands used in the scenario

  **Acceptance Criteria** (agent-executable only):
  - [ ] `OPENCLAW_HARNESS=1 pytest tests/e2e/test_openclaw_harness.py -k real_env -q` exits `0` when harness is available
  - [ ] `pytest tests/e2e/test_openclaw_harness.py -k real_env -q` skips cleanly when harness is not available

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Harness-specific real-environment subset skips cleanly outside harness mode
    Tool: Bash
    Steps: run `pytest tests/e2e/test_openclaw_harness.py -k real_env -q > .sisyphus/evidence/task-7-harness-skip.txt || true`
    Expected: output indicates clean skip behavior instead of hard failure when `OPENCLAW_HARNESS` is not set
    Evidence: .sisyphus/evidence/task-7-harness-skip.txt

  Scenario: Harness subset is executable when a harness environment is available
    Tool: Bash
    Steps: run `OPENCLAW_HARNESS=1 pytest tests/e2e/test_openclaw_harness.py -k real_env -q > .sisyphus/evidence/task-7-harness-run.txt` in a prepared harness environment
    Expected: harness real-environment subset passes
    Evidence: .sisyphus/evidence/task-7-harness-run.txt
  ```

  **Commit**: YES | Message: `test(e2e): add harness coverage for real-environment validation` | Files: `tests/e2e/test_openclaw_harness.py`

- [ ] 8. Integrate the real-environment loop into durable project workflow docs and completion gates

  **What to do**: Update durable project docs so the new loop is part of the default development process, not an optional note. At minimum, update `AGENTS.md`, `docs/opencode-iteration-handbook.md`, and any directly relevant operational/install docs so they reference the feature-class matrix, the `validate-feature` command, the mandatory `docs/reports/` output, and the requirement to run the loop before claiming feature completion.
  **Must NOT do**: Do not leave the new workflow only in `docs/testing-playbook.md`. Do not add conflicting instructions across docs.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: this task is about making the process durable and discoverable across canonical docs
  - Skills: [`writing-plans`] — why: must keep process language precise and consistent across docs
  - Omitted: [`test-driven-development`] — why not needed: documentation integration task

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: Final Verification | Blocked By: 1, 4, 5

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `AGENTS.md` — mandatory post-development checklist
  - Pattern: `docs/opencode-iteration-handbook.md` — durable workflow and quick reference anchors
  - Pattern: `docs/install.md` — install/verify guidance where the new real-environment gate may be referenced
  - Pattern: `docs/operations.md` — operational validation commands already documented
  - Test: `tests/unit/test_docs_examples.py` — doc example coverage

  **Acceptance Criteria** (agent-executable only):
  - [ ] `grep -q "validate-feature" AGENTS.md docs/opencode-iteration-handbook.md docs/testing-playbook.md` exits `0`
  - [ ] `pytest tests/unit/test_docs_examples.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Durable docs all point to the same validation loop entrypoint
    Tool: Bash
    Steps: run `grep -n "validate-feature\|docs/reports\|OpenClaw CLI real-world testing" AGENTS.md docs/opencode-iteration-handbook.md docs/testing-playbook.md > .sisyphus/evidence/task-8-workflow-docs.txt`
    Expected: all durable docs align on command, report location, and mandatory gate wording
    Evidence: .sisyphus/evidence/task-8-workflow-docs.txt

  Scenario: Docs examples remain valid after workflow integration
    Tool: Bash
    Steps: run `pytest tests/unit/test_docs_examples.py -q > .sisyphus/evidence/task-8-doc-examples.txt`
    Expected: docs example tests pass
    Evidence: .sisyphus/evidence/task-8-doc-examples.txt
  ```

  **Commit**: YES | Message: `docs(workflow): require real-environment validation reports` | Files: `AGENTS.md`, `docs/opencode-iteration-handbook.md`, `docs/install.md`, `docs/operations.md`, `docs/testing-playbook.md`, `tests/unit/test_docs_examples.py`

- [ ] 9. Bootstrap durable report storage with schema docs, template, and canonical examples

  **What to do**: Add `docs/reports/README.md` describing the report schema, naming convention, retention expectations, and required sections. Add one canonical template plus example reports for at least `install-lifecycle`, `workspace-routing`, and an exempt `docs-test-only` change so developers can see exactly what “good” looks like. Make sure the validation runner writes reports that match this contract.
  **Must NOT do**: Do not store the template only in `.sisyphus/`. Do not make example reports contradict the playbook or CLI output contract.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: durable evidence format and examples are documentation deliverables
  - Skills: [`writing-plans`] — why: report structure must be exact and reusable
  - Omitted: [`test-driven-development`] — why not needed: this is schema/example documentation rather than behavior implementation

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: Final Verification | Blocked By: 4

  **References** (executor has NO interview context — be exhaustive):
  - Contract: `docs/testing-playbook.md` — source of truth for what reports must contain
  - Pattern: `docs/adr/` — house style for durable operational markdown
  - Pattern: `docs/install.md` — example-rich command documentation style

  **Acceptance Criteria** (agent-executable only):
  - [ ] `test -f docs/reports/README.md` exits `0`
  - [ ] `test -f docs/reports/template.md` exits `0`
  - [ ] `grep -q "Conclusion" docs/reports/template.md` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Durable report schema and template exist in the repo
    Tool: Bash
    Steps: run `ls docs/reports && grep -n "schema\|Conclusion\|Feature Class" docs/reports/README.md docs/reports/template.md > .sisyphus/evidence/task-9-report-schema.txt`
    Expected: README and template both exist and document required report sections
    Evidence: .sisyphus/evidence/task-9-report-schema.txt

  Scenario: Example reports cover required classes and exemption behavior
    Tool: Bash
    Steps: run `grep -R "install-lifecycle\|workspace-routing\|docs-test-only" docs/reports/examples > .sisyphus/evidence/task-9-report-examples.txt`
    Expected: examples show at least one critical class, one behavior class, and one exempt class
    Evidence: .sisyphus/evidence/task-9-report-examples.txt
  ```

  **Commit**: YES | Message: `docs(reports): add real-environment validation templates` | Files: `docs/reports/README.md`, `docs/reports/template.md`, `docs/reports/examples/`

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [ ] F1. Plan Compliance Audit - oracle

  **What to do**: Verify the finished change set matches this plan only: default `~/.openclaw` target, feature-class matrix, durable `docs/reports/` evidence, repo-owned validation runner/CLI entrypoint, and workflow enforcement in durable docs.
  **Verification**:
  - [ ] `grep -q "~/.openclaw" docs/testing-playbook.md docs/reports/README.md` exits `0`
  - [ ] `grep -q "validate-feature" src/openclaw_enhance/cli.py AGENTS.md docs/testing-playbook.md` exits `0`
  - [ ] `test -f docs/reports/README.md && test -f docs/reports/template.md` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Real-environment workflow surfaces exist in code and docs
    Tool: Bash
    Steps: run `grep -R "validate-feature\|docs/reports\|~/.openclaw" src/openclaw_enhance/cli.py AGENTS.md docs/testing-playbook.md docs/reports > .sisyphus/evidence/f1-real-env-compliance.txt`
    Expected: command, report storage, and default-home targeting all appear in the expected places
    Evidence: .sisyphus/evidence/f1-real-env-compliance.txt

  Scenario: Forbidden scope drift was not introduced
    Tool: Bash
    Steps: run `! grep -R -- "--profile oe-validate\|dedicated profile required" src docs tests --include='*.md' --include='*.py' > .sisyphus/evidence/f1-real-env-banned.txt`
    Expected: the implementation does not drift back to dedicated-profile-only validation
    Evidence: .sisyphus/evidence/f1-real-env-banned.txt
  ```

  **Pass Condition**: The final implementation is a repo-owned, default-home, report-backed real-environment workflow with no profile-drift or missing enforcement surfaces.
- [ ] F2. Validation Implementation Review - unspecified-high

  **What to do**: Review validation types, guardrails, runner logic, and `validate-feature` CLI behavior for determinism, cleanup safety, and alignment with the documented feature-class matrix.
  **Verification**:
  - [ ] `pytest tests/unit/test_real_env_validation.py tests/unit/test_real_env_guardrails.py tests/unit/test_real_env_runner.py -q` exits `0`
  - [ ] `pytest tests/integration/test_real_env_validation.py -q` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Validation implementation test suite passes together
    Tool: Bash
    Steps: run `pytest tests/unit/test_real_env_validation.py tests/unit/test_real_env_guardrails.py tests/unit/test_real_env_runner.py tests/integration/test_real_env_validation.py -q > .sisyphus/evidence/f2-real-env-tests.txt`
    Expected: unit and integration suites pass together without contract drift
    Evidence: .sisyphus/evidence/f2-real-env-tests.txt

  Scenario: validate-feature help surface remains stable
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli validate-feature --help > .sisyphus/evidence/f2-real-env-help.txt`
    Expected: help documents required feature-class and report options
    Evidence: .sisyphus/evidence/f2-real-env-help.txt
  ```

  **Pass Condition**: Validation implementation is deterministic, tested, and safe for default-home execution.
- [ ] F3. Real Local Workflow QA - unspecified-high

  **What to do**: Execute at least one real local validation path in a prepared developer environment and confirm that it writes a durable report, records command evidence, and cleans up owned enhance state.
  **Verification**:
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class install-lifecycle --report-slug final-check --openclaw-home "$HOME/.openclaw"` exits `0` in a prepared local environment
  - [ ] `ls docs/reports/*-final-check-install-lifecycle.md` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Real local install-lifecycle validation writes a durable report
    Tool: Bash
    Steps: run the verification command above and save combined output to `.sisyphus/evidence/f3-real-env-local.txt`
    Expected: command exits successfully and produces a report under `docs/reports/`
    Evidence: .sisyphus/evidence/f3-real-env-local.txt

  Scenario: Generated report contains conclusion and command evidence
    Tool: Bash
    Steps: run `grep -n "Conclusion\|Commands Run\|Feature Class" docs/reports/*-final-check-install-lifecycle.md > .sisyphus/evidence/f3-real-env-report-scan.txt`
    Expected: the report includes the required schema sections
    Evidence: .sisyphus/evidence/f3-real-env-report-scan.txt
  ```

  **Pass Condition**: A real local run proves the loop works end-to-end and produces durable evidence.
- [ ] F4. Scope Fidelity Check - deep

  **What to do**: Verify the project now has a complete local real-environment validation loop without drifting into unrelated CI-platform redesign or OpenClaw core changes.
  **Verification**:
  - [ ] `python - <<'PY'
from pathlib import Path
blob = '\n'.join([
    Path('AGENTS.md').read_text(encoding='utf-8'),
    Path('docs/testing-playbook.md').read_text(encoding='utf-8'),
    Path('docs/opencode-iteration-handbook.md').read_text(encoding='utf-8'),
])
assert 'OpenClaw CLI real-world testing' in blob
assert 'docs/reports/' in blob
assert 'validate-feature' in blob
assert 'No OpenClaw source code edits' in Path('AGENTS.md').read_text(encoding='utf-8')
print('real-env-scope-ok')
PY` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  **QA Scenarios**:
  ```
  Scenario: Scope script proves workflow integration without boundary drift
    Tool: Bash
    Steps: run the verification script above and save stdout to `.sisyphus/evidence/f4-real-env-scope.txt`
    Expected: script prints `real-env-scope-ok`
    Evidence: .sisyphus/evidence/f4-real-env-scope.txt

  Scenario: Durable docs still validate after workflow integration
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli docs-check > .sisyphus/evidence/f4-real-env-docs-check.txt`
    Expected: docs-check passes
    Evidence: .sisyphus/evidence/f4-real-env-docs-check.txt
  ```

  **Pass Condition**: The implementation stays focused on local workflow closure, durable docs, and repo-owned validation without broader platform creep.

## Commit Strategy
- Keep validation contract/docs separate from runner code so workflow policy is reviewable.
- Keep report schema/template changes separate from runner logic when practical.
- Keep harness/E2E expansion separate from local unit/integration tests.
- Finish with durable checklist/doc updates after command/runner behavior is stable.

## Success Criteria
- Developers can identify a feature class and run one exact repo-owned real-environment validation path against `~/.openclaw`.
- The validation path writes a durable report to `docs/reports/` with pass/fail conclusion and command evidence.
- The workflow distinguishes real-world loop requirements from exemptions (docs/test-only changes).
- Existing harness tests remain complementary and aligned with the new real-environment workflow.
- Project docs/checklists make the real-environment report a non-optional completion gate.
