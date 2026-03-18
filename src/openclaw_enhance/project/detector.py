"""Project type detection and data model.

NOTE: This is a stub for Task 2 (registry) to depend on.
Task 1 (parallel) creates the full implementation.
If Task 1 completes first, this file will be replaced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ProjectType(str, Enum):
    """Detected project type based on indicator files."""

    python = "python"
    nodejs = "nodejs"
    rust = "rust"
    go = "go"
    java = "java"
    ruby = "ruby"
    php = "php"
    cpp = "cpp"
    unknown = "unknown"


class ProjectKind(str, Enum):
    """Project lifecycle kind."""

    permanent = "permanent"
    temporary = "temporary"


@dataclass
class ProjectInfo:
    """Information about a detected project."""

    path: Path
    name: str
    type: ProjectType
    subtype: str = ""
    kind: ProjectKind = ProjectKind.permanent
    indicator_file: str = ""
    indicator_mtime: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


def detect_project(path: Path) -> ProjectInfo | None:
    """Detect project type from directory.

    Stub implementation — checks for common indicator files.
    Full implementation in Task 1.
    """
    indicators = {
        "pyproject.toml": (ProjectType.python, "pyproject"),
        "package.json": (ProjectType.nodejs, "npm"),
        "Cargo.toml": (ProjectType.rust, "cargo"),
        "go.mod": (ProjectType.go, "module"),
    }
    for filename, (ptype, subtype) in indicators.items():
        indicator = path / filename
        if indicator.exists():
            return ProjectInfo(
                path=path.resolve(),
                name=path.name,
                type=ptype,
                subtype=subtype,
                indicator_file=filename,
                indicator_mtime=indicator.stat().st_mtime,
            )
    return None


def find_project_root(path: Path) -> Path | None:
    """Walk up from path to find project root.

    Stub — full implementation in Task 1.
    """
    current = path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None
