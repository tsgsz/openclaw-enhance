Normalized validate-feature contract to use --feature-class and --report-slug across all durable docs and checks.
- Expanded docs/testing-playbook.md with a "Current branch shipped set" matrix.
- Defined canonical backfill slugs for core capabilities: core-install, dev-install, cli-surface, routing-yield, recovery-worker, watchdog-reminder.
- Mapped each slug to a FeatureClass and defined explicit method contracts and observable proofs.
- This matrix serves as the source of truth for backfilling validation reports in subsequent tasks.
- Fixed heading case in docs/testing-playbook.md to match exact acceptance criteria (Current branch shipped set).
- Verified that grep -q is case-sensitive by default and requires exact matches for automated acceptance checks.

## Task 3: Validation Matrix Implementation

**Pattern**: Declarative catalog with typed entries
- Used simple list of dicts with FeatureClass enum for type safety
- Followed agent_catalog.py pattern: constants + lookup function
- Minimal API: SHIPPED_FEATURES constant + get_feature_entry() lookup

**Test Strategy**: Canonical slug inventory verification
- Test fails if required slugs missing (guards against accidental deletion)
- Test verifies FeatureClass mapping for each entry
- Test covers both successful and missing slug lookups

**Integration Points**:
- Compatible with existing ValidationReport.get_report_path()
- Aligns with FeatureClass enum in types.py
- Ready for CLI validate-feature command consumption

**Evidence**: All tests pass, import check confirms slug set integrity

## Task 4: Guardrails and Runner Semantics

### Harness Readiness Checks
- Added `_verify_harness_readiness()` to guardrails.py checking VERSION, config.json, and home existence
- Integrated into `capture_baseline_state()` so readiness failures happen before any validation work
- Failures raise RuntimeError with "unsupported/missing-home" prefix for clear classification
- Tests confirm readiness failures are distinguishable from product failures

### Cleanup Verification Enforcement
- Runner now captures initial and final guardrail state for install-lifecycle scenarios
- Calls `verify_cleanup_success()` after install-lifecycle command execution
- Cleanup failures result in PRODUCT_FAILURE with explicit "Cleanup verification failed" finding
- Only enforced for INSTALL_LIFECYCLE feature class to avoid overhead on other scenarios

### Docs-Test-Only Semantics
- Changed from no-op to executing `docs-check` command for evidence
- Still concludes EXEMPT but now records command result in report
- Finding updated to: "Exempt from real-environment testing (docs-check executed for evidence)"
- This makes the exemption explicit while providing audit trail of docs validation

### Test Coverage
- Added 3 new harness readiness tests to test_real_env_guardrails.py
- Updated all runner tests to mock guardrail state capture
- Updated integration test for docs-test-only to verify docs-check execution
- All 33 tests pass with proper mocking of new guardrail behavior
