# Operations Guide

This guide covers day-to-day operations with `openclaw-enhance`.

## v2 Architecture Overview

**openclaw-enhance v2 采用纯 Skill 架构**：
- **无工作区 (Workspaces)**：v1 的 agent 工作区已归档至 `~/.openclaw/openclaw-enhance/v1-archive/`
- **无 Agent 注册**：不再使用 `oe-orchestrator`、`oe-searcher` 等托管 Agent
- **纯 Skill 路由**：所有路由逻辑通过 Skills 实现，使用 OpenClaw 原生的 `sessions_spawn` 机制

## Overview

Once installed, `openclaw-enhance` operates transparently:
- **Main session** gets routing skills for task assessment
- **Complex tasks** automatically escalate via sessions_spawn
- **Skills** handle specialized subtasks
- **Watchdog** monitors for timeouts

You interact with OpenClaw normally—the enhancement layer handles complexity behind the scenes.

**How Routing Works**: The `oe-tag-router` skill guides routing decisions. Tasks are dispatched via native `sessions_spawn` to appropriate skills (oe-spawn-search, oe-spawn-coder, oe-spawn-ops).

## Tag-Based Routing

The `oe-tag-router` skill implements tag-based routing:

1. **Tag Extraction**: Analyze task to extract intent tags
2. **Tag Matching**: Match tags to appropriate skills
3. **Dispatch**: Spawn the matched skill via sessions_spawn

### Routing Examples

| Task Type | Tags | Skill |
|-----------|------|-------|
| Research, web search | `research`, `search`, `lookup` | oe-spawn-search |
| Code writing, testing | `code`, `write`, `test`, `implement` | oe-spawn-coder |
| Ops, tunnels, backup | `ops`, `backup`, `deploy`, `tunnel` | oe-spawn-ops |
| Project context | `project`, `context` | oe-project-context |
| Git history | `git`, `history`, `log` | oe-git-context |

## Task Routing Examples

### Example 1: Simple Task (Stays on Main)

**User**: "What time is it?"

**Flow**:
1. `oe-eta-estimator` estimates 1 TOOLCALL
2. `oe-tag-router` decides: handle locally
3. Main session responds directly

### Example 2: Complex Task (Escalates via sessions_spawn)

**User**: "Refactor the auth module to use JWT tokens"

**Flow**:
1. `oe-eta-estimator` estimates 8 TOOLCALLs, 20 minutes
2. `oe-tag-router` escalates via `sessions_spawn`
3. oe-spawn-coder handles:
   - Find auth-related files (via oe-git-context)
   - Research JWT best practices (via oe-spawn-search)
   - Implement changes
4. Returns to main session

### Example 3: Research Task

**User**: "Compare TypeScript vs Python for our new service"

**Flow**:
1. Main routes to oe-spawn-search
2. oe-spawn-search:
   - Research TypeScript ecosystem
   - Research Python ecosystem
   - Find comparison benchmarks
3. Returns structured analysis

## Session Cleanup Command

`python -m openclaw_enhance.cli cleanup-sessions` provides a conservative cleanup surface for stale session state.

**Safety model**:
- Defaults to dry-run when `--execute` is not provided
- Supports protected cleanup of OpenClaw core sessions only with `--include-core-sessions`
- Classifies candidates into `safe_to_remove`, `skipped_active`, and `skipped_uncertain`
- Only `safe_to_remove` targets may be deleted during execute mode

**Intended use**:
- Clear stale/orphaned enhance-managed session state
- Clear stale/orphaned agent session files under `--openclaw-home` when used by the managed cleanup LaunchAgent
- Preview cleanup candidates before destructive action
- Recover from accumulated stale session artifacts without touching active sessions

**Managed automation**:
- On macOS install, `ai.openclaw.session-cleanup` runs this cleanup surface hourly via `python -m openclaw_enhance.cleanup --execute --openclaw-home <...> --json`
- The automatic LaunchAgent path is intentionally conservative: it cleans clearly stale non-core artifacts by default, while `--include-core-sessions` remains a manual operator choice.

## Governance CLI Surface

`openclaw-enhance` owns the supported replacement for the legacy governance scripts.

| Legacy script | OE-managed replacement |
|---|---|
| `diagnose_stuck.sh` | `python -m openclaw_enhance.cli governance diagnose --json` |
| `healthcheck_openclaw.sh` | `python -m openclaw_enhance.cli governance healthcheck --json` |
| `safe_gateway_restart.py` | `python -m openclaw_enhance.cli governance safe-restart --dry-run --json` |
| `immediate_restart_resume.py` | `python -m openclaw_enhance.cli governance restart-resume --json` |
| `session_archiver.py` | `python -m openclaw_enhance.cli governance archive-sessions --dry-run --json` |
| `sub_agentsctl.py` | `python -m openclaw_enhance.cli governance subagents ...` |

## Timeout Monitoring

### How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   monitor   │────▶│  Runtime    │────▶│  Timeout    │
│   script    │     │   Store     │     │  Detector   │
└─────────────┘     └─────────────┘     └─────────────┘
   (1 min)             (state)             (confirm)
```

1. **Monitor script** runs every minute
2. Detects sessions exceeding expected duration
3. Writes `timeout_suspected` event to runtime store
4. **Timeout Detector** confirms or rejects the suspicion
5. If confirmed: sends reminder to original session

### Checking Timeout State

View current timeout state:

```bash
# Read runtime state directly
cat ~/.openclaw/openclaw-enhance/state/runtime-state.json | jq '.timeouts'
```

Or use the enhancement CLI:

```bash
python -m openclaw_enhance.cli status --json | jq '.timeouts'
```

### Timeout States

| State | Meaning | Action |
|-------|---------|--------|
| `suspected` | Monitor detected possible timeout | Waiting for confirmation |
| `confirmed` | Timeout confirmed | Reminder sent to session |
| `cleared` | Timeout resolved | No action needed |
| `escalated` | Escalated to user | Manual intervention may be needed |

## Runtime State Management

### State Location

All runtime state is stored at:

```
~/.openclaw/openclaw-enhance/state/runtime-state.json
```

### State Structure

```json
{
  "version": "2.0.0",
  "last_updated_utc": "2026-04-09T10:30:00",
  "restart_epoch": 1,
  "tasks": {
    "task_abc123": {
      "status": "active",
      "skill": "oe-spawn-coder",
      "started_at": "2026-04-09T10:00:00",
      "eta_minutes": 20,
      "ownership": {
        "channel_type": "feishu",
        "channel_conversation_id": "conv_789"
      }
    }
  },
  "timeouts": {
    "task_abc123": {
      "status": "suspected",
      "detected_at": "2026-04-09T10:25:00"
    }
  },
  "projects": {
    "my-project": {
      "path": "/home/user/projects/my-project",
      "type": "python",
      "last_accessed": "2026-04-09T10:00:00"
    }
  }
}
```

## Session Isolation & Restart Safety

To prevent session collisions and hijacking, `openclaw-enhance` implements a strict ownership model.

### Collision Prevention
The system binds external identities to OpenClaw sessions using a composite key:
`(channel_type, channel_conversation_id) -> session_id`

### Fail-Closed Behavior
If session ownership cannot be verified, the system **fails closed**.

### Restart Epoch
Every time the OpenClaw gateway or enhance-monitor restarts, the `restart_epoch` is incremented.
- Existing session bindings are tagged with the epoch they were created in.
- After a restart, bindings from previous epochs are considered "stale".

## Output Sanitization

The `oe-runtime` extension automatically sanitizes outgoing content.

### Sanitized Markers
- `[Pasted ~]` (Internal clipboard marker)
- `<|tool_call...|>` (Internal tool call protocol)
- `<|thought...|>` (Internal reasoning protocol)

## CLI Commands

### Status

Check installation status:

```bash
python -m openclaw_enhance.cli status
```

### Doctor

Run health checks:

```bash
python -m openclaw_enhance.cli doctor --openclaw-home "$HOME/.openclaw"
```

### Render Skills

View skill contracts:

```bash
python -m openclaw_enhance.cli render-skill oe-tag-router
python -m openclaw_enhance.cli render-skill oe-eta-estimator
python -m openclaw_enhance.cli render-skill oe-spawn-coder
```

### Render Hooks

View hook contracts:

```bash
python -m openclaw_enhance.cli render-hook oe-subagent-spawn-enrich
```

### Feature Validation

Validate changes in a real environment:

```bash
# Validate installation lifecycle changes
python -m openclaw_enhance.cli validate-feature --feature-class install-lifecycle --report-slug backfill-core-install

# Validate CLI surface changes
python -m openclaw_enhance.cli validate-feature --feature-class cli-surface --report-slug backfill-cli-surface

# Validate routing changes
python -m openclaw_enhance.cli validate-feature --feature-class skill-routing --report-slug backfill-skill-routing

# Validate watchdog or hook changes
python -m openclaw_enhance.cli validate-feature --feature-class runtime-watchdog --report-slug backfill-watchdog-reminder
```

Reports are automatically saved to `docs/reports/`.

## Best Practices

### 1. Let the Router Decide

Don't manually choose skills. Let `oe-tag-router` decide based on task tags.

### 2. Provide Clear Task Descriptions

Better descriptions lead to better routing:

- ❌ "Fix the bug"
- ✅ "Fix the authentication bug where JWT tokens aren't validated on protected routes"

### 3. Monitor Long-Running Tasks

Check timeout state periodically for tasks > 30 minutes:

```bash
watch -n 30 'cat ~/.openclaw/openclaw-enhance/state/runtime-state.json | jq .timeouts'
```

## Troubleshooting

See [Troubleshooting](troubleshooting.md) for:
- Routing issues
- Timeout false positives
- State corruption
- Performance problems

## Version

Operations Guide Version: 2.0.0
Last Updated: 2026-04-09
