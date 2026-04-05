"""Model discovery and selection for ACP opencode sessions."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, cast

from openclaw_enhance.paths import managed_root

DEFAULT_MODEL_PRIORITY = [
    "cliproxy/gpt-5.4",
    "minimax-coding-plan/MiniMax-M2.7",
    "minimax-coding-plan/MiniMax-M2.5",
    "kimi-for-coding/k2p5",
]

MODEL_CACHE_FILENAME = "model-cache.json"
MODEL_CONFIG_FILENAME = "model-config.json"


def _run_opencode_models() -> list[str]:
    try:
        result = subprocess.run(
            ["opencode", "models"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        lines = result.stdout.strip().split("\n")
        return [line.strip() for line in lines if line.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def _load_model_cache(user_home: Path | None = None) -> dict[str, Any]:
    cache_path = managed_root(user_home) / MODEL_CACHE_FILENAME
    if not cache_path.exists():
        return {}
    try:
        return cast(dict[str, Any], json.loads(cache_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_model_cache(cache: dict[str, Any], user_home: Path | None = None) -> None:
    cache_path = managed_root(user_home) / MODEL_CACHE_FILENAME
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_model_config(user_home: Path | None = None) -> dict[str, Any]:
    config_path = managed_root(user_home) / MODEL_CONFIG_FILENAME
    if not config_path.exists():
        return {}
    try:
        return cast(dict[str, Any], json.loads(config_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return {}


def discover_available_models(
    user_home: Path | None = None, force_refresh: bool = False
) -> list[str]:
    cache = _load_model_cache(user_home)

    if not force_refresh and cache.get("models"):
        cached_models = cache.get("models", [])
        if cached_models:
            return cast(list[str], cached_models)

    models = _run_opencode_models()

    cache["models"] = models
    cache["probe_time"] = time.time()
    _save_model_cache(cache, user_home)

    return models


def get_model_priority(user_home: Path | None = None) -> list[str]:
    config = _load_model_config(user_home)
    priority = config.get("acpModelPriority")
    if isinstance(priority, list) and priority:
        return [m for m in priority if isinstance(m, str)]
    return DEFAULT_MODEL_PRIORITY.copy()


def select_model_by_priority(user_home: Path | None = None) -> str | None:
    priority = get_model_priority(user_home)
    available = set(discover_available_models(user_home))

    for model in priority:
        if model in available:
            return model

    if available:
        return sorted(available, key=lambda x: x.lower())[0]

    return None


def rotate_on_failure(
    failed_model: str,
    user_home: Path | None = None,
) -> str | None:
    priority = get_model_priority(user_home)
    available = set(discover_available_models(user_home))

    found_failed = False
    for model in priority:
        if model == failed_model:
            found_failed = True
            continue
        if found_failed and model in available:
            return model

    priority_set = set(priority)
    for model in sorted(available, key=lambda x: x.lower()):
        if model not in priority_set:
            return model

    return None


def is_model_available(model: str, user_home: Path | None = None) -> bool:
    available = discover_available_models(user_home)
    return model in available
