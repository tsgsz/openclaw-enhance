from __future__ import annotations

import fcntl
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

PINNED_OPENCLAW_MODEL = "minimax/MiniMax-M2.1"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("OpenClaw config root must be a JSON object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def get_primary_model(config_path: Path) -> str | None:
    payload = _load_json(config_path)
    agents = payload.get("agents")
    if not isinstance(agents, dict):
        return None
    defaults = agents.get("defaults")
    if not isinstance(defaults, dict):
        return None
    model = defaults.get("model")
    if isinstance(model, dict):
        primary = model.get("primary")
        return primary if isinstance(primary, str) else None
    return model if isinstance(model, str) else None


def _pin_payload(payload: dict[str, Any], model: str) -> dict[str, Any]:
    agents = payload.setdefault("agents", {})
    if not isinstance(agents, dict):
        payload["agents"] = agents = {}

    defaults = agents.setdefault("defaults", {})
    if not isinstance(defaults, dict):
        agents["defaults"] = defaults = {}

    model_cfg = defaults.get("model")
    if isinstance(model_cfg, dict):
        model_cfg["primary"] = model
        model_cfg["fallbacks"] = []
    else:
        defaults["model"] = {"primary": model, "fallbacks": []}

    models_cfg = defaults.setdefault("models", {})
    if not isinstance(models_cfg, dict):
        defaults["models"] = models_cfg = {}
    models_cfg.setdefault(model, {})

    for key in ("heartbeat", "subagents"):
        value = defaults.get(key)
        if isinstance(value, dict):
            value["model"] = model

    agent_list = agents.get("list")
    if isinstance(agent_list, list):
        for agent in agent_list:
            if not isinstance(agent, dict):
                continue
            if agent.get("id") != "oe-orchestrator":
                continue

            if isinstance(agent.get("model"), dict):
                agent["model"]["primary"] = model
                agent["model"]["fallbacks"] = []
            else:
                agent["model"] = {"primary": model, "fallbacks": []}

            nested_defaults = agent.get("defaults")
            if isinstance(nested_defaults, dict):
                nested_model = nested_defaults.get("model")
                if isinstance(nested_model, dict):
                    nested_model["primary"] = model
                    nested_model["fallbacks"] = []
                else:
                    nested_defaults["model"] = {"primary": model, "fallbacks": []}

    return payload


@contextmanager
def pinned_openclaw_runtime_model(
    config_path: Path, model: str = PINNED_OPENCLAW_MODEL
) -> Iterator[str]:
    lock_path = config_path.with_name(f"{config_path.name}.model-pin.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        original_text = config_path.read_text(encoding="utf-8") if config_path.exists() else None
        payload = _load_json(config_path)
        pinned = _pin_payload(payload, model)
        _write_json(config_path, pinned)
        try:
            yield get_primary_model(config_path) or model
        finally:
            if original_text is None:
                if config_path.exists():
                    config_path.unlink()
            else:
                config_path.write_text(original_text, encoding="utf-8")
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
