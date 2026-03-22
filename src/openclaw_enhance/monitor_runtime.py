from __future__ import annotations

import argparse
import logging
from datetime import timedelta
from pathlib import Path

from openclaw_enhance.cleanup import CleanupCandidate, CleanupKind, cleanup_paths
from openclaw_enhance.watchdog.detector import DetectionConfig, TimeoutDetector
from openclaw_enhance.watchdog.notifier import Notifier
from openclaw_enhance.watchdog.policy import PolicyEngine
from openclaw_enhance.watchdog.state_sync import RuntimeStoreAdapter, StateSync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("openclaw.monitor")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor OpenClaw runtime for timeouts")
    parser.add_argument("--check-interval", type=int, default=60)
    parser.add_argument("--default-timeout", type=int, default=300)
    parser.add_argument("--grace-period", type=int, default=60)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--process-pending", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--openclaw-home", type=str, default=None)
    parser.add_argument("--state-root", type=str, default=None)
    return parser.parse_args()


def resolve_user_home(
    openclaw_home: Path | None,
    state_root: Path | None,
) -> Path | None:
    if state_root is not None:
        return state_root.expanduser().resolve().parent.parent
    if openclaw_home is not None:
        return openclaw_home.expanduser().resolve().parent
    return None


def get_user_home(args: argparse.Namespace) -> Path | None:
    openclaw_home = Path(args.openclaw_home) if args.openclaw_home else None
    state_root = Path(args.state_root) if args.state_root else None
    return resolve_user_home(openclaw_home=openclaw_home, state_root=state_root)


def setup_detector(args: argparse.Namespace) -> TimeoutDetector:
    config = DetectionConfig(
        default_timeout=timedelta(seconds=args.default_timeout),
        grace_period=timedelta(seconds=args.grace_period),
    )
    user_home = get_user_home(args)
    state_sync = StateSync(user_home=user_home)
    store_adapter = RuntimeStoreAdapter(state_sync)
    return TimeoutDetector(store=store_adapter, config=config)


def run_monitor_mode(detector: TimeoutDetector) -> int:
    logger.info("Starting runtime timeout monitoring...")
    try:
        events = detector.check_timeouts()
        if events:
            logger.info("Detected %s suspected timeout(s)", len(events))
            for event in events:
                logger.info(
                    "  - Session %s: expected %s, actual %s",
                    event.session_id,
                    event.expected_duration,
                    event.actual_duration,
                )
            return 1
        logger.debug("No timeouts detected")
        return 0
    except Exception as exc:
        logger.error("Error during monitoring: %s", exc)
        return 2


def run_watchdog_mode(args: argparse.Namespace) -> int:
    logger.info("Starting watchdog processing of suspected timeouts...")
    try:
        user_home = get_user_home(args)
        state_sync = StateSync(user_home=user_home)
        policy_engine = PolicyEngine()
        notifier = Notifier()
        events = state_sync.get_pending_suspected_events()

        if not events:
            logger.debug("No pending suspected timeouts to process")
            return 0

        logger.info("Processing %s suspected timeout(s)", len(events))
        actions_taken = 0
        for event in events:
            decision = policy_engine.evaluate(event)
            logger.info(
                "Session %s: policy=%s, reason=%s",
                event.session_id,
                decision.action.name,
                decision.reason,
            )

            if policy_engine.should_confirm_timeout(event, decision):
                confirmed = state_sync.confirm_timeout(event.session_id)
                if confirmed:
                    notifier.send_confirmed_timeout(confirmed)
                    policy_engine.record_reminder(event.session_id)
                    actions_taken += 1
            elif decision.should_send_reminder(policy_engine.get_reminder_count(event.session_id)):
                reminder = notifier.send_suspected_timeout(event)
                if reminder:
                    policy_engine.record_reminder(event.session_id)
                    actions_taken += 1

        logger.info("Watchdog processing complete. Actions taken: %s", actions_taken)
        return 0
    except Exception as exc:
        logger.error("Error during watchdog processing: %s", exc)
        return 2


def run_cleanup_mode(args: argparse.Namespace) -> int:
    logger.info("Starting automatic session cleanup...")
    try:
        sessions_root = Path.cwd() / "sessions"
        candidates: list[CleanupCandidate] = []
        if sessions_root.exists():
            for path in sessions_root.iterdir():
                candidates.append(
                    CleanupCandidate(
                        path=path,
                        kind=CleanupKind.RUNTIME_STATE,
                        age_hours=72,
                        in_runtime_active_set=False,
                        held_by_project_occupancy=False,
                        has_recent_activity=False,
                    )
                )

        report = cleanup_paths(
            candidates,
            dry_run=False,
            stale_threshold_hours=24,
            include_core_sessions=True,
        )
        logger.info(
            "Automatic cleanup complete. removed=%s skipped_active=%s skipped_uncertain=%s",
            len(report.removed),
            len(report.skipped_active),
            len(report.skipped_uncertain),
        )
        return 0
    except Exception as exc:
        logger.error("Error during automatic cleanup: %s", exc)
        return 2


def main() -> int:
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.process_pending:
        return run_watchdog_mode(args)

    detector = setup_detector(args)
    monitor_exit = run_monitor_mode(detector)
    cleanup_exit = run_cleanup_mode(args)
    if monitor_exit != 0:
        return monitor_exit
    return cleanup_exit


if __name__ == "__main__":
    raise SystemExit(main())
