"""State synchronization module for the watchdog runtime store.

This module provides functionality to sync timeout events and state with
the OpenClaw runtime store, allowing the monitor to emit events and the
watchdog to read and confirm them.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from openclaw_enhance.paths import ensure_managed_directories, runtime_state_file
from openclaw_enhance.runtime.schema import RuntimeState
from openclaw_enhance.watchdog.detector import (
    SessionStatus,
    TimeoutEvent,
)

# Key for storing timeout events in runtime state
TIMEOUT_EVENTS_KEY = "timeout_suspected_events"


@dataclass
class TimeoutSuspectedRecord:
    """Record of a suspected timeout in the runtime store.

    Attributes:
        session_id: Unique identifier of the session
        detected_at: ISO format timestamp when detected
        expected_duration_seconds: Expected duration in seconds
        actual_duration_seconds: Actual elapsed time in seconds
        status: Current status of the timeout
        metadata: Additional context
    """

    session_id: str
    detected_at: str
    expected_duration_seconds: float
    actual_duration_seconds: float
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "detected_at": self.detected_at,
            "expected_duration_seconds": self.expected_duration_seconds,
            "actual_duration_seconds": self.actual_duration_seconds,
            "status": self.status,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimeoutSuspectedRecord":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            detected_at=data["detected_at"],
            expected_duration_seconds=data["expected_duration_seconds"],
            actual_duration_seconds=data["actual_duration_seconds"],
            status=data["status"],
            metadata=data.get("metadata", {}),
        )


class StateSync:
    """Synchronizes watchdog state with the runtime store.

    Provides methods to emit timeout events to the runtime store and
    to read and manage the state for the watchdog to process.
    """

    def __init__(
        self,
        user_home: Path | None = None,
    ):
        """Initialize state sync.

        Args:
            user_home: User home directory, defaults to current user
        """
        self._user_home = user_home
        self._state_path = runtime_state_file(user_home)
        self._pending_events: list[TimeoutEvent] = []

    def _load_raw_state(self) -> dict[str, Any]:
        """Load raw state from file.

        Returns:
            Raw state dictionary
        """
        if not self._state_path.exists():
            # Return default state structure
            return RuntimeState().model_dump()

        try:
            raw_state = json.loads(self._state_path.read_text(encoding="utf-8"))
            if isinstance(raw_state, dict):
                return cast(dict[str, Any], raw_state)
            return RuntimeState().model_dump()
        except (json.JSONDecodeError, FileNotFoundError):
            return RuntimeState().model_dump()

    def _save_raw_state(self, state: dict[str, Any]) -> None:
        """Save raw state to file.

        Args:
            state: State dictionary to save
        """
        ensure_managed_directories(self._user_home)
        self._state_path.write_text(
            json.dumps(state, indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    def emit_timeout_suspected(self, event: TimeoutEvent) -> None:
        """Emit a timeout_suspected event to the runtime store.

        This is the primary interface for the monitor to report
        suspected timeouts for the watchdog to evaluate.

        Args:
            event: Timeout event to emit
        """
        state = self._load_raw_state()

        # Ensure timeout_suspected_events list exists
        if TIMEOUT_EVENTS_KEY not in state:
            state[TIMEOUT_EVENTS_KEY] = []

        record = TimeoutSuspectedRecord(
            session_id=event.session_id,
            detected_at=event.detected_at.isoformat(),
            expected_duration_seconds=event.expected_duration.total_seconds(),
            actual_duration_seconds=event.actual_duration.total_seconds(),
            status=event.status.name,
            metadata=event.metadata,
        )

        # Add record to events
        state[TIMEOUT_EVENTS_KEY].append(record.to_dict())

        # Update last updated timestamp
        state["last_updated_utc"] = datetime.utcnow().isoformat()

        self._save_raw_state(state)
        self._pending_events.append(event)

    def get_pending_suspected_events(self) -> list[TimeoutEvent]:
        """Get all pending timeout_suspected events from the runtime store.

        Returns:
            List of pending suspected timeout events
        """
        state = self._load_raw_state()
        events: list[TimeoutEvent] = []

        raw_events = state.get(TIMEOUT_EVENTS_KEY, [])

        for raw in raw_events:
            record = TimeoutSuspectedRecord.from_dict(raw)

            # Parse ISO timestamp
            detected_at = datetime.fromisoformat(record.detected_at)

            event = TimeoutEvent(
                session_id=record.session_id,
                detected_at=detected_at,
                expected_duration=timedelta(seconds=record.expected_duration_seconds),
                actual_duration=timedelta(seconds=record.actual_duration_seconds),
                status=SessionStatus[record.status],
                metadata=record.metadata,
            )
            events.append(event)

        return events

    def confirm_timeout(self, session_id: str) -> TimeoutEvent | None:
        """Confirm a suspected timeout for a session.

        Updates the event status to CONFIRMED_TIMEOUT in the runtime store.

        Args:
            session_id: Session to confirm timeout for

        Returns:
            Confirmed event, or None if not found
        """
        state = self._load_raw_state()

        if TIMEOUT_EVENTS_KEY not in state:
            return None

        events = state[TIMEOUT_EVENTS_KEY]
        confirmed_event = None

        for i, raw in enumerate(events):
            if raw["session_id"] == session_id:
                record = TimeoutSuspectedRecord.from_dict(raw)

                # Update status
                record.status = SessionStatus.CONFIRMED_TIMEOUT.name
                events[i] = record.to_dict()

                # Create event object
                detected_at = datetime.fromisoformat(record.detected_at)
                confirmed_event = TimeoutEvent(
                    session_id=record.session_id,
                    detected_at=detected_at,
                    expected_duration=timedelta(seconds=record.expected_duration_seconds),
                    actual_duration=timedelta(seconds=record.actual_duration_seconds),
                    status=SessionStatus.CONFIRMED_TIMEOUT,
                    metadata=record.metadata,
                )
                break

        if confirmed_event:
            state[TIMEOUT_EVENTS_KEY] = events
            state["last_updated_utc"] = datetime.utcnow().isoformat()
            self._save_raw_state(state)

        return confirmed_event

    def clear_confirmed_timeouts(self) -> int:
        """Clear all confirmed timeouts from the runtime store.

        Returns:
            Number of events cleared
        """
        state = self._load_raw_state()

        if TIMEOUT_EVENTS_KEY not in state:
            return 0

        events = state[TIMEOUT_EVENTS_KEY]
        original_count = len(events)

        # Keep only suspected events
        events = [e for e in events if e.get("status") != SessionStatus.CONFIRMED_TIMEOUT.name]

        cleared = original_count - len(events)

        if cleared > 0:
            state[TIMEOUT_EVENTS_KEY] = events
            state["last_updated_utc"] = datetime.utcnow().isoformat()
            self._save_raw_state(state)

        return cleared

    def get_state_path(self) -> Path:
        """Get the path to the runtime state file.

        Returns:
            Path to runtime state file
        """
        return self._state_path


class RuntimeStoreAdapter:
    """Adapter to make StateSync compatible with RuntimeStore protocol.

    Wraps StateSync to provide the RuntimeStore interface expected by
    the TimeoutDetector.
    """

    def __init__(self, state_sync: StateSync):
        """Initialize the adapter.

        Args:
            state_sync: State sync instance to wrap
        """
        self._state_sync = state_sync

    def emit_timeout_event(self, event: TimeoutEvent) -> None:
        """Emit a timeout event via the state sync.

        Args:
            event: Timeout event to emit
        """
        self._state_sync.emit_timeout_suspected(event)

    def get_session_last_activity(self, session_id: str) -> datetime | None:
        """Get last activity for a session (not implemented).

        Args:
            session_id: Session to check

        Returns:
            None (placeholder implementation)
        """
        # This would require session tracking integration
        return None
