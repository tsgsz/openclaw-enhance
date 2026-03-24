from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from openclaw_enhance.governance.paths import legacy_governance_dir, managed_governance_root


def run_command(command: list[str], *, timeout: int = 30) -> dict[str, Any]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def diagnose() -> dict[str, Any]:
    checks = [
        run_command(["openclaw", "gateway", "status"]),
        run_command(["openclaw", "gateway", "probe"]),
    ]
    summary = "ok" if all(check["returncode"] == 0 for check in checks) else "degraded"
    return {"summary": summary, "checks": checks}


def healthcheck(openclaw_home: Path) -> dict[str, Any]:
    return {
        "openclaw_home": str(openclaw_home),
        "openclaw_home_exists": openclaw_home.exists(),
        "managed_root": str(managed_governance_root(openclaw_home.parent)),
        "legacy_governance_dir": str(legacy_governance_dir(openclaw_home.parent)),
    }
