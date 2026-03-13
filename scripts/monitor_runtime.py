#!/usr/bin/env python3
"""Runtime monitor script for OpenClaw timeout detection.

This script monitors the OpenClaw runtime for suspected timeouts and emits
timeout_suspected events to the runtime store. The watchdog then reads these
events, confirms them, and sends reminders as appropriate.

This script is designed to be run periodically (e.g., every minute) via cron
or a similar scheduler.

Usage:
    python scripts/monitor_runtime.py [--check-interval SECONDS]

Exit codes:
    0 - Success, no timeouts detected
    1 - Success, timeouts detected and reported
    2 - Error occurred during monitoring
"""

import argparse
import logging
import sys
from datetime import timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openclaw_enhance.watchdog.detector import (
    DetectionConfig,
    TimeoutDetector,
)
from openclaw_enhance.watchdog.policy import PolicyEngine
from openclaw_enhance.watchdog.notifier import Notifier
from openclaw_enhance.watchdog.state_sync import RuntimeStoreAdapter, StateSync


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("openclaw.monitor")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Monitor OpenClaw runtime for timeouts",
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=60,
        help="Check interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--default-timeout",
        type=int,
        default=300,
        help="Default timeout in seconds (default: 300 = 5 minutes)",
    )
    parser.add_argument(
        "--grace-period",
        type=int,
        default=60,
        help="Grace period in seconds before marking timeout (default: 60)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--process-pending",
        action="store_true",
        help="Process pending suspected timeouts (watchdog mode)",
    )
    return parser.parse_args()


def setup_detector(args: argparse.Namespace) -> TimeoutDetector:
    """Set up the timeout detector with configuration.

    Args:
        args: Parsed command line arguments

    Returns:
        Configured TimeoutDetector
    """
    config = DetectionConfig(
        default_timeout=timedelta(seconds=args.default_timeout),
        grace_period=timedelta(seconds=args.grace_period),
    )

    # Create state sync and wrap it for the detector
    state_sync = StateSync()
    store_adapter = RuntimeStoreAdapter(state_sync)

    detector = TimeoutDetector(
        store=store_adapter,
        config=config,
    )

    return detector


def run_monitor_mode(detector: TimeoutDetector) -> int:
    """Run in monitor mode - detect and report suspected timeouts.

    Args:
        detector: Configured timeout detector

    Returns:
        Exit code (0 for success/no timeouts, 1 if timeouts detected)
    """
    logger.info("Starting runtime timeout monitoring...")

    try:
        # Check for timeouts
        events = detector.check_timeouts()

        if events:
            logger.info(f"Detected {len(events)} suspected timeout(s)")
            for event in events:
                logger.info(
                    f"  - Session {event.session_id}: "
                    f"expected {event.expected_duration}, "
                    f"actual {event.actual_duration}"
                )
            return 1
        else:
            logger.debug("No timeouts detected")
            return 0

    except Exception as e:
        logger.error(f"Error during monitoring: {e}")
        return 2


def run_watchdog_mode() -> int:
    """Run in watchdog mode - process pending suspected timeouts.

        This mode reads suspected timeouts from the runtime store, evaluates
    them against policies, confirms appropriate ones, and sends reminders.

        Returns:
            Exit code (0 for success, 2 for error)
    """
    logger.info("Starting watchdog processing of suspected timeouts...")

    try:
        state_sync = StateSync()
        policy_engine = PolicyEngine()
        notifier = Notifier()

        # Get pending suspected events
        events = state_sync.get_pending_suspected_events()

        if not events:
            logger.debug("No pending suspected timeouts to process")
            return 0

        logger.info(f"Processing {len(events)} suspected timeout(s)")
        actions_taken = 0

        for event in events:
            # Evaluate against policy
            decision = policy_engine.evaluate(event)

            logger.info(
                f"Session {event.session_id}: policy={decision.action.name}, "
                f"reason={decision.reason}"
            )

            # Check if we should confirm the timeout
            if policy_engine.should_confirm_timeout(event, decision):
                logger.info(f"Confirming timeout for session {event.session_id}")
                confirmed = state_sync.confirm_timeout(event.session_id)

                if confirmed:
                    # Send confirmed timeout reminder
                    notifier.send_confirmed_timeout(confirmed)
                    policy_engine.record_reminder(event.session_id)
                    actions_taken += 1

            # Send reminders based on policy
            elif decision.should_send_reminder(policy_engine.get_reminder_count(event.session_id)):
                logger.info(f"Sending reminder for session {event.session_id}")
                reminder = notifier.send_suspected_timeout(event)

                if reminder:
                    policy_engine.record_reminder(event.session_id)
                    actions_taken += 1

        logger.info(f"Watchdog processing complete. Actions taken: {actions_taken}")
        return 0

    except Exception as e:
        logger.error(f"Error during watchdog processing: {e}")
        return 2


def main() -> int:
    """Main entry point.

    Returns:
        Exit code
    """
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.process_pending:
            # Watchdog mode: process pending suspected timeouts
            return run_watchdog_mode()
        else:
            # Monitor mode: detect new suspected timeouts
            detector = setup_detector(args)
            return run_monitor_mode(detector)

    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
