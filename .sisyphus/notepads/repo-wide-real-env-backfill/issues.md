2026-03-15: F2 verification failure in tests/integration/test_validation_real_env.py
- Failing tests:
  - TestValidateFeatureCommandOrdering.test_install_lifecycle_command_order
  - TestValidateFeatureCommandOrdering.test_install_lifecycle_dev_mode_slug
- Symptom: mocked subprocess.run call list is empty (`len(calls)==0`), expected >=5.
- Likely cause: validate-feature exits before command execution due harness readiness guardrail assumptions against temp openclaw home in tests.
- Required fix: update tests and/or runner readiness gating so install-lifecycle ordering tests exercise command bundle under patched subprocess without breaking guardrails contract.
