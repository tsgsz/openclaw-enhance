import json
import os
import time
from pathlib import Path

from click.testing import CliRunner

from openclaw_enhance.cli import cli


def test_cleanup_sessions_dry_run_reports_without_mutation(tmp_path: Path) -> None:
    core_session = tmp_path / "sessions" / "stale-session"
    core_session.parent.mkdir(parents=True, exist_ok=True)
    core_session.write_text("stale", encoding="utf-8")

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        Path("sessions").mkdir(exist_ok=True)
        Path("sessions/stale-session").write_text("stale", encoding="utf-8")
        result = runner.invoke(
            cli,
            [
                "cleanup-sessions",
                "--dry-run",
                "--include-core-sessions",
                "--stale-threshold-hours",
                "24",
                "--json",
            ],
        )
        still_exists = Path("sessions/stale-session").exists()

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "safe_to_remove" in payload
    assert still_exists


def test_cleanup_sessions_execute_removes_only_safe_targets(tmp_path: Path) -> None:
    core_session = tmp_path / "sessions" / "stale-session"
    core_session.parent.mkdir(parents=True, exist_ok=True)
    core_session.write_text("stale", encoding="utf-8")

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        Path("sessions").mkdir(exist_ok=True)
        Path("sessions/stale-session").write_text("stale", encoding="utf-8")
        result = runner.invoke(
            cli,
            [
                "cleanup-sessions",
                "--execute",
                "--include-core-sessions",
                "--stale-threshold-hours",
                "24",
                "--json",
            ],
        )
        still_exists = Path("sessions/stale-session").exists()

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "removed" in payload
    assert not still_exists


def test_cleanup_sessions_openclaw_home_execute_removes_stale_orphan_session(
    tmp_path: Path,
) -> None:
    openclaw_home = tmp_path / ".openclaw"
    sessions_dir = openclaw_home / "agents" / "main" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    stale_session = sessions_dir / "stale-session.jsonl"
    stale_session.write_text("stale", encoding="utf-8")
    (sessions_dir / "sessions.json").write_text("{}", encoding="utf-8")
    old_mtime = time.time() - (72 * 3600)
    os.utime(stale_session, (old_mtime, old_mtime))

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cleanup-sessions",
            "--execute",
            "--include-core-sessions",
            "--stale-threshold-hours",
            "24",
            "--openclaw-home",
            str(openclaw_home),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert str(stale_session) in payload["removed"]
    assert not stale_session.exists()
