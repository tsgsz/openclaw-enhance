
## before_tool_call Event Verification (Wave 1, Task 1)

**Date**: 2026-03-22
**Finding**: CONFIRMED - `before_tool_call` event IS firing for oe-runtime plugin

**Evidence**: `~/.openclaw/logs/gateway.err.log` shows repeated crash entries:
```
[plugins] [hooks] before_tool_call handler from oe-runtime failed: TypeError: Cannot read properties of undefined (reading 'startsWith')
```

**Timestamps observed**: 11:41 through 11:45 on 2026-03-22, continuous stream (~30+ failures)

**Implication**: The event fires correctly and reaches the oe-runtime handler. The crash happens INSIDE the handler (unrelated to event wiring) - the handler tries to call `.startsWith()` on an undefined value. This means OpenClaw's plugin hook system is functioning correctly for before_tool_call.

## ACPX/OpenCode Infrastructure Verification (Wave 1, Task 4)

**Date**: 2026-03-22

### ACPX Configuration (from ~/.openclaw/openclaw.json)
- `acp.enabled: true` (line 54)
- `backend: "acpx"` (line 55)
- `defaultAgent: "opencode"` (line 56)
- `allowedAgents: ["opencode", "codex", "claude"]` (lines 57-61)
- `maxConcurrentSessions: 8`, `runtime.ttlMinutes: 30`
- Plugin `acpx` in `plugins.entries` with `enabled: true` (line 946-948)

### OpenCode Config (from ~/.config/opencode/opencode.json)
- File exists (90 lines) with providers: `sss`, `sss-us`, `sss-reverse-hk`, `cliproxy`
- Each provider has model definitions
- Plugin entry: `oh-my-opencode`

### ACP Session History (from ~/.acpx/sessions/)
- 6 historical ACP sessions dated 2026-03-07
- Session IDs: ses_3376a21e9ffeU3C15qAzjyNBa3, ses_337795d37ffejN7sKHRnTDWWUA, ses_3377c6cbfffePoow6s8z3JM6gr, ses_337c0185cffeWFm5wFtJMqYkMq, ses_337d9e6b0ffegP7N8RNChFy4qx, ses_3383bd86cffe08QyhRWj5gLR1Z
- All have .stream.ndjson event files

### ACP sessions_spawn Shape (canonical from openclaw-subagent-mechanism.md)
```json
sessions_spawn(
  runtime="acp",
  agentId="opencode",
  mode="persistent",
  cwd=project_root,
  task="..."
)
```
Default: harness=opencode, mode=persistent, cwd via project mechanism

### oe-worker-dispatch Gap
- Skill's dispatch examples (lines 384-424) only show OpenClaw agent dispatch via `agentId`
- NO ACP branch exists — skill does NOT dispatch to ACP opencode harness
- Confirms planning finding: ACP branch needed
