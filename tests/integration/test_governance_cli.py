import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from openclaw_enhance.cli import cli


def test_governance_group_is_visible_in_main_help() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "governance" in result.output


def test_governance_archive_sessions_dry_run_reports_without_mutation(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    stale_session = sessions_dir / "stale-session"
    stale_session.write_text("stale", encoding="utf-8")
    archive_root = tmp_path / "archive"

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        Path("sessions").mkdir(exist_ok=True)
        Path("sessions/stale-session").write_text("stale", encoding="utf-8")
        result = runner.invoke(
            cli,
            [
                "governance",
                "archive-sessions",
                "--dry-run",
                "--include-core-sessions",
                "--archive-root",
                str(archive_root),
                "--json",
            ],
        )

        payload = json.loads(result.output)
        assert Path("sessions/stale-session").exists()

    assert result.exit_code == 0
    assert payload["dry_run"] is True
    assert payload["safe_to_archive"]
    assert payload["archived"] == []


def test_governance_subagents_mark_done_updates_json(tmp_path: Path) -> None:
    subagents_file = tmp_path / "sub_agents.json"
    subagents_file.write_text(
        json.dumps(
            {
                "version": 1,
                "sub_agents": [
                    {
                        "child_session_id": "child-1",
                        "from_session_id": "parent-1",
                        "status": "running",
                        "suggestion": "",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "governance",
            "subagents",
            "mark-done",
            "--child",
            "child-1",
            "--subagents-file",
            str(subagents_file),
            "--suggestion",
            "complete",
        ],
    )

    payload = json.loads(subagents_file.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert payload["sub_agents"][0]["status"] == "done"
    assert payload["sub_agents"][0]["suggestion"] == "complete"


def test_governance_diagnose_json_returns_command_results() -> None:
    runner = CliRunner()

    with patch("openclaw_enhance.governance.health.run_command") as run_command:
        run_command.side_effect = [
            {
                "command": ["openclaw", "gateway", "status"],
                "returncode": 0,
                "stdout": "ok",
                "stderr": "",
            },
            {
                "command": ["openclaw", "gateway", "probe"],
                "returncode": 0,
                "stdout": "reachable",
                "stderr": "",
            },
        ]
        result = runner.invoke(cli, ["governance", "diagnose", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["summary"] == "ok"
    assert len(payload["checks"]) == 2


def test_governance_healthcheck_json_reports_paths(tmp_path: Path) -> None:
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["governance", "healthcheck", "--openclaw-home", str(openclaw_home), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["openclaw_home"] == str(openclaw_home)
    assert "managed_root" in payload


def test_governance_safe_restart_dry_run_reports_gate_without_restart() -> None:
    runner = CliRunner()

    with patch("openclaw_enhance.governance.restart.run_openclaw_command") as run_openclaw_command:
        run_openclaw_command.return_value = {
            "command": ["openclaw", "sessions", "--json"],
            "returncode": 0,
            "stdout": "[]",
            "stderr": "",
        }
        result = runner.invoke(cli, ["governance", "safe-restart", "--dry-run", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["eligible"] is True
    assert payload["executed"] is False
