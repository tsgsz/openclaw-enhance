"""Install manifest management for openclaw-enhance.

The manifest tracks installation state, versions, and installed components
to enable proper lifecycle management and rollback support.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_enhance.constants import VERSION

MANIFEST_FILENAME = "install-manifest.json"


@dataclass
class ComponentInstall:
    """Installation record for a single component."""

    name: str
    version: str
    install_time: datetime
    source_path: str | None = None
    target_path: str | None = None
    checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "install_time": self.install_time.isoformat(),
            "source_path": self.source_path,
            "target_path": self.target_path,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComponentInstall:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            version=data["version"],
            install_time=datetime.fromisoformat(data["install_time"]),
            source_path=data.get("source_path"),
            target_path=data.get("target_path"),
            checksum=data.get("checksum"),
        )


@dataclass
class InstallManifest:
    """Manifest tracking complete installation state."""

    version: str = VERSION
    install_time: datetime = field(default_factory=datetime.utcnow)
    components: list[ComponentInstall] = field(default_factory=list)
    openclaw_home: str | None = None
    last_updated: datetime = field(default_factory=datetime.utcnow)
    rollback_points: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "install_time": self.install_time.isoformat(),
            "components": [c.to_dict() for c in self.components],
            "openclaw_home": self.openclaw_home,
            "last_updated": self.last_updated.isoformat(),
            "rollback_points": self.rollback_points,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InstallManifest:
        """Create from dictionary."""
        return cls(
            version=data.get("version", VERSION),
            install_time=datetime.fromisoformat(data["install_time"]),
            components=[ComponentInstall.from_dict(c) for c in data.get("components", [])],
            openclaw_home=data.get("openclaw_home"),
            last_updated=datetime.fromisoformat(data.get("last_updated", data["install_time"])),
            rollback_points=data.get("rollback_points", []),
        )

    def get_component(self, name: str) -> ComponentInstall | None:
        """Get a component by name."""
        for component in self.components:
            if component.name == name:
                return component
        return None

    def add_component(self, component: ComponentInstall) -> None:
        """Add or update a component."""
        existing = self.get_component(component.name)
        if existing:
            self.components.remove(existing)
        self.components.append(component)
        self.last_updated = datetime.utcnow()

    def remove_component(self, name: str) -> bool:
        """Remove a component by name. Returns True if found and removed."""
        component = self.get_component(name)
        if component:
            self.components.remove(component)
            self.last_updated = datetime.utcnow()
            return True
        return False

    def add_rollback_point(self, description: str, backup_paths: dict[str, str]) -> None:
        """Add a rollback point for recovery."""
        rollback_point = {
            "timestamp": datetime.utcnow().isoformat(),
            "description": description,
            "backup_paths": backup_paths,
        }
        self.rollback_points.append(rollback_point)
        # Keep only last 10 rollback points
        self.rollback_points = self.rollback_points[-10:]
        self.last_updated = datetime.utcnow()


def manifest_path(managed_root: Path) -> Path:
    """Get the path to the manifest file."""
    return managed_root / MANIFEST_FILENAME


def load_manifest(managed_root: Path) -> InstallManifest | None:
    """Load manifest from disk if it exists."""
    path = manifest_path(managed_root)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return InstallManifest.from_dict(data)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def save_manifest(manifest: InstallManifest, managed_root: Path) -> Path:
    """Save manifest to disk."""
    path = manifest_path(managed_root)
    managed_root.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def is_installed(managed_root: Path) -> bool:
    """Check if openclaw-enhance is installed."""
    manifest = load_manifest(managed_root)
    if manifest is None:
        return False
    return len(manifest.components) > 0


def get_install_version(managed_root: Path) -> str | None:
    """Get the installed version if any."""
    manifest = load_manifest(managed_root)
    if manifest is None:
        return None
    return manifest.version
