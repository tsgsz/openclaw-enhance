from pathlib import Path

from openclaw_enhance.cleanup import (
    CleanupCandidate,
    CleanupKind,
    CleanupStatus,
    classify_candidate,
)


def test_classify_core_session_as_skipped_active_when_recent() -> None:
    candidate = CleanupCandidate(
        path=Path("/tmp/session-active"),
        kind=CleanupKind.CORE_SESSION,
        age_hours=1,
        in_runtime_active_set=True,
    )

    classified = classify_candidate(candidate, stale_threshold_hours=24)

    assert classified.status is CleanupStatus.SKIPPED_ACTIVE


def test_classify_core_session_as_skipped_uncertain_when_old_but_unproven() -> None:
    candidate = CleanupCandidate(
        path=Path("/tmp/session-uncertain"),
        kind=CleanupKind.CORE_SESSION,
        age_hours=72,
        in_runtime_active_set=False,
    )

    classified = classify_candidate(candidate, stale_threshold_hours=24)

    assert classified.status is CleanupStatus.SKIPPED_UNCERTAIN


def test_classify_runtime_candidate_as_safe_to_remove_when_old_and_unowned() -> None:
    candidate = CleanupCandidate(
        path=Path("/tmp/runtime-entry"),
        kind=CleanupKind.RUNTIME_STATE,
        age_hours=72,
        in_runtime_active_set=False,
    )

    classified = classify_candidate(candidate, stale_threshold_hours=24)

    assert classified.status is CleanupStatus.SAFE_TO_REMOVE
