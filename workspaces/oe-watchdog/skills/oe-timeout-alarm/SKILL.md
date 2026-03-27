---
name: oe-timeout-alarm
version: 2.0.0
description: State classification for task progress monitoring — distinguishes delayed, blocked, stalled, and completed-late states instead of simple timeout detection.
author: openclaw-enhance
tags: [watchdog, state_classification, monitoring, ETA]
---

# oe-timeout-alarm v2 — State Classification, Not Timeout Detection

## Purpose

This skill classifies task progress into explicit states that drive human-intuitive communication.
It replaces the old "timeout detection" model with a state classification model.

**Key shift**: watchdog does NOT emit "timeout" alerts. It classifies state and feeds the ETA protocol.
The main session owns all user-facing communication.

## Task State Model

| State | Meaning | User Communication |
|-------|---------|-------------------|
| `on_track` | Within original ETA | None needed |
| `delayed` | Exceeded ETA but making progress | Three-part delay update |
| `blocked` | Specific blocker identified | Blocked update with ETA if available |
| `stalled` | No progress signal for extended period | Near-timeout warning |
| `completed_late` | Finished but exceeded original ETA | Summary with explanation |
| `completed_on_time` | Finished within original ETA | Silent or brief confirmation |

## Authority Boundaries

### ✅ ALLOWED
- Read session metadata and messages
- Calculate elapsed time vs registered ETA
- Classify task into one of the 6 states above
- Write state updates to ETA registry (runtime state) via CLI
- Report classification to orchestrator

### ❌ PROHIBITED
- Directly send messages to user sessions
- Emit "timeout" alerts to users
- Make recovery decisions
- Kill or terminate sessions
- Modify project files

## When to Use

Use this skill when:
- Monitoring an active task's progress against its registered ETA
- Checking if a task needs a delay update
- Determining if a task is blocked vs simply slow
- Detecting stalled tasks that need human intervention
- Checking if a completed task was on-time or late

## State Classification Workflow

### Step 1: Check ETA Registry for Active Tasks

```python
from openclaw_enhance.runtime.eta_registry import TaskETARegistry

registry = TaskETARegistry()
active_tasks = registry.list_active()

for task in active_tasks:
    print(f"Task {task.task_id}: state={task.current_state}, eta={task.estimated_minutes}min")
```

### Step 2: Classify Each Task

```python
from openclaw_enhance.runtime.states import TaskState
from datetime import datetime

def classify_task(task_record) -> TaskState:
    elapsed = (datetime.utcnow() - datetime.fromisoformat(task_record.created_at)).total_seconds() / 60
    eta = task_record.estimated_minutes

    # Within ETA
    if elapsed <= eta * 1.0:
        return TaskState.ON_TRACK

    # Beyond ETA — check progress
    session_info = ...  # Get session_info for child_session_id
    recent_messages = ...  # session_read for child_session_id

    has_progress = check_has_recent_activity(recent_messages)
    has_completion_marker = check_completion_marker(recent_messages)

    if has_completion_marker:
        # Task is actually done but not marked as such
        return TaskState.COMPLETED_LATE

    if not has_progress:
        # No recent activity — could be stalled
        return TaskState.STALLED

    # Has progress but exceeded ETA — delayed
    return TaskState.DELAYED


def check_has_recent_activity(messages, threshold_minutes=5) -> bool:
    if not messages:
        return False
    last_msg_time = max(datetime.fromisoformat(m.timestamp) for m in messages)
    return (datetime.utcnow() - last_msg_time).total_seconds() / 60 < threshold_minutes


def check_completion_marker(messages) -> bool:
    completion_keywords = ["completed", "done", "finished", "delivered", "结果", "好了"]
    for msg in messages:
        content = msg.content.lower() if hasattr(msg, 'content') else str(msg)
        if any(kw in content for kw in completion_keywords):
            return True
    return False
```

### Step 3: Update Registry with Classification

```python
from openclaw_enhance.runtime.states import TaskState

new_state = classify_task(task_record)

if new_state != TaskState(task_record.current_state):
    registry.update_state(
        task_record.task_id,
        new_state=new_state,
        reason="",  # Fill in based on classification
    )
```

## Delay vs Blocked vs Stalled

### Delayed (健康地慢)
- Exceeded ETA
- Still making progress
- New results arriving
- **Action**: Trigger delay update to user (Phase 2)

### Blocked (明确阻塞)
- Exceeded ETA
- No recent progress
- Identifiable blocker: waiting on external, error loop, etc.
- **Action**: Trigger blocked update to user (Phase 3)

### Stalled (疑似停滞)
- Exceeded ETA significantly (e.g., 2x)
- No progress for extended period
- Unknown cause
- **Action**: Flag for human intervention — this is the only "near-timeout" state

## Integration with Watchdog

Watchdog uses this skill to:
1. Check `TaskETARegistry` for active tasks on each monitoring cycle
2. Classify each task's current state
3. Update the registry with the new state
4. If state is `stalled`, alert orchestrator for human intervention
5. If state is `completed_late`, trigger completion summary
6. If state is `delayed` or `blocked`, the main session handles user communication

## Output Contract

This skill produces state classification results, NOT user-facing messages:

```python
@dataclass
class StateClassificationResult:
    task_id: str
    classified_state: TaskState
    elapsed_minutes: float
    eta_minutes: int
    has_progress: bool
    has_completion_marker: bool
    recommended_action: str  # "delay_update" | "blocked_update" | "human_intervention" | "completed_summary"
```

## Best Practices

1. **Classify before communicating** — determine the state first, then choose the right update template
2. **Never skip the blocked state** — blocked is different from delayed; blocked needs a different message
3. **Use `stalled` sparingly** — only when there is genuine concern about task viability
4. **Check completion markers first** — a task may be complete but not yet marked as such in the registry
5. **Let main own communication** — watchdog classifies, main communicates

## Version

Version: 2.0.0 (replaces v1 timeout detection model)
Last Updated: 2026-03-27
