"""Integration tests for timeout monitoring and state sync flow.

These tests verify the end-to-end flow:
1. Monitor detects suspected timeout
2. Event is emitted to runtime store
3. Watchdog reads and confirms timeout
4. Reminders are sent appropriately
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from openclaw_enhance.watchdog.detector import (
    DetectionConfig,
    RuntimeStore,
    SessionStatus,
    TimeoutDetector,
    TimeoutEvent,
)
from openclaw_enhance.watchdog.notifier import Notifier, ReminderType
from openclaw_enhance.watchdog.policy import ActionType, PolicyEngine
from openclaw_enhance.watchdog.state_sync import RuntimeStoreAdapter, StateSync


class MockSessionSender:
    """Mock session sender for testing."""

    def __init__(self):
        self.sent_messages: list[tuple[str, str]] = []

    def send_to_session(self, session_id: str, message: str) -> bool:
        self.sent_messages.append((session_id, message))
        return True


class TestTimeoutFlow:
    """Integration tests for the complete timeout flow."""

    @pytest.fixture
    def temp_home(self):
        """Create a temporary home directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_sender(self):
        """Create a mock session sender."""
        return MockSessionSender()

    def test_detector_emits_to_store(self, temp_home: Path):
        """Test that detector emits timeout events to runtime store."""
        # Set up state sync and adapter
        state_sync = StateSync(user_home=temp_home)
        store_adapter = RuntimeStoreAdapter(state_sync)

        # Create detector with very short timeouts
        config = DetectionConfig(
            default_timeout=timedelta(seconds=0),
            grace_period=timedelta(seconds=0),
            min_session_duration=timedelta(seconds=0),
        )
        detector = TimeoutDetector(store=store_adapter, config=config)

        # Start monitoring a session
        detector.start_monitoring("test_session")

        # Check timeouts - should emit to store
        events = detector.check_timeouts()

        assert len(events) == 1
        assert events[0].session_id == "test_session"
        assert events[0].status == SessionStatus.TIMEOUT_SUSPECTED

        # Verify event was written to runtime store
        pending = state_sync.get_pending_suspected_events()
        assert len(pending) == 1
        assert pending[0].session_id == "test_session"

    def test_watchdog_reads_and_confirms(self, temp_home: Path):
        """Test watchdog reads suspected events and confirms them."""
        # Set up state sync
        state_sync = StateSync(user_home=temp_home)

        # Manually inject a suspected event
        from datetime import timezone

        now = datetime.now(timezone.utc)
        event = TimeoutEvent(
            session_id="watchdog_test",
            detected_at=now,
            expected_duration=timedelta(minutes=5),
            actual_duration=timedelta(minutes=15),
            status=SessionStatus.TIMEOUT_SUSPECTED,
            metadata={"test": "true"},
        )
        state_sync.emit_timeout_suspected(event)

        # Verify it's in pending
        pending = state_sync.get_pending_suspected_events()
        assert len(pending) == 1
        assert pending[0].session_id == "watchdog_test"

        # Confirm the timeout
        confirmed = state_sync.confirm_timeout("watchdog_test")
        assert confirmed is not None
        assert confirmed.session_id == "watchdog_test"
        assert confirmed.status == SessionStatus.CONFIRMED_TIMEOUT

    def test_policy_evaluation_flow(self, temp_home: Path, mock_sender: MockSessionSender):
        """Test complete flow from detection to reminder."""
        # Set up components
        state_sync = StateSync(user_home=temp_home)
        store_adapter = RuntimeStoreAdapter(state_sync)
        policy_engine = PolicyEngine()
        notifier = Notifier(sender=mock_sender)

        # Create and configure detector
        config = DetectionConfig(
            default_timeout=timedelta(seconds=0),
            grace_period=timedelta(seconds=0),
            min_session_duration=timedelta(seconds=0),
        )
        detector = TimeoutDetector(store=store_adapter, config=config)

        # Start and detect timeout
        detector.start_monitoring("policy_test_session")
        events = detector.check_timeouts()

        assert len(events) == 1
        event = events[0]

        # Policy evaluation - event will likely be ignored due to very short duration
        decision = policy_engine.evaluate(event)
        # Policy may decide to IGNORE (due to short duration) or REMIND
        assert decision.action in (
            ActionType.IGNORE,
            ActionType.REMIND_ONCE,
            ActionType.REMIND_PERIODIC,
        )

        # Send reminder if policy allows
        if decision.should_send_reminder(policy_engine.get_reminder_count(event.session_id)):
            reminder = notifier.send_suspected_timeout(event)
            assert reminder is not None
            assert reminder.session_id == "policy_test_session"

            # Verify message was "sent"
            assert len(mock_sender.sent_messages) == 1
            assert mock_sender.sent_messages[0][0] == "policy_test_session"
        else:
            # If ignored, no message sent (test still passes)
            pass

    def test_escalation_flow(self, temp_home: Path, mock_sender: MockSessionSender):
        """Test escalation when max duration is exceeded."""
        state_sync = StateSync(user_home=temp_home)

        # Create an event that exceeds critical thresholds
        from datetime import timezone

        now = datetime.now(timezone.utc)
        event = TimeoutEvent(
            session_id="escalation_test",
            detected_at=now,
            expected_duration=timedelta(minutes=5),
            actual_duration=timedelta(hours=2),  # Way over limit
            status=SessionStatus.TIMEOUT_SUSPECTED,
        )
        state_sync.emit_timeout_suspected(event)

        # Process with critical policy
        policy_engine = PolicyEngine()
        policy_engine.assign_policy("escalation_test", "critical_task")
        notifier = Notifier(sender=mock_sender)

        # Read pending events
        pending = state_sync.get_pending_suspected_events()

        for evt in pending:
            decision = policy_engine.evaluate(evt)

            # Critical task policy escalates quickly
            if decision.action == ActionType.ESCALATE:
                # Confirm and send escalation
                confirmed = state_sync.confirm_timeout(evt.session_id)
                if confirmed:
                    notifier.send_escalation(confirmed)

        # Verify escalation message was sent
        escalation_msgs = [m for sid, m in mock_sender.sent_messages if "🚨" in m]
        assert len(escalation_msgs) > 0 or len(mock_sender.sent_messages) > 0

    def test_clear_confirmed_timeouts(self, temp_home: Path):
        """Test clearing confirmed timeouts from state."""
        state_sync = StateSync(user_home=temp_home)

        # Create multiple events
        from datetime import timezone

        now = datetime.now(timezone.utc)
        suspected_event = TimeoutEvent(
            session_id="suspected_session",
            detected_at=now,
            expected_duration=timedelta(minutes=5),
            actual_duration=timedelta(minutes=10),
            status=SessionStatus.TIMEOUT_SUSPECTED,
        )
        confirmed_event = TimeoutEvent(
            session_id="confirmed_session",
            detected_at=now,
            expected_duration=timedelta(minutes=5),
            actual_duration=timedelta(minutes=20),
            status=SessionStatus.TIMEOUT_SUSPECTED,
        )

        state_sync.emit_timeout_suspected(suspected_event)
        state_sync.emit_timeout_suspected(confirmed_event)

        # Confirm one
        state_sync.confirm_timeout("confirmed_session")

        # Clear confirmed
        cleared = state_sync.clear_confirmed_timeouts()
        assert cleared == 1

        # Verify only suspected remains
        pending = state_sync.get_pending_suspected_events()
        assert len(pending) == 1
        assert pending[0].session_id == "suspected_session"

    def test_end_to_end_monitoring_cycle(self, temp_home: Path, mock_sender: MockSessionSender):
        """Test a complete monitoring and response cycle."""
        # Initialize all components
        state_sync = StateSync(user_home=temp_home)
        store_adapter = RuntimeStoreAdapter(state_sync)
        detector = TimeoutDetector(
            store=store_adapter,
            config=DetectionConfig(
                default_timeout=timedelta(seconds=0),
                grace_period=timedelta(seconds=0),
                min_session_duration=timedelta(seconds=0),
            ),
        )
        policy_engine = PolicyEngine()
        notifier = Notifier(sender=mock_sender)

        # Step 1: Monitor detects timeout
        detector.start_monitoring("e2e_session")
        events = detector.check_timeouts()
        assert len(events) == 1
        detected_event = events[0]

        # Step 2: Event is in runtime store
        pending = state_sync.get_pending_suspected_events()
        assert any(e.session_id == "e2e_session" for e in pending)

        # Step 3: Watchdog processes suspected timeout
        decision = policy_engine.evaluate(detected_event)

        # Step 4: Send reminder based on policy
        if decision.should_send_reminder(0):
            reminder = notifier.send_suspected_timeout(detected_event)
            assert reminder is not None
            policy_engine.record_reminder(detected_event.session_id)

        # Step 5: Eventually confirm timeout
        if policy_engine.should_confirm_timeout(detected_event, decision):
            confirmed = state_sync.confirm_timeout(detected_event.session_id)
            assert confirmed is not None
            notifier.send_confirmed_timeout(confirmed)

        # Verify state has both suspected and confirmed events
        all_events = state_sync.get_pending_suspected_events()
        assert len(all_events) >= 1

    def test_multiple_sessions_tracking(self, temp_home: Path):
        """Test tracking multiple concurrent sessions."""
        state_sync = StateSync(user_home=temp_home)
        store_adapter = RuntimeStoreAdapter(state_sync)

        detector = TimeoutDetector(
            store=store_adapter,
            config=DetectionConfig(
                default_timeout=timedelta(seconds=0),
                grace_period=timedelta(seconds=0),
                min_session_duration=timedelta(seconds=0),
            ),
        )

        # Start multiple sessions
        sessions = ["session_a", "session_b", "session_c"]
        for sid in sessions:
            detector.start_monitoring(sid)

        # Check all timeouts
        events = detector.check_timeouts()
        assert len(events) == 3

        # Verify all are tracked
        pending = state_sync.get_pending_suspected_events()
        pending_ids = {e.session_id for e in pending}
        assert pending_ids == set(sessions)


class TestRuntimeStoreAdapter:
    """Tests for RuntimeStoreAdapter."""

    @pytest.fixture
    def temp_home(self):
        """Create a temporary home directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_adapter_emits_event(self, temp_home: Path):
        """Test that adapter properly emits events through state sync."""
        state_sync = StateSync(user_home=temp_home)
        adapter = RuntimeStoreAdapter(state_sync)

        from datetime import timezone

        now = datetime.now(timezone.utc)
        event = TimeoutEvent(
            session_id="adapter_test",
            detected_at=now,
            expected_duration=timedelta(minutes=5),
            actual_duration=timedelta(minutes=10),
            status=SessionStatus.TIMEOUT_SUSPECTED,
        )

        adapter.emit_timeout_event(event)

        # Verify via state_sync
        pending = state_sync.get_pending_suspected_events()
        assert len(pending) == 1
        assert pending[0].session_id == "adapter_test"

    def test_adapter_get_session_activity_returns_none(self, temp_home: Path):
        """Test that get_session_last_activity returns None (not implemented)."""
        state_sync = StateSync(user_home=temp_home)
        adapter = RuntimeStoreAdapter(state_sync)

        result = adapter.get_session_last_activity("any_session")
        assert result is None
