Rewrote docs/testing-playbook.md to be a decision-complete validation contract. Defined feature classes, command bundles, and report locations.

### Real-Environment Validation Module
- Encoded the feature-class matrix from `docs/testing-playbook.md` into `FeatureClass` enum and `get_bundle_commands` mapping.
- Standardized report path generation using `ValidationReport.get_report_path`.
- Followed existing dataclass and enum patterns from `manifest.py` and `schema.py`.
- Used `datetime.utcnow()` for consistency with the rest of the codebase, despite deprecation warnings in newer Python versions.

## Task 3: Baseline State Capture and Cleanup Guardrails

Created `src/openclaw_enhance/validation/guardrails.py` with minimal baseline capture logic:
- `BaselineState` dataclass tracks: openclaw_home, is_installed, owned_by_checkout, config_state, managed_root_state
- `capture_baseline_state()` captures state before validation
- `verify_ownership()` checks if target belongs to current checkout (dev mode symlinks indicate ownership)
- `verify_cleanup_success()` compares before/after states
- `ForeignStateError` raised when attempting to mutate foreign installations

Ownership detection: Checks for workspace symlinks (dev mode indicator). Production installs without symlinks are considered foreign.

Config state capture: Records existence, enhance namespace presence, and enhance config content.

Managed root state: Records directory contents with type flags (dir/symlink).

All 9 unit tests pass. Module imports successfully.

## Task 4: Runner Layer and Markdown Reporting

Created `src/openclaw_enhance/validation/runner.py` and `src/openclaw_enhance/validation/reporting.py`:

- `execute_command()` runs commands via subprocess, captures stdout/stderr/exit codes/duration
- `run_scenario()` orchestrates full validation: baseline capture, ownership verification, command execution, conclusion determination
- `build_report_path()` generates standard report path: `YYYY-MM-DD-slug-feature-class.md`
- `generate_markdown_report()` creates structured markdown with execution log, baseline state, findings
- `write_report()` writes report to disk with parent directory creation

Key design decisions:
- Two `BaselineState` classes exist (guardrails.py vs types.py) - used types.py version for ValidationReport compatibility
- Created `_capture_baseline()` helper to bridge between guardrails ownership checks and types.BaselineState
- Exit code 127 = environment failure (command not found), other non-zero = product failure
- DOCS_TEST_ONLY feature class returns EXEMPT conclusion without execution
- Markdown report includes pass/fail indicators (✓/✗), command output blocks, duration metrics

All 10 unit tests pass. Module imports successfully. Evidence saved to `.sisyphus/evidence/`.

### Task 5: CLI Entrypoint for Validation
- Added `validate-feature` command to `openclaw_enhance.cli`.
- Command requires `--feature-class` and `--report-slug`.
- Defaults `--openclaw-home` to `~/.openclaw` and `--reports-dir` to `docs/reports`.
- Successfully integrated `run_scenario` and `write_report`.
- Verified with smoke tests and `--help` output.

## Task 7: Harness Real-Environment Validation Coverage

Added `TestHarnessRealEnvironmentValidation` class with `test_real_env_validation_install_lifecycle()` to exercise the validation runner through actual CLI commands.

**Key patterns:**
- Test uses `--feature-class` and `--report-slug` flags (not positional args)
- Exit codes: 0 (pass), 1 (product failure), 2+ (environment/usage error)
- Test validates both execution and report generation
- Accepts exit code 0 or 1 since we're testing harness integration, not product state
- Clean skip when OPENCLAW_HARNESS not set (module-level pytestmark)

**Verification:**
- Without harness: `pytest -k real_env` → 1 skipped cleanly
- With harness: `OPENCLAW_HARNESS=1 pytest -k real_env` → 1 passed, report generated
## Task 9: Report Schema and Examples
- Established docs/reports/ structure for real-environment validation.
- Defined naming convention: YYYY-MM-DD-slug-feature-class.md.
- Created canonical template matching reporting.py logic.
- Provided examples for critical, behavior, and exempt feature classes.
- Reports serve as permanent audit trails for feature merges.

## Documentation Integration (Task 8)
- Updated AGENTS.md, handbook, install, and operations docs to require real-environment validation.
- Integrated `validate-feature` command into the standard development workflow.
- Updated `test_docs_examples.py` to ensure new CLI examples are tracked.
- All durable docs now align on the mandatory gate: features cannot be merged without a successful report in `docs/reports/`.

## Task 6: Integration Tests for validate-feature

### Test Structure
- Created `tests/integration/test_real_env_validation.py` with 10 comprehensive tests
- Used `@patch("openclaw_enhance.validation.runner.subprocess.run")` to mock subprocess calls
- Fixtures: `mock_openclaw_home` and `reports_dir` for isolated test environments

### CLI Command Structure
- Command: `validate-feature --feature-class <class> --report-slug <slug>`
- Exit codes: 0 for PASS/EXEMPT, 1 for PRODUCT_FAILURE/ENVIRONMENT_FAILURE
- Reports written to: `{reports_dir}/{date}-{slug}-{feature-class}.md`

### Test Coverage
1. **Report Creation** (2 tests): File creation, baseline state in reports
2. **Command Ordering** (2 tests): Install lifecycle sequence, CLI surface render commands
3. **Exemptions** (2 tests): docs-test-only exempt status, no subprocess execution
4. **Failure Classification** (3 tests): Exit 127 → ENVIRONMENT_FAILURE, Exit 1 → PRODUCT_FAILURE, Exit 0 → PASS
5. **Cleanup Verification** (1 test): Baseline captured before execution

### Key Patterns
- Mock subprocess with `MagicMock(returncode=X, stdout="", stderr="")`
- Use Click's `CliRunner()` for CLI testing
- Glob patterns for report file discovery: `reports_dir.glob("*-{slug}-{class}.md")`
- Assert exit codes match validation conclusions (failures exit 1, not 0)

### Test Results
- All 10 tests pass
- Evidence saved to `.sisyphus/evidence/task-6-real-env-integration.txt`
