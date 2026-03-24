from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from openclaw_enhance.constants import VERSION
from openclaw_enhance.install.manifest import ComponentInstall, InstallManifest

MONITOR_SERVICE_LABEL = "ai.openclaw.enhance.monitor"
SESSION_CLEANUP_SERVICE_LABEL = "ai.openclaw.session-cleanup"


class MonitorServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class ManagedLaunchAgentSpec:
    component_name: str
    label: str
    program_arguments: list[str]
    start_interval: int
    stdout_log_name: str
    stderr_log_name: str


def session_cleanup_launch_agent_path(user_home: Path | None = None) -> Path:
    base_home = user_home if user_home is not None else Path.home()
    return base_home / "Library" / "LaunchAgents" / f"{SESSION_CLEANUP_SERVICE_LABEL}.plist"


def monitor_launch_agent_path(user_home: Path | None = None) -> Path:
    base_home = user_home if user_home is not None else Path.home()
    return base_home / "Library" / "LaunchAgents" / f"{MONITOR_SERVICE_LABEL}.plist"


def _launchctl_domain() -> str:
    return f"gui/{os.getuid()}"


def _run_launchctl(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["launchctl", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise MonitorServiceError(
            f"launchctl {' '.join(args)} failed\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


def _launch_agent_specs(openclaw_home: Path, target_root: Path) -> list[ManagedLaunchAgentSpec]:
    return [
        ManagedLaunchAgentSpec(
            component_name="monitor:launchagent",
            label=MONITOR_SERVICE_LABEL,
            program_arguments=[
                sys.executable,
                "-m",
                "openclaw_enhance.monitor_runtime",
                "--once",
                "--openclaw-home",
                str(openclaw_home),
                "--state-root",
                str(target_root),
            ],
            start_interval=60,
            stdout_log_name="monitor.log",
            stderr_log_name="monitor.err.log",
        ),
        ManagedLaunchAgentSpec(
            component_name="session-cleanup:launchagent",
            label=SESSION_CLEANUP_SERVICE_LABEL,
            program_arguments=[
                sys.executable,
                "-m",
                "openclaw_enhance.cleanup",
                "--execute",
                "--openclaw-home",
                str(openclaw_home),
                "--json",
            ],
            start_interval=3600,
            stdout_log_name="session-cleanup.log",
            stderr_log_name="session-cleanup.err.log",
        ),
    ]


def _launch_agent_path_for_label(label: str, user_home: Path | None = None) -> Path:
    if label == MONITOR_SERVICE_LABEL:
        return monitor_launch_agent_path(user_home)
    if label == SESSION_CLEANUP_SERVICE_LABEL:
        return session_cleanup_launch_agent_path(user_home)
    raise MonitorServiceError(f"Unknown managed launch agent label: {label}")


def install_managed_launchagents(
    manifest: InstallManifest,
    openclaw_home: Path,
    target_root: Path,
    user_home: Path | None = None,
) -> list[ComponentInstall]:
    del manifest
    if sys.platform != "darwin":
        return []

    logs_dir = target_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    domain = _launchctl_domain()
    installed_components: list[ComponentInstall] = []
    installed_specs: list[ManagedLaunchAgentSpec] = []

    try:
        for spec in _launch_agent_specs(openclaw_home, target_root):
            plist_path = _launch_agent_path_for_label(spec.label, user_home)
            plist_path.parent.mkdir(parents=True, exist_ok=True)

            payload = {
                "Label": spec.label,
                "ProgramArguments": spec.program_arguments,
                "RunAtLoad": True,
                "StartInterval": spec.start_interval,
                "WorkingDirectory": "/",
                "StandardOutPath": str((logs_dir / spec.stdout_log_name).absolute()),
                "StandardErrorPath": str((logs_dir / spec.stderr_log_name).absolute()),
            }
            plist_path.write_bytes(plistlib.dumps(payload, sort_keys=True))

            _run_launchctl(["bootout", f"{domain}/{spec.label}"], check=False)
            _run_launchctl(["bootstrap", domain, str(plist_path)])
            _run_launchctl(["kickstart", "-k", f"{domain}/{spec.label}"])

            installed_specs.append(spec)
            installed_components.append(
                ComponentInstall(
                    name=spec.component_name,
                    version=VERSION,
                    install_time=datetime.utcnow(),
                    target_path=str(plist_path.absolute()),
                    metadata={
                        "label": spec.label,
                        "domain": domain,
                    },
                )
            )
    except Exception:
        for spec in reversed(installed_specs):
            plist_path = _launch_agent_path_for_label(spec.label, user_home)
            _run_launchctl(["bootout", f"{domain}/{spec.label}"], check=False)
            if plist_path.exists():
                plist_path.unlink()
        raise

    return installed_components


def uninstall_managed_launchagents(
    manifest: InstallManifest | None,
    target_root: Path,
    user_home: Path | None = None,
) -> list[str]:
    if sys.platform != "darwin":
        return []

    removed: list[str] = []
    component_names = ("monitor:launchagent", "session-cleanup:launchagent")
    for component_name in component_names:
        component = manifest.get_component(component_name) if manifest is not None else None
        label = (
            str(component.metadata.get("label"))
            if component is not None and component.metadata.get("label")
            else (
                MONITOR_SERVICE_LABEL
                if component_name == "monitor:launchagent"
                else SESSION_CLEANUP_SERVICE_LABEL
            )
        )
        plist_path = (
            Path(component.target_path)
            if component is not None and component.target_path
            else _launch_agent_path_for_label(label, user_home)
        )
        domain = (
            str(component.metadata.get("domain"))
            if component is not None and component.metadata.get("domain")
            else _launchctl_domain()
        )

        _run_launchctl(["bootout", f"{domain}/{label}"], check=False)

        if plist_path.exists():
            plist_path.unlink()
            removed.append(component_name)

    logs_dir = target_root / "logs"
    for log_name in (
        "monitor.log",
        "monitor.err.log",
        "session-cleanup.log",
        "session-cleanup.err.log",
    ):
        log_path = logs_dir / log_name
        if log_path.exists():
            log_path.unlink()
    if logs_dir.exists() and not any(logs_dir.iterdir()):
        logs_dir.rmdir()

    return removed
