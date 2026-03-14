"""Workspace management for openclaw-enhance.

This module provides functionality for:
- Discovering and listing workspaces
- Rendering workspace configurations
- Managing workspace metadata
"""

import os
from pathlib import Path
from typing import Any

from openclaw_enhance.agent_catalog import parse_agent_manifest


def _resolve_workspaces_dir() -> Path:
    """Resolve the workspaces directory based on environment and installation."""
    # 1. Environment variable override (highest priority for validation/testing)
    env_path = os.environ.get("OPENCLAW_ENHANCE_WORKSPACES_DIR")
    if env_path:
        return Path(env_path)

    # 2. Check local directory (dev mode in repo root)
    local_dir = Path("workspaces")
    if local_dir.exists() and local_dir.is_dir():
        return local_dir

    # 3. Check managed root (standard installation)
    try:
        from openclaw_enhance.paths import managed_root

        managed = managed_root() / "workspaces"
        if managed.exists() and managed.is_dir():
            return managed
    except Exception:
        pass

    # 4. Fallback to package-relative (for repo-based execution from anywhere)
    # src/openclaw_enhance/workspaces.py -> ../../workspaces
    pkg_workspaces = Path(__file__).parent.parent.parent / "workspaces"
    if pkg_workspaces.exists() and pkg_workspaces.is_dir():
        return pkg_workspaces

    return Path("workspaces")


WORKSPACES_DIR = _resolve_workspaces_dir()


def _get_workspace_path(workspace_name: str) -> Path:
    """Get the path to a workspace directory.

    Args:
        workspace_name: Name of the workspace.

    Returns:
        Path to the workspace directory.
    """
    return WORKSPACES_DIR / workspace_name


def list_workspaces() -> list[str]:
    """List all available workspaces.

    Returns:
        List of workspace names.
    """
    if not WORKSPACES_DIR.exists():
        return []

    return [d.name for d in WORKSPACES_DIR.iterdir() if d.is_dir() and (d / "AGENTS.md").exists()]


def workspace_exists(workspace_name: str) -> bool:
    """Check if a workspace exists.

    Args:
        workspace_name: Name of the workspace.

    Returns:
        True if the workspace exists, False otherwise.
    """
    workspace_path = _get_workspace_path(workspace_name)
    return workspace_path.exists() and workspace_path.is_dir()


def get_workspace_skills(workspace_name: str) -> list[str]:
    """Get list of skills for a workspace.

    Args:
        workspace_name: Name of the workspace.

    Returns:
        List of skill names.

    Raises:
        ValueError: If workspace does not exist.
    """
    if not workspace_exists(workspace_name):
        raise ValueError(f"Unknown workspace: {workspace_name}")

    skills_dir = _get_workspace_path(workspace_name) / "skills"
    if not skills_dir.exists():
        return []

    return [d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]


def get_workspace_metadata(workspace_name: str) -> dict[str, Any]:
    """Get metadata for a workspace.

    Args:
        workspace_name: Name of the workspace.

    Returns:
        Dictionary with workspace metadata including parsed frontmatter if available.

    Raises:
        ValueError: If workspace does not exist.
    """
    if not workspace_exists(workspace_name):
        raise ValueError(f"Unknown workspace: {workspace_name}")

    workspace_path = _get_workspace_path(workspace_name)
    skills = get_workspace_skills(workspace_name)

    metadata = {
        "name": workspace_name,
        "path": str(workspace_path.absolute()),
        "skills": skills,
        "has_agents": (workspace_path / "AGENTS.md").exists(),
        "has_tools": (workspace_path / "TOOLS.md").exists(),
    }

    # Parse frontmatter from AGENTS.md if available
    agents_path = workspace_path / "AGENTS.md"
    if agents_path.exists():
        manifest = parse_agent_manifest(agents_path.read_text())
        metadata["manifest"] = {
            "agent_id": manifest.agent_id,
            "workspace": manifest.workspace,
            "routing": manifest.routing,
            "is_valid": manifest.is_valid,
            "errors": manifest.errors,
        }

    return metadata


def _read_file_if_exists(path: Path) -> str:
    """Read file content if it exists, otherwise return empty string.

    Args:
        path: Path to the file.

    Returns:
        File content or empty string.
    """
    if path.exists():
        return path.read_text()
    return ""


def render_workspace(workspace_name: str) -> str:
    """Render a workspace configuration as markdown.

    This combines AGENTS.md, TOOLS.md, and all skill definitions into
    a single comprehensive document.

    Args:
        workspace_name: Name of the workspace to render.

    Returns:
        Rendered workspace configuration as markdown string.

    Raises:
        ValueError: If workspace does not exist.
    """
    if not workspace_exists(workspace_name):
        raise ValueError(f"Unknown workspace: {workspace_name}")

    workspace_path = _get_workspace_path(workspace_name)

    parts: list[str] = []

    # Header
    parts.append(f"# Workspace: {workspace_name}")
    parts.append("")
    parts.append(f"**Path:** `{workspace_path}`")
    parts.append("")

    # AGENTS.md
    agents_content = _read_file_if_exists(workspace_path / "AGENTS.md")
    if agents_content:
        parts.append(agents_content)
        parts.append("")
        parts.append("---")
        parts.append("")

    # TOOLS.md
    tools_content = _read_file_if_exists(workspace_path / "TOOLS.md")
    if tools_content:
        parts.append(tools_content)
        parts.append("")
        parts.append("---")
        parts.append("")

    # Skills
    skills = get_workspace_skills(workspace_name)
    if skills:
        parts.append("# Workspace Skills")
        parts.append("")

        for skill_name in sorted(skills):
            skill_path = workspace_path / "skills" / skill_name / "SKILL.md"
            skill_content = _read_file_if_exists(skill_path)

            if skill_content:
                parts.append(f"## {skill_name}")
                parts.append("")
                parts.append(skill_content)
                parts.append("")
                parts.append("---")
                parts.append("")

    return "\n".join(parts)
