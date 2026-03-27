"""Task state model for human-intuitive ETA protocol.

States:
- on_track: within original ETA, no user action needed
- delayed: exceeded ETA but making meaningful progress
- blocked: specific blocker identified, cannot auto-resolve
- stalled: no progress signal for extended period
- completed_late: finished but exceeded original ETA
"""

from __future__ import annotations

from enum import Enum


class TaskState(str, Enum):
    ON_TRACK = "on_track"
    DELAYED = "delayed"
    BLOCKED = "blocked"
    STALLED = "stalled"
    COMPLETED_LATE = "completed_late"
    COMPLETED_ON_TIME = "completed_on_time"


# Human-readable descriptions for each state
STATE_DESCRIPTIONS: dict[TaskState, str] = {
    TaskState.ON_TRACK: "按计划推进中",
    TaskState.DELAYED: "比预期久，但仍在推进",
    TaskState.BLOCKED: "遇到明确阻塞点",
    TaskState.STALLED: "疑似停滞，建议人工介入",
    TaskState.COMPLETED_LATE: "已完成，但比预期晚",
    TaskState.COMPLETED_ON_TIME: "按时完成",
}


def is_terminal(state: TaskState) -> bool:
    """Return True if this is a terminal (completed) state."""
    return state in (TaskState.COMPLETED_LATE, TaskState.COMPLETED_ON_TIME)


def is_active(state: TaskState) -> bool:
    """Return True if this state means the task is still running."""
    return state not in (TaskState.COMPLETED_LATE, TaskState.COMPLETED_ON_TIME)
