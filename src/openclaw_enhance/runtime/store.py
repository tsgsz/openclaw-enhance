import json
from pathlib import Path

from openclaw_enhance.paths import ensure_managed_directories, runtime_state_file
from openclaw_enhance.runtime.schema import RuntimeState


def load_runtime_state(user_home: Path | None = None) -> RuntimeState:
    state_path = runtime_state_file(user_home)
    if not state_path.exists():
        return RuntimeState()
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    return RuntimeState.model_validate(payload)


def save_runtime_state(state: RuntimeState, user_home: Path | None = None) -> Path:
    ensure_managed_directories(user_home)
    state_path = runtime_state_file(user_home)
    state_path.write_text(state.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return state_path
