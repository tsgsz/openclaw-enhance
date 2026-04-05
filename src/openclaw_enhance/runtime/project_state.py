import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, cast

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


# ---------------------------------------------------------------------------
# Restart epoch and ownership binding helpers
# ---------------------------------------------------------------------------


def bump_restart_epoch(user_home: Path | None = None) -> int:
    """Increment restart_epoch by 1 and persist. Returns the new value."""
    state = _load_state(user_home)
    new_epoch = state.get("restart_epoch", 0) + 1
    state["restart_epoch"] = new_epoch
    _save_state(state, user_home)
    return cast(int, new_epoch)


def get_binding_status(user_home: Path | None = None) -> dict[str, Any]:
    """Return the current ownership_contract dict."""
    state = _load_state(user_home)
    return dict(state.get("ownership_contract", {}))


def is_binding_stale(user_home: Path | None = None) -> bool:
    """Return True when binding_epoch < restart_epoch (binding is stale)."""
    state = _load_state(user_home)
    binding_epoch = state.get("ownership_contract", {}).get("binding_epoch", 0)
    restart_epoch = state.get("restart_epoch", 0)
    return cast(bool, binding_epoch < restart_epoch)


def revoke_binding(user_home: Path | None = None) -> None:
    """Set binding_status to 'revoked' in the ownership contract."""
    state = _load_state(user_home)
    contract = state.get("ownership_contract", {})
    contract["binding_status"] = "revoked"
    state["ownership_contract"] = contract
    _save_state(state, user_home)


def rebind_ownership(
    channel_type: str | None,
    channel_conversation_id: str | None,
    bound_session_id: str | None,
    user_home: Path | None = None,
) -> None:
    """Bind the ownership contract with the current restart_epoch."""
    state = _load_state(user_home)
    state["ownership_contract"] = {
        "channel_type": channel_type,
        "channel_conversation_id": channel_conversation_id,
        "bound_session_id": bound_session_id,
        "binding_epoch": state.get("restart_epoch", 0),
        "binding_status": "bound",
    }
    _save_state(state, user_home)
