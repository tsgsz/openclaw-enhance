from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

ALLOWED_SUBAGENT_STATUS = {"spawning", "running", "done", "dead", "suspicious"}


def read_subagents(path: Path) -> dict[str, Any]:
    return _read_json(path, {"version": 1, "sub_agents": []})


def read_subagent_state(path: Path) -> dict[str, Any]:
    return _read_json(path, {"version": 1, "state": {}})


def set_subagent_status(
    path: Path, child_session_id: str, status: str, *, suggestion: str = ""
) -> None:
    if status not in ALLOWED_SUBAGENT_STATUS:
        raise ValueError(f"invalid status: {status}")

    payload = read_subagents(path)
    rows = payload.get("sub_agents")
    if not isinstance(rows, list):
        raise RuntimeError("invalid sub_agents payload")

    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("child_session_id") or "") != child_session_id:
            continue
        row["status"] = status
        row["suggestion"] = suggestion
        _atomic_write_json(path, payload)
        return

    raise KeyError(child_session_id)


def set_subagent_eta(path: Path, child_session_id: str, eta: str) -> None:
    payload = read_subagents(path)
    rows = payload.get("sub_agents")
    if not isinstance(rows, list):
        raise RuntimeError("invalid sub_agents payload")

    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("child_session_id") or "") != child_session_id:
            continue
        row["eta"] = str(eta)
        _atomic_write_json(path, payload)
        return

    raise KeyError(child_session_id)


def merge_subagent_state(path: Path, child_session_id: str, patch: dict[str, Any]) -> None:
    payload = read_subagent_state(path)
    state = payload.get("state")
    if not isinstance(state, dict):
        raise RuntimeError("invalid sub_agents_state payload")

    current = state.get(child_session_id)
    if not isinstance(current, dict):
        current = {}
        state[child_session_id] = current

    current.update(patch)
    _atomic_write_json(path, payload)


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return payload if isinstance(payload, dict) else default


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + f".tmp.{os.getpid()}.{int(time.time() * 1000)}")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)
