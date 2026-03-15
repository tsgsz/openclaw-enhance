---
name: oe-timeout-alarm
version: 1.0.0
description: Timeout detection and alerting for session monitoring
author: openclaw-enhance
tags: [watchdog, timeout, monitoring, alerting]
---

# oe-timeout-alarm

Skill for detecting session timeouts and triggering alerts.

## Purpose

This skill provides timeout monitoring capabilities:
- ETA tracking and comparison
- Timeout detection algorithms
- Alert triggering
- Event logging to runtime state
- Escalation workflows

## When to Use

Use this skill when:
- Monitoring session duration vs ETA
- Detecting stuck or hung sessions
- Triggering timeout alerts
- Logging timeout events
- Coordinating with orchestrator on recovery

## Authority Boundaries

### ✅ ALLOWED
- Read session metadata and messages
- Calculate elapsed time vs ETA
- Write timeout events to runtime state
- Report timeout status to orchestrator
- Log monitoring events

### ❌ PROHIBITED
- Modify session state
- Send messages to sessions (session_send not available)
- Kill or terminate sessions
- Make recovery decisions
- Modify project files

## Capabilities

### ETA Tracking

#### Calculate Elapsed Time
```python
from datetime import datetime

def get_elapsed_minutes(session_id):
    """Calculate elapsed time for session."""
    info = session_info(session_id=session_id)
    
    start_time = datetime.fromisoformat(info.start_time)
    elapsed = datetime.now() - start_time
    
    return elapsed.total_seconds() / 60
```

#### Compare with ETA
```python
def check_timeout(session_id, eta_minutes, threshold=1.5):
    """Check if session has exceeded ETA threshold."""
    elapsed = get_elapsed_minutes(session_id)
    
    # Apply threshold (e.g., 1.5x ETA)
    timeout_threshold = eta_minutes * threshold
    
    is_timeout = elapsed > timeout_threshold
    
    return {
        "session_id": session_id,
        "elapsed_minutes": elapsed,
        "eta_minutes": eta_minutes,
        "threshold": threshold,
        "is_timeout": is_timeout,
        "excess_minutes": elapsed - timeout_threshold if is_timeout else 0
    }
```

### Timeout Detection

#### Check Session Progress
```python
def verify_progress(session_id, last_check_time):
    """Verify session is making progress."""
    # Get recent messages
    recent = session_read(session_id=session_id, limit=10)
    
    if not recent:
        return {"has_progress": False, "reason": "no_messages"}
    
    # Check timestamp of last message
    last_message_time = recent[-1].timestamp
    
    # If no new messages since last check, session may be stuck
    if last_message_time <= last_check_time:
        return {"has_progress": False, "reason": "no_new_messages"}
    
    # Check for completion markers
    completion_keywords = ["completed", "done", "finished", "delivered"]
    for msg in recent:
        if any(kw in msg.content.lower() for kw in completion_keywords):
            return {"has_progress": True, "completed": True}
    
    return {"has_progress": True, "completed": False}
```

#### Detect Stuck State
```python
def detect_stuck_session(session_id, eta_minutes):
    """Detect if session is stuck."""
    # Check basic timeout
    timeout_info = check_timeout(session_id, eta_minutes)
    
    if not timeout_info["is_timeout"]:
        return {"stuck": False, "reason": "within_eta"}
    
    # Verify no progress
    progress = verify_progress(session_id, get_last_check_time(session_id))
    
    if progress["has_progress"]:
        return {"stuck": False, "reason": "making_progress"}
    
    # Confirm stuck state
    return {
        "stuck": True,
        "elapsed": timeout_info["elapsed_minutes"],
        "eta": timeout_info["eta_minutes"],
        "excess": timeout_info["excess_minutes"],
        "reason": progress["reason"]
    }
```

### Event Logging

#### Log Timeout Event
```python
import json
from datetime import datetime

def log_timeout_event(session_id, timeout_info):
    """Log timeout event to runtime state."""
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": "timeout_detected",
        "session_id": session_id,
        "elapsed_minutes": timeout_info["elapsed_minutes"],
        "eta_minutes": timeout_info["eta_minutes"],
        "excess_minutes": timeout_info.get("excess_minutes", 0),
        "threshold_applied": timeout_info.get("threshold", 1.5)
    }
    
    # Write to runtime state only
    Write(
        filePath=".runtime/timeout_events.json",
        content=json.dumps(event, indent=2)
    )
    
    return event
```

#### Log Reminder Delivery
```python
def log_reminder(session_id, message):
    """Log reminder delivery attempt."""
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": "reminder_delivery",
        "session_id": session_id,
        "message_preview": message[:100] if len(message) > 100 else message,
        "status": "logged"  # Note: actual sending not available
    }
    
    # Append to runtime log
    Write(
        filePath=".runtime/reminder_log.json",
        content=json.dumps(event, indent=2)
    )
    
    return event
```

## Monitoring Workflows

### Workflow 1: Single Session Check
```python
def monitor_session(session_id, eta_minutes):
    """Monitor a single session for timeout."""
    # Step 1: Get session info
    info = session_info(session_id=session_id)
    
    # Step 2: Check if timeout
    timeout_info = check_timeout(session_id, eta_minutes)
    
    if not timeout_info["is_timeout"]:
        return {
            "status": "ok",
            "session_id": session_id,
            "elapsed": timeout_info["elapsed_minutes"],
            "eta": timeout_info["eta_minutes"]
        }
    
    # Step 3: Verify stuck state
    stuck_info = detect_stuck_session(session_id, eta_minutes)
    
    if not stuck_info["stuck"]:
        return {
            "status": "warning",
            "session_id": session_id,
            "message": "Exceeds ETA but making progress"
        }
    
    # Step 4: Log timeout event
    event = log_timeout_event(session_id, timeout_info)
    
    # Step 5: Prepare alert (report to orchestrator)
    alert = {
        "severity": "high",
        "session_id": session_id,
        "elapsed": stuck_info["elapsed"],
        "eta": stuck_info["eta"],
        "excess": stuck_info["excess"],
        "event_logged": event["timestamp"]
    }
    
    return {
        "status": "timeout",
        "alert": alert
    }
```

### Workflow 2: Batch Monitoring
```python
def monitor_all_sessions(sessions_with_eta):
    """Monitor multiple sessions."""
    results = []
    
    for session_id, eta in sessions_with_eta.items():
        result = monitor_session(session_id, eta)
        results.append(result)
    
    # Summarize
    timeouts = [r for r in results if r["status"] == "timeout"]
    warnings = [r for r in results if r["status"] == "warning"]
    ok = [r for r in results if r["status"] == "ok"]
    
    return {
        "total": len(results),
        "timeouts": len(timeouts),
        "warnings": len(warnings),
        "ok": len(ok),
        "details": results
    }
```

## Output Formats

### Timeout Event
```json
{
  "timestamp": "2026-03-13T10:30:00Z",
  "event_type": "timeout_detected",
  "session_id": "abc123",
  "elapsed_minutes": 15,
  "eta_minutes": 10,
  "excess_minutes": 5,
  "threshold_applied": 1.5
}
```

### Monitoring Report
```markdown
# Timeout Monitoring Report

## Timestamp: 2026-03-13T10:30:00Z

## Sessions Checked: 5

### Timeouts Detected: 1

#### Session abc123
- **Elapsed**: 15 minutes
- **ETA**: 10 minutes
- **Excess**: 5 minutes (1.5x threshold)
- **Status**: Stuck (no progress in 10 minutes)
- **Event Logged**: 2026-03-13T10:30:00Z

### Warnings: 1

#### Session def456
- **Status**: Exceeds ETA but making progress
- **Elapsed**: 12 minutes
- **ETA**: 10 minutes

### OK: 3
- Session ghi789 (3m / 10m ETA)
- Session jkl012 (5m / 15m ETA)
- Session mno345 (2m / 5m ETA)

## Actions Taken
- Logged 1 timeout event to runtime state
- Reported to orchestrator for decision
```

## Best Practices

1. **Confirm Before Alerting**: Verify stuck state, not just timeout
2. **Log Everything**: All events written to runtime state
3. **Thresholds**: Use reasonable multipliers (1.5x typical)
4. **Grace Period**: Allow for natural variance in task duration
5. **Report Only**: Let orchestrator decide on recovery

## Safety

### Narrow Authority
- Only read session metadata
- Only write to runtime state
- Cannot modify sessions
- Cannot make decisions
- Reports to orchestrator only

### Error Handling
- Handle missing sessions gracefully
- Log errors to runtime state
- Continue monitoring other sessions
- Report failures to orchestrator

## Integration

### With oe-watchdog Agent
This skill is designed for the oe-watchdog agent:
- Timeout detection
- Event logging
- Status reporting
- Monitoring workflows

### With Orchestrator
- Reports timeout events
- Provides status summaries
- Does NOT make recovery decisions
- Escalates to orchestrator

## Constraints & Workflow

### Write Access
- **Runtime State**: The only write access allowed is to runtime state store (`.runtime/` or equivalent). 
- **Project Files**: Cannot write to or modify project files (`Write`, `Edit` prohibited).

### Tool Usage
- `session_list`, `session_read`, `session_info`, `session_search`: Allowed for timeout detection.
- `Read`: Allowed for runtime state and config only.
- `Bash`: Read-only commands only (status checks).
- `call_omo_agent`, `websearch_web_search_exa`: Prohibited. No agent spawning. No web searches.

## Version

Version: 1.1.0
Last Updated: 2026-03-15
