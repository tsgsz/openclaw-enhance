from collections.abc import Mapping
from copy import deepcopy
from typing import Any

OWNED_NAMESPACE = "openclawEnhance"

# v2: No owned agent specs - agents no longer exist in v2 architecture
OWNED_AGENT_SPECS: tuple[tuple[str, str], ...] = ()

OWNED_HOOK_ENTRY_IDS: tuple[str, ...] = ("oe-subagent-spawn-enrich",)

OWNED_EXTENSION_ID = "oe-runtime"


def filter_owned_keys(
    patch: Mapping[str, Any], namespace: str = OWNED_NAMESPACE
) -> dict[str, dict[str, Any]]:
    owned_value = patch.get(namespace)
    if not isinstance(owned_value, Mapping):
        return {}
    return {namespace: deepcopy(dict(owned_value))}


def deep_merge(base: dict[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def changed_paths(before: Mapping[str, Any], after: Mapping[str, Any], prefix: str) -> list[str]:
    keys = sorted(set(before.keys()) | set(after.keys()))
    results: list[str] = []
    for key in keys:
        before_value = before.get(key)
        after_value = after.get(key)
        current_path = f"{prefix}.{key}"
        if isinstance(before_value, Mapping) and isinstance(after_value, Mapping):
            results.extend(changed_paths(before_value, after_value, current_path))
            continue
        if before_value != after_value:
            results.append(current_path)
    return results
