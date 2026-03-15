---
name: oe-timeout-state-sync
version: 1.0.0
description: Synchronizes timeout state between main session and runtime storage. Triggered when tasks exceed ETA or sessions appear hung.
user-invocable: false
allowed-tools: "Read, Write, Bash"
metadata:
  routing_heuristics:
    max_toolcalls: 1
    max_duration_minutes: 5
    sync_interval_seconds: 60
---

# Timeout State Sync

Synchronize timeout state with runtime storage for recovery and monitoring.

## Purpose

When a task times out:
1. Record timeout event in runtime state
2. Update `last_updated_utc` timestamp
3. Enable recovery workflows

## Trigger Conditions

Sync timeout state when:
- Task exceeds ETA by 2x
- Session appears hung (>30 min no response)
- User explicitly requests timeout handling
- Subagent task doesn't return within expected window

## Usage

```python
from openclaw_enhance.skills_catalog import sync_timeout_state
from openclaw_enhance.runtime.schema import RuntimeState
from datetime import timedelta

runtime_state = RuntimeState()

result = sync_timeout_state(
    session_id="sess_abc123",
    task_description="Long-running refactor",
    timeout_duration=timedelta(minutes=45),
    runtime_state=runtime_state,
)

# result = {
#     "synced": True,
#     "session_id": "sess_abc123",
#     "timestamp": "2026-03-13T12:00:00",
#     "task_description": "Long-running refactor",
#     "timeout_duration_seconds": 2700.0,
# }
```

## State Updates

Updates `RuntimeState`:
- `last_updated_utc`: Current UTC timestamp
- Records timeout event for monitoring

## Recovery Workflow

After timeout sync:

1. **Check subagent status**: Is it still running or completed?
2. **Resume**: If subagent finished, resume from results
3. **Retry**: If failed, retry with adjusted parameters
4. **Update planning**: If using `planning-with-files`, update `task_plan.md`

## Integration with Hooks

This skill is typically invoked from:
- PreToolUse hooks (detect long-running operations)
- PostToolUse hooks (detect timeouts)
- External monitoring scripts (watchdog)

## Example: Monitoring Script

```bash
#!/bin/bash
# Check for stale sessions and trigger timeout sync

STALE_THRESHOLD=1800  # 30 minutes
CURRENT_TIME=$(date +%s)

# Check runtime state timestamp
LAST_UPDATED=$(cat runtime-state.json | jq -r '.last_updated_utc')
LAST_EPOCH=$(date -d "$LAST_UPDATED" +%s)

DELTA=$((CURRENT_TIME - LAST_EPOCH))

if [ $DELTA -gt $STALE_THRESHOLD ]; then
    echo "Session appears stale, triggering timeout sync"
    # Trigger sync_timeout_state
fi
```

## Output Contract

Returns dict with:
- `synced`: bool - Whether sync succeeded
- `session_id`: str - Session that timed out
- `timestamp`: str - ISO format timestamp
- `task_description`: str - Description of timed-out task
- `timeout_duration_seconds`: float - How long task ran

## Security Notes

- Only updates timestamp, no sensitive data written
- Safe to call multiple times (idempotent)
- Does not interrupt running tasks
