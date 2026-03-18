from __future__ import annotations

import fcntl
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openclaw_enhance.project.detector import ProjectInfo

logger = logging.getLogger(__name__)

REGISTRY_FILENAME = "project-registry.json"
REGISTRY_SCHEMA_VERSION = 2

_EMPTY_REGISTRY: dict[str, Any] = {
    "schema_version": REGISTRY_SCHEMA_VERSION,
    "last_scan": None,
    "projects": {},
}


class ProjectRegistry:
    def __init__(self, registry_path: Path) -> None:
        self._path = registry_path
        self._data = self.load()

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return _make_empty()

        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, OSError):
            logger.warning("Corrupt or unreadable registry at %s, starting fresh", self._path)
            return _make_empty()

        return _migrate(data)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        lock_path = self._path.parent / f"{REGISTRY_FILENAME}.lock"
        tmp_path = self._path.parent / f"{REGISTRY_FILENAME}.tmp"

        try:
            lock_fd = open(lock_path, "w")  # noqa: SIM115
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
                tmp_path.write_text(
                    json.dumps(self._data, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                os.replace(str(tmp_path), str(self._path))
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    def register(
        self,
        project_info: ProjectInfo,
        kind: str,
        github_remote: str | None = None,
    ) -> str:
        canonical = str(Path(project_info.path).resolve())
        now = datetime.now(timezone.utc).isoformat()

        entry: dict[str, Any] = {
            "name": project_info.name,
            "type": str(project_info.type.value)
            if hasattr(project_info.type, "value")
            else str(project_info.type),
            "subtype": project_info.subtype,
            "kind": kind,
            "path": canonical,
            "indicator_file": project_info.indicator_file,
            "indicator_mtime": project_info.indicator_mtime,
            "github_remote": github_remote,
            "detected_at": self._data["projects"].get(canonical, {}).get("detected_at", now),
            "last_accessed": now,
            "metadata": dict(project_info.metadata) if project_info.metadata else {},
        }

        self._data["projects"][canonical] = entry
        self.save()
        return canonical

    def get(self, path: Path) -> dict[str, Any] | None:
        canonical = str(Path(path).resolve())
        return self._data["projects"].get(canonical)

    def list_projects(self, kind: str | None = None) -> list[dict[str, Any]]:
        projects = list(self._data["projects"].values())
        if kind is not None:
            projects = [p for p in projects if p.get("kind") == kind]
        return projects

    def scan(self, root: Path, kind: str = "permanent") -> list[dict[str, Any]]:
        from openclaw_enhance.project.detector import detect_project

        found: list[dict[str, Any]] = []
        root = root.resolve()

        if not root.is_dir():
            return found

        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            info = detect_project(child)
            if info is not None:
                key = self.register(info, kind=kind)
                entry = self._data["projects"][key]
                found.append(entry)

        self._data["last_scan"] = datetime.now(timezone.utc).isoformat()
        self.save()
        return found

    def update_last_accessed(self, path: Path) -> None:
        canonical = str(Path(path).resolve())
        entry = self._data["projects"].get(canonical)
        if entry is not None:
            entry["last_accessed"] = datetime.now(timezone.utc).isoformat()
            self.save()

    def is_stale(self, path: Path) -> bool:
        canonical = str(Path(path).resolve())
        entry = self._data["projects"].get(canonical)
        if entry is None:
            return False

        indicator_file = Path(entry["path"]) / entry["indicator_file"]
        if not indicator_file.exists():
            return True

        current_mtime = indicator_file.stat().st_mtime
        stored_mtime = entry.get("indicator_mtime", 0.0)
        return current_mtime != stored_mtime


def _make_empty() -> dict[str, Any]:
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "last_scan": None,
        "projects": {},
    }


def _migrate(data: dict[str, Any]) -> dict[str, Any]:
    if "version" in data and "schema_version" not in data:
        migrated = _make_empty()
        if isinstance(data.get("projects"), list):
            for entry in data["projects"]:
                if isinstance(entry, dict) and "path" in entry:
                    migrated["projects"][entry["path"]] = entry
        return migrated

    if data.get("schema_version", 0) < REGISTRY_SCHEMA_VERSION:
        data["schema_version"] = REGISTRY_SCHEMA_VERSION
        if isinstance(data.get("projects"), list):
            projects_dict: dict[str, Any] = {}
            for entry in data["projects"]:
                if isinstance(entry, dict) and "path" in entry:
                    projects_dict[entry["path"]] = entry
            data["projects"] = projects_dict
        elif not isinstance(data.get("projects"), dict):
            data["projects"] = {}
        data.setdefault("last_scan", None)

    return data
