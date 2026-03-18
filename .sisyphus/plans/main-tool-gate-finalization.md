# Plan: Main Tool Gate Finalization

## TL;DR

> Finalize the main-to-orchestrator routing fix by updating docs, cleaning up files, committing, and merging.
> All implementation is done. This is cleanup + commit only.

## Context

All implementation is complete in worktree `fix-main-orch-routing-gaps`:

1. `src/openclaw_enhance/install/main_tool_gate.py` — Install-time AGENTS.md injection (idempotent, marker-delimited)
2. `src/openclaw_enhance/install/installer.py` — Calls inject on install
3. `src/openclaw_enhance/install/uninstaller.py` — Calls remove on uninstall
4. `skills/oe-toolcall-router/SKILL.md` — v2.0 "main = router only"
5. `extensions/openclaw-enhance-runtime/index.ts` — Plugin with before_tool_call gate (backup)
6. `hooks/oe-main-routing-gate/` — Advisory hook (secondary)

Tests pass: npm test 15/15, pytest 315/315.

## TODOs

- [x] 1. Update handbook invariant

  **What to do**:
  - Edit `docs/opencode-iteration-handbook.md` line 142-145
  - Change `No runtime modifications to main's AGENTS.md/TOOLS.md`
  - To: `No **runtime** modifications to main's AGENTS.md/TOOLS.md. **Install-time injection is allowed**: installer may append idempotent, marker-delimited blocks. Must be cleanly removable by uninstaller.`

  **Recommended Agent Profile**: `quick`

- [ ] 2. Add milestone to handbook

  **What to do**:
  - Add `main-tool-gate-enforcement` milestone to Permanent Progress Record
  - Date: 2026-03-18, Scope: Main session enforced as router-only via install-time AGENTS.md injection

  **Recommended Agent Profile**: `quick`

- [x] 3. Clean up unnecessary files

  **What to do**:
  - Remove `scripts/test_channel_escalation.py`
  - Remove `extensions/openclaw-enhance-runtime/src/before-prompt-build.ts`
  - Remove `extensions/openclaw-enhance-runtime/src/before-tool-call.ts`
  - Remove `.openclaw/` directory from worktree
  - Remove `config.json.model-pin.lock`

  **Recommended Agent Profile**: `quick`

- [x] 4. Update validation report

  **What to do**:
  - Update `docs/reports/2026-03-17-backfill-main-escalation-workspace-routing.md`
  - Change conclusion to `CONDITIONAL_PASS`
  - Document: AGENTS.md injection verified, plugin loaded, CLI probe limited by architecture

  **Recommended Agent Profile**: `quick`

- [x] 5. Run docs-check and fix issues

  **What to do**:
  - Run `python -m openclaw_enhance.cli docs-check`
  - Fix any alignment issues

  **Recommended Agent Profile**: `quick`

- [x] 6. Commit all changes

  **What to do**:
  - `git add` all modified and new files
  - Commit: `feat(main-tool-gate): enforce main as router-only via install-time AGENTS.md injection`

  **Recommended Agent Profile**: `quick`

- [x] 7. Merge to main and cleanup worktree

  **What to do**:
  - Merge `fix-main-orch-routing-gaps` into main
  - Clean up worktree

  **Recommended Agent Profile**: `quick`

## Success Criteria

- [ ] npm test passes
- [ ] pytest unit passes
- [ ] docs-check passes
- [ ] Handbook invariant updated
- [ ] Milestone recorded
- [ ] All changes committed and merged
