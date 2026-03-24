from __future__ import annotations

from pathlib import Path

from openclaw_enhance.paths import managed_root


def legacy_workspace_root(user_home: Path | None = None) -> Path:
    base_home = user_home if user_home is not None else Path.home()
    return base_home / ".openclaw" / "workspace"


def legacy_governance_dir(user_home: Path | None = None) -> Path:
    return legacy_workspace_root(user_home) / "scripts" / "governance"


def legacy_subagents_file(user_home: Path | None = None) -> Path:
    return legacy_workspace_root(user_home) / "sub_agents.json"


def legacy_subagents_state_file(user_home: Path | None = None) -> Path:
    return legacy_workspace_root(user_home) / "sub_agents_state.json"


def managed_governance_root(user_home: Path | None = None) -> Path:
    return managed_root(user_home) / "governance"


def managed_archive_root(user_home: Path | None = None) -> Path:
    return managed_governance_root(user_home) / "archive"
