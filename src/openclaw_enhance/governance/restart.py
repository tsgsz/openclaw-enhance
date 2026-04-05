from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from openclaw_enhance.runtime.project_state import bump_restart_epoch, revoke_binding


def run_openclaw_command(arguments: list[str], *, timeout: int = 30) -> dict[str, Any]:
    command = ["openclaw", *arguments]
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def evaluate_safe_restart() -> dict[str, Any]:
    sessions_result = run_openclaw_command(["sessions", "--json"])
    sessions = []
    if sessions_result["returncode"] == 0:
        try:
            sessions = json.loads(sessions_result["stdout"] or "[]")
        except json.JSONDecodeError:
            sessions = []
    eligible = sessions_result["returncode"] == 0 and sessions == []
    return {
        "eligible": eligible,
        "reason": "idle" if eligible else "active_sessions_or_probe_failure",
        "sessions_check": sessions_result,
    }


def safe_restart(*, dry_run: bool, user_home: Path | None = None) -> dict[str, Any]:
    evaluation = evaluate_safe_restart()
    if dry_run or not evaluation["eligible"]:
        return {**evaluation, "executed": False}

    restart_result = run_openclaw_command(["gateway", "restart"])
    executed = restart_result["returncode"] == 0
    if executed:
        bump_restart_epoch(user_home)
    return {
        **evaluation,
        "executed": executed,
        "restart": restart_result,
    }


def immediate_restart_resume(user_home: Path | None = None) -> dict[str, Any]:
    restart_result = run_openclaw_command(["gateway", "restart"])
    if restart_result["returncode"] == 0:
        revoke_binding(user_home)
    return {
        "executed": restart_result["returncode"] == 0,
        "restart": restart_result,
        "followup": "resume_required",
    }
