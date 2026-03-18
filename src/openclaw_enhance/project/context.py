from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from openclaw_enhance.project.detector import ProjectKind, detect_project
from openclaw_enhance.project.git_ops import gather_git_context

if TYPE_CHECKING:
    from openclaw_enhance.project.registry import ProjectRegistry


def build_project_context(project_path: Path, registry: ProjectRegistry) -> dict:
    """Build full dispatch context for a registered project."""
    path_str = str(project_path.resolve())
    entry = registry.get(project_path)

    if entry:
        return {
            "project_id": path_str,
            "project_name": entry["name"],
            "project_type": entry["type"],
            "project_subtype": entry["subtype"],
            "project_kind": entry["kind"],
            "working_dir": path_str,
            "git_context": gather_git_context(project_path),
            "metadata": entry.get("metadata", {}),
        }

    # Fallback if not in registry but we want to build context anyway (e.g. during detection)
    info = detect_project(project_path)
    if info:
        return {
            "project_id": path_str,
            "project_name": info.name,
            "project_type": str(info.type.value) if hasattr(info.type, "value") else str(info.type),
            "project_subtype": info.subtype,
            "project_kind": ProjectKind.temporary.value,
            "working_dir": path_str,
            "git_context": gather_git_context(project_path),
            "metadata": info.metadata,
        }

    # Ultimate fallback
    return {
        "project_id": "default",
        "project_name": "default",
        "project_type": "unknown",
        "project_subtype": "",
        "project_kind": ProjectKind.temporary.value,
        "working_dir": path_str,
        "git_context": gather_git_context(project_path),
        "metadata": {},
    }


def resolve_project_context(
    path: Path,
    registry: ProjectRegistry,
    active_project: str | None = None,
) -> dict:
    """Canonical resolution chain: explicit → active_project → detect → 'default'."""
    # 1. Explicit path in registry
    if registry.get(path):
        return build_project_context(path, registry)

    # 2. active_project matches a registered project
    if active_project:
        active_path = Path(active_project)
        if registry.get(active_path):
            return build_project_context(active_path, registry)

    # 3. Detect and auto-register as temporary
    info = detect_project(path)
    if info:
        registry.register(info, kind=ProjectKind.temporary.value)
        return build_project_context(path, registry)

    # 4. Default fallback
    return build_project_context(path, registry)
