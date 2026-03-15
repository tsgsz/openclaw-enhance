"""Notifier module for sending timeout reminders and notifications.

This module provides functionality to send reminders to sessions when
timeouts are suspected or confirmed, via the OpenClaw session_send mechanism.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Protocol

from openclaw_enhance.watchdog.detector import TimeoutEvent


class ReminderType(Enum):
    """Types of reminders that can be sent."""

    SUSPECTED_TIMEOUT = auto()
    CONFIRMED_TIMEOUT = auto()
    PROGRESS_CHECK = auto()
    ESCALATION = auto()


@dataclass(frozen=True)
class Reminder:
    """A reminder message to be sent to a session.

    Attributes:
        session_id: Target session ID
        reminder_type: Type of reminder
        message: Human-readable reminder message
        timestamp: When the reminder was created
        metadata: Additional context
    """

    session_id: str
    reminder_type: ReminderType
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, str] = field(default_factory=dict)


class SessionSender(Protocol):
    """Protocol for sending messages to sessions."""

    def send_to_session(self, session_id: str, message: str) -> bool:
        """Send a message to a session.

        Args:
            session_id: Target session ID
            message: Message to send

        Returns:
            True if message was sent successfully
        """
        ...


@dataclass
class NotifierConfig:
    """Configuration for the notifier.

    Attributes:
        include_eta: Include expected completion time in reminders
        include_duration: Include elapsed duration in reminders
        custom_templates: Custom message templates by reminder type
    """

    include_eta: bool = True
    include_duration: bool = True
    custom_templates: dict[ReminderType, str] = field(default_factory=dict)


class Notifier:
    """Sends reminders and notifications for timeout events.

    Provides formatted messages for different reminder types and tracks
    reminder history to avoid duplicate notifications.
    """

    # Default message templates
    _TEMPLATES: dict[ReminderType, str] = {
        ReminderType.SUSPECTED_TIMEOUT: (
            "⚠️ Session '{session_id}' may have timed out. "
            "Expected: {expected_duration}, Elapsed: {actual_duration}. "
            "Please provide an update on your progress."
        ),
        ReminderType.CONFIRMED_TIMEOUT: (
            "⏰ Session '{session_id}' has exceeded its expected duration. "
            "Elapsed: {actual_duration}. Please check if the task is still active."
        ),
        ReminderType.PROGRESS_CHECK: (
            "📝 Checking in on session '{session_id}'. "
            "Task has been running for {actual_duration}. "
            "How is it going?"
        ),
        ReminderType.ESCALATION: (
            "🚨 Session '{session_id}' requires attention. "
            "Significant timeout detected ({actual_duration}). "
            "Please respond or the task may be marked as failed."
        ),
    }

    def __init__(
        self,
        sender: SessionSender | None = None,
        config: NotifierConfig | None = None,
    ):
        """Initialize the notifier.

        Args:
            sender: Session sender for delivering messages
            config: Notifier configuration
        """
        self._sender = sender
        self._config = config or NotifierConfig()
        self._sent_reminders: dict[str, list[Reminder]] = {}

    def _get_template(self, reminder_type: ReminderType) -> str:
        """Get the message template for a reminder type.

        Args:
            reminder_type: Type of reminder

        Returns:
            Message template string
        """
        return self._config.custom_templates.get(
            reminder_type,
            self._TEMPLATES[reminder_type],
        )

    def _format_message(
        self,
        reminder_type: ReminderType,
        event: TimeoutEvent,
    ) -> str:
        """Format a reminder message for a timeout event.

        Args:
            reminder_type: Type of reminder
            event: Timeout event data

        Returns:
            Formatted message string
        """
        template = self._get_template(reminder_type)

        # Format durations for readability
        expected_str = self._format_duration(event.expected_duration)
        actual_str = self._format_duration(event.actual_duration)

        return template.format(
            session_id=event.session_id,
            expected_duration=expected_str,
            actual_duration=actual_str,
            **event.metadata,
        )

    def _format_duration(self, duration: timedelta) -> str:
        """Format a duration for human readability.

        Args:
            duration: Time duration

        Returns:
            Formatted string (e.g., "5m 30s")
        """
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")

        return " ".join(parts)

    def send_reminder(
        self,
        event: TimeoutEvent,
        reminder_type: ReminderType = ReminderType.SUSPECTED_TIMEOUT,
    ) -> Reminder | None:
        """Send a reminder for a timeout event.

        Args:
            event: Timeout event data
            reminder_type: Type of reminder to send

        Returns:
            Sent reminder, or None if sending failed
        """
        message = self._format_message(reminder_type, event)

        reminder = Reminder(
            session_id=event.session_id,
            reminder_type=reminder_type,
            message=message,
            metadata=event.metadata.copy(),
        )

        # Send via session sender if available
        if self._sender is not None:
            success = self._sender.send_to_session(event.session_id, message)
            if not success:
                return None

        # Record the reminder
        if event.session_id not in self._sent_reminders:
            self._sent_reminders[event.session_id] = []
        self._sent_reminders[event.session_id].append(reminder)

        return reminder

    def send_suspected_timeout(self, event: TimeoutEvent) -> Reminder | None:
        """Send a suspected timeout reminder.

        Args:
            event: Timeout event data

        Returns:
            Sent reminder, or None if failed
        """
        return self.send_reminder(event, ReminderType.SUSPECTED_TIMEOUT)

    def send_confirmed_timeout(self, event: TimeoutEvent) -> Reminder | None:
        """Send a confirmed timeout reminder.

        Args:
            event: Timeout event data

        Returns:
            Sent reminder, or None if failed
        """
        return self.send_reminder(event, ReminderType.CONFIRMED_TIMEOUT)

    def send_escalation(self, event: TimeoutEvent) -> Reminder | None:
        """Send an escalation reminder.

        Args:
            event: Timeout event data

        Returns:
            Sent reminder, or None if failed
        """
        return self.send_reminder(event, ReminderType.ESCALATION)

    def get_reminder_history(self, session_id: str) -> list[Reminder]:
        """Get reminder history for a session.

        Args:
            session_id: Session to get history for

        Returns:
            List of reminders sent to the session
        """
        return list(self._sent_reminders.get(session_id, []))

    def get_last_reminder_time(self, session_id: str) -> datetime | None:
        """Get the timestamp of the last reminder for a session.

        Args:
            session_id: Session to check

        Returns:
            Timestamp of last reminder, or None if no reminders sent
        """
        history = self._sent_reminders.get(session_id, [])
        if not history:
            return None
        return history[-1].timestamp

    def clear_session(self, session_id: str) -> None:
        """Clear reminder history for a session.

        Args:
            session_id: Session to clear
        """
        self._sent_reminders.pop(session_id, None)

    def should_send_reminder(
        self,
        session_id: str,
        cooldown: timedelta,
    ) -> bool:
        """Check if enough time has passed since the last reminder.

        Args:
            session_id: Session to check
            cooldown: Minimum time between reminders

        Returns:
            True if a new reminder should be sent
        """
        last_time = self.get_last_reminder_time(session_id)
        if last_time is None:
            return True

        elapsed = datetime.utcnow() - last_time
        return elapsed >= cooldown
