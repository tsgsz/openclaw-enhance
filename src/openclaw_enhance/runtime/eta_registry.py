"""TaskETA registry for tracking spawn-level ETA metadata.

This is NOT the runtime state store — it tracks ETA protocol data
specifically for the human-intuitive expectation management system.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from openclaw_enhance.runtime.states import TaskState, is_terminal


@dataclass
class TaskETARecord:
    """Record of a task's ETA and progress state."""

    task_id: str
    child_session_id: str
    parent_session: str
    estimated_minutes: int
    created_at: str  # ISO format
    first_update_eta: str  # ISO format — when main promised to return
    completion_eta: str  # ISO format — full completion estimate
    current_state: str  # TaskState value
    state_reason: str = ""  # Human-readable reason for current state
    new_remaining_minutes: int | None = None  # Refreshed ETA when delayed
    completed_at: str | None = None  # ISO format when finished

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskETARecord:
        return cls(**data)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".tmp.{os.getpid()}.{int(time.time() * 1000)}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


class TaskETARegistry:
    """Registry for tracking ETA records for all active tasks.

    Stored at: ~/.openclaw/openclaw-enhance/state/task_eta_registry.json
    """

    FILENAME = "task_eta_registry.json"

    def __init__(self, registry_path: Path | None = None):
        if registry_path is None:
            registry_path = Path.home() / ".openclaw" / "openclaw-enhance" / "state" / self.FILENAME
        self._path = registry_path

    def _read(self) -> dict[str, Any]:
        try:
            return cast(dict[str, Any], json.loads(self._path.read_text(encoding="utf-8")))
        except Exception:
            return {"version": 1, "tasks": {}}

    def _write(self, payload: dict[str, Any]) -> None:
        _atomic_write_json(self._path, payload)

    def register(
        self,
        task_id: str,
        child_session_id: str,
        parent_session: str,
        estimated_minutes: int,
        first_update_minutes: int,
    ) -> TaskETARecord:
        """Register a new task with its ETA metadata."""
        now = datetime.utcnow()
        payload = self._read()

        record = TaskETARecord(
            task_id=task_id,
            child_session_id=child_session_id,
            parent_session=parent_session,
            estimated_minutes=estimated_minutes,
            created_at=now.isoformat(),
            first_update_eta=(now + timedelta(minutes=first_update_minutes)).isoformat(),
            completion_eta=(now + timedelta(minutes=estimated_minutes)).isoformat(),
            current_state=TaskState.ON_TRACK.value,
        )

        payload["tasks"][task_id] = record.to_dict()
        self._write(payload)
        return record

    def get(self, task_id: str) -> TaskETARecord | None:
        """Get a task record by task_id."""
        payload = self._read()
        data = payload.get("tasks", {}).get(task_id)
        if data is None:
            return None
        return TaskETARecord.from_dict(data)

    def update_state(
        self,
        task_id: str,
        new_state: TaskState,
        reason: str = "",
        new_remaining_minutes: int | None = None,
    ) -> TaskETARecord | None:
        """Update the state of a task, optionally refreshing ETA."""
        payload = self._read()
        tasks = payload.get("tasks", {})
        if task_id not in tasks:
            return None

        data = dict(tasks[task_id])
        data["current_state"] = new_state.value
        data["state_reason"] = reason
        if new_remaining_minutes is not None:
            data["new_remaining_minutes"] = new_remaining_minutes

        if is_terminal(new_state):
            data["completed_at"] = datetime.utcnow().isoformat()

        tasks[task_id] = data
        payload["tasks"] = tasks
        self._write(payload)
        return TaskETARecord.from_dict(data)

    def list_active(self) -> list[TaskETARecord]:
        """List all non-terminal task records."""
        payload = self._read()
        return [
            TaskETARecord.from_dict(t)
            for t in payload.get("tasks", {}).values()
            if not is_terminal(TaskState(t["current_state"]))
        ]

    def list_delayed(self) -> list[TaskETARecord]:
        """List all tasks in delayed, blocked, or stalled state."""
        payload = self._read()
        active_states = {
            TaskState.DELAYED.value,
            TaskState.BLOCKED.value,
            TaskState.STALLED.value,
        }
        return [
            TaskETARecord.from_dict(t)
            for t in payload.get("tasks", {}).values()
            if t["current_state"] in active_states
        ]

    def mark_completed(self, task_id: str, was_on_time: bool = False) -> TaskETARecord | None:
        """Mark a task as completed, with on-time vs late designation."""
        state = TaskState.COMPLETED_ON_TIME if was_on_time else TaskState.COMPLETED_LATE
        return self.update_state(task_id, state, reason="")
