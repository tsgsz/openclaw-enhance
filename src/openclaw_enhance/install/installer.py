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
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_enhance.constants import VERSION
from openclaw_enhance.install.lock import InstallLock, InstallLockError
from openclaw_enhance.install.main_skill_sync import sync_main_skills
from openclaw_enhance.install.main_tool_gate import inject_main_tool_gate
from openclaw_enhance.install.manifest import (
    ComponentInstall,
    InstallManifest,
    load_manifest,
    save_manifest,
)
from . import monitor_service
from openclaw_enhance.paths import (
    ensure_managed_directories,
    managed_root,
    resolve_main_workspace,
    resolve_openclaw_config_path,
)
from openclaw_enhance.runtime.ownership import (
    OWNED_AGENT_SPECS,
    OWNED_EXTENSION_ID,
    OWNED_HOOK_ENTRY_IDS,
    OWNED_NAMESPACE,
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


def _sync_hooks(target_root: Path, dev_mode: bool = False) -> list[ComponentInstall]:
    components: list[ComponentInstall] = []

    source_path = Path(__file__).resolve().parents[3] / "hooks"
    if not source_path.exists() or not source_path.is_dir():
        return components

    target_path = target_root / "hooks"
    if target_path.exists() or target_path.is_symlink():
        if target_path.is_symlink():
            target_path.unlink()
        else:
            shutil.rmtree(target_path)

    if dev_mode:
        target_path.symlink_to(source_path.absolute())
    else:
        shutil.copytree(source_path, target_path)

    components.append(
        ComponentInstall(
            name="hooks:assets",
            version=VERSION,
            install_time=datetime.utcnow(),
            source_path=str(source_path.absolute()),
            target_path=str(target_path.absolute()),
            is_symlink=dev_mode,
        )
    )
    return components


def _sync_playbook(target_root: Path) -> ComponentInstall | None:
    """Copy PLAYBOOK.md to managed root for AI/human reference."""
    source_path = Path(__file__).resolve().parents[3] / "PLAYBOOK.md"
    if not source_path.exists():
        return None

    target_path = target_root / "PLAYBOOK.md"
    shutil.copy2(source_path, target_path)

    return ComponentInstall(
        name="playbook",
        version=VERSION,
        install_time=datetime.utcnow(),
        source_path=str(source_path.absolute()),
        target_path=str(target_path.absolute()),
        is_symlink=False,
    )


def _write_openclaw_config(config_path: Path, config: dict[str, Any]) -> str:
    backup_path = config_path.with_name(f"{config_path.name}.bak")
    temp_path = config_path.with_name(f"{config_path.name}.tmp")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        shutil.copy2(config_path, backup_path)

    try:
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_path, config_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        if backup_path.exists():
            shutil.copy2(backup_path, config_path)
        raise

    return str(backup_path)


def _ensure_allow_agent_id(
    subagents_obj: dict[str, Any],
    agent_id: str,
) -> None:
    allow_agents_obj = subagents_obj.get("allowAgents")
    allow_agents: list[str] = []
    if isinstance(allow_agents_obj, list):
        allow_agents = [v for v in allow_agents_obj if isinstance(v, str)]

    if agent_id not in allow_agents:
        allow_agents.append(agent_id)

    subagents_obj["allowAgents"] = allow_agents


def _ensure_main_orchestrator_allowlist(agents_obj: dict[str, Any]) -> None:
    defaults_obj = agents_obj.get("defaults")
    if isinstance(defaults_obj, dict):
        defaults_subagents = defaults_obj.get("subagents")
        if isinstance(defaults_subagents, dict):
            defaults_subagents.pop("allowAgents", None)

    list_obj = agents_obj.get("list")
    if isinstance(list_obj, list):
        for entry in list_obj:
            if not isinstance(entry, dict):
                continue
            if entry.get("id") != "main":
                continue
            subagents_obj = entry.get("subagents")
            if not isinstance(subagents_obj, dict):
                subagents_obj = {}
                entry["subagents"] = subagents_obj
            _ensure_allow_agent_id(subagents_obj, "oe-orchestrator")
            break


def _ensure_orchestrator_worker_allowlist(agents_obj: dict[str, Any]) -> None:
    """Ensure oe-orchestrator can spawn all oe-* agents."""
    list_obj = agents_obj.get("list")
    if isinstance(list_obj, list):
        all_oe_agents = [
            entry.get("id")
            for entry in list_obj
            if isinstance(entry, dict)
            and isinstance(entry.get("id"), str)
            and entry.get("id", "").startswith("oe-")
        ]

        for entry in list_obj:
            if not isinstance(entry, dict):
                continue
            if entry.get("id") != "oe-orchestrator":
                continue
            subagents_obj = entry.get("subagents")
            if not isinstance(subagents_obj, dict):
                subagents_obj = {}
                entry["subagents"] = subagents_obj
            for agent_id in all_oe_agents:
                if isinstance(agent_id, str) and agent_id != "oe-orchestrator":
                    _ensure_allow_agent_id(subagents_obj, agent_id)
            break


def _register_agents_via_cli(
    target_root: Path,
) -> list[ComponentInstall]:
    """Register owned agents using ``openclaw agents add`` CLI.

    Workspaces must already be synced before calling this function.
    ``openclaw agents add`` will not overwrite existing files in the workspace.
    """
    existing_ids: set[str] = set()
    check = _run_openclaw_cli(["agents", "list", "--json"], check=False)
    if check.returncode == 0:
        try:
            stdout = check.stdout
            json_text = stdout.split("\n")[0] if stdout.startswith("[") else stdout
            for line in stdout.split("\n"):
                if line.strip().startswith("["):
                    json_text = line
                    break
            agents_data = json.loads(json_text)
            existing_ids = {a["id"] for a in agents_data if isinstance(a, dict) and "id" in a}
        except (json.JSONDecodeError, TypeError):
            pass

    components: list[ComponentInstall] = []
    for agent_id, workspace_name in OWNED_AGENT_SPECS:
        workspace_path = str((target_root / "workspaces" / workspace_name).absolute())
        source_workspace = str((WORKSPACES_DIR / workspace_name).absolute())

        if agent_id not in existing_ids:
            result = _run_openclaw_cli(
                [
                    "agents",
                    "add",
                    agent_id,
                    "--workspace",
                    workspace_path,
                    "--non-interactive",
                ],
                check=False,
            )
            if (
                result.returncode != 0
                and "already exists" not in result.stdout
                and "already exists" not in result.stderr
            ):
                raise InstallError(f"Failed to add agent {agent_id}: {result.stderr}")

        components.append(
            ComponentInstall(
                name=f"agent:{agent_id}",
                version=VERSION,
                install_time=datetime.utcnow(),
                source_path=source_workspace,
                target_path=workspace_path,
                is_symlink=False,
            )
        )

    return components


# Extension source directory (relative to this file: src/openclaw_enhance/install/ -> extensions/)
_EXTENSION_SOURCE_DIR = (
    Path(__file__).resolve().parents[3] / "extensions" / "openclaw-enhance-runtime"
)


def _verify_extension_in_config(openclaw_home: Path | None = None) -> bool:
    home = openclaw_home or Path.home() / ".openclaw"
    config_path = resolve_openclaw_config_path(home)
    config = _load_openclaw_config(config_path)
    plugins = config.get("plugins", {})
    allow_list = plugins.get("allow", [])
    entries = plugins.get("entries", {})
    return OWNED_EXTENSION_ID in allow_list and OWNED_EXTENSION_ID in entries


def _install_extension(openclaw_home: Path | None = None) -> ComponentInstall | None:
    if not _EXTENSION_SOURCE_DIR.exists():
        return None

    source_path = str(_EXTENSION_SOURCE_DIR.absolute())

    check = _run_openclaw_cli(["plugins", "list", "--json"], check=False)
    already_installed = False
    if check.returncode == 0:
        try:
            data = json.loads(check.stdout)
            already_installed = any(
                isinstance(p, dict) and p.get("id") == OWNED_EXTENSION_ID for p in data
            )
        except (json.JSONDecodeError, TypeError):
            pass

    if already_installed:
        _run_openclaw_cli(["plugins", "uninstall", "--force", OWNED_EXTENSION_ID], check=False)

    result = _run_openclaw_cli(
        ["plugins", "install", "--link", source_path],
        check=False,
    )
    if result.returncode != 0 and "already exists" not in (result.stdout + result.stderr):
        raise InstallError(f"Failed to install extension {OWNED_EXTENSION_ID}: {result.stderr}")

    if not _verify_extension_in_config(openclaw_home):
        raise InstallError(
            f"Extension {OWNED_EXTENSION_ID} was installed but not found in "
            f"openclaw.json plugins config. The CLI may have failed silently."
        )

    return ComponentInstall(
        name=f"extension:{OWNED_EXTENSION_ID}",
        version=VERSION,
        install_time=datetime.utcnow(),
        source_path=source_path,
        target_path=source_path,
        is_symlink=True,
    )


def _register_runtime_surfaces(
    manifest: InstallManifest,
    openclaw_home: Path,
    target_root: Path,
) -> list[ComponentInstall]:
    config_path = resolve_openclaw_config_path(openclaw_home)
    config = _load_openclaw_config(config_path)

    config.pop(OWNED_NAMESPACE, None)

    agents_obj = config.get("agents")
    if not isinstance(agents_obj, dict):
        agents_obj = {}
        config["agents"] = agents_obj

    _ensure_main_orchestrator_allowlist(agents_obj)
    _ensure_orchestrator_worker_allowlist(agents_obj)

    hooks_obj = config.get("hooks")
    if not isinstance(hooks_obj, dict):
        hooks_obj = {}
        config["hooks"] = hooks_obj

    internal_obj = hooks_obj.get("internal")
    if not isinstance(internal_obj, dict):
        internal_obj = {}
        hooks_obj["internal"] = internal_obj

    previous_enabled_present = "enabled" in internal_obj
    previous_enabled_value = internal_obj.get("enabled")

    entries_obj = internal_obj.get("entries")
    entry_values: dict[str, Any] = {}
    if isinstance(entries_obj, dict):
        for hook_id, hook_config in entries_obj.items():
            if isinstance(hook_id, str):
                entry_values[hook_id] = deepcopy(hook_config)
    elif isinstance(entries_obj, list):
        for hook_id in entries_obj:
            if isinstance(hook_id, str):
                entry_values[hook_id] = {"enabled": True}

    for hook_id in OWNED_HOOK_ENTRY_IDS:
        entry_values[hook_id] = {"enabled": True}
    internal_obj["entries"] = entry_values
    internal_obj["enabled"] = True

    load_obj = internal_obj.get("load")
    if not isinstance(load_obj, dict):
        load_obj = {}
        internal_obj["load"] = load_obj

    extra_dirs_obj = load_obj.get("extraDirs")
    extra_dirs: list[str] = []
    if isinstance(extra_dirs_obj, list):
        extra_dirs = [v for v in extra_dirs_obj if isinstance(v, str)]

    managed_hooks_dir = str((target_root / "hooks").absolute())
    if managed_hooks_dir not in extra_dirs:
        extra_dirs.append(managed_hooks_dir)
    load_obj["extraDirs"] = extra_dirs

    try:
        backup_path = _write_openclaw_config(config_path, config)
    except OSError as exc:
        raise InstallError(f"Failed to write OpenClaw config: {exc}") from exc

    manifest.add_rollback_point(
        description="Runtime registration",
        backup_paths={"config": backup_path},
    )

    return [
        ComponentInstall(
            name="agents:registry",
            version=VERSION,
            install_time=datetime.utcnow(),
            target_path=str(config_path.absolute()),
        ),
        ComponentInstall(
            name="hooks:subagent-spawn-enrich",
            version=VERSION,
            install_time=datetime.utcnow(),
            target_path=str(config_path.absolute()),
            metadata={
                "previous_enabled_present": previous_enabled_present,
                "previous_enabled_value": previous_enabled_value,
            },
        ),
    ]


AGENT_MODEL_OVERRIDES: dict[str, str] = {
    "oe-orchestrator": "litellm-local/gpt-5.4",
    "oe-script_coder": "litellm-local/gpt-5.3-codex",
    "oe-tool-recovery": "litellm-local/gpt-5.4",
    "oe-syshelper": "minimax/MiniMax-M2.7",
    "oe-searcher": "minimax/MiniMax-M2.5",
    "oe-watchdog": "minimax/MiniMax-M2.1",
}


def _configure_agent_models(
    manifest: InstallManifest,
    openclaw_home: Path,
    target_root: Path,
) -> list[ComponentInstall]:
    config_path = resolve_openclaw_config_path(openclaw_home)
    config = _load_openclaw_config(config_path)

    agents_obj = config.get("agents")
    if not isinstance(agents_obj, dict):
        agents_obj = {}
        config["agents"] = agents_obj

    list_obj = agents_obj.get("list")
    if not isinstance(list_obj, list):
        list_obj = []
        agents_obj["list"] = list_obj

    for agent_entry in list_obj:
        if not isinstance(agent_entry, dict):
            continue
        agent_id = agent_entry.get("id")
        if not agent_id or agent_id == "main":
            continue

        model_id = AGENT_MODEL_OVERRIDES.get(agent_id)
        if model_id:
            agent_entry["model"] = model_id

    try:
        backup_path = _write_openclaw_config(config_path, config)
    except OSError as exc:
        raise InstallError(f"Failed to write agent model config: {exc}") from exc

    manifest.add_rollback_point(
        description="Agent model configuration",
        backup_paths={"config": backup_path},
    )

    return [
        ComponentInstall(
            name="agents:model-config",
            version=VERSION,
            install_time=datetime.utcnow(),
            target_path=str(config_path.absolute()),
        ),
    ]


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
    launchagent_components: list[ComponentInstall] = []

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

        try:
            injected = inject_main_tool_gate(
                openclaw_home=openclaw_home,
                config=config,
                env=os.environ,
            )
            if injected:
                all_components.append(
                    ComponentInstall(
                        name="main-tool-gate",
                        version=VERSION,
                        install_time=datetime.utcnow(),
                        source_path="openclaw_enhance.install.main_tool_gate",
                        target_path=str(
                            resolve_main_workspace(openclaw_home, config=config, env=os.environ)
                            / "AGENTS.md"
                        ),
                        is_symlink=False,
                    )
                )
        except Exception as exc:
            errors.append(f"Main tool gate injection failed: {exc}")

        try:
            hook_asset_components = _sync_hooks(target_root, dev_mode=dev_mode)
            all_components.extend(hook_asset_components)
        except Exception as exc:
            errors.append(f"Hook asset sync failed: {exc}")
            raise InstallError(f"Hook asset sync failed: {exc}") from exc

        try:
            agent_components = _register_agents_via_cli(target_root)
            all_components.extend(agent_components)
        except Exception as exc:
            errors.append(f"Agent CLI registration failed: {exc}")
            raise InstallError(f"Agent CLI registration failed: {exc}") from exc

        try:
            runtime_registration_components = _register_runtime_surfaces(
                manifest,
                openclaw_home,
                target_root,
            )
            all_components.extend(runtime_registration_components)
        except InstallError:
            raise
        except Exception as exc:
            errors.append(f"Runtime registration failed: {exc}")
            raise InstallError(f"Runtime registration failed: {exc}") from exc

        try:
            model_config_components = _configure_agent_models(
                manifest,
                openclaw_home,
                target_root,
            )
            all_components.extend(model_config_components)
        except Exception as exc:
            errors.append(f"Agent model configuration failed: {exc}")

        # Extension install MUST be after all _write_openclaw_config calls.
        # openclaw plugins install --link writes to openclaw.json directly;
        # if _configure_agent_models (or any other function that does
        # load→modify→write on openclaw.json) runs AFTER, it will overwrite
        # the plugins.allow/entries that the CLI just added.
        try:
            ext_component = _install_extension(openclaw_home=openclaw_home)
            if ext_component is not None:
                all_components.append(ext_component)
        except Exception as exc:
            errors.append(f"Extension install failed: {exc}")
            raise InstallError(f"Extension install failed: {exc}") from exc

        # Step 7: Initialize runtime state
        try:
            runtime_component = _install_runtime_state(manifest, target_root)
            all_components.append(runtime_component)
        except Exception as exc:
            errors.append(f"Runtime state initialization failed: {exc}")

        try:
            playbook_component = _sync_playbook(target_root)
            if playbook_component is not None:
                all_components.append(playbook_component)
        except Exception as exc:
            errors.append(f"Playbook sync failed: {exc}")

        try:
            launchagent_components = monitor_service.install_managed_launchagents(
                manifest=manifest,
                openclaw_home=openclaw_home,
                target_root=target_root,
                user_home=user_home,
            )
            all_components.extend(launchagent_components)
        except Exception as exc:
            errors.append(f"Monitor service installation failed: {exc}")
            raise InstallError(f"Monitor service installation failed: {exc}") from exc

        # Update manifest with all components
        for component in all_components:
            manifest.add_component(component)

        # Collect backup paths
        for rp in manifest.rollback_points:
            backup_paths.update(rp.get("backup_paths", {}))

        # Save manifest
        try:
            save_manifest(manifest, target_root)
        except Exception:
            if launchagent_components:
                try:
                    monitor_service.uninstall_managed_launchagents(
                        manifest=None,
                        target_root=target_root,
                        user_home=user_home,
                    )
                except Exception:
                    pass
            raise

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

    status: dict[str, Any] = {
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
