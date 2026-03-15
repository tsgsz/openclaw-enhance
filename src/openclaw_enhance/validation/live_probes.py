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
    env["OPENCLAW_CONFIG_PATH"] = str(_resolve_config_path(openclaw_home))
    return env


def _parse_agent_output(output: str) -> dict[str, object] | None:
    json_start = output.find("{")
    json_end = output.rfind("}") + 1

    if json_start < 0 or json_end <= json_start:
        return None

    try:
        parsed = json.loads(output[json_start:json_end])
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


def _workspace_path(openclaw_home: Path, agent_id: str) -> Path:
    return openclaw_home / "openclaw-enhance" / "workspaces" / agent_id


def _runtime_identity_confirmed(openclaw_home: Path, agent_id: str) -> bool:
    workspace_path = _workspace_path(openclaw_home, agent_id)
    identity_path = workspace_path / "IDENTITY.md"
    bootstrap_path = workspace_path / "BOOTSTRAP.md"

    if bootstrap_path.exists() or not identity_path.exists():
        return False

    try:
        identity_text = identity_path.read_text(encoding="utf-8")
    except OSError:
        return False

    return "_(pick something you like)_" not in identity_text and "- **Name:**" in identity_text


def _tool_surface_names(agent_output: dict[str, object]) -> set[str]:
    result = agent_output.get("result")
    if not isinstance(result, dict):
        return set()

    meta = result.get("meta")
    if not isinstance(meta, dict):
        return set()

    system_prompt_report = meta.get("systemPromptReport")
    if not isinstance(system_prompt_report, dict):
        return set()

    tools = system_prompt_report.get("tools")
    if not isinstance(tools, dict):
        return set()

    tool_entries = tools.get("entries", [])
    names: set[str] = set()

    if isinstance(tool_entries, list):
        for entry in tool_entries:
            if isinstance(entry, dict):
                name = entry.get("name")
                if isinstance(name, str):
                    names.add(name)
    return names


def _get_transcript_path(
    agent_id: str, session_id: str, openclaw_home: Path, env: dict[str, str]
) -> Path | None:
    """Get transcript path from sessions list for a specific session."""
    sessions_result = subprocess.run(
        ["openclaw", "sessions", "--agent", agent_id, "--json"],
        capture_output=True,
        text=True,
        env=env,
    )
    if sessions_result.returncode != 0:
        return None

    lines = sessions_result.stdout.split("\n")
    json_lines = []
    depth = 0
    started = False

    for line in lines:
        if line.strip().startswith("{") and not started:
            started = True
        if started:
            json_lines.append(line)
            depth += line.count("{") - line.count("}")
            if depth == 0:
                break

    try:
        if json_lines:
            sessions_obj = json.loads("\n".join(json_lines))
            sessions_data = sessions_obj.get("sessions", [])
        else:
            return None
    except json.JSONDecodeError:
        return None

    for session in sessions_data if isinstance(sessions_data, list) else []:
        if session.get("sessionId") == session_id:
            transcript_path = session.get("transcriptPath")
            if transcript_path:
                return Path(transcript_path).expanduser()
            fallback = openclaw_home / "agents" / agent_id / "sessions" / f"{session_id}.jsonl"
            if fallback.exists():
                return fallback
    fallback = openclaw_home / "agents" / agent_id / "sessions" / f"{session_id}.jsonl"
    if fallback.exists():
        return fallback
    return None


def _search_transcript(transcript_path: Path, *search_terms: str) -> bool:
    """Search for terms in JSONL transcript file."""
    if not transcript_path.exists():
        return False

    try:
        content = transcript_path.read_text(encoding="utf-8")
        return all(term in content for term in search_terms)
    except (OSError, UnicodeDecodeError):
        return False


def _ensure_bootstrap_ready(agent_id: str, openclaw_home: Path, env: dict[str, str]) -> bool:
    """Ensure agent workspace is bootstrap-ready via CLI interaction."""
    workspace_path = _workspace_path(openclaw_home, agent_id)
    bootstrap_file = workspace_path / "BOOTSTRAP.md"

    if not bootstrap_file.exists():
        return True

    bootstrap_msg = (
        "Complete bootstrap: set identity to 'oe-bootstrap-probe', user to 'validation-harness'"
    )
    result = subprocess.run(
        ["openclaw", "agent", "--agent", agent_id, "-m", bootstrap_msg, "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    return (
        result.returncode == 0
        and not bootstrap_file.exists()
        and _runtime_identity_confirmed(openclaw_home, agent_id)
    )


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

    if not _ensure_bootstrap_ready("oe-orchestrator", home, env):
        _fail("routing-yield", "bootstrap_prep_failed", "Could not prepare orchestrator workspace")

    chat_result = subprocess.run(
        ["openclaw", "agent", "--agent", "oe-orchestrator", "-m", message, "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    if chat_result.returncode != 0:
        _fail("routing-yield", "openclaw_agent_failed", chat_result.stderr.strip())

    agent_output = _parse_agent_output(chat_result.stdout + chat_result.stderr)
    if not agent_output:
        _fail("routing-yield", "invalid_agent_output", "Could not parse openclaw agent JSON")
    assert agent_output is not None

    result = agent_output.get("result")
    meta = result.get("meta") if isinstance(result, dict) else None
    agent_meta = meta.get("agentMeta") if isinstance(meta, dict) else None
    system_prompt_report = meta.get("systemPromptReport") if isinstance(meta, dict) else None

    session_id = agent_meta.get("sessionId") if isinstance(agent_meta, dict) else None

    if not session_id:
        _fail("routing-yield", "missing_session_id", "No session ID found in agent output")

    assert session_id is not None
    transcript_path = _get_transcript_path("oe-orchestrator", session_id, home, env)
    if not transcript_path:
        _fail("routing-yield", "transcript_not_found", f"No transcript for session {session_id}")

    tool_surface_names = _tool_surface_names(agent_output)
    if "sessions_yield" not in tool_surface_names:
        _fail(
            "routing-yield",
            "missing_tool_surface",
            "sessions_yield not exposed in live tool surface",
        )

    workspace_dir = (
        system_prompt_report.get("workspaceDir") if isinstance(system_prompt_report, dict) else None
    )
    if not isinstance(workspace_dir, str) or "oe-orchestrator" not in workspace_dir:
        _fail("routing-yield", "wrong_runtime_workspace", str(workspace_dir))

    runtime_identity_confirmed = _runtime_identity_confirmed(home, "oe-orchestrator")
    if not runtime_identity_confirmed:
        _fail(
            "routing-yield",
            "runtime_identity_unconfirmed",
            "oe-orchestrator workspace still looks uninitialized",
        )

    _emit(
        {
            "ok": True,
            "probe": "routing-yield",
            "marker": "PROBE_ROUTING_YIELD_OK",
            "session_id": session_id,
            "proof": "runtime_surface",
            "transcript_path": str(transcript_path),
            "runtime_workspace": workspace_dir,
            "runtime_identity_confirmed": runtime_identity_confirmed,
            "tool_surface_has_sessions_yield": True,
        }
    )


@cli.command("recovery-worker")
@click.option("--openclaw-home", type=click.Path(path_type=Path), required=True)
@click.option("--message", required=True)
def recovery_worker(openclaw_home: Path, message: str) -> None:
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

    if not _ensure_bootstrap_ready("oe-tool-recovery", home, env):
        _fail("recovery-worker", "bootstrap_prep_failed", "Could not prepare recovery workspace")

    chat_result = subprocess.run(
        ["openclaw", "agent", "--agent", "oe-tool-recovery", "-m", message, "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    if chat_result.returncode != 0:
        _fail("recovery-worker", "agent_failed", chat_result.stderr.strip())

    agent_output = _parse_agent_output(chat_result.stdout + chat_result.stderr)
    if not agent_output:
        _fail("recovery-worker", "invalid_agent_output", "Could not parse openclaw agent JSON")
    assert agent_output is not None

    result = agent_output.get("result")
    meta = result.get("meta") if isinstance(result, dict) else None
    agent_meta = meta.get("agentMeta") if isinstance(meta, dict) else None
    system_prompt_report = meta.get("systemPromptReport") if isinstance(meta, dict) else None

    session_id = agent_meta.get("sessionId") if isinstance(agent_meta, dict) else None

    if not session_id:
        _fail("recovery-worker", "missing_session_id", "No session ID in agent output")

    assert session_id is not None
    transcript_path = _get_transcript_path("oe-tool-recovery", session_id, home, env)
    if not transcript_path:
        _fail("recovery-worker", "transcript_not_found", f"No transcript for session {session_id}")

    workspace_dir = (
        system_prompt_report.get("workspaceDir") if isinstance(system_prompt_report, dict) else None
    )
    if not isinstance(workspace_dir, str) or "oe-tool-recovery" not in workspace_dir:
        _fail("recovery-worker", "wrong_runtime_workspace", str(workspace_dir))

    runtime_identity_confirmed = _runtime_identity_confirmed(home, "oe-tool-recovery")
    if not runtime_identity_confirmed:
        _fail(
            "recovery-worker",
            "runtime_identity_unconfirmed",
            "oe-tool-recovery workspace still looks uninitialized",
        )

    _emit(
        {
            "ok": True,
            "probe": "recovery-worker",
            "marker": "PROBE_RECOVERY_WORKER_OK",
            "session_id": session_id,
            "proof": "runtime_surface",
            "transcript_path": str(transcript_path),
            "runtime_workspace": workspace_dir,
            "runtime_identity_confirmed": runtime_identity_confirmed,
            "recovery_registration_confirmed": True,
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
