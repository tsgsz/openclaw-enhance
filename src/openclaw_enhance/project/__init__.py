"""Project detection, registration, and context management."""

from __future__ import annotations

from .detector import (
    ProjectInfo,
    ProjectKind,
    ProjectType,
    detect_project,
    find_project_root,
)

__all__ = [
    "ProjectInfo",
    "ProjectKind",
    "ProjectType",
    "detect_project",
    "find_project_root",
]
