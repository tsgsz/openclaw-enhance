from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import click

from openclaw_enhance import paths as openclaw_paths


def _resolve_config_path(openclaw_home: Path) -> Path:
    """Resolve OpenClaw config path via shared paths utility."""
    resolver = getattr(openclaw_paths, "resolve_openclaw_config_path", None)
    if callable(resolver):
        resolved = resolver(openclaw_home)
        return resolved if isinstance(resolved, Path) else Path(str(resolved))
    return openclaw_home / "config.json"


def _emit(payload: dict[str, object], *, err: bool = False) -> None:
    """Emit sorted JSON payload for deterministic probe output."""
    click.echo(json.dumps(payload, sort_keys=True), err=err)


def _fail(probe: str, reason: str, detail: str | None = None, exit_code: int = 2) -> None:
    """Emit machine-readable failure payload and exit non-zero."""
    payload: dict[str, object] = {"ok": False, "probe": probe, "reason": reason}
    if detail:
        payload["detail"] = detail
    _emit(payload, err=True)
    raise click.exceptions.Exit(exit_code)


def _require_openclaw_home(probe: str, openclaw_home: Path) -> Path:
    """Validate and return the OpenClaw home directory path."""
    home = openclaw_home.expanduser()
    if not home.exists() or not home.is_dir():
        _fail(probe, "missing_openclaw_home", str(home))
    return home


def _probe_env(openclaw_home: Path) -> dict[str, str]:
    """Build subprocess environment with explicit OpenClaw paths."""
    env = os.environ.copy()
    env["OPENCLAW_HOME"] = str(openclaw_home)
    env["OPENCLAW_CONFIG_PATH"] = str(_resolve_config_path(openclaw_home))
    return env


@click.group()
def cli() -> None:
    """Run strict live proof probes for canonical bundles."""
    pass


@cli.command("dev-symlink")
@click.option("--openclaw-home", type=click.Path(path_type=Path), required=True)
@click.option("--workspace", default="oe-orchestrator", show_default=True)
def dev_symlink(openclaw_home: Path, workspace: str) -> None:
    """Verify dev install workspace path is a symlink."""
    home = _require_openclaw_home("dev-symlink", openclaw_home)
    workspace_path = home / "openclaw-enhance" / "workspaces" / workspace

    if not workspace_path.exists():
        _fail("dev-symlink", "missing_workspace_path", str(workspace_path))
    if not workspace_path.is_symlink():
        _fail("dev-symlink", "workspace_not_symlink", str(workspace_path))

    target = workspace_path.resolve(strict=False)
    _emit(
        {
            "ok": True,
            "probe": "dev-symlink",
            "marker": "PROBE_DEV_SYMLINK_OK",
            "workspace": workspace,
            "path": str(workspace_path),
            "target": str(target),
        }
    )


@cli.command("routing-yield")
@click.option("--openclaw-home", type=click.Path(path_type=Path), required=True)
@click.option("--message", required=True, help="Message to send to openclaw chat")
def routing_yield(openclaw_home: Path, message: str) -> None:
    """Verify orchestrator routing via live openclaw chat session."""
    home = _require_openclaw_home("routing-yield", openclaw_home)
    env = _probe_env(home)

    openclaw_cmd = subprocess.run(
        ["which", "openclaw"],
        capture_output=True,
        text=True,
        env=env,
    )
    if openclaw_cmd.returncode != 0:
        _fail("routing-yield", "openclaw_cli_not_found", "openclaw command not in PATH")

    chat_result = subprocess.run(
        ["openclaw", "agent", "-m", message],
        capture_output=True,
        text=True,
        env=env,
    )
    if chat_result.returncode != 0:
        _fail("routing-yield", "openclaw_agent_failed", chat_result.stderr.strip())

    session_id = None
    for line in chat_result.stdout.splitlines():
        if "session" in line.lower() and "ses_" in line:
            parts = line.split()
            for part in parts:
                if part.startswith("ses_"):
                    session_id = part.strip(",:;")
                    break
            if session_id:
                break

    if not session_id:
        _fail("routing-yield", "missing_session_id", "No session ID found in agent output")

    assert session_id is not None
    sessions_result = subprocess.run(
        ["openclaw", "sessions", "--json"],
        capture_output=True,
        text=True,
        env=env,
    )
    if sessions_result.returncode != 0:
        _fail("routing-yield", "sessions_list_failed", sessions_result.stderr.strip())

    try:
        sessions_data = json.loads(sessions_result.stdout)
    except json.JSONDecodeError as exc:
        _fail("routing-yield", "sessions_json_invalid", str(exc))
        return

    session_info = None
    for session in sessions_data if isinstance(sessions_data, list) else []:
        if session.get("session_id") == session_id:
            session_info = session
            break

    if not session_info:
        _fail("routing-yield", "session_not_found", f"Session {session_id} not in sessions list")

    output = json.dumps(session_info)
    has_orchestrator = "oe-orchestrator" in output
    has_yield = "sessions_yield" in output

    if not has_orchestrator or not has_yield:
        missing = []
        if not has_orchestrator:
            missing.append("oe-orchestrator")
        if not has_yield:
            missing.append("sessions_yield")
        _fail("routing-yield", "missing_routing_evidence", f"Missing: {', '.join(missing)}")

    _emit(
        {
            "ok": True,
            "probe": "routing-yield",
            "marker": "PROBE_ROUTING_YIELD_OK",
            "session_id": session_id,
            "proof": "live_session",
        }
    )


@cli.command("recovery-worker")
@click.option("--openclaw-home", type=click.Path(path_type=Path), required=True)
@click.option("--message", required=True)
def recovery_worker(openclaw_home: Path, message: str) -> None:
    """Verify recovery worker registration and live dispatch with corrected method."""
    home = _require_openclaw_home("recovery-worker", openclaw_home)
    env = _probe_env(home)

    list_result = subprocess.run(
        ["openclaw", "agents", "list"],
        capture_output=True,
        text=True,
        env=env,
    )
    if list_result.returncode != 0:
        _fail("recovery-worker", "agents_list_failed", list_result.stderr.strip())
    if "oe-tool-recovery" not in list_result.stdout:
        _fail("recovery-worker", "missing_recovery_registration")

    chat_result = subprocess.run(
        ["openclaw", "agent", "-m", message],
        capture_output=True,
        text=True,
        env=env,
    )
    if chat_result.returncode != 0:
        _fail("recovery-worker", "agent_failed", chat_result.stderr.strip())

    session_id = None
    for line in chat_result.stdout.splitlines():
        if "ses_" in line:
            parts = line.split()
            for part in parts:
                if part.startswith("ses_"):
                    session_id = part.strip(",:;")
                    break
            if session_id:
                break

    if not session_id:
        _fail("recovery-worker", "missing_session_id", "No session ID in agent output")

    assert session_id is not None
    sessions_result = subprocess.run(
        ["openclaw", "sessions", "--json"],
        capture_output=True,
        text=True,
        env=env,
    )
    if sessions_result.returncode != 0:
        _fail("recovery-worker", "sessions_list_failed", sessions_result.stderr.strip())

    try:
        sessions_data = json.loads(sessions_result.stdout)
    except json.JSONDecodeError as exc:
        _fail("recovery-worker", "sessions_json_invalid", str(exc))
        return

    session_info = None
    for session in sessions_data if isinstance(sessions_data, list) else []:
        if session.get("session_id") == session_id:
            session_info = session
            break

    if not session_info:
        _fail("recovery-worker", "session_not_found", f"Session {session_id} not in sessions list")

    output = json.dumps(session_info)
    has_recovery = "oe-tool-recovery" in output
    has_corrected = "websearch_web_search_exa" in output

    if not has_recovery:
        _fail("recovery-worker", "no_recovery_dispatch", "oe-tool-recovery not in session")
    if not has_corrected:
        _fail("recovery-worker", "no_corrected_method", "websearch_web_search_exa not found")

    _emit(
        {
            "ok": True,
            "probe": "recovery-worker",
            "marker": "PROBE_RECOVERY_WORKER_OK",
            "session_id": session_id,
        }
    )


@cli.command("watchdog-reminder")
@click.option("--openclaw-home", type=click.Path(path_type=Path), required=True)
@click.option("--config-path", type=click.Path(path_type=Path), default=None)
@click.option("--session-id", default="strict-watchdog-probe")
def watchdog_reminder(openclaw_home: Path, config_path: Path | None, session_id: str) -> None:
    """Verify openclaw.json hook config and live reminder delivery."""
    from datetime import timedelta

    from openclaw_enhance.watchdog.detector import DetectionConfig, TimeoutDetector
    from openclaw_enhance.watchdog.state_sync import RuntimeStoreAdapter, StateSync

    home = _require_openclaw_home("watchdog-reminder", openclaw_home)
    resolved_config = Path(config_path) if config_path else _resolve_config_path(home)

    if not resolved_config.exists():
        _fail("watchdog-reminder", "missing_openclaw_config", str(resolved_config))

    try:
        config_data = json.loads(resolved_config.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail("watchdog-reminder", "invalid_openclaw_config_json", str(exc))
        return
    except OSError as exc:
        _fail("watchdog-reminder", "config_read_error", str(exc))
        return

    enhance_fragment = config_data.get("openclawEnhance")
    proof_type = (
        "config_hook_plus_live_reminder"
        if enhance_fragment
        else "workspace_contract_plus_live_reminder"
    )

    if not enhance_fragment:
        result = subprocess.run(
            ["python", "-m", "openclaw_enhance.cli", "render-workspace", "oe-watchdog"],
            capture_output=True,
            text=True,
            env=_probe_env(home),
        )
        if result.returncode != 0 or "oe-watchdog" not in result.stdout:
            _fail("watchdog-reminder", "missing_watchdog_workspace_and_config")
            return

    state_sync = StateSync(user_home=home)
    store_adapter = RuntimeStoreAdapter(state_sync)
    detector = TimeoutDetector(
        store=store_adapter,
        config=DetectionConfig(
            default_timeout=timedelta(seconds=0),
            grace_period=timedelta(seconds=0),
            min_session_duration=timedelta(seconds=0),
        ),
    )

    detector.start_monitoring(session_id)
    events = detector.check_timeouts()

    if not events or not any(e.session_id == session_id for e in events):
        _fail("watchdog-reminder", "no_timeout_event_generated")

    pending = state_sync.get_pending_suspected_events()
    if not any(e.session_id == session_id for e in pending):
        _fail("watchdog-reminder", "no_reminder_delivery_evidence")

    payload = {
        "ok": True,
        "probe": "watchdog-reminder",
        "marker": "PROBE_WATCHDOG_REMINDER_OK",
        "config_path": str(resolved_config),
        "session_id": session_id,
        "proof": proof_type,
    }
    if enhance_fragment:
        payload["config_fragment"] = json.dumps(enhance_fragment, sort_keys=True)

    _emit(payload)


def main() -> None:
    """Module entry point."""
    cli()


if __name__ == "__main__":
    main()
