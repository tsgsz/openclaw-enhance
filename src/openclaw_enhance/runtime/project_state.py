import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_enhance.paths import ensure_managed_directories, runtime_state_file
from openclaw_enhance.runtime.schema import RuntimeState


def _load_state(user_home: Path | None = None) -> dict[str, Any]:
    """Load runtime state as a dictionary."""
    path = runtime_state_file(user_home)
    if not path.exists():
        return RuntimeState().model_dump()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Use Pydantic to validate and fill defaults, then dump back to dict
        return RuntimeState.model_validate(data).model_dump()
    except (json.JSONDecodeError, Exception):
        return RuntimeState().model_dump()


def _save_state(state: dict[str, Any], user_home: Path | None = None) -> None:
    """Save runtime state atomically."""
    ensure_managed_directories(user_home)
    path = runtime_state_file(user_home)
    tmp_path = path.with_suffix(".tmp")

    # Update last_updated_utc
    state["last_updated_utc"] = datetime.utcnow().isoformat()

    try:
        tmp_path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        os.replace(str(tmp_path), str(path))
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def get_active_project(user_home: Path | None = None) -> str | None:
    """Read active_project from runtime state file."""
    state = _load_state(user_home)
    return state.get("active_project")


def set_active_project(path: str | None, user_home: Path | None = None) -> None:
    """Write active_project to runtime state file."""
    state = _load_state(user_home)
    state["active_project"] = path
    _save_state(state, user_home)


def acquire_project(path: str, session_id: str, user_home: Path | None = None) -> bool:
    """Try to occupy a permanent project. Returns True if acquired."""
    state = _load_state(user_home)
    occupancy = state.get("project_occupancy", {})

    current_owner = occupancy.get(path)
    if current_owner and current_owner != session_id:
        return False

    occupancy[path] = session_id
    state["project_occupancy"] = occupancy
    _save_state(state, user_home)
    return True


def release_project(path: str, session_id: str, user_home: Path | None = None) -> bool:
    """Release project occupation. Returns True if released."""
    state = _load_state(user_home)
    occupancy = state.get("project_occupancy", {})

    if occupancy.get(path) == session_id:
        del occupancy[path]
        state["project_occupancy"] = occupancy
        _save_state(state, user_home)
        return True
    return False


def get_project_owner(path: str, user_home: Path | None = None) -> str | None:
    """Get session_id currently occupying path, or None."""
    state = _load_state(user_home)
    occupancy: dict[str, str] = state.get("project_occupancy", {})
    return occupancy.get(path)
