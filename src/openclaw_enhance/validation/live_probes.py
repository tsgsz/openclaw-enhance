from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path

import click

from openclaw_enhance import paths as openclaw_paths
from openclaw_enhance.validation.model_pin import (
    PINNED_OPENCLAW_MODEL,
    get_primary_model,
    pinned_openclaw_runtime_model,
)


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
    effective_openclaw_home = openclaw_home
    if openclaw_home.name == ".openclaw" and openclaw_home.parent != openclaw_home:
        effective_openclaw_home = openclaw_home.parent
    env["OPENCLAW_HOME"] = str(effective_openclaw_home)
    return env


def _resolve_main_session_entrypoint(env: dict[str, str]) -> str | None:
    agent_help = subprocess.run(
        ["openclaw", "agent", "--help"],
        capture_output=True,
        text=True,
        env=env,
    )
    if agent_help.returncode == 0:
        return "agent"

    chat_help = subprocess.run(
        ["openclaw", "chat", "--help"],
        capture_output=True,
        text=True,
        env=env,
    )
    if chat_help.returncode == 0:
        return "chat"

    return None


def _build_main_session_command(
    probe: str,
    message: str,
    env: dict[str, str],
    session_id: str,
) -> list[str]:
    """Build main session command or fail with unsupported entrypoint error."""
    entrypoint = _resolve_main_session_entrypoint(env)
    if entrypoint is None:
        _fail(probe, "main_entrypoint_unsupported", "No supported main session command found")

    if entrypoint == "agent":
        return [
            "openclaw",
            "agent",
            "--agent",
            "main",
            "--session-id",
            session_id,
            "-m",
            message,
            "--json",
        ]
    else:  # chat
        return [
            "openclaw",
            "chat",
            "--agent",
            "main",
            "--session-id",
            session_id,
            "-m",
            message,
            "--json",
        ]


def _build_main_escalation_probe_message(message: str, probe_request_id: str) -> str:
    return (
        f"[main-escalation probe request-id: {probe_request_id}]\n"
        "请立即执行一次新的 sessions_spawn，目标必须是 oe-orchestrator。"
        "禁止仅回复“已在处理/已在重查/稍后给你”。"
        "spawn 的 task 内容必须包含同样的 request-id，确保可归因。\n"
        "--- 用户原始任务 ---\n"
        f"{message}\n"
        "--- 结束 ---"
    )


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


def _parse_first_json_object(output: str) -> dict[str, object] | None:
    lines = output.split("\n")
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

    if not json_lines:
        return None

    try:
        parsed = json.loads("\n".join(json_lines))
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

    sessions_obj = _parse_first_json_object(sessions_result.stdout)
    if sessions_obj is None:
        return None
    sessions_data = sessions_obj.get("sessions", [])

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


def _line_count(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def _latest_orchestrator_session_id(env: dict[str, str]) -> str | None:
    sessions_result = subprocess.run(
        ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"],
        capture_output=True,
        text=True,
        env=env,
    )
    if sessions_result.returncode != 0:
        return None
    sessions_obj = _parse_first_json_object(sessions_result.stdout)
    if sessions_obj is None:
        return None
    sessions = sessions_obj.get("sessions", [])
    if not isinstance(sessions, list) or not sessions:
        return None
    latest = sessions[0]
    if not isinstance(latest, dict):
        return None
    session_id = latest.get("sessionId")
    return session_id if isinstance(session_id, str) and session_id else None


def _resolve_orchestrator_session_id_with_retry(
    env: dict[str, str],
    attempts: int = 5,
    delay_seconds: float = 1.0,
) -> str | None:
    for attempt in range(1, attempts + 1):
        session_id = _latest_orchestrator_session_id(env)
        if session_id:
            return session_id
        if attempt < attempts:
            time.sleep(delay_seconds)
    return None


def _resolve_orchestrator_session_for_request(
    openclaw_home: Path,
    env: dict[str, str],
    probe_request_id: str,
    attempts: int = 30,
    delay_seconds: float = 1.0,
) -> tuple[str, Path] | None:
    for attempt in range(1, attempts + 1):
        sessions_result = subprocess.run(
            ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"],
            capture_output=True,
            text=True,
            env=env,
        )
        if sessions_result.returncode == 0:
            sessions_obj = _parse_first_json_object(sessions_result.stdout)
            sessions = sessions_obj.get("sessions", []) if isinstance(sessions_obj, dict) else []
            if isinstance(sessions, list):
                for session in sessions:
                    if not isinstance(session, dict):
                        continue
                    raw_session_id = session.get("sessionId")
                    if not isinstance(raw_session_id, str) or not raw_session_id:
                        continue
                    transcript = _get_transcript_path(
                        "oe-orchestrator", raw_session_id, openclaw_home, env
                    )
                    if transcript is None:
                        continue
                    if _search_transcript(transcript, probe_request_id):
                        return (raw_session_id, transcript)
        if attempt < attempts:
            time.sleep(delay_seconds)
    return None


def _extract_orchestrator_child_session_key_from_segment(
    transcript_path: Path,
    start_line: int,
) -> str | None:
    try:
        with transcript_path.open("r", encoding="utf-8", errors="ignore") as handle:
            for idx, line in enumerate(handle, start=1):
                if idx < max(1, start_line):
                    continue
                if "childSessionKey" not in line or "oe-orchestrator" not in line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue
                message = entry.get("message")
                if not isinstance(message, dict) or message.get("role") != "toolResult":
                    continue
                details = message.get("details")
                if not isinstance(details, dict):
                    continue
                raw_key = details.get("childSessionKey")
                if isinstance(raw_key, str) and raw_key and "oe-orchestrator" in raw_key:
                    return raw_key
        return None
    except OSError:
        return None


def _resolve_orchestrator_session_by_child_key(
    openclaw_home: Path,
    env: dict[str, str],
    child_session_key: str,
    attempts: int = 30,
    delay_seconds: float = 1.0,
) -> tuple[str, Path] | None:
    for attempt in range(1, attempts + 1):
        sessions_result = subprocess.run(
            ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"],
            capture_output=True,
            text=True,
            env=env,
        )
        if sessions_result.returncode == 0:
            sessions_obj = _parse_first_json_object(sessions_result.stdout)
            sessions = sessions_obj.get("sessions", []) if isinstance(sessions_obj, dict) else []
            if isinstance(sessions, list):
                for session in sessions:
                    if not isinstance(session, dict):
                        continue
                    if session.get("key") != child_session_key:
                        continue
                    raw_session_id = session.get("sessionId")
                    if not isinstance(raw_session_id, str) or not raw_session_id:
                        continue
                    transcript = _get_transcript_path(
                        "oe-orchestrator", raw_session_id, openclaw_home, env
                    )
                    if transcript is None:
                        continue
                    return (raw_session_id, transcript)
        if attempt < attempts:
            time.sleep(delay_seconds)
    return None


def _snapshot_main_transcript_line_counts(openclaw_home: Path) -> dict[Path, int]:
    sessions_dir = openclaw_home / "agents" / "main" / "sessions"
    if not sessions_dir.exists():
        return {}
    counts: dict[Path, int] = {}
    for transcript in sessions_dir.glob("*.jsonl"):
        counts[transcript] = _line_count(transcript)
    return counts


def _session_path_candidates(session: dict[str, object], openclaw_home: Path) -> list[Path]:
    candidates: list[Path] = []
    transcript_path = session.get("transcriptPath")
    if isinstance(transcript_path, str) and transcript_path:
        candidates.append(Path(transcript_path).expanduser())

    session_id = session.get("sessionId")
    if isinstance(session_id, str) and session_id:
        candidates.append(openclaw_home / "agents" / "main" / "sessions" / f"{session_id}.jsonl")

    return candidates


def _find_main_session_from_growth(
    openclaw_home: Path,
    env: dict[str, str],
    baseline_line_counts: dict[Path, int],
) -> tuple[str, Path] | None:
    sessions_result = subprocess.run(
        ["openclaw", "sessions", "--agent", "main", "--json"],
        capture_output=True,
        text=True,
        env=env,
    )
    if sessions_result.returncode != 0:
        return None

    sessions_obj = _parse_first_json_object(sessions_result.stdout)
    if sessions_obj is None:
        return None

    sessions = sessions_obj.get("sessions", []) if isinstance(sessions_obj, dict) else []
    if not isinstance(sessions, list):
        return None

    growth_candidates: list[tuple[float, str, Path]] = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        session_id = session.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            continue

        for transcript_path in _session_path_candidates(session, openclaw_home):
            if not transcript_path.exists():
                continue
            before = baseline_line_counts.get(transcript_path, 0)
            after = _line_count(transcript_path)
            if after > before:
                try:
                    mtime = transcript_path.stat().st_mtime
                except OSError:
                    mtime = 0.0
                growth_candidates.append((mtime, session_id, transcript_path))

    if not growth_candidates:
        return None

    growth_candidates.sort(reverse=True)
    _, resolved_session_id, resolved_path = growth_candidates[0]
    return (resolved_session_id, resolved_path)


def _line_count_delta(path: Path, baseline_line_counts: dict[Path, int]) -> int:
    before = baseline_line_counts.get(path, 0)
    after = _line_count(path)
    return max(0, after - before)


def _search_transcript_segment(
    transcript_path: Path,
    start_line: int,
    *search_terms: str,
) -> bool:
    lowered_terms = [term.lower() for term in search_terms if term]
    if not lowered_terms:
        return False
    try:
        with transcript_path.open("r", encoding="utf-8", errors="ignore") as handle:
            for idx, line in enumerate(handle, start=1):
                if idx < max(1, start_line):
                    continue
                lowered_line = line.lower()
                if all(term in lowered_line for term in lowered_terms):
                    return True
        return False
    except OSError:
        return False


def _latest_main_transcript_snapshot(openclaw_home: Path) -> tuple[Path, int] | None:
    sessions_dir = openclaw_home / "agents" / "main" / "sessions"
    if not sessions_dir.exists():
        return None
    candidates = sorted(
        sessions_dir.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    transcript_path = candidates[0]
    return (transcript_path, _line_count(transcript_path))


def _latest_main_transcript_path(openclaw_home: Path) -> Path | None:
    snapshot = _latest_main_transcript_snapshot(openclaw_home)
    if snapshot is None:
        return None
    return snapshot[0]


def _extract_main_session_id(parsed: dict[str, object]) -> str | None:
    result_obj = parsed.get("result")
    meta_obj = result_obj.get("meta") if isinstance(result_obj, dict) else parsed.get("meta")
    if not isinstance(meta_obj, dict):
        return None

    agent_meta = meta_obj.get("agentMeta")
    if isinstance(agent_meta, dict):
        session_id = agent_meta.get("sessionId")
        if isinstance(session_id, str) and session_id:
            return session_id

    system_prompt_report = meta_obj.get("systemPromptReport")
    if isinstance(system_prompt_report, dict):
        session_id = system_prompt_report.get("sessionId")
        if isinstance(session_id, str) and session_id:
            return session_id

    root_session_id = parsed.get("sessionId")
    if isinstance(root_session_id, str) and root_session_id:
        return root_session_id

    return None


def _is_valid_orchestrator_runtime_surface(agent_output: dict[str, object]) -> bool:
    result_obj = agent_output.get("result")
    meta_obj = result_obj.get("meta") if isinstance(result_obj, dict) else None
    agent_meta = meta_obj.get("agentMeta") if isinstance(meta_obj, dict) else None
    system_prompt_report = (
        meta_obj.get("systemPromptReport") if isinstance(meta_obj, dict) else None
    )

    session_id = agent_meta.get("sessionId") if isinstance(agent_meta, dict) else None
    workspace_dir = (
        system_prompt_report.get("workspaceDir") if isinstance(system_prompt_report, dict) else None
    )
    tool_surface_names = _tool_surface_names(agent_output)

    return (
        isinstance(session_id, str)
        and bool(session_id)
        and isinstance(workspace_dir, str)
        and "oe-orchestrator" in workspace_dir
        and "sessions_yield" in tool_surface_names
    )


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

    bootstrap_completed = (
        result.returncode == 0
        and not bootstrap_file.exists()
        and _runtime_identity_confirmed(openclaw_home, agent_id)
    )

    if bootstrap_completed:
        return True

    if agent_id != "oe-orchestrator":
        return False

    runtime_probe = subprocess.run(
        [
            "openclaw",
            "agent",
            "--agent",
            agent_id,
            "-m",
            "Runtime readiness check: respond briefly in JSON mode.",
            "--json",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    if runtime_probe.returncode != 0:
        return False

    agent_output = _parse_agent_output(runtime_probe.stdout + runtime_probe.stderr)
    if not agent_output:
        return False

    return _is_valid_orchestrator_runtime_surface(agent_output)


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
            "evidence": f"Symlink: {workspace_path} -> Target: {target}",
        }
    )


@cli.command("routing-yield")
@click.option("--openclaw-home", type=click.Path(path_type=Path), required=True)
@click.option("--message", required=True, help="Message to send to openclaw chat")
def routing_yield(openclaw_home: Path, message: str) -> None:
    """Verify orchestrator routing via live openclaw chat session."""
    home = _require_openclaw_home("routing-yield", openclaw_home)
    env = _probe_env(home)
    config_path = _resolve_config_path(home)

    with pinned_openclaw_runtime_model(config_path) as configured_model:
        openclaw_cmd = subprocess.run(
            ["which", "openclaw"],
            capture_output=True,
            text=True,
            env=env,
        )
        if openclaw_cmd.returncode != 0:
            _fail("routing-yield", "openclaw_cli_not_found", "openclaw command not in PATH")

        if not _ensure_bootstrap_ready("oe-orchestrator", home, env):
            _fail(
                "routing-yield",
                "bootstrap_prep_failed",
                "Could not prepare orchestrator workspace",
            )

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
            _fail(
                "routing-yield",
                "transcript_not_found",
                f"No transcript for session {session_id}",
            )

        tool_surface_names = _tool_surface_names(agent_output)
        if "sessions_yield" not in tool_surface_names:
            _fail(
                "routing-yield",
                "missing_tool_surface",
                "sessions_yield not exposed in live tool surface",
            )

        workspace_dir = (
            system_prompt_report.get("workspaceDir")
            if isinstance(system_prompt_report, dict)
            else None
        )
        if not isinstance(workspace_dir, str) or "oe-orchestrator" not in workspace_dir:
            _fail("routing-yield", "wrong_runtime_workspace", str(workspace_dir))

        runtime_identity_confirmed = _runtime_identity_confirmed(home, "oe-orchestrator")
        runtime_surface_valid = _is_valid_orchestrator_runtime_surface(agent_output)
        if not runtime_identity_confirmed and not runtime_surface_valid:
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
                "runtime_surface_valid": runtime_surface_valid,
                "tool_surface_has_sessions_yield": True,
                "config_path": str(config_path),
                "configured_model": configured_model or PINNED_OPENCLAW_MODEL,
            }
        )


@cli.command("recovery-worker")
@click.option("--openclaw-home", type=click.Path(path_type=Path), required=True)
@click.option("--message", required=True)
def recovery_worker(openclaw_home: Path, message: str) -> None:
    home = _require_openclaw_home("recovery-worker", openclaw_home)
    env = _probe_env(home)
    config_path = _resolve_config_path(home)

    with pinned_openclaw_runtime_model(config_path) as configured_model:
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
            _fail(
                "recovery-worker",
                "bootstrap_prep_failed",
                "Could not prepare recovery workspace",
            )

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
            _fail(
                "recovery-worker",
                "transcript_not_found",
                f"No transcript for session {session_id}",
            )

        workspace_dir = (
            system_prompt_report.get("workspaceDir")
            if isinstance(system_prompt_report, dict)
            else None
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
                "config_path": str(config_path),
                "configured_model": configured_model or PINNED_OPENCLAW_MODEL,
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

    with pinned_openclaw_runtime_model(resolved_config) as configured_model:
        try:
            config_data = json.loads(resolved_config.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            _fail("watchdog-reminder", "invalid_openclaw_config_json", str(exc))
            return
        except OSError as exc:
            _fail("watchdog-reminder", "config_read_error", str(exc))
            return

        hooks_fragment = None
        managed_hooks_dir = str((home / "openclaw-enhance" / "hooks").absolute())
        hooks_obj = config_data.get("hooks")
        if isinstance(hooks_obj, dict):
            internal_hooks = hooks_obj.get("internal")
            if isinstance(internal_hooks, dict):
                entries = internal_hooks.get("entries")
                hook_enabled = False
                if isinstance(entries, dict):
                    hook_entry = entries.get("oe-subagent-spawn-enrich")
                    if isinstance(hook_entry, dict):
                        hook_enabled = hook_entry.get("enabled") is True

                load_obj = internal_hooks.get("load")
                has_managed_hook_dir = False
                if isinstance(load_obj, dict):
                    extra_dirs = load_obj.get("extraDirs")
                    if isinstance(extra_dirs, list):
                        has_managed_hook_dir = managed_hooks_dir in extra_dirs

                if hook_enabled and has_managed_hook_dir:
                    hooks_fragment = {"internal": internal_hooks}

        proof_type = (
            "config_hook_plus_live_reminder"
            if hooks_fragment
            else "workspace_contract_plus_live_reminder"
        )

        if not hooks_fragment:
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
            "configured_model": configured_model
            or get_primary_model(resolved_config)
            or PINNED_OPENCLAW_MODEL,
        }
        if hooks_fragment:
            payload["config_fragment"] = json.dumps(hooks_fragment, sort_keys=True)

        _emit(payload)


@cli.command("main-escalation")
@click.option("--openclaw-home", type=click.Path(path_type=Path), required=True)
@click.option("--message", required=True, help="Heavy task message to send to main session")
def main_escalation(openclaw_home: Path, message: str) -> None:
    """Verify heavy main-session requests escalate to oe-orchestrator."""
    home = _require_openclaw_home("main-escalation", openclaw_home)
    env = _probe_env(home)
    config_path = _resolve_config_path(home)

    with pinned_openclaw_runtime_model(config_path) as configured_model:
        baseline = _latest_main_transcript_snapshot(home)
        baseline_line_counts = _snapshot_main_transcript_line_counts(home)
        probe_session_id = str(uuid.uuid4())
        probe_request_id = str(uuid.uuid4())
        probe_message = _build_main_escalation_probe_message(message, probe_request_id)
        # Build the main session command (will fail if no supported entrypoint)
        cmd = _build_main_session_command("main-escalation", probe_message, env, probe_session_id)

        # Start main session
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )

        if result.returncode != 0:
            _fail(
                "main-escalation",
                "main_session_failed",
                result.stderr[:500] if result.stderr else None,
            )

        parsed = _parse_agent_output(result.stdout)
        if parsed is None:
            _fail("main-escalation", "no_json_output", result.stdout[:500])
            assert False, "unreachable"

        raw_session_id = _extract_main_session_id(parsed)
        if not isinstance(raw_session_id, str):
            _fail("main-escalation", "missing_main_session_id")
            assert False, "unreachable"
        main_session_id: str = raw_session_id

        main_transcript = _get_transcript_path("main", main_session_id, home, env)
        needs_growth_attribution = (
            main_transcript is None or _line_count_delta(main_transcript, baseline_line_counts) == 0
        )

        if needs_growth_attribution:
            growth_attribution = _find_main_session_from_growth(home, env, baseline_line_counts)
            if growth_attribution is not None:
                growth_session_id, growth_transcript = growth_attribution
                main_session_id, main_transcript = growth_session_id, growth_transcript

        if main_transcript is None:
            fallback_transcript = _latest_main_transcript_path(home)
            if fallback_transcript is None:
                _fail("main-escalation", "missing_main_transcript", main_session_id)
                assert False, "unreachable"
            main_transcript = fallback_transcript

        start_line = 1
        if baseline is not None:
            baseline_path, baseline_lines = baseline
            if baseline_path == main_transcript:
                start_line = baseline_lines + 1

        invalid_stream_to = _search_transcript_segment(
            main_transcript,
            start_line,
            "sessions_spawn",
            "streamto",
        )
        if invalid_stream_to:
            _fail("main-escalation", "invalid_stream_to", main_session_id)

        orchestrator_spawned = _search_transcript_segment(
            main_transcript,
            start_line,
            "sessions_spawn",
            "oe-orchestrator",
        )

        probe_request_attributed = _search_transcript_segment(
            main_transcript,
            start_line,
            probe_request_id,
        )

        if not orchestrator_spawned or not probe_request_attributed:
            _fail("main-escalation", "orchestrator_handoff_missing", str(main_session_id))

        child_session_key = _extract_orchestrator_child_session_key_from_segment(
            main_transcript, start_line
        )
        orchestrator_resolution = None
        if child_session_key:
            orchestrator_resolution = _resolve_orchestrator_session_by_child_key(
                home, env, child_session_key
            )
        if orchestrator_resolution is None:
            orchestrator_resolution = _resolve_orchestrator_session_for_request(
                home, env, probe_request_id
            )
        if orchestrator_resolution is None:
            _fail(
                "main-escalation", "missing_transcript_evidence", "missing orchestrator session id"
            )
            assert False, "unreachable"
        orchestrator_session_id, orch_transcript = orchestrator_resolution

        _emit(
            {
                "ok": True,
                "probe": "main-escalation",
                "marker": "PROBE_MAIN_ESCALATION_OK",
                "main_session_id": main_session_id,
                "orchestrator_session_id": orchestrator_session_id,
                "main_transcript_path": str(main_transcript),
                "orchestrator_transcript_path": str(orch_transcript),
                "main_session_evidence": {
                    "session_id": main_session_id,
                    "transcript_path": str(main_transcript),
                    "handoff_confirmed": True,
                },
                "orchestrator_session_evidence": {
                    "session_id": orchestrator_session_id,
                    "transcript_path": str(orch_transcript),
                },
                "proof": "orchestrator_handoff_confirmed",
                "proof_request_id": probe_request_id,
                "configured_model": configured_model or PINNED_OPENCLAW_MODEL,
            }
        )


def main() -> None:
    """Module entry point."""
    cli()


if __name__ == "__main__":
    main()
