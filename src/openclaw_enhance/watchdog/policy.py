"""Policy engine for evaluating timeout events and determining actions.

This module provides policy-based evaluation of timeout events to determine
whether timeouts should be escalated to confirmed status and what actions
the watchdog should take.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum, auto
from typing import Callable

from openclaw_enhance.watchdog.detector import SessionStatus, TimeoutEvent


class ActionType(Enum):
    """Actions the watchdog can take in response to timeouts."""

    IGNORE = auto()
    REMIND_ONCE = auto()
    REMIND_PERIODIC = auto()
    ESCALATE = auto()


@dataclass(frozen=True)
class PolicyDecision:
    """Decision made by the policy engine.

    Attributes:
        action: Type of action to take
        reason: Human-readable reason for the decision
        cooldown: Time before next reminder (if periodic)
        max_repeats: Maximum number of reminders to send
    """

    action: ActionType
    reason: str
    cooldown: timedelta = field(default_factory=lambda: timedelta(minutes=2))
    max_repeats: int = 3

    def should_send_reminder(self, reminder_count: int) -> bool:
        """Check if a reminder should be sent based on count.

        Args:
            reminder_count: Number of reminders already sent

        Returns:
            True if another reminder should be sent
        """
        if self.action == ActionType.REMIND_ONCE:
            return reminder_count < 1
        if self.action == ActionType.REMIND_PERIODIC:
            return reminder_count < self.max_repeats
        return False


@dataclass
class TimeoutPolicy:
    """Policy for handling timeout events.

    Attributes:
        name: Policy identifier
        min_duration: Minimum timeout duration to trigger action
        max_duration: Maximum timeout before auto-escalation
        multiplier_threshold: Factor of expected duration to trigger
        action: Default action for timeouts matching this policy
        cooldown: Time between repeated reminders
        max_repeats: Maximum reminder count for periodic reminders
    """

    name: str
    min_duration: timedelta = field(default_factory=lambda: timedelta(minutes=1))
    max_duration: timedelta | None = None
    multiplier_threshold: float = 2.0
    action: ActionType = ActionType.REMIND_PERIODIC
    cooldown: timedelta = field(default_factory=lambda: timedelta(minutes=2))
    max_repeats: int = 3

    def evaluate(self, event: TimeoutEvent) -> PolicyDecision:
        """Evaluate a timeout event against this policy.

        Args:
            event: Timeout event to evaluate

        Returns:
            Policy decision with recommended action
        """
        # Calculate multiplier
        expected_seconds = event.expected_duration.total_seconds()
        actual_seconds = event.actual_duration.total_seconds()
        multiplier = actual_seconds / expected_seconds if expected_seconds > 0 else float("inf")

        # Check minimum duration
        if event.actual_duration < self.min_duration:
            return PolicyDecision(
                action=ActionType.IGNORE,
                reason=f"Duration {event.actual_duration} below minimum {self.min_duration}",
            )

        # Check max duration (auto-escalation)
        if self.max_duration is not None and event.actual_duration >= self.max_duration:
            return PolicyDecision(
                action=ActionType.ESCALATE,
                reason=f"Duration {event.actual_duration} exceeded maximum {self.max_duration}",
                cooldown=self.cooldown,
                max_repeats=self.max_repeats,
            )

        # Check multiplier threshold
        if multiplier >= self.multiplier_threshold:
            return PolicyDecision(
                action=self.action,
                reason=(
                    f"Duration {multiplier:.1f}x expected threshold ({self.multiplier_threshold}x)"
                ),
                cooldown=self.cooldown,
                max_repeats=self.max_repeats,
            )

        # Default: periodic reminders
        return PolicyDecision(
            action=self.action,
            reason="Timeout within acceptable bounds, sending periodic reminders",
            cooldown=self.cooldown,
            max_repeats=self.max_repeats,
        )


class PolicyEngine:
    """Engine for evaluating timeout events against policies.

    Maintains a registry of policies and evaluates timeout events to determine
    appropriate actions for the watchdog to take.
    """

    def __init__(self):
        """Initialize the policy engine with default policies."""
        self._policies: dict[str, TimeoutPolicy] = {}
        self._session_policies: dict[str, str] = {}
        self._reminder_counts: dict[str, int] = {}

        # Register default policies
        self.register_default_policies()

    def register_default_policies(self) -> None:
        """Register the default set of timeout policies."""
        # Quick tasks: short timeouts, single reminder
        self.register_policy(
            TimeoutPolicy(
                name="quick_task",
                min_duration=timedelta(seconds=30),
                max_duration=timedelta(minutes=5),
                multiplier_threshold=1.5,
                action=ActionType.REMIND_ONCE,
                cooldown=timedelta(minutes=1),
            )
        )

        # Standard tasks: moderate timeouts, periodic reminders
        self.register_policy(
            TimeoutPolicy(
                name="standard_task",
                min_duration=timedelta(minutes=1),
                max_duration=timedelta(minutes=15),
                multiplier_threshold=2.0,
                action=ActionType.REMIND_PERIODIC,
                cooldown=timedelta(minutes=2),
                max_repeats=3,
            )
        )

        # Long tasks: extended timeouts, periodic reminders with longer cooldown
        self.register_policy(
            TimeoutPolicy(
                name="long_task",
                min_duration=timedelta(minutes=5),
                max_duration=timedelta(hours=1),
                multiplier_threshold=2.0,
                action=ActionType.REMIND_PERIODIC,
                cooldown=timedelta(minutes=5),
                max_repeats=5,
            )
        )

        # Critical tasks: escalate quickly
        self.register_policy(
            TimeoutPolicy(
                name="critical_task",
                min_duration=timedelta(seconds=10),
                max_duration=timedelta(minutes=10),
                multiplier_threshold=1.2,
                action=ActionType.ESCALATE,
                cooldown=timedelta(minutes=1),
            )
        )

    def register_policy(self, policy: TimeoutPolicy) -> None:
        """Register a new policy.

        Args:
            policy: Policy to register
        """
        self._policies[policy.name] = policy

    def assign_policy(self, session_id: str, policy_name: str) -> bool:
        """Assign a policy to a session.

        Args:
            session_id: Session to assign policy to
            policy_name: Name of the policy to assign

        Returns:
            True if policy was assigned successfully
        """
        if policy_name not in self._policies:
            return False
        self._session_policies[session_id] = policy_name
        return True

    def evaluate(self, event: TimeoutEvent) -> PolicyDecision:
        """Evaluate a timeout event and return a decision.

        Args:
            event: Timeout event to evaluate

        Returns:
            Policy decision with recommended action
        """
        # Get policy for session, or use standard_task as default
        policy_name = self._session_policies.get(event.session_id, "standard_task")
        policy = self._policies.get(policy_name, self._policies["standard_task"])

        return policy.evaluate(event)

    def record_reminder(self, session_id: str) -> int:
        """Record that a reminder was sent for a session.

        Args:
            session_id: Session that received reminder

        Returns:
            Updated reminder count for the session
        """
        current = self._reminder_counts.get(session_id, 0)
        self._reminder_counts[session_id] = current + 1
        return current + 1

    def get_reminder_count(self, session_id: str) -> int:
        """Get the number of reminders sent for a session.

        Args:
            session_id: Session to check

        Returns:
            Number of reminders sent
        """
        return self._reminder_counts.get(session_id, 0)

    def clear_session(self, session_id: str) -> None:
        """Clear tracking data for a session.

        Args:
            session_id: Session to clear
        """
        self._session_policies.pop(session_id, None)
        self._reminder_counts.pop(session_id, None)

    def get_policy_names(self) -> list[str]:
        """Get list of registered policy names.

        Returns:
            List of policy names
        """
        return list(self._policies.keys())

    def should_confirm_timeout(
        self,
        event: TimeoutEvent,
        decision: PolicyDecision | None = None,
    ) -> bool:
        """Determine if a suspected timeout should be confirmed.

        Args:
            event: Timeout event to evaluate
            decision: Pre-computed decision, or None to evaluate

        Returns:
            True if timeout should be confirmed
        """
        if decision is None:
            decision = self.evaluate(event)

        # Only confirm suspected timeouts
        if not event.is_suspected():
            return False

        # Escalate action means confirm immediately
        if decision.action == ActionType.ESCALATE:
            return True

        # Check if we've hit the max repeats
        reminder_count = self.get_reminder_count(event.session_id)
        if reminder_count >= decision.max_repeats:
            return True

        return False
