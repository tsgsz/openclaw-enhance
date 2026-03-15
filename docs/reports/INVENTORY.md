# Validation Report Inventory

This document tracks the canonical validation reports for the current branch and maintains a record of superseded reports.

## Canonical Current-Branch Backfill

These reports represent the baseline validation for core primitives in the current branch.

| Feature Capability | Canonical Slug | Feature Class | Report File | Status |
| :--- | :--- | :--- | :--- | :--- |
| Core Installation | `backfill-core-install` | `install-lifecycle` | `2026-03-15-backfill-core-install-install-lifecycle.md` | PASS |
| Dev Mode (Symlinks) | `backfill-dev-install` | `install-lifecycle` | `2026-03-15-backfill-dev-install-install-lifecycle.md` | PASS |
| CLI Surface Area | `backfill-cli-surface` | `cli-surface` | `2026-03-15-backfill-cli-surface-cli-surface.md` | PASS |
| Orchestrator Yield | `backfill-routing-yield` | `workspace-routing` | `2026-03-15-backfill-routing-yield-workspace-routing.md` | PASS |
| Recovery Worker | `backfill-recovery-worker` | `workspace-routing` | `2026-03-15-backfill-recovery-worker-workspace-routing.md` | PASS |
| Watchdog Hooks | `backfill-watchdog-reminder` | `runtime-watchdog` | `2026-03-15-backfill-watchdog-reminder-runtime-watchdog.md` | PASS |

## Superseded Reports

These reports have been replaced by newer versions or are from previous architectural milestones.

| Date | Slug | Feature Class | Reason for Supersession |
| :--- | :--- | :--- | :--- |
| 2026-03-13 | `initial-install-test` | `install-lifecycle` | Replaced by canonical backfill |
| 2026-03-13 | `router-smoke-test` | `workspace-routing` | Replaced by canonical backfill |
