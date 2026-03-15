import json
import os
import shutil
from pathlib import Path
from typing import Any

from openclaw_enhance.runtime.ownership import (
    OWNED_NAMESPACE,
    changed_paths,
    deep_merge,
    filter_owned_keys,
)
from openclaw_enhance.runtime.schema import ConfigPatchResult


class ConfigPatchError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ConfigPatchError("Config root must be an object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def apply_owned_config_patch(
    config_path: Path,
    patch: dict[str, Any],
    namespace: str = OWNED_NAMESPACE,
    fail_on_write: bool = False,
) -> ConfigPatchResult:
    original = _read_json(config_path)
    owned_patch_wrapper = filter_owned_keys(patch, namespace)
    owned_patch = owned_patch_wrapper.get(namespace, {})

    previous_owned = original.get(namespace, {})
    previous_owned_dict = previous_owned if isinstance(previous_owned, dict) else {}
    updated_owned = deep_merge(previous_owned_dict, owned_patch)

    updated_config = dict(original)
    if owned_patch:
        updated_config[namespace] = updated_owned

    backup_path = config_path.with_name(f"{config_path.name}.bak")
    temp_path = config_path.with_name(f"{config_path.name}.tmp")

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if config_path.exists():
            shutil.copy2(config_path, backup_path)
        _write_json(temp_path, updated_config)
        if fail_on_write:
            raise OSError("Injected write failure")
        os.replace(temp_path, config_path)
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        if backup_path.exists():
            shutil.copy2(backup_path, config_path)
        raise ConfigPatchError(f"Failed to apply config patch: {exc}") from exc

    changes = changed_paths(previous_owned_dict, updated_owned, namespace)
    return ConfigPatchResult(changed_keys=changes, backup_path=str(backup_path))
