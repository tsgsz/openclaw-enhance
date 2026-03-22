from __future__ import annotations

import shutil
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path


class CleanupKind(str, Enum):
    CORE_SESSION = "core_session"
    RUNTIME_STATE = "runtime_state"


class CleanupStatus(str, Enum):
    SAFE_TO_REMOVE = "safe_to_remove"
    SKIPPED_ACTIVE = "skipped_active"
    SKIPPED_UNCERTAIN = "skipped_uncertain"


@dataclass(frozen=True)
class CleanupCandidate:
    path: Path
    kind: CleanupKind
    age_hours: float
    in_runtime_active_set: bool
    held_by_project_occupancy: bool
    has_recent_activity: bool
    status: CleanupStatus | None = None


@dataclass(frozen=True)
class CleanupReport:
    safe_to_remove: list[str]
    skipped_active: list[str]
    skipped_uncertain: list[str]
    removed: list[str]
    dry_run: bool


def classify_candidate(
    candidate: CleanupCandidate,
    stale_threshold_hours: float,
) -> CleanupCandidate:
    if (
        candidate.in_runtime_active_set
        or candidate.held_by_project_occupancy
        or candidate.has_recent_activity
    ):
        return replace(candidate, status=CleanupStatus.SKIPPED_ACTIVE)
    if candidate.age_hours < stale_threshold_hours:
        return replace(candidate, status=CleanupStatus.SKIPPED_ACTIVE)
    if candidate.kind is CleanupKind.CORE_SESSION:
        return replace(candidate, status=CleanupStatus.SKIPPED_UNCERTAIN)
    return replace(candidate, status=CleanupStatus.SAFE_TO_REMOVE)


def cleanup_paths(
    candidates: list[CleanupCandidate],
    *,
    dry_run: bool,
    stale_threshold_hours: float,
    include_core_sessions: bool,
) -> CleanupReport:
    safe_to_remove: list[str] = []
    skipped_active: list[str] = []
    skipped_uncertain: list[str] = []
    removed: list[str] = []

    for candidate in candidates:
        classified = classify_candidate(candidate, stale_threshold_hours)
        if classified.kind is CleanupKind.CORE_SESSION and not include_core_sessions:
            skipped_uncertain.append(str(classified.path))
            continue
        if classified.status is CleanupStatus.SAFE_TO_REMOVE:
            safe_to_remove.append(str(classified.path))
            if not dry_run:
                if classified.path.is_dir():
                    shutil.rmtree(classified.path)
                elif classified.path.exists():
                    classified.path.unlink()
                removed.append(str(classified.path))
        elif classified.status is CleanupStatus.SKIPPED_ACTIVE:
            skipped_active.append(str(classified.path))
        else:
            skipped_uncertain.append(str(classified.path))

    return CleanupReport(
        safe_to_remove=safe_to_remove,
        skipped_active=skipped_active,
        skipped_uncertain=skipped_uncertain,
        removed=removed,
        dry_run=dry_run,
    )
