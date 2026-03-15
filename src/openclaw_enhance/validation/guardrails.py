"""Baseline state capture and cleanup verification for real environment testing.

Captures state before validation and verifies cleanup afterward.
Refuses to mutate foreign/preexisting enhance state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openclaw_enhance.install.manifest import load_manifest
from openclaw_enhance.paths import managed_root


class ForeignStateError(RuntimeError):
    """Raised when target state is foreign or unsafe to mutate."""

    pass


@dataclass
class BaselineState:
    """Captured baseline state before validation."""

    openclaw_home: Path
    is_installed: bool
    owned_by_checkout: bool
    config_state: dict[str, Any]
    managed_root_state: dict[str, Any]


def capture_baseline_state(openclaw_home: Path) -> BaselineState:
    """Capture baseline state before validation.

    Args:
        openclaw_home: Path to OpenClaw home directory.

    Returns:
        BaselineState with captured information.

    Raises:
        RuntimeError: If harness readiness checks fail.
    """
    # Harness readiness checks for canonical ~/.openclaw
    _verify_harness_readiness(openclaw_home)

    target_root = managed_root(openclaw_home.parent)

    # Check if installed
    manifest = load_manifest(target_root)
    is_installed = manifest is not None

    # Check ownership
    owned_by_checkout = _check_ownership(target_root)

    # Capture config state
    config_state = _capture_config_state(openclaw_home)

    # Capture managed root state
    managed_root_state = _capture_managed_root_state(target_root)

    return BaselineState(
        openclaw_home=openclaw_home,
        is_installed=is_installed,
        owned_by_checkout=owned_by_checkout,
        config_state=config_state,
        managed_root_state=managed_root_state,
    )


def _check_ownership(target_root: Path) -> bool:
    """Check if target belongs to current checkout."""
    if not target_root.exists():
        return True

    manifest = load_manifest(target_root)
    if not manifest:
        return False

    # Check for workspace symlinks (dev mode indicator)
    workspaces_dir = target_root / "workspaces"
    if workspaces_dir.exists():
        for item in workspaces_dir.iterdir():
            if item.is_symlink():
                return True

    return False


def _capture_config_state(openclaw_home: Path) -> dict[str, Any]:
    """Capture config.json state."""
    from openclaw_enhance.paths import resolve_openclaw_config_path

    config_path = resolve_openclaw_config_path(openclaw_home)
    if not config_path.exists():
        return {"exists": False}

    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)

        return {
            "exists": True,
            "has_enhance_namespace": "openclawEnhance" in config,
            "enhance_config": config.get("openclawEnhance", {}),
        }
    except (json.JSONDecodeError, OSError):
        return {"exists": True, "readable": False}


def _capture_managed_root_state(target_root: Path) -> dict[str, Any]:
    """Capture managed root directory state."""
    if not target_root.exists():
        return {"exists": False}

    state = {"exists": True, "contents": []}

    try:
        for item in target_root.iterdir():
            state["contents"].append(
                {
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "is_symlink": item.is_symlink(),
                }
            )
    except OSError:
        state["readable"] = False

    return state


def _verify_harness_readiness(openclaw_home: Path) -> None:
    """Verify canonical harness target readiness.

    Args:
        openclaw_home: Path to OpenClaw home directory.

    Raises:
        RuntimeError: If harness readiness checks fail.
    """
    from openclaw_enhance.paths import resolve_openclaw_config_path

    if not openclaw_home.exists():
        raise RuntimeError(
            f"unsupported/missing-home: OpenClaw home {openclaw_home} does not exist"
        )

    version_file = openclaw_home / "VERSION"
    if not version_file.exists():
        raise RuntimeError(f"unsupported/missing-home: missing VERSION file under {openclaw_home}")

    config_path = resolve_openclaw_config_path(openclaw_home)
    if not config_path.exists():
        raise RuntimeError(
            f"unsupported/missing-home: missing OpenClaw config "
            f"(openclaw.json or config.json) under {openclaw_home}"
        )


def verify_ownership(state: BaselineState) -> bool:
    """Verify if target is owned by current checkout.

    Args:
        state: Captured baseline state.

    Returns:
        True if owned by current checkout.

    Raises:
        ForeignStateError: If state is foreign or unsafe.
    """
    if state.is_installed and not state.owned_by_checkout:
        target_root = managed_root(state.openclaw_home.parent)
        raise ForeignStateError(
            f"Target {target_root} appears to be managed by a different installation. "
            "Refusing to mutate foreign state."
        )

    return state.owned_by_checkout


def verify_cleanup_success(
    initial_state: BaselineState,
    final_state: BaselineState,
) -> bool:
    """Verify cleanup was successful by comparing states.

    Args:
        initial_state: State before validation.
        final_state: State after cleanup.

    Returns:
        True if cleanup successful.
    """
    # If wasn't installed initially, should still not be installed
    if not initial_state.is_installed:
        return not final_state.is_installed

    # If was installed and owned, should be cleaned up
    if initial_state.owned_by_checkout:
        return not final_state.is_installed

    # Foreign state should remain unchanged
    return (
        initial_state.is_installed == final_state.is_installed
        and initial_state.config_state == final_state.config_state
    )
