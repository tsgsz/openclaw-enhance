"""Uninstallation logic for openclaw-enhance.

Handles the complete uninstall flow:
1. Preflight checks
2. Acquire lock
3. Remove hooks
4. Unregister agents
5. Remove synced main skills
6. Remove workspaces
7. Clean up namespace
8. Remove manifest

Supports rollback to restore on failure.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openclaw_enhance.install.lock import InstallLock, InstallLockError
from openclaw_enhance.install.main_tool_gate import remove_main_tool_gate
from openclaw_enhance.install.manifest import (
    InstallManifest,
    load_manifest,
    manifest_path,
)
from openclaw_enhance.paths import (
    managed_root,
    resolve_openclaw_config_path,
)
from openclaw_enhance.runtime.ownership import (
    OWNED_AGENT_SPECS,
    OWNED_EXTENSION_ID,
    OWNED_HOOK_ENTRY_IDS,
    OWNED_NAMESPACE,
)

from . import monitor_service

LEGACY_ENHANCE_WORKSPACE_DIRS: tuple[str, ...] = (
    "workspace-oe-orchestrator",
    "workspace-oe-searcher",
    "workspace-oe-syshelper",
    "workspace-oe-script_coder",
    "workspace-oe-watchdog",
    "workspace-oe-tool-recovery",
    "workspace-openclaw-enhance-orchestrator",
    "workspace-openclaw-enhance-searcher",
    "workspace-openclaw-enhance-syshelper",
    "workspace-openclaw-enhance-script_coder",
    "workspace-openclaw-enhance-watchdog",
    "workspace-openclaw-enhance-tool-recovery",
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

    config_path = resolve_openclaw_config_path(openclaw_home)

    if not config_path.exists():
        return removed

    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)

        if not isinstance(config, dict):
            return removed

        changed = False
        hook_component = manifest.get_component("hooks:subagent-spawn-enrich")
        hook_metadata = hook_component.metadata if hook_component is not None else {}
        previous_enabled_present = hook_metadata.get("previous_enabled_present")
        previous_enabled_value = hook_metadata.get("previous_enabled_value")
        managed_hook_dirs: set[Path] = set()
        for component in manifest.components:
            if component.name == "hooks:assets" and component.target_path:
                managed_hook_dirs.add(Path(component.target_path).resolve())
        if not managed_hook_dirs:
            managed_hook_dirs.add((managed_root() / "hooks").resolve())

        hooks_obj = config.get("hooks")
        if isinstance(hooks_obj, dict):
            internal_obj = hooks_obj.get("internal")
            if isinstance(internal_obj, dict):
                entries_obj = internal_obj.get("entries")
                if isinstance(entries_obj, dict):
                    filtered_entries_dict = {
                        key: value
                        for key, value in entries_obj.items()
                        if key not in OWNED_HOOK_ENTRY_IDS
                    }
                    if filtered_entries_dict != entries_obj:
                        internal_obj["entries"] = filtered_entries_dict
                        removed.append("hooks:subagent-spawn-enrich")
                        changed = True
                elif isinstance(entries_obj, list):
                    filtered_entries_list = [
                        value
                        for value in entries_obj
                        if not (isinstance(value, str) and value in OWNED_HOOK_ENTRY_IDS)
                    ]
                    if filtered_entries_list != entries_obj:
                        internal_obj["entries"] = filtered_entries_list
                        removed.append("hooks:subagent-spawn-enrich")
                        changed = True

                if previous_enabled_present is True:
                    if internal_obj.get("enabled") != previous_enabled_value:
                        internal_obj["enabled"] = previous_enabled_value
                        changed = True
                elif previous_enabled_present is False:
                    if "enabled" in internal_obj:
                        del internal_obj["enabled"]
                        changed = True
                elif list(internal_obj.keys()) == ["enabled"]:
                    del internal_obj["enabled"]
                    changed = True

                load_obj = internal_obj.get("load")
                if isinstance(load_obj, dict):
                    extra_dirs_obj = load_obj.get("extraDirs")
                    if isinstance(extra_dirs_obj, list):
                        filtered_dirs = [
                            v
                            for v in extra_dirs_obj
                            if not (isinstance(v, str) and Path(v).resolve() in managed_hook_dirs)
                        ]
                        if filtered_dirs != extra_dirs_obj:
                            load_obj["extraDirs"] = filtered_dirs
                            changed = True
                        if not load_obj["extraDirs"]:
                            del load_obj["extraDirs"]
                            changed = True

                if isinstance(internal_obj.get("load"), dict) and not internal_obj["load"]:
                    del internal_obj["load"]
                    changed = True
                if isinstance(internal_obj.get("entries"), dict) and not internal_obj["entries"]:
                    del internal_obj["entries"]
                    changed = True
                if isinstance(internal_obj.get("entries"), list) and not internal_obj["entries"]:
                    del internal_obj["entries"]
                    changed = True
                if not internal_obj:
                    del hooks_obj["internal"]
                    changed = True

            if not hooks_obj:
                del config["hooks"]
                changed = True

        if OWNED_NAMESPACE in config:
            del config[OWNED_NAMESPACE]
            changed = True

        if not changed:
            return removed

        backup_path = config_path.with_suffix(".json.bak")
        shutil.copy2(config_path, backup_path)

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

    config_path = resolve_openclaw_config_path(openclaw_home)

    if not config_path.exists():
        return removed

    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)

        if not isinstance(config, dict):
            return removed

        changed = False
        agents_obj = config.get("agents")
        if isinstance(agents_obj, dict):
            current_list = agents_obj.get("list")
            if isinstance(current_list, list):
                owned_ids = {agent_id for agent_id, _ in OWNED_AGENT_SPECS}
                filtered_list = [
                    entry
                    for entry in current_list
                    if not (
                        isinstance(entry, dict)
                        and isinstance(entry.get("id"), str)
                        and entry["id"] in owned_ids
                    )
                ]
                if filtered_list != current_list:
                    agents_obj["list"] = filtered_list
                    removed.append("agents:registry")
                    changed = True

                if isinstance(agents_obj.get("list"), list) and not agents_obj["list"]:
                    del agents_obj["list"]
                    changed = True

            if not agents_obj:
                del config["agents"]
                changed = True

        if OWNED_NAMESPACE in config:
            del config[OWNED_NAMESPACE]
            changed = True

        if not changed:
            return removed

        backup_path = config_path.with_suffix(".json.bak")
        shutil.copy2(config_path, backup_path)

        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, sort_keys=True)
            f.write("\n")

        return removed
    except (json.JSONDecodeError, OSError, KeyError) as exc:
        raise UninstallError(f"Failed to unregister agents: {exc}") from exc


def _uninstall_extension() -> list[str]:
    """Uninstall the oe-runtime plugin via ``openclaw plugins uninstall --force``."""
    removed: list[str] = []
    try:
        result = subprocess.run(
            ["openclaw", "plugins", "uninstall", "--force", OWNED_EXTENSION_ID],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 or "not found" in (result.stdout + result.stderr).lower():
            removed.append(f"extension:{OWNED_EXTENSION_ID}")
    except FileNotFoundError:
        pass  # openclaw CLI not available; skip
    return removed


def _remove_hook_assets(target_root: Path) -> list[str]:
    removed: list[str] = []
    hooks_dir = target_root / "hooks"

    if hooks_dir.exists() or hooks_dir.is_symlink():
        try:
            if hooks_dir.is_symlink():
                hooks_dir.unlink()
            else:
                shutil.rmtree(hooks_dir)
            removed.append("hooks:assets")
        except OSError as exc:
            raise UninstallError(f"Failed to remove hooks assets: {exc}") from exc

    return removed


def _remove_workspaces(target_root: Path) -> list[str]:
    """Remove synced workspace configurations."""
    removed: list[str] = []
    workspaces_dir = target_root / "workspaces"

    if workspaces_dir.exists() or workspaces_dir.is_symlink():
        try:
            if workspaces_dir.is_symlink():
                workspaces_dir.unlink()
            else:
                shutil.rmtree(workspaces_dir)
            removed.append("workspaces")
        except OSError as exc:
            raise UninstallError(f"Failed to remove workspaces: {exc}") from exc

    return removed


def _remove_legacy_enhance_workspaces(openclaw_home: Path) -> list[str]:
    removed: list[str] = []
    for dirname in LEGACY_ENHANCE_WORKSPACE_DIRS:
        legacy_dir = openclaw_home / dirname
        if not legacy_dir.exists() and not legacy_dir.is_symlink():
            continue
        try:
            if legacy_dir.is_symlink():
                legacy_dir.unlink()
            else:
                shutil.rmtree(legacy_dir)
            removed.append(f"legacy_workspace:{dirname}")
        except OSError as exc:
            raise UninstallError(f"Failed to remove legacy workspace {dirname}: {exc}") from exc

    return removed


def _remove_main_skills(manifest: InstallManifest | None) -> list[str]:
    removed: list[str] = []
    if manifest is None:
        return removed

    for component in manifest.components:
        if not component.name.startswith("main-skill:"):
            continue

        if not component.target_path:
            removed.append(component.name)
            continue

        skill_file = Path(component.target_path)
        skill_dir = skill_file.parent

        try:
            if skill_file.is_symlink():
                skill_file.unlink()
            elif skill_dir.exists():
                shutil.rmtree(skill_dir)
            removed.append(component.name)
        except OSError as exc:
            raise UninstallError(
                f"Failed to remove main skill component {component.name}: {exc}"
            ) from exc

        skills_dir = skill_dir.parent
        if skills_dir.exists():
            try:
                skills_dir.rmdir()
            except OSError:
                pass

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
    has_partial_monitor_install = sys.platform == "darwin" and (
        monitor_service.monitor_launch_agent_path(user_home).exists()
        or monitor_service.session_cleanup_launch_agent_path(user_home).exists()
    )
    if not manifest and not force and not has_partial_monitor_install:
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
        try:
            monitor_service_removed = monitor_service.uninstall_managed_launchagents(
                manifest=manifest,
                target_root=target_root,
                user_home=user_home,
            )
            removed.extend(monitor_service_removed)
        except Exception as exc:
            failed.append(f"monitor-service: {exc}")
            if not force:
                raise

        # Step 2a: Uninstall oe-runtime extension
        try:
            ext_removed = _uninstall_extension()
            removed.extend(ext_removed)
        except Exception as exc:
            failed.append(f"extension: {exc}")
            # Non-fatal — continue uninstall

        # Step 2b: Remove hooks
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

        # Step 4: Remove synced main skills
        try:
            main_skills_removed = _remove_main_skills(manifest)
            removed.extend(main_skills_removed)
        except UninstallError as exc:
            failed.append(f"main-skills: {exc}")
            if not force:
                raise

        # Step 4b: Remove main tool gate
        try:
            config_path = resolve_openclaw_config_path(openclaw_home)
            config = (
                json.loads(config_path.read_text(encoding="utf-8"))
                if config_path.exists()
                else None
            )
            gate_removed = remove_main_tool_gate(
                openclaw_home=openclaw_home,
                config=config,
                env=os.environ,
            )
            if gate_removed:
                removed.append("main-tool-gate")
        except Exception as exc:
            failed.append(f"main-tool-gate: {exc}")

        # Step 5: Remove workspaces
        try:
            workspaces_removed = _remove_workspaces(target_root)
            removed.extend(workspaces_removed)
        except UninstallError as exc:
            failed.append(f"workspaces: {exc}")
            if not force:
                raise

        try:
            legacy_workspaces_removed = _remove_legacy_enhance_workspaces(openclaw_home)
            removed.extend(legacy_workspaces_removed)
        except UninstallError as exc:
            failed.append(f"legacy-workspaces: {exc}")
            if not force:
                raise

        try:
            hook_assets_removed = _remove_hook_assets(target_root)
            removed.extend(hook_assets_removed)
        except UninstallError as exc:
            failed.append(f"hooks-assets: {exc}")
            if not force:
                raise

        try:
            runtime_removed = _remove_runtime_state(target_root)
            removed.extend(runtime_removed)
        except UninstallError as exc:
            failed.append(f"runtime: {exc}")
            # Non-fatal

        manifest_file = manifest_path(target_root)
        if manifest_file.exists():
            try:
                manifest_file.unlink()
                removed.append("manifest")
            except OSError as exc:
                failed.append(f"manifest: {exc}")

        lock_removed = _remove_lock_file(target_root)
        removed.extend(lock_removed)

        playbook_file = target_root / "PLAYBOOK.md"
        if playbook_file.exists():
            try:
                playbook_file.unlink()
                removed.append("playbook")
            except OSError as exc:
                failed.append(f"playbook: {exc}")

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
        "monitor:": ["monitor:launchagent"],
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
