from pathlib import Path
from typing import Any, Mapping

OPENCLAW_HOME_DIRNAME = ".openclaw"
ENHANCE_DIRNAME = "openclaw-enhance"
RUNTIME_STATE_FILENAME = "runtime-state.json"
CONFIG_BACKUP_FILENAME = "config.json.bak"


def managed_root(user_home: Path | None = None) -> Path:
    base_home = user_home if user_home is not None else Path.home()
    return base_home / OPENCLAW_HOME_DIRNAME / ENHANCE_DIRNAME


def runtime_state_file(user_home: Path | None = None) -> Path:
    return managed_root(user_home) / RUNTIME_STATE_FILENAME


def config_backup_file(user_home: Path | None = None) -> Path:
    return managed_root(user_home) / CONFIG_BACKUP_FILENAME


def ensure_managed_directories(user_home: Path | None = None) -> Path:
    root = managed_root(user_home)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _normalize_workspace_path(workspace: str, openclaw_home: Path) -> Path:
    expanded = Path(workspace).expanduser()
    if expanded.is_absolute():
        return expanded
    return openclaw_home / expanded


def _workspace_from_config(config: Mapping[str, Any], openclaw_home: Path) -> Path | None:
    agent = config.get("agent")
    if isinstance(agent, Mapping):
        workspace = agent.get("workspace")
        if isinstance(workspace, str) and workspace:
            return _normalize_workspace_path(workspace, openclaw_home)

    agents = config.get("agents")
    if isinstance(agents, Mapping):
        defaults = agents.get("defaults")
        if isinstance(defaults, Mapping):
            workspace = defaults.get("workspace")
            if isinstance(workspace, str) and workspace:
                return _normalize_workspace_path(workspace, openclaw_home)

    return None


def resolve_main_workspace(
    openclaw_home: Path,
    config: Mapping[str, Any] | None,
    env: Mapping[str, str] | None,
) -> Path:
    resolved_from_config = _workspace_from_config(config or {}, openclaw_home)
    if resolved_from_config is not None:
        return resolved_from_config

    profile = (env or {}).get("OPENCLAW_PROFILE")
    if profile and profile != "default":
        return openclaw_home / f"workspace-{profile}"

    return openclaw_home / "workspace"


def main_workspace_skills_dir(workspace_path: Path) -> Path:
    return workspace_path / "skills"


def resolve_openclaw_config_path(openclaw_home: Path) -> Path:
    """Resolve OpenClaw config path, preferring openclaw.json over config.json.

    Args:
        openclaw_home: Path to OpenClaw home directory.

    Returns:
        Path to openclaw.json if it exists, otherwise config.json.
    """
    openclaw_json = openclaw_home / "openclaw.json"
    if openclaw_json.exists():
        return openclaw_json
    return openclaw_home / "config.json"
