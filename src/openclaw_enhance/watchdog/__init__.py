"""Watchdog package for monitoring OpenClaw runtime and detecting timeouts.

This package provides components for:
- Detecting timeouts in OpenClaw sessions
- Evaluating timeout policies
- Sending notifications/reminders
- Syncing state with the runtime store
"""

from openclaw_enhance.watchdog.detector import TimeoutDetector, TimeoutEvent
from openclaw_enhance.watchdog.notifier import Notifier, ReminderType
from openclaw_enhance.watchdog.policy import PolicyEngine, TimeoutPolicy
from openclaw_enhance.watchdog.state_sync import StateSync

__all__ = [
    "PolicyEngine",
    "ReminderType",
    "StateSync",
    "TimeoutDetector",
    "TimeoutEvent",
    "TimeoutPolicy",
    "Notifier",
]
