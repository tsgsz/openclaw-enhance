# Validation Report Inventory

This document tracks canonical and superseded validation reports for openclaw-enhance, including the Canonical Current-Branch Backfill.

## Canonical Current-Branch Backfill

These are the authoritative validation reports for each feature slug:

| Slug | Report File | Date | Conclusion |
|------|-------------|------|------------|
| backfill-core-install | [2026-03-14-backfill-core-install-install-lifecycle.md](./2026-03-14-backfill-core-install-install-lifecycle.md) | 2026-03-14 | PASS |
| backfill-dev-install | [2026-03-14-backfill-dev-install-install-lifecycle.md](./2026-03-14-backfill-dev-install-install-lifecycle.md) | 2026-03-14 | PASS |
| backfill-cli-surface | [2026-03-14-backfill-cli-surface-cli-surface.md](./2026-03-14-backfill-cli-surface-cli-surface.md) | 2026-03-14 | PASS |
| backfill-routing-yield | [2026-03-15-backfill-routing-yield-workspace-routing.md](./2026-03-15-backfill-routing-yield-workspace-routing.md) | 2026-03-15 | PASS |
| backfill-recovery-worker | [2026-03-15-backfill-recovery-worker-workspace-routing.md](./2026-03-15-backfill-recovery-worker-workspace-routing.md) | 2026-03-15 | PASS |
| backfill-watchdog-reminder | [2026-03-15-backfill-watchdog-reminder-runtime-watchdog.md](./2026-03-15-backfill-watchdog-reminder-runtime-watchdog.md) | 2026-03-15 | PASS |

## Superseded Reports

These reports have been replaced by newer canonical versions:

| Report File | Date | Superseded By | Reason |
|-------------|------|---------------|--------|
| [2026-03-15-backfill-core-install-install-lifecycle.md](./2026-03-15-backfill-core-install-install-lifecycle.md) | 2026-03-15 | 2026-03-14-backfill-core-install-install-lifecycle.md | Validation framework change; 2026-03-14 version is canonical |
| [2026-03-15-backfill-dev-install-install-lifecycle.md](./2026-03-15-backfill-dev-install-install-lifecycle.md) | 2026-03-15 | 2026-03-14-backfill-dev-install-install-lifecycle.md | Validation framework change; 2026-03-14 version is canonical |
| [2026-03-15-backfill-cli-surface-cli-surface.md](./2026-03-15-backfill-cli-surface-cli-surface.md) | 2026-03-15 | 2026-03-14-backfill-cli-surface-cli-surface.md | Validation framework change; 2026-03-14 version is canonical |
| [2026-03-14-backfill-routing-yield-workspace-routing.md](./2026-03-14-backfill-routing-yield-workspace-routing.md) | 2026-03-14 | 2026-03-15-backfill-routing-yield-workspace-routing.md | Replaced by live runtime-surface proof using real OpenClaw agent/session metadata |
| [2026-03-14-backfill-recovery-worker-workspace-routing.md](./2026-03-14-backfill-recovery-worker-workspace-routing.md) | 2026-03-14 | 2026-03-15-backfill-recovery-worker-workspace-routing.md | Replaced by live runtime-surface proof using real OpenClaw agent/session metadata |
| [2026-03-14-backfill-watchdog-reminder-runtime-watchdog.md](./2026-03-14-backfill-watchdog-reminder-runtime-watchdog.md) | 2026-03-14 | 2026-03-15-backfill-watchdog-reminder-runtime-watchdog.md | Replaced by regenerated live watchdog proof on the current runtime contract |

## Notes

- The canonical routing/recovery reports use the strongest honest runtime-backed proof available in the current OpenClaw environment: real session creation, live tool surface, transcript-path discovery, and initialized runtime identity.
- The superseded 2026-03-14 routing/recovery reports relied on static render-oriented proof instead of runtime-backed OpenClaw evidence.
- The canonical watchdog report is now the regenerated 2026-03-15 runtime-watchdog PASS report.
