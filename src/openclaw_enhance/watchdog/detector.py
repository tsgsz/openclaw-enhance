"""Timeout detection module for monitoring OpenClaw sessions.

This module provides functionality to detect when OpenClaw sessions have
exceeded expected execution times, emitting timeout_suspected events to
the runtime store for the watchdog to evaluate and act upon.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Protocol


class SessionStatus(Enum):
    """Possible states of a monitored session."""

    ACTIVE = auto()
    IDLE = auto()
    TIMEOUT_SUSPECTED = auto()
    CONFIRMED_TIMEOUT = auto()
    COMPLETED = auto()


@dataclass(frozen=True)
class TimeoutEvent:
    """Event emitted when a timeout is suspected or confirmed.

    Attributes:
        session_id: Unique identifier of the session
        detected_at: When the timeout was detected
        expected_duration: Expected duration for the session/task
        actual_duration: Actual elapsed time
        status: Current status of the session
        metadata: Additional context about the session
    """

    session_id: str
    detected_at: datetime
    expected_duration: timedelta
    actual_duration: timedelta
    status: SessionStatus
    metadata: dict[str, str] = field(default_factory=dict)

    def is_suspected(self) -> bool:
        """Check if this is a suspected timeout (not yet confirmed)."""
        return self.status == SessionStatus.TIMEOUT_SUSPECTED

    def is_confirmed(self) -> bool:
        """Check if this is a confirmed timeout."""
        return self.status == SessionStatus.CONFIRMED_TIMEOUT


class RuntimeStore(Protocol):
    """Protocol for the runtime store interface."""

    def emit_timeout_event(self, event: TimeoutEvent) -> None:
        """Emit a timeout event to the runtime store."""
        ...

    def get_session_last_activity(self, session_id: str) -> datetime | None:
        """Get the last activity timestamp for a session."""
        ...


@dataclass
class DetectionConfig:
    """Configuration for timeout detection.

    Attributes:
        default_timeout: Default timeout duration if not specified
        grace_period: Additional time to wait before marking as suspected
        min_session_duration: Minimum duration before checking for timeouts
    """

    default_timeout: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    grace_period: timedelta = field(default_factory=lambda: timedelta(minutes=1))
    min_session_duration: timedelta = field(default_factory=lambda: timedelta(seconds=30))


class TimeoutDetector:
    """Detects timeouts in OpenClaw sessions.

    Monitors active sessions and emits timeout_suspected events to the
    runtime store when sessions exceed their expected duration plus grace period.
    """

    def __init__(
        self,
        store: RuntimeStore | None = None,
        config: DetectionConfig | None = None,
    ):
        """Initialize the timeout detector.

        Args:
            store: Runtime store for emitting events
            config: Detection configuration
        """
        self._store = store
        self._config = config or DetectionConfig()
        self._monitored_sessions: dict[str, dict[str, datetime | timedelta]] = {}

    def start_monitoring(
        self,
        session_id: str,
        expected_duration: timedelta | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Start monitoring a session for timeouts.

        Args:
            session_id: Unique identifier for the session
            expected_duration: Expected duration for this session
            metadata: Additional context about the session
        """
        now = datetime.utcnow()
        self._monitored_sessions[session_id] = {
            "started_at": now,
            "expected_duration": expected_duration or self._config.default_timeout,
            "metadata": metadata or {},
        }

    def stop_monitoring(self, session_id: str) -> None:
        """Stop monitoring a session.

        Args:
            session_id: Session to stop monitoring
        """
        if session_id in self._monitored_sessions:
            del self._monitored_sessions[session_id]

    def check_timeouts(self) -> list[TimeoutEvent]:
        """Check all monitored sessions for timeouts.

        Returns:
            List of timeout events detected
        """
        events: list[TimeoutEvent] = []
        now = datetime.utcnow()

        for session_id, data in list(self._monitored_sessions.items()):
            started_at = data["started_at"]
            expected = data["expected_duration"]
            metadata = data.get("metadata", {})

            actual_duration = now - started_at  # type: ignore[operator]
            threshold = expected + self._config.grace_period  # type: ignore[operator]

            # Skip if session hasn't reached minimum duration
            if actual_duration < self._config.min_session_duration:
                continue

            if actual_duration > threshold:
                event = TimeoutEvent(
                    session_id=session_id,
                    detected_at=now,
                    expected_duration=expected,  # type: ignore[arg-type]
                    actual_duration=actual_duration,
                    status=SessionStatus.TIMEOUT_SUSPECTED,
                    metadata=metadata,  # type: ignore[arg-type]
                )
                events.append(event)

                if self._store is not None:
                    self._store.emit_timeout_event(event)

        return events

    def confirm_timeout(self, session_id: str) -> TimeoutEvent | None:
        """Confirm a suspected timeout for a session.

        Args:
            session_id: Session with suspected timeout

        Returns:
            Confirmed timeout event, or None if session not monitored
        """
        if session_id not in self._monitored_sessions:
            return None

        now = datetime.utcnow()
        data = self._monitored_sessions[session_id]
        started_at = data["started_at"]
        expected = data["expected_duration"]
        metadata = data.get("metadata", {})

        actual_duration = now - started_at  # type: ignore[operator]

        event = TimeoutEvent(
            session_id=session_id,
            detected_at=now,
            expected_duration=expected,  # type: ignore[arg-type]
            actual_duration=actual_duration,
            status=SessionStatus.CONFIRMED_TIMEOUT,
            metadata=metadata,  # type: ignore[arg-type]
        )

        if self._store is not None:
            self._store.emit_timeout_event(event)

        return event

    def get_active_sessions(self) -> list[str]:
        """Get list of currently monitored session IDs.

        Returns:
            List of active session IDs
        """
        return list(self._monitored_sessions.keys())

    def is_monitoring(self, session_id: str) -> bool:
        """Check if a session is being monitored.

        Args:
            session_id: Session to check

        Returns:
            True if session is being monitored
        """
        return session_id in self._monitored_sessions
