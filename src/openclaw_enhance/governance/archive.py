from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from openclaw_enhance.cleanup import CleanupCandidate, CleanupKind, CleanupStatus


@dataclass(frozen=True)
class ArchiveReport:
    safe_to_archive: list[str]
    skipped_active: list[str]
    skipped_uncertain: list[str]
    archived: list[str]
    archive_root: str
    dry_run: bool


def discover_session_candidates(sessions_root: Path) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    if not sessions_root.exists():
        return candidates

    for path in sessions_root.iterdir():
        candidates.append(
            CleanupCandidate(
                path=path,
                kind=CleanupKind.CORE_SESSION,
                age_hours=72,
                in_runtime_active_set=False,
                held_by_project_occupancy=False,
                has_recent_activity=False,
            )
        )
    return candidates


def archive_paths(
    candidates: list[CleanupCandidate],
    *,
    archive_root: Path,
    dry_run: bool,
    stale_threshold_hours: float,
    include_core_sessions: bool,
) -> ArchiveReport:
    safe_to_archive: list[str] = []
    skipped_active: list[str] = []
    skipped_uncertain: list[str] = []
    archived: list[str] = []

    for candidate in candidates:
        status = classify_archive_candidate(
            candidate,
            stale_threshold_hours=stale_threshold_hours,
            include_core_sessions=include_core_sessions,
        )
        if status is CleanupStatus.SAFE_TO_REMOVE:
            safe_to_archive.append(str(candidate.path))
            if not dry_run:
                destination = archive_root / candidate.path.name
                archive_root.mkdir(parents=True, exist_ok=True)
                shutil.move(str(candidate.path), destination)
                archived.append(str(destination))
        elif status is CleanupStatus.SKIPPED_ACTIVE:
            skipped_active.append(str(candidate.path))
        else:
            skipped_uncertain.append(str(candidate.path))

    return ArchiveReport(
        safe_to_archive=safe_to_archive,
        skipped_active=skipped_active,
        skipped_uncertain=skipped_uncertain,
        archived=archived,
        archive_root=str(archive_root),
        dry_run=dry_run,
    )


def classify_archive_candidate(
    candidate: CleanupCandidate,
    *,
    stale_threshold_hours: float,
    include_core_sessions: bool,
) -> CleanupStatus:
    if (
        candidate.in_runtime_active_set
        or candidate.held_by_project_occupancy
        or candidate.has_recent_activity
    ):
        return CleanupStatus.SKIPPED_ACTIVE
    if candidate.age_hours < stale_threshold_hours:
        return CleanupStatus.SKIPPED_ACTIVE
    if not include_core_sessions and candidate.kind is CleanupKind.CORE_SESSION:
        return CleanupStatus.SKIPPED_UNCERTAIN
    return CleanupStatus.SAFE_TO_REMOVE
