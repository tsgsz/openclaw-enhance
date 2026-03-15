# Validation Reports

This directory contains real-environment validation reports for `openclaw-enhance`. Every feature or bugfix that affects runtime behavior must have a corresponding report here before it can be merged.

## Purpose

Real-environment validation ensures that changes work correctly within the actual OpenClaw environment, beyond what unit and integration tests can verify. These reports provide an audit trail of successful deployments and operations.

## Naming Convention

Reports must follow this naming pattern:
`YYYY-MM-DD-<slug>-<feature-class>.md`

- **YYYY-MM-DD**: The date the validation was performed.
- **slug**: A short, hyphenated description of the change (e.g., `fix-path-resolution`).
- **feature-class**: One of the classes defined in the [Testing Playbook](../testing-playbook.md).

Example: `2026-03-14-fix-agent-routing-workspace-routing.md`

## Report Schema

Each report must include the following sections:

1. **Header**: `# Validation Report: [Feature Name]`
2. **Metadata**:
   - **Date**: YYYY-MM-DD
   - **Feature Class**: The class being tested.
   - **Environment**: OS and environment details (e.g., macOS, default `~/.openclaw`).
   - **Conclusion**: `PASS`, `PRODUCT_FAILURE`, `ENVIRONMENT_FAILURE`, or `EXEMPT`.
3. **Baseline State**: The state of the environment before testing began (OpenClaw home, installation status, version).
4. **Execution Log**: A detailed log of every command executed, including its exit code, duration, and output (stdout/stderr).
5. **Findings**: (Optional) Any observations, minor issues, or notes discovered during validation.

## Retention Policy

Validation reports are permanent records. They should be committed to the repository along with the code changes they validate. The [INVENTORY.md](./INVENTORY.md) tracks the canonical status of these reports. Do not delete reports unless they were created in error or are being replaced by a more accurate version for the same change.

## Strict Proof Bundles

All reports must align with the "Strict Proof" bundles defined in the [Testing Playbook](../testing-playbook.md). This means every PASS conclusion must be backed by observable evidence from `openclaw.json` or CLI output.

## Templates and Examples

- [Canonical Template](./template.md)
- [Inventory](./INVENTORY.md)
- [Examples](./examples/)
