from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
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


def build_cleanup_report_payload(report: CleanupReport) -> dict[str, object]:
    return {
        "safe_to_remove": report.safe_to_remove,
        "skipped_active": report.skipped_active,
        "skipped_uncertain": report.skipped_uncertain,
        "removed": report.removed,
        "dry_run": report.dry_run,
    }


def discover_cleanup_candidates(
    *,
    openclaw_home: Path | None = None,
    working_directory: Path | None = None,
) -> list[CleanupCandidate]:
    if openclaw_home is not None:
        return _discover_openclaw_home_candidates(openclaw_home)
    base_dir = working_directory if working_directory is not None else Path.cwd()
    return _discover_working_directory_candidates(base_dir)


def _discover_working_directory_candidates(base_dir: Path) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    sessions_root = base_dir / "sessions"
    if not sessions_root.exists():
        return candidates

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
    return candidates


def _discover_openclaw_home_candidates(openclaw_home: Path) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    agents_root = openclaw_home / "agents"
    if not agents_root.exists():
        return candidates

    for sessions_root in agents_root.glob("*/sessions"):
        if not sessions_root.is_dir():
            continue
        active_session_ids = _read_live_session_ids(sessions_root / "sessions.json")
        for path in sessions_root.iterdir():
            if not path.is_file() or path.name == "sessions.json":
                continue
            session_id = _derive_session_id(path)
            kind = _kind_for_openclaw_session_path(path)
            candidates.append(
                CleanupCandidate(
                    path=path,
                    kind=kind,
                    age_hours=_age_hours(path),
                    in_runtime_active_set=session_id in active_session_ids,
                    held_by_project_occupancy=False,
                    has_recent_activity=False,
                )
            )

    return candidates


def _read_live_session_ids(sessions_json: Path) -> set[str]:
    if not sessions_json.exists():
        return set()
    try:
        payload = json.loads(sessions_json.read_text(encoding="utf-8"))
    except Exception:
        return set()
    if not isinstance(payload, dict):
        return set()

    session_ids: set[str] = set()
    for value in payload.values():
        if not isinstance(value, dict):
            continue
        session_id = value.get("sessionId")
        if isinstance(session_id, str) and session_id:
            session_ids.add(session_id)
    return session_ids


def _derive_session_id(path: Path) -> str:
    name = path.name
    if ".jsonl.deleted." in name:
        return name.split(".jsonl.deleted.", 1)[0]
    if ".jsonl.reset." in name:
        return name.split(".jsonl.reset.", 1)[0]
    if name.endswith(".jsonl"):
        return name[: -len(".jsonl")]
    return path.stem


def _kind_for_openclaw_session_path(path: Path) -> CleanupKind:
    name = path.name
    if ".jsonl.deleted." in name or ".jsonl.reset." in name:
        return CleanupKind.RUNTIME_STATE
    return CleanupKind.CORE_SESSION


def _age_hours(path: Path) -> float:
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    return max((now - modified).total_seconds() / 3600, 0.0)


def _is_binding_stale_for_classification(
    binding_status: dict[str, object],
    restart_epoch: int,
) -> bool:
    """Determine if a binding is stale based on status and epoch comparison."""
    status = binding_status.get("binding_status")
    if status in ("unbound", "revoked"):
        return True
    if status == "bound":
        binding_epoch_val = binding_status.get("binding_epoch", 0)
        if isinstance(binding_epoch_val, int):
            return binding_epoch_val < restart_epoch
        return False
    return False


def classify_candidate(
    candidate: CleanupCandidate,
    stale_threshold_hours: float,
    binding_status: dict[str, object] | None = None,
    restart_epoch: int = 0,
) -> CleanupCandidate:
    # For RUNTIME_STATE candidates, check ownership binding status.
    # If binding is stale (unbound, revoked, or binding_epoch < restart_epoch),
    # treat as safe to remove - the runtime state is orphaned.
    if candidate.kind is CleanupKind.RUNTIME_STATE and binding_status is not None:
        if _is_binding_stale_for_classification(binding_status, restart_epoch):
            return replace(candidate, status=CleanupStatus.SAFE_TO_REMOVE)

    # RUNTIME_STATE files (.deleted., .reset.) are already terminated sessions.
    # Skip in_runtime_active_set check for these - the .deleted/.reset suffix
    # means the session was intentionally ended, so we trust the suffix over sessions.json.
    is_terminated = candidate.kind is CleanupKind.RUNTIME_STATE

    # If a session appears in sessions.json but its file is way older than the
    # stale threshold (>= 48x), the sessions.json entry is orphaned and we
    # should trust the file age over sessions.json. OpenClaw doesn't always
    # clean up sessions.json entries when sessions end.
    sessions_json_max_age_hours = stale_threshold_hours * 48
    is_sessions_json_stale = (
        candidate.in_runtime_active_set and candidate.age_hours >= sessions_json_max_age_hours
    )

    if not is_terminated and (
        (candidate.in_runtime_active_set and not is_sessions_json_stale)
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
    binding_status: dict[str, object] | None = None,
    restart_epoch: int = 0,
) -> CleanupReport:
    safe_to_remove: list[str] = []
    skipped_active: list[str] = []
    skipped_uncertain: list[str] = []
    removed: list[str] = []

    for candidate in candidates:
        classified = classify_candidate(
            candidate,
            stale_threshold_hours,
            binding_status=binding_status,
            restart_epoch=restart_epoch,
        )
        if classified.kind is CleanupKind.CORE_SESSION and not include_core_sessions:
            skipped_uncertain.append(str(classified.path))
            continue
        if (
            classified.kind is CleanupKind.CORE_SESSION
            and include_core_sessions
            and classified.status is CleanupStatus.SKIPPED_UNCERTAIN
        ):
            classified = replace(classified, status=CleanupStatus.SAFE_TO_REMOVE)
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


def main(argv: list[str] | None = None) -> int:
    from openclaw_enhance.cli import cli

    cleanup_args = list(argv) if argv is not None else sys.argv[1:]
    command = ["cleanup-sessions", *cleanup_args]
    try:
        cli.main(
            args=command, prog_name="python -m openclaw_enhance.cleanup", standalone_mode=False
        )
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
