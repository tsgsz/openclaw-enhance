# Validation Report Inventory

This document tracks canonical and superseded validation reports for openclaw-enhance, including the Canonical Current-Branch Backfill.

## Canonical Reports

These are the authoritative validation reports for each feature slug:

| Slug | Report File | Date | Conclusion |
|------|-------------|------|------------|
| backfill-core-install | [2026-03-14-backfill-core-install-install-lifecycle.md](./2026-03-14-backfill-core-install-install-lifecycle.md) | 2026-03-14 | PASS |
| backfill-dev-install | [2026-03-14-backfill-dev-install-install-lifecycle.md](./2026-03-14-backfill-dev-install-install-lifecycle.md) | 2026-03-14 | PASS |
| backfill-cli-surface | [2026-03-14-backfill-cli-surface-cli-surface.md](./2026-03-14-backfill-cli-surface-cli-surface.md) | 2026-03-14 | PASS |
| backfill-routing-yield | [2026-03-14-backfill-routing-yield-workspace-routing.md](./2026-03-14-backfill-routing-yield-workspace-routing.md) | 2026-03-14 | PASS |
| backfill-recovery-worker | [2026-03-14-backfill-recovery-worker-workspace-routing.md](./2026-03-14-backfill-recovery-worker-workspace-routing.md) | 2026-03-14 | PASS |
| backfill-watchdog-reminder | [2026-03-14-backfill-watchdog-reminder-runtime-watchdog.md](./2026-03-14-backfill-watchdog-reminder-runtime-watchdog.md) | 2026-03-14 | PASS |

## Superseded Reports

These reports have been replaced by newer canonical versions:

| Report File | Date | Superseded By | Reason |
|-------------|------|---------------|--------|
| [2026-03-15-backfill-core-install-install-lifecycle.md](./2026-03-15-backfill-core-install-install-lifecycle.md) | 2026-03-15 | 2026-03-14-backfill-core-install-install-lifecycle.md | Validation framework change; 2026-03-14 version is canonical |
| [2026-03-15-backfill-dev-install-install-lifecycle.md](./2026-03-15-backfill-dev-install-install-lifecycle.md) | 2026-03-15 | 2026-03-14-backfill-dev-install-install-lifecycle.md | Validation framework change; 2026-03-14 version is canonical |
| [2026-03-15-backfill-cli-surface-cli-surface.md](./2026-03-15-backfill-cli-surface-cli-surface.md) | 2026-03-15 | 2026-03-14-backfill-cli-surface-cli-surface.md | Validation framework change; 2026-03-14 version is canonical |
| [2026-03-15-backfill-routing-yield-workspace-routing.md](./2026-03-15-backfill-routing-yield-workspace-routing.md) | 2026-03-15 | 2026-03-14-backfill-routing-yield-workspace-routing.md | Environment incompatibility (openclaw chat command missing) |
| [2026-03-15-backfill-recovery-worker-workspace-routing.md](./2026-03-15-backfill-recovery-worker-workspace-routing.md) | 2026-03-15 | 2026-03-14-backfill-recovery-worker-workspace-routing.md | Environment incompatibility (openclaw chat command missing) |
| [2026-03-15-backfill-watchdog-reminder-runtime-watchdog.md](./2026-03-15-backfill-watchdog-reminder-runtime-watchdog.md) | 2026-03-15 | 2026-03-14-backfill-watchdog-reminder-runtime-watchdog.md | Validation framework change; 2026-03-14 version is canonical |

## Notes

- The 2026-03-14 reports use a validation approach compatible with OpenClaw 2026.3.12
- The 2026-03-15 reports attempted to use live probes requiring `openclaw chat`, which is not available in the current environment
- All canonical reports contain strict proof markers as required by the validation contract
