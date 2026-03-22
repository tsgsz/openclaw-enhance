
## before_tool_call Handler Bug (Wave 1)

**Issue**: oe-runtime's before_tool_call handler crashes with `TypeError: Cannot read properties of undefined (reading 'startsWith')`
- The error is in the handler's own code, not in event dispatch
- Handler tries to call `.startsWith()` on something that is undefined
- Does NOT indicate a problem with OpenClaw's hook/plugin system

**Impact**: Every tool call triggers this crash, flooding gateway.err.log
**Next**: Fix the oe-runtime before_tool_call handler to handle undefined values gracefully

## ACPX/OpenCode Verification (Wave 1, Task 4)

**Caveats / Open Questions**:
1. ACP sessions exist but all are from 2026-03-07 — no recent sessions visible. May indicate sessions expire/rotate.
2. The `opencode` binary itself was not verified for availability (CLI check not performed per read-only constraints).
3. The exact `sessions_spawn` parameters for ACP beyond `runtime="acp"`, `agentId`, `mode`, `cwd`, `task` were not exhaustively verified — only the canonical documented shape was confirmed.
4. Whether `harness` parameter is required vs inferred from `agentId` when `runtime="acp"` is used — not tested.
5. The `oe-worker-dispatch` skill has no ACP branch — this is the confirmed gap for later implementation.
