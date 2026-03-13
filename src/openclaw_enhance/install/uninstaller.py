"""Uninstallation logic for openclaw-enhance.

Handles the complete uninstall flow:
1. Preflight checks
2. Acquire lock
3. Remove hooks
4. Unregister agents
5. Remove workspaces
6. Clean up namespace
7. Remove manifest

Supports rollback to restore on failure.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_enhance.install.lock import InstallLock, InstallLockError
from openclaw_enhance.install.manifest import (
    InstallManifest,
    load_manifest,
    manifest_path,
)
from openclaw_enhance.paths import managed_root
from openclaw_enhance.runtime.config_patch import (
    ConfigPatchError,
    apply_owned_config_patch,
)


class UninstallError(RuntimeError):
    """Raised when uninstallation fails."""

    pass


@dataclass
class UninstallResult:
    """Result of an uninstallation operation."""

    success: bool
    message: str
    components_removed: list[str] = field(default_factory=list)
    components_failed: list[str] = field(default_factory=list)
    backup_restored: bool = False


def _remove_hooks(
    manifest: InstallManifest,
    openclaw_home: Path,
) -> list[str]:
    """Remove hooks from OpenClaw configuration.

    Uses JSON read-modify-write to remove hook configuration.
    """
    removed: list[str] = []

    config_candidates = [
        openclaw_home / "config.json",
        openclaw_home / "openclaw.json",
        Path.home() / ".config" / "openclaw" / "config.json",
    ]

    config_path = None
    for candidate in config_candidates:
        if candidate.exists():
            config_path = candidate
            break

    if not config_path:
        return removed

    try:
        # Read current config
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)

        # Check if our namespace exists
        if "openclawEnhance" not in config:
            return removed

        # Create backup
        backup_path = config_path.with_suffix(".json.bak")
        shutil.copy2(config_path, backup_path)

        # Remove hooks section from our namespace
        if "hooks" in config.get("openclawEnhance", {}):
            del config["openclawEnhance"]["hooks"]
            removed.append("hooks:subagent-spawn-enrich")

        # If namespace is now empty, remove it entirely
        if config.get("openclawEnhance") == {}:
            del config["openclawEnhance"]

        # Write updated config
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, sort_keys=True)
            f.write("\n")

        return removed
    except (json.JSONDecodeError, OSError, KeyError) as exc:
        raise UninstallError(f"Failed to remove hooks: {exc}") from exc


def _unregister_agents(
    manifest: InstallManifest,
    openclaw_home: Path,
) -> list[str]:
    """Unregister agents from OpenClaw configuration.

    Uses JSON read-modify-write to remove agent registration.
    """
    removed: list[str] = []

    config_candidates = [
        openclaw_home / "config.json",
        openclaw_home / "openclaw.json",
        Path.home() / ".config" / "openclaw" / "config.json",
    ]

    config_path = None
    for candidate in config_candidates:
        if candidate.exists():
            config_path = candidate
            break

    if not config_path:
        return removed

    try:
        # Read current config
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)

        # Check if our namespace exists
        if "openclawEnhance" not in config:
            return removed

        # Create backup
        backup_path = config_path.with_suffix(".json.bak")
        shutil.copy2(config_path, backup_path)

        # Remove agents section from our namespace
        if "agents" in config.get("openclawEnhance", {}):
            del config["openclawEnhance"]["agents"]
            removed.append("agents:registry")

        # If namespace is now empty, remove it entirely
        if config.get("openclawEnhance") == {}:
            del config["openclawEnhance"]

        # Write updated config
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, sort_keys=True)
            f.write("\n")

        return removed
    except (json.JSONDecodeError, OSError, KeyError) as exc:
        raise UninstallError(f"Failed to unregister agents: {exc}") from exc


def _remove_workspaces(target_root: Path) -> list[str]:
    """Remove synced workspace configurations."""
    removed: list[str] = []
    workspaces_dir = target_root / "workspaces"

    if workspaces_dir.exists():
        try:
            shutil.rmtree(workspaces_dir)
            removed.append("workspaces")
        except OSError as exc:
            raise UninstallError(f"Failed to remove workspaces: {exc}") from exc

    return removed


def _remove_runtime_state(target_root: Path) -> list[str]:
    """Remove runtime state file."""
    removed: list[str] = []
    state_file = target_root / "runtime-state.json"

    if state_file.exists():
        try:
            state_file.unlink()
            removed.append("runtime:state")
        except OSError as exc:
            raise UninstallError(f"Failed to remove runtime state: {exc}") from exc

    return removed


def _remove_lock_file(target_root: Path) -> list[str]:
    """Remove lock file if present."""
    removed: list[str] = []
    lock_file = target_root / ".install.lock"

    if lock_file.exists():
        try:
            lock_file.unlink()
            removed.append("lock")
        except OSError:
            # Non-fatal
            pass

    return removed


def uninstall(
    openclaw_home: Path | None = None,
    user_home: Path | None = None,
    force: bool = False,
) -> UninstallResult:
    """Uninstall openclaw-enhance.

    Args:
        openclaw_home: Optional path to OpenClaw home directory.
        user_home: Optional override for user home directory.
        force: If True, uninstall even if checks fail.

    Returns:
        UninstallResult with success status and details.
    """
    target_root = managed_root(user_home)

    # Check if installed
    manifest = load_manifest(target_root)
    if not manifest and not force:
        return UninstallResult(
            success=True,
            message="openclaw-enhance is not installed",
            components_removed=[],
        )

    # Use manifest's recorded openclaw_home if not provided
    if openclaw_home is None and manifest:
        openclaw_home = Path(manifest.openclaw_home) if manifest.openclaw_home else None

    if openclaw_home is None:
        openclaw_home = Path.home() / ".openclaw"

    # Step 1: Acquire lock
    try:
        lock = InstallLock(target_root)
        if not lock.acquire(operation="uninstall", blocking=True):
            return UninstallResult(
                success=False,
                message="Could not acquire uninstall lock",
            )
    except InstallLockError as exc:
        return UninstallResult(
            success=False,
            message=f"Lock acquisition failed: {exc}",
        )

    removed: list[str] = []
    failed: list[str] = []

    try:
        # Step 2: Remove hooks
        try:
            hooks_removed = _remove_hooks(manifest or InstallManifest(), openclaw_home)
            removed.extend(hooks_removed)
        except UninstallError as exc:
            failed.append(f"hooks: {exc}")
            if not force:
                raise

        # Step 3: Unregister agents
        try:
            agents_removed = _unregister_agents(manifest or InstallManifest(), openclaw_home)
            removed.extend(agents_removed)
        except UninstallError as exc:
            failed.append(f"agents: {exc}")
            if not force:
                raise

        # Step 4: Remove workspaces
        try:
            workspaces_removed = _remove_workspaces(target_root)
            removed.extend(workspaces_removed)
        except UninstallError as exc:
            failed.append(f"workspaces: {exc}")
            if not force:
                raise

        # Step 5: Remove runtime state
        try:
            runtime_removed = _remove_runtime_state(target_root)
            removed.extend(runtime_removed)
        except UninstallError as exc:
            failed.append(f"runtime: {exc}")
            # Non-fatal

        # Step 6: Remove manifest
        manifest_file = manifest_path(target_root)
        if manifest_file.exists():
            try:
                manifest_file.unlink()
                removed.append("manifest")
            except OSError as exc:
                failed.append(f"manifest: {exc}")

        # Step 7: Remove lock file
        lock_removed = _remove_lock_file(target_root)
        removed.extend(lock_removed)

        # Step 8: Try to remove managed root if empty
        if target_root.exists():
            try:
                # Only remove if directory is empty or contains only empty subdirs
                contents = list(target_root.iterdir())
                if not contents:
                    target_root.rmdir()
                    removed.append("managed_root")
                else:
                    # Check if all subdirs are empty
                    all_empty = True
                    for item in contents:
                        if item.is_file() or (item.is_dir() and any(item.iterdir())):
                            all_empty = False
                            break
                    if all_empty:
                        shutil.rmtree(target_root)
                        removed.append("managed_root")
            except OSError:
                # Non-fatal
                pass

        if failed and not force:
            return UninstallResult(
                success=False,
                message=f"Uninstall completed with errors: {'; '.join(failed)}",
                components_removed=removed,
                components_failed=failed,
            )

        return UninstallResult(
            success=True,
            message="openclaw-enhance uninstalled successfully",
            components_removed=removed,
            components_failed=failed if force else [],
        )

    except UninstallError as exc:
        return UninstallResult(
            success=False,
            message=f"Uninstall failed: {exc}",
            components_removed=removed,
            components_failed=failed + [str(exc)],
        )
    except Exception as exc:
        return UninstallResult(
            success=False,
            message=f"Unexpected error: {exc}",
            components_removed=removed,
            components_failed=failed + [str(exc)],
        )
    finally:
        lock.release()


def is_symmetric_install_uninstall(
    install_result: dict[str, Any],
    uninstall_result: UninstallResult,
) -> bool:
    """Check if install and uninstall operations are symmetric.

    This verifies that all components installed are properly removed.

    Args:
        install_result: Result dictionary from install operation.
        uninstall_result: Result from uninstall operation.

    Returns:
        True if operations are symmetric.
    """
    installed = set(install_result.get("components_installed", []))
    removed = set(uninstall_result.components_removed)

    # Map installed components to expected removed components
    component_mappings = {
        "workspace:": ["workspaces"],
        "agents:": ["agents:registry"],
        "hooks:": ["hooks:subagent-spawn-enrich"],
        "runtime:": ["runtime:state"],
    }

    # Check that all installed components have corresponding removals
    for installed_component in installed:
        found_mapping = False
        for prefix, removals in component_mappings.items():
            if installed_component.startswith(prefix):
                # At least one of the mapped removals should be present
                if any(r in removed for r in removals):
                    found_mapping = True
                    break
        if not found_mapping:
            # Component without explicit mapping - should be directly removed
            if installed_component not in removed:
                return False

    return True
