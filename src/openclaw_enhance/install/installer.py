"""Main installation logic for openclaw-enhance.

Handles the complete install flow:
1. Preflight checks
2. Acquire lock
3. Create namespace (~/.openclaw/openclaw-enhance/)
4. Sync workspaces
5. Register agents
6. Enable hooks
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_enhance.constants import VERSION
from openclaw_enhance.install.lock import InstallLock, InstallLockError
from openclaw_enhance.install.main_skill_sync import sync_main_skills
from openclaw_enhance.install.manifest import (
    ComponentInstall,
    InstallManifest,
    load_manifest,
    save_manifest,
)
from openclaw_enhance.paths import (
    ensure_managed_directories,
    managed_root,
    resolve_openclaw_config_path,
)
from openclaw_enhance.runtime.config_patch import (
    ConfigPatchError,
    apply_owned_config_patch,
)
from openclaw_enhance.runtime.support_matrix import SupportError, validate_environment
from openclaw_enhance.workspaces import WORKSPACES_DIR, list_workspaces


class InstallError(RuntimeError):
    """Raised when installation fails."""

    pass


@dataclass
class InstallResult:
    """Result of an installation operation."""

    success: bool
    message: str
    components_installed: list[str] = field(default_factory=list)
    backup_paths: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class PreflightResult:
    """Result of preflight checks."""

    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _run_openclaw_cli(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run an OpenClaw CLI command."""
    cmd = ["openclaw"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            raise InstallError(
                f"OpenClaw CLI command failed: {' '.join(args)}\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        return result
    except FileNotFoundError as exc:
        raise InstallError("OpenClaw CLI not found. Ensure 'openclaw' is in PATH.") from exc


def _load_openclaw_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}

    try:
        content = config_path.read_text(encoding="utf-8")
    except OSError:
        return {}

    if not content.strip():
        return {}

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def preflight_checks(
    openclaw_home: Path,
    user_home: Path | None = None,
    dev_mode: bool = False,
) -> PreflightResult:
    """Run preflight checks before installation.

    Args:
        openclaw_home: Path to OpenClaw home directory.
        user_home: Optional override for user home directory.

    Returns:
        PreflightResult with pass/fail status and any errors/warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check OpenClaw environment
    try:
        validate_environment(openclaw_home)
    except SupportError as exc:
        errors.append(f"Environment validation failed: {exc}")
        return PreflightResult(passed=False, errors=errors, warnings=warnings)

    # Check dev mode compatibility (Windows not supported)
    if dev_mode and sys.platform == "win32":
        errors.append(
            "Development mode (--dev) is not supported on Windows. "
            "Use macOS or Linux for development installations."
        )
        return PreflightResult(passed=False, errors=errors, warnings=warnings)

    # Check if OpenClaw CLI is available
    try:
        result = subprocess.run(
            ["openclaw", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            warnings.append("OpenClaw CLI version check returned non-zero")
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        warnings.append(f"OpenClaw CLI not available: {exc}")

    # Check write permissions to managed root
    target_root = managed_root(user_home)
    try:
        target_root.mkdir(parents=True, exist_ok=True)
        test_file = target_root / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
    except OSError as exc:
        errors.append(f"Cannot write to managed root {target_root}: {exc}")

    # Check if already installed
    if target_root.exists():
        existing_manifest = load_manifest(target_root)
        if existing_manifest:
            warnings.append(
                f"openclaw-enhance v{existing_manifest.version} already installed. "
                "Will upgrade in place."
            )

    passed = len(errors) == 0
    return PreflightResult(passed=passed, errors=errors, warnings=warnings)


def _sync_workspaces(
    manifest: InstallManifest,
    target_root: Path,
    dev_mode: bool = False,
) -> list[ComponentInstall]:
    """Sync workspace configurations to managed directory.

    Copies or symlinks workspace definitions from the package to the managed directory.
    """
    components: list[ComponentInstall] = []

    if not WORKSPACES_DIR.exists():
        return components

    workspaces_target = target_root / "workspaces"
    workspaces_target.mkdir(parents=True, exist_ok=True)

    for workspace_name in list_workspaces():
        source_path = WORKSPACES_DIR / workspace_name
        target_path = workspaces_target / workspace_name

        if target_path.exists() or target_path.is_symlink():
            if target_path.is_symlink():
                target_path.unlink()
            else:
                shutil.rmtree(target_path)

        if dev_mode:
            # Development mode: create symlink
            target_path.symlink_to(source_path.absolute())
        else:
            # Production mode: copy files
            shutil.copytree(source_path, target_path)

        component = ComponentInstall(
            name=f"workspace:{workspace_name}",
            version=VERSION,
            install_time=datetime.utcnow(),
            source_path=str(source_path.absolute()),
            target_path=str(target_path.absolute()),
            is_symlink=dev_mode,
        )
        components.append(component)

    return components


def _register_agents(
    manifest: InstallManifest,
    openclaw_home: Path,
    target_root: Path,
) -> list[ComponentInstall]:
    """Register agents with OpenClaw configuration.

    Uses JSON read-modify-write with backup for config changes.
    """
    components: list[ComponentInstall] = []
    config_path = resolve_openclaw_config_path(openclaw_home)

    # Define the agents configuration patch
    # NOTE: Registry descriptions are non-authoritative.
    # Actual routing metadata (capabilities, constraints) is read from
    # each worker's AGENTS.md frontmatter at runtime.
    agents_patch = {
        "openclawEnhance": {
            "agents": {
                "enabled": True,
                "registry": {
                    "oe-orchestrator": {
                        "workspace": "oe-orchestrator",
                        "description": "Orchestrator agent for task planning and dispatch",
                        "version": VERSION,
                    },
                    "oe-searcher": {
                        "workspace": "oe-searcher",
                        "description": "Search and research agent",
                        "version": VERSION,
                    },
                    "oe-syshelper": {
                        "workspace": "oe-syshelper",
                        "description": "System helper for grep and file operations",
                        "version": VERSION,
                    },
                    "oe-script-coder": {
                        "workspace": "oe-script-coder",
                        "description": "Script coding and testing agent",
                        "version": VERSION,
                    },
                    "oe-watchdog": {
                        "workspace": "oe-watchdog",
                        "description": "Session monitoring and timeout handling",
                        "version": VERSION,
                    },
                    "oe-tool-recovery": {
                        "workspace": "oe-tool-recovery",
                        "description": "Tool failure recovery and retry agent",
                        "version": VERSION,
                    },
                },
            },
        },
    }

    try:
        result = apply_owned_config_patch(
            config_path,
            agents_patch,
            fail_on_write=False,
        )

        component = ComponentInstall(
            name="agents:registry",
            version=VERSION,
            install_time=datetime.utcnow(),
            target_path=str(config_path.absolute()),
        )
        components.append(component)

        # Track backup for rollback
        manifest.add_rollback_point(
            description="Agent registration",
            backup_paths={"config": result.backup_path},
        )
    except ConfigPatchError as exc:
        raise InstallError(f"Failed to register agents: {exc}") from exc

    return components


def _enable_hooks(
    manifest: InstallManifest,
    openclaw_home: Path,
    target_root: Path,
) -> list[ComponentInstall]:
    """Enable hooks for OpenClaw events.

    Uses JSON read-modify-write with backup for config changes.
    """
    components: list[ComponentInstall] = []
    config_path = resolve_openclaw_config_path(openclaw_home)

    # Define the hooks configuration patch
    hooks_patch = {
        "openclawEnhance": {
            "hooks": {
                "enabled": True,
                "subscribers": [
                    {
                        "event": "subagent_spawning",
                        "handler": "oe-subagent-spawn-enrich",
                        "priority": 100,
                    },
                ],
            },
        },
    }

    try:
        result = apply_owned_config_patch(
            config_path,
            hooks_patch,
            fail_on_write=False,
        )

        component = ComponentInstall(
            name="hooks:subagent-spawn-enrich",
            version=VERSION,
            install_time=datetime.utcnow(),
            target_path=str(config_path.absolute()),
        )
        components.append(component)

        # Track backup for rollback
        manifest.add_rollback_point(
            description="Hook enablement",
            backup_paths={"config": result.backup_path},
        )
    except ConfigPatchError as exc:
        raise InstallError(f"Failed to enable hooks: {exc}") from exc

    return components


def _install_runtime_state(
    manifest: InstallManifest,
    target_root: Path,
) -> ComponentInstall:
    """Initialize runtime state file."""
    from openclaw_enhance.runtime.schema import RuntimeState
    from openclaw_enhance.runtime.store import save_runtime_state

    state = RuntimeState(
        doctor_last_ok=True,
    )
    state_path = save_runtime_state(state, target_root.parent.parent)

    return ComponentInstall(
        name="runtime:state",
        version=VERSION,
        install_time=datetime.utcnow(),
        target_path=str(state_path.absolute()),
    )


def install(
    openclaw_home: Path,
    user_home: Path | None = None,
    force: bool = False,
    dev_mode: bool = False,
) -> InstallResult:
    """Install openclaw-enhance.

    Args:
        openclaw_home: Path to OpenClaw home directory.
        user_home: Optional override for user home directory.
        force: If True, reinstall even if already installed.
        dev_mode: If True, use symlinks instead of copying files.

    Returns:
        InstallResult with success status and details.
    """
    target_root = managed_root(user_home)

    # Step 1: Preflight checks
    preflight = preflight_checks(openclaw_home, user_home, dev_mode=dev_mode)
    if not preflight.passed:
        return InstallResult(
            success=False,
            message="Preflight checks failed",
            errors=preflight.errors,
        )

    # Step 2: Acquire lock
    try:
        lock = InstallLock(target_root)
        if not lock.acquire(operation="install", blocking=True):
            return InstallResult(
                success=False,
                message="Could not acquire install lock",
            )
    except InstallLockError as exc:
        return InstallResult(
            success=False,
            message=f"Lock acquisition failed: {exc}",
        )

    all_components: list[ComponentInstall] = []
    backup_paths: dict[str, str] = {}
    errors: list[str] = []

    try:
        # Step 3: Create namespace
        ensure_managed_directories(user_home)

        # Load or create manifest
        manifest = load_manifest(target_root) or InstallManifest()
        manifest.openclaw_home = str(openclaw_home.absolute())

        # Step 4: Sync workspaces
        try:
            workspace_components = _sync_workspaces(manifest, target_root, dev_mode=dev_mode)
            all_components.extend(workspace_components)
        except Exception as exc:
            errors.append(f"Workspace sync failed: {exc}")
            raise InstallError(f"Workspace sync failed: {exc}") from exc

        try:
            config_path = resolve_openclaw_config_path(openclaw_home)
            config = _load_openclaw_config(config_path)
            main_skill_components = sync_main_skills(
                openclaw_home=openclaw_home,
                config=config,
                env=os.environ,
                dev_mode=dev_mode,
            )
            all_components.extend(main_skill_components)
        except Exception as exc:
            errors.append(f"Main skill sync failed: {exc}")
            raise InstallError(f"Main skill sync failed: {exc}") from exc

        # Step 5: Register agents
        try:
            agent_components = _register_agents(manifest, openclaw_home, target_root)
            all_components.extend(agent_components)
        except InstallError:
            raise
        except Exception as exc:
            errors.append(f"Agent registration failed: {exc}")
            raise InstallError(f"Agent registration failed: {exc}") from exc

        # Step 6: Enable hooks
        try:
            hook_components = _enable_hooks(manifest, openclaw_home, target_root)
            all_components.extend(hook_components)
        except InstallError:
            raise
        except Exception as exc:
            errors.append(f"Hook enablement failed: {exc}")
            raise InstallError(f"Hook enablement failed: {exc}") from exc

        # Step 7: Initialize runtime state
        try:
            runtime_component = _install_runtime_state(manifest, target_root)
            all_components.append(runtime_component)
        except Exception as exc:
            errors.append(f"Runtime state initialization failed: {exc}")
            # Non-fatal - continue

        # Update manifest with all components
        for component in all_components:
            manifest.add_component(component)

        # Collect backup paths
        for rp in manifest.rollback_points:
            backup_paths.update(rp.get("backup_paths", {}))

        # Save manifest
        save_manifest(manifest, target_root)

        return InstallResult(
            success=True,
            message=f"openclaw-enhance v{VERSION} installed successfully",
            components_installed=[c.name for c in all_components],
            backup_paths=backup_paths,
        )

    except InstallError:
        # Don't suppress InstallError - let it propagate with details
        return InstallResult(
            success=False,
            message="Installation failed",
            components_installed=[c.name for c in all_components],
            backup_paths=backup_paths,
            errors=errors,
        )
    except Exception as exc:
        return InstallResult(
            success=False,
            message=f"Unexpected error: {exc}",
            components_installed=[c.name for c in all_components],
            backup_paths=backup_paths,
            errors=errors + [str(exc)],
        )
    finally:
        lock.release()


def get_install_status(
    openclaw_home: Path | None = None,
    user_home: Path | None = None,
) -> dict[str, Any]:
    """Get current installation status.

    Args:
        openclaw_home: Optional path to OpenClaw home directory.
        user_home: Optional override for user home directory.

    Returns:
        Dictionary with installation status information.
    """
    from openclaw_enhance.install.lock import get_lock_info, is_locked

    target_root = managed_root(user_home)

    status = {
        "installed": False,
        "version": None,
        "install_path": str(target_root),
        "components": [],
        "locked": False,
        "lock_info": None,
    }

    manifest = load_manifest(target_root)
    if manifest:
        status["installed"] = True
        status["version"] = manifest.version
        status["install_time"] = manifest.install_time.isoformat()
        status["components"] = [c.name for c in manifest.components]

    if is_locked(target_root):
        status["locked"] = True
        lock_info = get_lock_info(target_root)
        if lock_info:
            status["lock_info"] = {
                "pid": lock_info.pid,
                "operation": lock_info.operation,
                "created_at": lock_info.created_at.isoformat(),
            }

    return status
