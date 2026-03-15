"""Unit tests for watchdog policy engine."""

from datetime import datetime, timedelta

from openclaw_enhance.watchdog.detector import SessionStatus, TimeoutEvent
from openclaw_enhance.watchdog.policy import (
    ActionType,
    PolicyDecision,
    PolicyEngine,
    TimeoutPolicy,
)


class TestTimeoutPolicy:
    """Tests for TimeoutPolicy class."""

    def test_policy_creation_with_defaults(self):
        """Test creating a policy with default values."""
        policy = TimeoutPolicy(name="test_policy")
        assert policy.name == "test_policy"
        assert policy.min_duration == timedelta(minutes=1)
        assert policy.max_duration is None
        assert policy.multiplier_threshold == 2.0
        assert policy.action == ActionType.REMIND_PERIODIC
        assert policy.cooldown == timedelta(minutes=2)
        assert policy.max_repeats == 3

    def test_policy_creation_with_custom_values(self):
        """Test creating a policy with custom values."""
        policy = TimeoutPolicy(
            name="custom_policy",
            min_duration=timedelta(seconds=30),
            max_duration=timedelta(minutes=10),
            multiplier_threshold=1.5,
            action=ActionType.REMIND_ONCE,
            cooldown=timedelta(minutes=5),
            max_repeats=1,
        )
        assert policy.name == "custom_policy"
        assert policy.min_duration == timedelta(seconds=30)
        assert policy.max_duration == timedelta(minutes=10)
        assert policy.multiplier_threshold == 1.5
        assert policy.action == ActionType.REMIND_ONCE
        assert policy.cooldown == timedelta(minutes=5)
        assert policy.max_repeats == 1

    def test_evaluate_duration_below_minimum(self):
        """Test evaluating event below minimum duration."""
        policy = TimeoutPolicy(
            name="test",
            min_duration=timedelta(minutes=5),
        )
        event = TimeoutEvent(
            session_id="session_1",
            detected_at=datetime.utcnow(),
            expected_duration=timedelta(minutes=10),
            actual_duration=timedelta(minutes=2),
            status=SessionStatus.TIMEOUT_SUSPECTED,
        )

        decision = policy.evaluate(event)
        assert decision.action == ActionType.IGNORE
        assert "below minimum" in decision.reason

    def test_evaluate_duration_above_maximum(self):
        """Test evaluating event exceeding maximum duration."""
        policy = TimeoutPolicy(
            name="test",
            min_duration=timedelta(minutes=1),
            max_duration=timedelta(minutes=30),
        )
        event = TimeoutEvent(
            session_id="session_1",
            detected_at=datetime.utcnow(),
            expected_duration=timedelta(minutes=10),
            actual_duration=timedelta(minutes=45),
            status=SessionStatus.TIMEOUT_SUSPECTED,
        )

        decision = policy.evaluate(event)
        assert decision.action == ActionType.ESCALATE
        assert "exceeded maximum" in decision.reason

    def test_evaluate_multiplier_threshold(self):
        """Test evaluating event exceeding multiplier threshold."""
        policy = TimeoutPolicy(
            name="test",
            min_duration=timedelta(minutes=1),
            max_duration=timedelta(hours=1),
            multiplier_threshold=2.0,
        )
        event = TimeoutEvent(
            session_id="session_1",
            detected_at=datetime.utcnow(),
            expected_duration=timedelta(minutes=5),
            actual_duration=timedelta(minutes=12),  # 2.4x expected
            status=SessionStatus.TIMEOUT_SUSPECTED,
        )

        decision = policy.evaluate(event)
        assert decision.action == ActionType.REMIND_PERIODIC
        assert "2.4x expected" in decision.reason

    def test_evaluate_within_bounds(self):
        """Test evaluating event within acceptable bounds."""
        policy = TimeoutPolicy(
            name="test",
            min_duration=timedelta(minutes=1),
            max_duration=timedelta(minutes=30),
            multiplier_threshold=2.0,
        )
        event = TimeoutEvent(
            session_id="session_1",
            detected_at=datetime.utcnow(),
            expected_duration=timedelta(minutes=10),
            actual_duration=timedelta(minutes=12),  # 1.2x expected
            status=SessionStatus.TIMEOUT_SUSPECTED,
        )

        decision = policy.evaluate(event)
        assert decision.action == ActionType.REMIND_PERIODIC
        assert "within acceptable bounds" in decision.reason


class TestPolicyDecision:
    """Tests for PolicyDecision class."""

    def test_should_send_reminder_once(self):
        """Test reminder sending for REMIND_ONCE action."""
        decision = PolicyDecision(
            action=ActionType.REMIND_ONCE,
            reason="test",
        )
        assert decision.should_send_reminder(0) is True
        assert decision.should_send_reminder(1) is False
        assert decision.should_send_reminder(2) is False

    def test_should_send_reminder_periodic(self):
        """Test reminder sending for REMIND_PERIODIC action."""
        decision = PolicyDecision(
            action=ActionType.REMIND_PERIODIC,
            reason="test",
            max_repeats=3,
        )
        assert decision.should_send_reminder(0) is True
        assert decision.should_send_reminder(1) is True
        assert decision.should_send_reminder(2) is True
        assert decision.should_send_reminder(3) is False

    def test_should_send_reminder_other_actions(self):
        """Test reminder sending for non-reminder actions."""
        ignore_decision = PolicyDecision(
            action=ActionType.IGNORE,
            reason="test",
        )
        escalate_decision = PolicyDecision(
            action=ActionType.ESCALATE,
            reason="test",
        )
        assert ignore_decision.should_send_reminder(0) is False
        assert escalate_decision.should_send_reminder(0) is False


class TestPolicyEngine:
    """Tests for PolicyEngine class."""

    def test_default_policies_registered(self):
        """Test that default policies are registered on init."""
        engine = PolicyEngine()
        policy_names = engine.get_policy_names()
        assert "quick_task" in policy_names
        assert "standard_task" in policy_names
        assert "long_task" in policy_names
        assert "critical_task" in policy_names

    def test_register_custom_policy(self):
        """Test registering a custom policy."""
        engine = PolicyEngine()
        custom_policy = TimeoutPolicy(
            name="custom",
            min_duration=timedelta(seconds=10),
        )

        engine.register_policy(custom_policy)
        assert "custom" in engine.get_policy_names()

    def test_assign_policy_to_session(self):
        """Test assigning a policy to a session."""
        engine = PolicyEngine()
        result = engine.assign_policy("session_1", "quick_task")
        assert result is True

    def test_assign_nonexistent_policy(self):
        """Test assigning a non-existent policy fails."""
        engine = PolicyEngine()
        result = engine.assign_policy("session_1", "nonexistent")
        assert result is False

    def test_evaluate_with_assigned_policy(self):
        """Test evaluation uses assigned policy."""
        engine = PolicyEngine()
        engine.assign_policy("session_1", "quick_task")

        # quick_task has low multiplier threshold (1.5) and max_duration of 5 min
        # Use duration that exceeds multiplier but not max_duration
        event = TimeoutEvent(
            session_id="session_1",
            detected_at=datetime.utcnow(),
            expected_duration=timedelta(minutes=2),
            actual_duration=timedelta(minutes=4),  # 2x, under 5 min max
            status=SessionStatus.TIMEOUT_SUSPECTED,
        )

        decision = engine.evaluate(event)
        assert decision.action == ActionType.REMIND_ONCE

    def test_evaluate_with_default_policy(self):
        """Test evaluation uses default policy for unassigned sessions."""
        engine = PolicyEngine()

        event = TimeoutEvent(
            session_id="session_1",
            detected_at=datetime.utcnow(),
            expected_duration=timedelta(minutes=5),
            actual_duration=timedelta(minutes=12),  # 2.4x
            status=SessionStatus.TIMEOUT_SUSPECTED,
        )

        decision = engine.evaluate(event)
        # standard_task policy applies
        assert decision.action == ActionType.REMIND_PERIODIC

    def test_record_and_get_reminder_count(self):
        """Test recording and retrieving reminder counts."""
        engine = PolicyEngine()

        assert engine.get_reminder_count("session_1") == 0
        assert engine.record_reminder("session_1") == 1
        assert engine.record_reminder("session_1") == 2
        assert engine.get_reminder_count("session_1") == 2

    def test_clear_session(self):
        """Test clearing session data."""
        engine = PolicyEngine()
        engine.assign_policy("session_1", "quick_task")
        engine.record_reminder("session_1")

        engine.clear_session("session_1")

        assert engine.get_reminder_count("session_1") == 0

    def test_should_confirm_timeout_suspected(self):
        """Test confirming suspected timeouts."""
        engine = PolicyEngine()

        event = TimeoutEvent(
            session_id="session_1",
            detected_at=datetime.utcnow(),
            expected_duration=timedelta(minutes=5),
            actual_duration=timedelta(minutes=10),
            status=SessionStatus.TIMEOUT_SUSPECTED,
        )

        decision = PolicyDecision(
            action=ActionType.ESCALATE,
            reason="test",
            max_repeats=1,
        )

        assert engine.should_confirm_timeout(event, decision) is True

    def test_should_confirm_timeout_not_suspected(self):
        """Test that non-suspected events are not confirmed."""
        engine = PolicyEngine()

        event = TimeoutEvent(
            session_id="session_1",
            detected_at=datetime.utcnow(),
            expected_duration=timedelta(minutes=5),
            actual_duration=timedelta(minutes=10),
            status=SessionStatus.CONFIRMED_TIMEOUT,  # Already confirmed
        )

        decision = PolicyDecision(
            action=ActionType.ESCALATE,
            reason="test",
            max_repeats=1,
        )

        assert engine.should_confirm_timeout(event, decision) is False

    def test_should_confirm_timeout_max_repeats(self):
        """Test confirmation when max repeats reached."""
        engine = PolicyEngine()
        engine.record_reminder("session_1")  # count = 1
        engine.record_reminder("session_1")  # count = 2
        engine.record_reminder("session_1")  # count = 3

        event = TimeoutEvent(
            session_id="session_1",
            detected_at=datetime.utcnow(),
            expected_duration=timedelta(minutes=5),
            actual_duration=timedelta(minutes=10),
            status=SessionStatus.TIMEOUT_SUSPECTED,
        )

        decision = PolicyDecision(
            action=ActionType.REMIND_PERIODIC,
            reason="test",
            max_repeats=3,
        )

        assert engine.should_confirm_timeout(event, decision) is True
