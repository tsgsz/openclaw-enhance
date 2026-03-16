from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from openclaw_enhance.constants import VERSION
from openclaw_enhance.install.manifest import ComponentInstall, InstallManifest

MONITOR_SERVICE_LABEL = "ai.openclaw.enhance.monitor"


class MonitorServiceError(RuntimeError):
    pass


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


def install_monitor_launchagent(
    manifest: InstallManifest,
    openclaw_home: Path,
    target_root: Path,
    user_home: Path | None = None,
) -> ComponentInstall | None:
    if sys.platform != "darwin":
        return None

    logs_dir = target_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    plist_path = monitor_launch_agent_path(user_home)
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "Label": MONITOR_SERVICE_LABEL,
        "ProgramArguments": [
            sys.executable,
            "-m",
            "openclaw_enhance.monitor_runtime",
            "--once",
            "--openclaw-home",
            str(openclaw_home),
            "--state-root",
            str(target_root),
        ],
        "RunAtLoad": True,
        "StartInterval": 60,
        "WorkingDirectory": "/",
        "StandardOutPath": str((logs_dir / "monitor.log").absolute()),
        "StandardErrorPath": str((logs_dir / "monitor.err.log").absolute()),
    }
    plist_path.write_bytes(plistlib.dumps(payload, sort_keys=True))

    domain = _launchctl_domain()
    try:
        _run_launchctl(["bootout", f"{domain}/{MONITOR_SERVICE_LABEL}"], check=False)
        _run_launchctl(["bootstrap", domain, str(plist_path)])
        _run_launchctl(["kickstart", "-k", f"{domain}/{MONITOR_SERVICE_LABEL}"])
    except Exception:
        _run_launchctl(["bootout", f"{domain}/{MONITOR_SERVICE_LABEL}"], check=False)
        if plist_path.exists():
            plist_path.unlink()
        raise

    return ComponentInstall(
        name="monitor:launchagent",
        version=VERSION,
        install_time=datetime.utcnow(),
        target_path=str(plist_path.absolute()),
        metadata={
            "label": MONITOR_SERVICE_LABEL,
            "domain": domain,
        },
    )


def uninstall_monitor_launchagent(
    manifest: InstallManifest | None,
    target_root: Path,
    user_home: Path | None = None,
) -> list[str]:
    if sys.platform != "darwin":
        return []

    component = manifest.get_component("monitor:launchagent") if manifest is not None else None
    plist_path = (
        Path(component.target_path)
        if component is not None and component.target_path
        else monitor_launch_agent_path(user_home)
    )
    label = (
        str(component.metadata.get("label"))
        if component is not None and component.metadata.get("label")
        else MONITOR_SERVICE_LABEL
    )
    domain = (
        str(component.metadata.get("domain"))
        if component is not None and component.metadata.get("domain")
        else _launchctl_domain()
    )

    _run_launchctl(["bootout", f"{domain}/{label}"], check=False)

    removed: list[str] = []
    if plist_path.exists():
        plist_path.unlink()
        removed.append("monitor:launchagent")

    logs_dir = target_root / "logs"
    for log_name in ("monitor.log", "monitor.err.log"):
        log_path = logs_dir / log_name
        if log_path.exists():
            log_path.unlink()
    if logs_dir.exists() and not any(logs_dir.iterdir()):
        logs_dir.rmdir()

    return removed
