# Current Python Deployment

## TL;DR
> **Summary**: Align `openclaw-enhance` so deployment explicitly uses the interpreter from the current Python environment instead of implying a separate virtualenv is required. The code already behaves this way in most places; the missing pieces are validation and documentation clarity.
> **Deliverables**:
> - Python-version validation added to environment checks used by `doctor` and installer preflight
> - Install/troubleshooting docs updated to treat venv as optional rather than recommended/required
> - Tests updated to lock current-interpreter behavior and failure messages
> - No interpreter-management features added
> **Effort**: Short
> **Parallel**: YES - 2 waves
> **Critical Path**: 1 -> 2 -> 3 -> 4

## Context
### Original Request
- Deployment should not require creating a new Python environment and should use the current environment's Python.

### Interview Summary
- Repo exploration shows there is no installer code that actually creates a venv today.
- The mismatch is primarily documentation (`docs/install.md` still recommends `.venv`) plus missing validation (`doctor` and installer preflight do not verify the current interpreter version).
- Tests already invoke the CLI with `sys.executable`, which is the correct current-interpreter pattern and should be preserved.

### Metis Review (gaps addressed)
- Default minimum Python version is fixed to `>=3.10` from `pyproject.toml`; no separate user decision is needed.
- Validation behavior is fixed to hard-fail for unsupported Python versions in `doctor` and installer preflight.
- venv guidance is fixed to “optional isolation” rather than “recommended setup”.
- Scope is constrained to interpreter-version validation and docs/tests alignment only; no dependency manager, pyenv, conda, uv, or interpreter-switching automation is included.
- Existing venv users remain supported because the current interpreter may still be a venv interpreter; the project simply stops implying that a new venv must be created.

## Work Objectives
### Core Objective
- Make the project explicitly support deployment from the currently active Python interpreter, and validate that interpreter up front before install-time work begins.

### Deliverables
- `src/openclaw_enhance/runtime/support_matrix.py` extended to validate the running Python version in addition to OpenClaw version/platform.
- `doctor` and installer preflight continue to use shared environment validation, now with explicit current-Python checks and actionable failure messages.
- `docs/install.md` and any related operator docs updated to remove the implied requirement to create `.venv` before installing.
- Tests covering the new Python-version validation and the updated docs language.

### Definition of Done (verifiable conditions with commands)
- `pytest tests/unit/test_support_matrix.py -q` exits `0`.
- `pytest tests/unit/test_docs_examples.py -q` exits `0`.
- `pytest tests/unit/test_cli_smoke.py -q` exits `0`.
- `python - <<'PY'
from pathlib import Path
content = Path('docs/install.md').read_text(encoding='utf-8')
assert 'python -m venv .venv' not in content
assert 'current Python environment' in content or 'current interpreter' in content
print('install-doc-current-python-ok')
PY` exits `0`.
- `python - <<'PY'
from openclaw_enhance.runtime.support_matrix import validate_environment
from pathlib import Path
tmp = Path('.tmp-openclaw-home-check')
tmp.mkdir(exist_ok=True)
(tmp / 'VERSION').write_text('2026.3.1\n', encoding='utf-8')
validate_environment(tmp)
print('validate-environment-current-python-ok')
(tmp / 'VERSION').unlink()
tmp.rmdir()
PY` exits `0`.

### Must Have
- Python version validation must derive from the project requirement in `pyproject.toml` (`>=3.10`).
- Validation must use the current interpreter (`sys.version_info` / `sys.executable` context), not assume or create a new environment.
- `doctor` and installer preflight must fail clearly when the current interpreter is unsupported.
- Documentation must say a virtualenv is optional isolation, not a required deployment step.
- Existing `sys.executable` test patterns must remain intact.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No code that creates a venv/virtualenv automatically.
- No pyenv/conda/uv/pipx-specific branching or environment management.
- No requirement that users leave a venv if they already have one active.
- No new persisted runtime metadata for Python path selection unless absolutely needed (it is not needed based on current exploration).
- No broad rewrite of installer lifecycle; only align validation and docs with the existing current-interpreter model.

## Verification Strategy
> ZERO HUMAN INTERVENTION — all verification is agent-executed.
- Test decision: tests-after, but write focused validation tests before changing runtime logic where practical.
- QA policy: every task includes a direct command check and one failure/edge check.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`.

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: 1) support-matrix Python validation, 2) doctor/preflight + tests

Wave 2: 3) docs alignment for current-interpreter deployment, 4) final drift review and integrated verification

### Dependency Matrix (full, all tasks)
| Task | Depends On | Blocks |
| --- | --- | --- |
| 1 | none | 2, 3, 4 |
| 2 | 1 | 4 |
| 3 | 1 | 4 |
| 4 | 1, 2, 3 | Final Verification |

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 -> 2 tasks -> `quick`, `unspecified-high`
- Wave 2 -> 2 tasks -> `writing`, `unspecified-high`
- Final Verification -> 4 tasks -> `oracle`, `unspecified-high`, `deep`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 1. Extend support-matrix validation to check the current Python interpreter version

  **What to do**: Update `src/openclaw_enhance/runtime/support_matrix.py` so environment validation includes the running interpreter version in addition to OpenClaw version and platform. Use the project requirement from `pyproject.toml` (`>=3.10`) as the acceptance floor. Keep the implementation explicit and small: either add a dedicated helper such as `validate_python_version()` / `validate_python_support()` and call it from `validate_environment()`, or extend the existing support-matrix functions in the same module. Error messages must clearly say the current Python version is unsupported and state the supported floor.
  **Must NOT do**: Do not parse or manage virtualenv paths. Do not shell out to `python --version`. Do not record interpreter paths in manifests or runtime state.

  **Recommended Agent Profile**:
  - Category: `quick` — Reason: small, bounded runtime validation change
  - Skills: [`test-driven-development`] — lock version-validation behavior before changing runtime checks
  - Omitted: [`systematic-debugging`] — no evidence of a complex bug, just missing validation

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 2, 3, 4 | Blocked By: none

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `pyproject.toml:11` — project Python requirement is `>=3.10`
  - Pattern: `src/openclaw_enhance/runtime/support_matrix.py:13` — current support-matrix validation only covers OpenClaw version/platform
  - Pattern: `src/openclaw_enhance/runtime/support_matrix.py:33` — `validate_environment()` is the shared entrypoint used by CLI/install lifecycle
  - Test: `tests/unit/test_support_matrix.py:4` — existing style for support-matrix acceptance/rejection tests
  - Pattern: `tests/e2e/test_openclaw_harness.py:248` — doctor command already runs under the current interpreter in tests

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_support_matrix.py -q` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
from openclaw_enhance.runtime.support_matrix import validate_environment
tmp = Path('.tmp-openclaw-home-check')
tmp.mkdir(exist_ok=True)
(tmp / 'VERSION').write_text('2026.3.1\n', encoding='utf-8')
validate_environment(tmp)
print('support-matrix-current-python-ok')
(tmp / 'VERSION').unlink()
tmp.rmdir()
PY` exits `0`
  - [ ] `python - <<'PY'
from openclaw_enhance.runtime.support_matrix import SupportError
try:
    raise SupportError("Unsupported Python version '3.9'. Supported: >=3.10")
except SupportError as exc:
    assert 'python' in str(exc).lower()
    assert '3.10' in str(exc)
print('python-error-shape-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Supported current interpreter passes validation
    Tool: Bash
    Steps: run the acceptance snippet that creates a temp OpenClaw home with VERSION=2026.3.1 and calls validate_environment()
    Expected: validation succeeds under the current interpreter with no separate env involved
    Evidence: .sisyphus/evidence/task-1-python-validation.txt

  Scenario: Unsupported Python error text is actionable
    Tool: Bash
    Steps: run the error-shape snippet or a focused unit test asserting the message includes the current Python issue and the supported floor
    Expected: failure text clearly says the current Python is unsupported and references >=3.10
    Evidence: .sisyphus/evidence/task-1-python-validation-error.txt
  ```

  **Commit**: YES | Message: `feat(runtime): validate current python version` | Files: `src/openclaw_enhance/runtime/support_matrix.py`, `tests/unit/test_support_matrix.py`

- [x] 2. Surface current-Python validation through `doctor` and installer preflight

  **What to do**: Ensure the shared environment validation from Task 1 reaches both the CLI `doctor` command and installer preflight without drift. Update tests so `doctor` and preflight explicitly cover the new Python-version path. If messaging needs adjustment, keep it actionable: current interpreter unsupported, install/use Python >=3.10, then rerun. Preserve the existing lifecycle shape where `doctor` and preflight call the shared validator rather than duplicating logic.
  **Must NOT do**: Do not add interpreter selection flags. Do not make install silently continue on unsupported Python.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: shared lifecycle behavior plus CLI/install test coverage
  - Skills: [`test-driven-development`] — capture doctor/preflight behavior first
  - Omitted: [`brainstorming`] — behavior is already chosen

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 4 | Blocked By: 1

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/cli.py:107` — `doctor` command uses `validate_environment(openclaw_home)` today
  - Pattern: `src/openclaw_enhance/install/installer.py:122` — `preflight_checks()` uses shared environment validation
  - Test: `tests/unit/test_cli_smoke.py:37` — CLI command existence/help patterns
  - Test: `tests/e2e/test_openclaw_harness.py:242` — current doctor harness behavior and exit-shape expectations
  - Test: `tests/integration/test_install_uninstall.py:49` — install lifecycle/integration style to extend carefully

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_cli_smoke.py -q` exits `0`
  - [ ] `pytest tests/integration/test_install_uninstall.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli doctor --help` exits `0`
  - [ ] `python - <<'PY'
import subprocess, sys
result = subprocess.run([sys.executable, '-m', 'openclaw_enhance.cli', 'doctor', '--help'], capture_output=True, text=True)
assert result.returncode == 0
assert 'doctor' in result.stdout.lower()
print('doctor-cli-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Doctor validates using the current interpreter path
    Tool: Bash
    Steps: run `python -m openclaw_enhance.cli doctor --help` and the focused CLI smoke/integration tests that invoke the module with `sys.executable`
    Expected: doctor remains callable from the current interpreter and tests pass without any venv-specific setup
    Evidence: .sisyphus/evidence/task-2-doctor-preflight.txt

  Scenario: Unsupported Python path would hard-fail install-time validation
    Tool: Bash
    Steps: add/execute focused unit or integration coverage around preflight / shared validation asserting unsupported Python raises `SupportError` or a wrapped install validation error
    Expected: install preflight does not proceed when the current interpreter is below the supported floor
    Evidence: .sisyphus/evidence/task-2-doctor-preflight-error.txt
  ```

  **Commit**: YES | Message: `test(cli): enforce current-python preflight checks` | Files: `src/openclaw_enhance/cli.py` if needed, `src/openclaw_enhance/install/installer.py` if needed, related tests

- [x] 3. Rewrite install/operator docs so current Python is the default deployment model

  **What to do**: Update `docs/install.md` so installation instructions use the current Python environment directly. Replace the `.venv` creation block with guidance like: ensure the current interpreter is Python >=3.10, optionally activate an existing env if desired, then run `pip install -e ".[dev]"`. Update any troubleshooting or operator-facing docs that imply a separate env is required, and adjust doc tests if they assume the old wording. Keep compatibility language: existing venv users are fine, but a new venv is no longer recommended as the default step.
  **Must NOT do**: Do not introduce dependency-manager-specific instructions (`uv`, `conda`, `pipx`, `poetry`). Do not remove `python -m openclaw_enhance.cli ...` usage.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: primarily documentation alignment with a precise operational message
  - Skills: [`writing-plans`] — keep wording concise and consistent with runtime behavior
  - Omitted: [`frontend-ui-ux`] — documentation only

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 4 | Blocked By: 1

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `docs/install.md:53` — current setup flow still recommends `python -m venv .venv`
  - Pattern: `docs/install.md:70` — doctor command is already documented as the environment check
  - Pattern: `docs/troubleshooting.md:12` — troubleshooting already anchors on `doctor`, likely the right place to mention unsupported current Python
  - Pattern: `tests/unit/test_docs_examples.py:99` — install docs example coverage already exists
  - Pattern: `pyproject.toml:11` — exact supported Python floor to document
  - Pattern: `tests/e2e/test_openclaw_harness.py:248` — current interpreter invocation pattern to preserve conceptually in docs

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_docs_examples.py -q` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
content = Path('docs/install.md').read_text(encoding='utf-8')
assert 'python -m venv .venv' not in content
assert '>=3.10' in content or 'Python 3.10' in content
assert 'current Python environment' in content or 'current interpreter' in content
print('docs-current-python-ok')
PY` exits `0`
  - [ ] `grep -q "python -m openclaw_enhance.cli doctor" docs/install.md` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Install docs now describe current-interpreter deployment
    Tool: Bash
    Steps: run the acceptance snippet and `grep -n "current Python environment\|current interpreter\|3.10" docs/install.md`
    Expected: docs no longer instruct creating `.venv` first and clearly state the current interpreter requirement
    Evidence: .sisyphus/evidence/task-3-docs-current-python.txt

  Scenario: Existing operator flow still points users to doctor rather than env creation
    Tool: Bash
    Steps: run `grep -n "doctor --openclaw-home" docs/install.md docs/troubleshooting.md`
    Expected: troubleshooting/install flow points to `doctor` for environment validation instead of telling users to create a new environment
    Evidence: .sisyphus/evidence/task-3-docs-current-python-error.txt
  ```

  **Commit**: YES | Message: `docs(install): default to current python environment` | Files: `docs/install.md`, related docs/tests as needed

- [x] 4. Run final drift review so validation, docs, and tests all describe the same deployment model

  **What to do**: Perform a final pass across validation code, CLI/install flow, and docs. Confirm the project now consistently says: use the current Python interpreter if it satisfies >=3.10; a venv is optional isolation, not a required deployment step; `doctor`/preflight are the enforcement points. Fix any stale wording or mismatched tests. Re-run the focused verification commands and ensure no place still implies that install creates or requires a separate env.
  **Must NOT do**: Do not broaden into packaging redesign or toolchain migration.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: cross-file reconciliation plus verification burden
  - Skills: [`verification-before-completion`] — evidence-first final pass
  - Omitted: [`brainstorming`] — scope is already fixed

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: Final Verification | Blocked By: 1, 2, 3

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `src/openclaw_enhance/runtime/support_matrix.py` — final Python validation source
  - Pattern: `src/openclaw_enhance/cli.py:107` — doctor command user-facing validation entrypoint
  - Pattern: `src/openclaw_enhance/install/installer.py:122` — install preflight entrypoint
  - Pattern: `docs/install.md:53` — setup section to verify after rewrite
  - Pattern: `tests/unit/test_support_matrix.py` — validation behavior lock
  - Pattern: `tests/unit/test_cli_smoke.py` — CLI command availability
  - Pattern: `tests/unit/test_docs_examples.py:99` — docs examples lock

  **Acceptance Criteria** (agent-executable only):
  - [ ] `pytest tests/unit/test_support_matrix.py tests/unit/test_cli_smoke.py tests/unit/test_docs_examples.py -q` exits `0`
  - [ ] `python -m openclaw_enhance.cli doctor --help` exits `0`
  - [ ] `python -m openclaw_enhance.cli docs-check` exits `0`
  - [ ] `python - <<'PY'
from pathlib import Path
blob = '\n'.join([
    Path('docs/install.md').read_text(encoding='utf-8'),
    Path('docs/troubleshooting.md').read_text(encoding='utf-8') if Path('docs/troubleshooting.md').exists() else '',
])
assert 'python -m venv .venv' not in blob
assert 'current Python environment' in blob or 'current interpreter' in blob
print('final-current-python-alignment-ok')
PY` exits `0`

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Future user can deploy from the active interpreter without separate-env instructions
    Tool: Bash
    Steps: run the final alignment snippet plus the focused test suite
    Expected: validation/tests pass and no install/troubleshooting docs still instruct creating a new env as the default path
    Evidence: .sisyphus/evidence/task-4-final-alignment.txt

  Scenario: Validation and docs agree on the supported current interpreter floor
    Tool: Bash
    Steps: run `grep -n ">=3.10\|Python 3.10" docs/install.md src/openclaw_enhance/runtime/support_matrix.py pyproject.toml`
    Expected: docs, runtime validation, and packaging metadata all align on the same minimum supported Python version
    Evidence: .sisyphus/evidence/task-4-final-alignment-error.txt
  ```

  **Commit**: YES | Message: `docs(runtime): align deployment with current python` | Files: validation code, CLI/install flow if touched, docs, tests

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [x] F1. Plan Compliance Audit — oracle ✅ All 4 tasks complete, deliverables present
- [x] F2. Code Quality Review — unspecified-high ✅ 35 tests pass, docs-check passes, clean code
- [x] F3. Real Manual QA — unspecified-high ✅ CLI works, Python 3.13 supported, commits verified
- [x] F4. Scope Fidelity Check — deep ✅ Current Python model, no venv creation, docs aligned

## Commit Strategy
- Commit Task 1 separately from Task 2 so the shared validator lands before lifecycle/test adjustments.
- Keep docs-only changes in their own commit.
- Final alignment/polish commit should only reconcile wording or test drift left after the earlier atomic units.

## Success Criteria
- The project no longer implies that deployment requires creating a new Python environment.
- `doctor` and installer preflight explicitly validate the current interpreter against the supported Python floor.
- Docs tell users to use the current Python environment by default, while still allowing existing venv users to continue.
- Tests and validation consistently reinforce current-interpreter deployment and reject unsupported Python versions.
