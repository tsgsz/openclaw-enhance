"""Tests for live validation probes."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from openclaw_enhance.validation.live_probes import (
    _build_orchestrator_spawn_probe_message,
    cli,
)


def test_dev_symlink_probe_fails_when_no_symlinks(mock_openclaw_home: Path):
    """Probe should fail if no symlinks are found in workspaces."""
    workspaces_dir = mock_openclaw_home / "openclaw-enhance" / "workspaces"
    workspaces_dir.mkdir(parents=True)

    # Create a regular directory instead of a symlink
    (workspaces_dir / "oe-orchestrator").mkdir()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dev-symlink",
            "--openclaw-home",
            str(mock_openclaw_home),
            "--workspace",
            "oe-orchestrator",
        ],
    )

    assert result.exit_code != 0
    assert '"reason": "workspace_not_symlink"' in result.output


def test_dev_symlink_probe_succeeds_with_symlink(mock_openclaw_home: Path, tmp_path: Path):
    """Probe should succeed and print paths if symlink exists."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    workspaces_dir = mock_openclaw_home / "openclaw-enhance" / "workspaces"
    workspaces_dir.mkdir(parents=True)

    target_link = workspaces_dir / "oe-orchestrator"
    os.symlink(source_dir, target_link)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dev-symlink",
            "--openclaw-home",
            str(mock_openclaw_home),
            "--workspace",
            "oe-orchestrator",
        ],
    )

    assert result.exit_code == 0
    assert str(target_link) in result.output
    assert str(source_dir) in result.output


def test_watchdog_reminder_prefers_supported_hook_config(mock_openclaw_home: Path):
    managed_hook_dir = mock_openclaw_home / "openclaw-enhance" / "hooks"
    config_path = mock_openclaw_home / "openclaw.json"
    config_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "internal": {
                        "enabled": True,
                        "entries": {"oe-subagent-spawn-enrich": {"enabled": True}},
                        "load": {"extraDirs": [str(managed_hook_dir)]},
                    }
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "watchdog-reminder",
            "--openclaw-home",
            str(mock_openclaw_home),
            "--session-id",
            "watchdog-test-session",
        ],
    )

    assert result.exit_code == 0, result.output
    assert '"proof": "config_hook_plus_live_reminder"' in result.output
    assert '"config_fragment"' in result.output


def test_watchdog_reminder_requires_enabled_hook_entry(mock_openclaw_home: Path):
    managed_hook_dir = mock_openclaw_home / "openclaw-enhance" / "hooks"
    config_path = mock_openclaw_home / "openclaw.json"
    config_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "internal": {
                        "enabled": True,
                        "entries": {"oe-subagent-spawn-enrich": {"enabled": False}},
                        "load": {"extraDirs": [str(managed_hook_dir)]},
                    }
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "watchdog-reminder",
            "--openclaw-home",
            str(mock_openclaw_home),
            "--session-id",
            "watchdog-disabled-hook",
        ],
    )

    # v2: watchdog workspace doesn't exist, probe fails with missing_watchdog_workspace_and_config
    assert result.exit_code == 2, result.output
    assert "missing_watchdog_workspace_and_config" in result.output


def test_watchdog_reminder_requires_managed_hook_dir(mock_openclaw_home: Path):
    config_path = mock_openclaw_home / "openclaw.json"
    config_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "internal": {
                        "enabled": True,
                        "entries": {"oe-subagent-spawn-enrich": {"enabled": True}},
                        "load": {"extraDirs": ["/tmp/hooks"]},
                    }
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "watchdog-reminder",
            "--openclaw-home",
            str(mock_openclaw_home),
            "--session-id",
            "watchdog-missing-dir",
        ],
    )

    # v2: watchdog workspace doesn't exist, probe fails with missing_watchdog_workspace_and_config
    assert result.exit_code == 2, result.output
    assert "missing_watchdog_workspace_and_config" in result.output


@patch("openclaw_enhance.validation.live_probes.uuid.uuid4")
@patch("openclaw_enhance.validation.live_probes.subprocess.run")
def test_orchestrator_spawn_probe_emits_parent_child_evidence_tuple(
    mock_run,
    mock_uuid4,
    tmp_path: Path,
):
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)
    (openclaw_home / "openclaw.json").write_text("{}\n", encoding="utf-8")

    worker_agent_id = "oe-searcher"
    orchestrator_transcript = tmp_path / "orchestrator-transcript.jsonl"
    worker_transcript = tmp_path / "worker-transcript.jsonl"

    request_id = "request-id-123"
    parent_session_id = "orch-session-123"
    child_session_key = "agent:oe-searcher:subagent:child-key-123"
    child_session_id = "worker-session-456"
    mock_uuid4.side_effect = [parent_session_id, request_id]

    parsed_orchestrator = {
        "result": {
            "meta": {
                "agentMeta": {
                    "sessionId": parent_session_id,
                }
            }
        }
    }

    def _side_effect(cmd, **kwargs):
        if cmd[:4] == ["openclaw", "agent", "--agent", "oe-orchestrator"]:
            env = kwargs["env"]
            assert env["OPENCLAW_HOME"] == str(tmp_path)
            assert env["OPENCLAW_CONFIG_PATH"] == str(openclaw_home / "openclaw.json")
            assert "--local" in cmd
            probe_message = cmd[cmd.index("-m") + 1]
            with orchestrator_transcript.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "message": {
                                "role": "assistant",
                                "content": probe_message,
                            }
                        }
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "tool": "sessions_spawn",
                            "agentId": worker_agent_id,
                            "task": probe_message,
                        }
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "message": {
                                "role": "toolResult",
                                "details": {
                                    "childSessionKey": child_session_key,
                                },
                            }
                        }
                    )
                    + "\n"
                )
            with worker_transcript.open("w", encoding="utf-8") as handle:
                handle.write(json.dumps({"task": probe_message}) + "\n")
            return MagicMock(returncode=0, stdout=json.dumps(parsed_orchestrator), stderr="")

        if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
            sessions_payload = {
                "sessions": [
                    {
                        "sessionId": parent_session_id,
                        "transcriptPath": str(orchestrator_transcript),
                    }
                ]
            }
            return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

        if cmd == ["openclaw", "sessions", "--agent", worker_agent_id, "--json"]:
            sessions_payload = {
                "sessions": [
                    {
                        "key": child_session_key,
                        "sessionId": child_session_id,
                        "transcriptPath": str(worker_transcript),
                    }
                ]
            }
            return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

        raise AssertionError(f"Unexpected subprocess call: {cmd}")

    mock_run.side_effect = _side_effect

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "orchestrator-spawn",
            "--openclaw-home",
            str(openclaw_home),
            "--message",
            "Research the competitive landscape and return attributable sources.",
        ],
    )

    assert result.exit_code == 0, result.output or result.stderr
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["probe"] == "orchestrator-spawn"
    assert payload["marker"] == "PROBE_ORCHESTRATOR_SPAWN_OK"
    assert payload["orchestrator_session_id"] == parent_session_id
    assert payload["child_session_key"] == child_session_key
    assert payload["child_session_id"] == child_session_id
    assert payload["worker_agent_id"] == worker_agent_id
    assert payload["transcript_path"] == str(worker_transcript)
    assert payload["proof_request_id"] == request_id


def test_orchestrator_spawn_probe_message_is_bounded_and_fresh():
    prompt = _build_orchestrator_spawn_probe_message(
        "Research the competitive landscape and return attributable sources.",
        "request-id-abc",
    )

    assert "request-id-abc" in prompt
    assert "orchestrator-spawn:request-id-abc" in prompt
    assert "README.md" not in prompt
    assert "sessions_spawn" in prompt
    assert "本次唯一任务" in prompt
    assert "background info" not in prompt
    assert "背景信息（不要把它当作主任务）" in prompt
    assert "Research the competitive landscape" in prompt


@patch("openclaw_enhance.validation.live_probes.uuid.uuid4")
@patch("openclaw_enhance.validation.live_probes.subprocess.run")
def test_orchestrator_spawn_probe_reports_upstream_runtime_failure_when_error_turn_precedes_spawn(
    mock_run,
    mock_uuid4,
    tmp_path: Path,
):
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)

    orchestrator_transcript = tmp_path / "orchestrator-transcript.jsonl"

    request_id = "request-id-upstream-error"
    parent_session_id = "orch-session-error-123"
    mock_uuid4.side_effect = [parent_session_id, request_id]

    parsed_orchestrator = {
        "result": {
            "meta": {
                "agentMeta": {
                    "sessionId": parent_session_id,
                }
            }
        }
    }

    def _side_effect(cmd, **_kwargs):
        if cmd[:4] == ["openclaw", "agent", "--agent", "oe-orchestrator"]:
            assert "--local" in cmd
            probe_message = cmd[cmd.index("-m") + 1]
            with orchestrator_transcript.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "message": {
                                "role": "assistant",
                                "content": probe_message,
                            }
                        }
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "message": {
                                "role": "assistant",
                                "stopReason": "error",
                                "errorMessage": "request ended without sending any chunks",
                            }
                        }
                    )
                    + "\n"
                )
            return MagicMock(returncode=0, stdout=json.dumps(parsed_orchestrator), stderr="")

        if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
            sessions_payload = {
                "sessions": [
                    {
                        "sessionId": parent_session_id,
                        "transcriptPath": str(orchestrator_transcript),
                    }
                ]
            }
            return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

        raise AssertionError(f"Unexpected subprocess call: {cmd}")

    mock_run.side_effect = _side_effect

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "orchestrator-spawn",
            "--openclaw-home",
            str(openclaw_home),
            "--message",
            "Research the competitive landscape and return attributable sources.",
        ],
    )

    assert result.exit_code != 0, result.output
    assert '"probe": "orchestrator-spawn"' in result.output
    assert '"reason": "upstream_runtime_failure"' in result.output
    assert "request ended without sending any chunks" in result.output


@patch("openclaw_enhance.validation.live_probes.uuid.uuid4")
@patch("openclaw_enhance.validation.live_probes.subprocess.run")
def test_orchestrator_spawn_attributes_parent_transcript_by_request_id_when_session_is_reused(
    mock_run,
    mock_uuid4,
    tmp_path: Path,
):
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)
    (openclaw_home / "openclaw.json").write_text("{}\n", encoding="utf-8")

    stale_orchestrator_transcript = tmp_path / "orchestrator-stale.jsonl"
    live_orchestrator_transcript = tmp_path / "orchestrator-live.jsonl"
    worker_transcript = tmp_path / "worker-transcript.jsonl"

    requested_session_id = "requested-parent-session"
    stale_metadata_session_id = "stale-parent-session"
    live_parent_session_id = "live-parent-session"
    request_id = "request-id-reused-parent"
    worker_agent_id = "oe-searcher"
    child_session_key = "agent:oe-searcher:subagent:child-key-reused"
    child_session_id = "worker-session-reused"
    mock_uuid4.side_effect = [requested_session_id, request_id]

    stale_orchestrator_transcript.write_text(
        json.dumps({"message": {"role": "assistant", "content": "old unrelated turn"}}) + "\n",
        encoding="utf-8",
    )

    parsed_orchestrator = {
        "result": {
            "meta": {
                "agentMeta": {
                    "sessionId": stale_metadata_session_id,
                }
            }
        }
    }

    def _side_effect(cmd, **kwargs):
        if cmd[:4] == ["openclaw", "agent", "--agent", "oe-orchestrator"]:
            assert "--local" in cmd
            probe_message = cmd[cmd.index("-m") + 1]
            with live_orchestrator_transcript.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "message": {
                                "role": "assistant",
                                "content": probe_message,
                            }
                        }
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "tool": "sessions_spawn",
                            "agentId": worker_agent_id,
                            "task": probe_message,
                        }
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "message": {
                                "role": "toolResult",
                                "details": {
                                    "childSessionKey": child_session_key,
                                },
                            }
                        }
                    )
                    + "\n"
                )
            with worker_transcript.open("w", encoding="utf-8") as handle:
                handle.write(json.dumps({"task": probe_message}) + "\n")
            return MagicMock(returncode=0, stdout=json.dumps(parsed_orchestrator), stderr="")

        if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
            sessions_payload = {
                "sessions": [
                    {
                        "sessionId": stale_metadata_session_id,
                        "transcriptPath": str(stale_orchestrator_transcript),
                    },
                    {
                        "sessionId": live_parent_session_id,
                        "transcriptPath": str(live_orchestrator_transcript),
                    },
                ]
            }
            return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

        if cmd == ["openclaw", "sessions", "--agent", worker_agent_id, "--json"]:
            sessions_payload = {
                "sessions": [
                    {
                        "key": child_session_key,
                        "sessionId": child_session_id,
                        "transcriptPath": str(worker_transcript),
                    }
                ]
            }
            return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

        raise AssertionError(f"Unexpected subprocess call: {cmd}")

    mock_run.side_effect = _side_effect

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "orchestrator-spawn",
            "--openclaw-home",
            str(openclaw_home),
            "--message",
            "Research the competitive landscape and return attributable sources.",
        ],
    )

    assert result.exit_code == 0, result.output or result.stderr
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["orchestrator_session_id"] == live_parent_session_id
    assert payload["orchestrator_transcript_path"] == str(live_orchestrator_transcript)
    assert payload["child_session_id"] == child_session_id
    assert payload["worker_agent_id"] == worker_agent_id
    assert payload["proof_request_id"] == request_id


@patch("openclaw_enhance.validation.live_probes.uuid.uuid4")
@patch("openclaw_enhance.validation.live_probes.subprocess.run")
def test_orchestrator_spawn_rejects_stale_child_reuse_for_current_request_id(
    mock_run,
    mock_uuid4,
    tmp_path: Path,
):
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)
    (openclaw_home / "openclaw.json").write_text("{}\n", encoding="utf-8")

    worker_agent_id = "oe-searcher"
    orchestrator_transcript = (
        openclaw_home / "agents" / "oe-orchestrator" / "sessions" / "orch-session-stale-123.jsonl"
    )
    worker_transcript = (
        openclaw_home / "agents" / worker_agent_id / "sessions" / "worker-session-stale.jsonl"
    )
    orchestrator_transcript.parent.mkdir(parents=True, exist_ok=True)
    worker_transcript.parent.mkdir(parents=True, exist_ok=True)

    request_id = "request-id-stale-child"
    parent_session_id = "orch-session-stale-123"
    child_session_key = "agent:oe-searcher:subagent:child-key-stale"
    child_session_id = "worker-session-stale"
    mock_uuid4.side_effect = [parent_session_id, request_id]

    parsed_orchestrator = {
        "result": {
            "meta": {
                "agentMeta": {
                    "sessionId": parent_session_id,
                }
            }
        }
    }

    worker_transcript.write_text(json.dumps({"task": request_id}) + "\n", encoding="utf-8")

    def _side_effect(cmd, **kwargs):
        if cmd[:4] == ["openclaw", "agent", "--agent", "oe-orchestrator"]:
            assert "--local" in cmd
            probe_message = cmd[cmd.index("-m") + 1]
            with orchestrator_transcript.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "message": {
                                "role": "assistant",
                                "content": probe_message,
                            }
                        }
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "tool": "sessions_spawn",
                            "agentId": worker_agent_id,
                            "task": probe_message,
                        }
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "message": {
                                "role": "toolResult",
                                "details": {
                                    "childSessionKey": child_session_key,
                                },
                            }
                        }
                    )
                    + "\n"
                )
            with worker_transcript.open("w", encoding="utf-8") as handle:
                handle.write(json.dumps({"task": request_id}) + "\n")
            return MagicMock(returncode=0, stdout=json.dumps(parsed_orchestrator), stderr="")

        if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
            sessions_payload = {
                "sessions": [
                    {
                        "sessionId": parent_session_id,
                        "transcriptPath": str(orchestrator_transcript),
                    }
                ]
            }
            return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

        if cmd == ["openclaw", "sessions", "--agent", worker_agent_id, "--json"]:
            sessions_payload = {
                "sessions": [
                    {
                        "key": child_session_key,
                        "sessionId": child_session_id,
                        "transcriptPath": str(worker_transcript),
                    }
                ]
            }
            return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

        raise AssertionError(f"Unexpected subprocess call: {cmd}")

    mock_run.side_effect = _side_effect

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "orchestrator-spawn",
            "--openclaw-home",
            str(openclaw_home),
            "--message",
            "Research the competitive landscape and return attributable sources.",
        ],
    )

    assert result.exit_code != 0, result.output
    assert '"probe": "orchestrator-spawn"' in result.output
    assert '"reason": "stale_child_reuse"' in result.output


@patch("openclaw_enhance.validation.live_probes.uuid.uuid4")
@patch("openclaw_enhance.validation.live_probes.subprocess.run")
def test_orchestrator_spawn_accepts_fresh_child_when_request_id_precedes_spawn_line(
    mock_run,
    mock_uuid4,
    tmp_path: Path,
):
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)
    (openclaw_home / "openclaw.json").write_text("{}\n", encoding="utf-8")

    worker_agent_id = "oe-searcher"
    orchestrator_transcript = (
        openclaw_home / "agents" / "oe-orchestrator" / "sessions" / "orch-session-fresh-123.jsonl"
    )
    worker_transcript = (
        openclaw_home / "agents" / worker_agent_id / "sessions" / "worker-session-fresh.jsonl"
    )
    orchestrator_transcript.parent.mkdir(parents=True, exist_ok=True)
    worker_transcript.parent.mkdir(parents=True, exist_ok=True)

    request_id = "request-id-precedes-spawn"
    parent_session_id = "orch-session-fresh-123"
    child_session_key = "agent:oe-searcher:subagent:child-key-fresh"
    child_session_id = "worker-session-fresh"
    mock_uuid4.side_effect = [parent_session_id, request_id]

    parsed_orchestrator = {
        "result": {
            "meta": {
                "agentMeta": {
                    "sessionId": parent_session_id,
                }
            }
        }
    }

    def _side_effect(cmd, **kwargs):
        if cmd[:4] == ["openclaw", "agent", "--agent", "oe-orchestrator"]:
            assert "--local" in cmd
            probe_message = cmd[cmd.index("-m") + 1]
            with orchestrator_transcript.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "message": {
                                "role": "assistant",
                                "content": probe_message,
                            }
                        }
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "message": {
                                "role": "assistant",
                                "content": f"dispatching current probe request {request_id}",
                            }
                        }
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "tool": "sessions_spawn",
                            "agentId": worker_agent_id,
                            "task": "printf exactly one line and nothing else",
                        }
                    )
                    + "\n"
                )
                handle.write(
                    json.dumps(
                        {
                            "message": {
                                "role": "toolResult",
                                "details": {
                                    "childSessionKey": child_session_key,
                                },
                            }
                        }
                    )
                    + "\n"
                )
            with worker_transcript.open("w", encoding="utf-8") as handle:
                handle.write(json.dumps({"old": "stale line before probe"}) + "\n")
                handle.write(json.dumps({"task": f"orchestrator-spawn:{request_id}"}) + "\n")
            return MagicMock(returncode=0, stdout=json.dumps(parsed_orchestrator), stderr="")

        if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
            sessions_payload = {
                "sessions": [
                    {
                        "sessionId": parent_session_id,
                        "transcriptPath": str(orchestrator_transcript),
                    }
                ]
            }
            return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

        if cmd == ["openclaw", "sessions", "--agent", worker_agent_id, "--json"]:
            sessions_payload = {
                "sessions": [
                    {
                        "key": child_session_key,
                        "sessionId": child_session_id,
                        "transcriptPath": str(worker_transcript),
                    }
                ]
            }
            return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

        raise AssertionError(f"Unexpected subprocess call: {cmd}")

    mock_run.side_effect = _side_effect

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "orchestrator-spawn",
            "--openclaw-home",
            str(openclaw_home),
            "--message",
            "printf a single line with the current probe request-id and nothing else",
        ],
    )

    assert result.exit_code == 0, result.output or result.stderr
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["probe"] == "orchestrator-spawn"
    assert payload["child_session_key"] == child_session_key
    assert payload["child_session_id"] == child_session_id
    assert payload["worker_agent_id"] == worker_agent_id
    assert payload["proof_request_id"] == request_id


@patch("openclaw_enhance.validation.live_probes.uuid.uuid4")
@patch("openclaw_enhance.validation.live_probes.subprocess.run")
def test_orchestrator_spawn_prefers_parent_session_when_child_also_contains_request_id(
    mock_run,
    mock_uuid4,
    tmp_path: Path,
):
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)
    (openclaw_home / "openclaw.json").write_text("{}\n", encoding="utf-8")

    worker_agent_id = "oe-orchestrator"
    parent_transcript = tmp_path / "orchestrator-parent.jsonl"
    child_transcript = tmp_path / "orchestrator-child.jsonl"

    request_id = "request-id-parent-vs-child"
    parent_session_id = "orchestrator-parent-session"
    child_session_id = "orchestrator-child-session"
    child_session_key = "agent:oe-orchestrator:subagent:child-parent-vs-child"
    mock_uuid4.side_effect = [parent_session_id, request_id]

    parsed_orchestrator = {
        "result": {
            "meta": {
                "agentMeta": {
                    "sessionId": parent_session_id,
                }
            }
        }
    }

    def _side_effect(cmd, **kwargs):
        if cmd[:4] == ["openclaw", "agent", "--agent", "oe-orchestrator"]:
            probe_message = cmd[cmd.index("-m") + 1]
            parent_transcript.write_text(
                "\n".join(
                    [
                        json.dumps({"message": {"role": "user", "content": probe_message}}),
                        json.dumps(
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": [
                                        {
                                            "type": "toolCall",
                                            "name": "sessions_spawn",
                                            "arguments": {
                                                "task": f"[{request_id}] echo once",
                                                "agentId": worker_agent_id,
                                            },
                                        }
                                    ],
                                }
                            }
                        ),
                        json.dumps(
                            {
                                "message": {
                                    "role": "toolResult",
                                    "toolName": "sessions_spawn",
                                    "details": {
                                        "childSessionKey": child_session_key,
                                    },
                                }
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            child_transcript.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {"message": {"role": "user", "content": f"[{request_id}] child task"}}
                        ),
                        json.dumps(
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": f"orchestrator-spawn:{request_id}",
                                        }
                                    ],
                                }
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            return MagicMock(returncode=0, stdout=json.dumps(parsed_orchestrator), stderr="")

        if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
            sessions_payload = {
                "sessions": [
                    {
                        "sessionId": child_session_id,
                        "key": child_session_key,
                        "transcriptPath": str(child_transcript),
                    },
                    {
                        "sessionId": parent_session_id,
                        "key": "agent:oe-orchestrator:main",
                        "transcriptPath": str(parent_transcript),
                    },
                ]
            }
            return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

        raise AssertionError(f"Unexpected subprocess call: {cmd}")

    mock_run.side_effect = _side_effect

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "orchestrator-spawn",
            "--openclaw-home",
            str(openclaw_home),
            "--message",
            "printf a single line with the current probe request-id and nothing else",
        ],
    )

    assert result.exit_code == 0, result.output or result.stderr
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["orchestrator_session_id"] == parent_session_id
    assert payload["orchestrator_transcript_path"] == str(parent_transcript)
    assert payload["child_session_id"] == child_session_id
    assert payload["child_session_key"] == child_session_key


@patch("openclaw_enhance.validation.live_probes.uuid.uuid4")
@patch("openclaw_enhance.validation.live_probes.subprocess.run")
def test_orchestrator_spawn_falls_back_to_parent_transcript_files_when_sessions_list_misses_parent(
    mock_run,
    mock_uuid4,
    tmp_path: Path,
):
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)
    (openclaw_home / "openclaw.json").write_text("{}\n", encoding="utf-8")

    worker_agent_id = "oe-orchestrator"
    parent_session_id = "parent-file-fallback-session"
    child_session_id = "child-file-fallback-session"
    child_session_key = "agent:oe-orchestrator:subagent:file-fallback-key"
    request_id = "request-id-file-fallback"
    mock_uuid4.side_effect = [parent_session_id, request_id]

    parent_transcript = (
        openclaw_home / "agents" / "oe-orchestrator" / "sessions" / f"{parent_session_id}.jsonl"
    )
    child_transcript = (
        openclaw_home / "agents" / "oe-orchestrator" / "sessions" / f"{child_session_id}.jsonl"
    )
    parent_transcript.parent.mkdir(parents=True, exist_ok=True)

    parsed_orchestrator = {
        "result": {
            "meta": {
                "agentMeta": {
                    "sessionId": parent_session_id,
                }
            }
        }
    }

    def _side_effect(cmd, **kwargs):
        if cmd[:4] == ["openclaw", "agent", "--agent", "oe-orchestrator"]:
            probe_message = cmd[cmd.index("-m") + 1]
            parent_transcript.write_text(
                "\n".join(
                    [
                        json.dumps({"message": {"role": "user", "content": probe_message}}),
                        json.dumps(
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": [
                                        {
                                            "type": "toolCall",
                                            "name": "sessions_spawn",
                                            "arguments": {
                                                "task": f"[{request_id}] echo once",
                                                "agentId": worker_agent_id,
                                            },
                                        }
                                    ],
                                }
                            }
                        ),
                        json.dumps(
                            {
                                "message": {
                                    "role": "toolResult",
                                    "toolName": "sessions_spawn",
                                    "details": {
                                        "childSessionKey": child_session_key,
                                    },
                                }
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            child_transcript.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {"message": {"role": "user", "content": f"[{request_id}] child task"}}
                        ),
                        json.dumps(
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": f"orchestrator-spawn:{request_id}",
                                        }
                                    ],
                                }
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            return MagicMock(returncode=0, stdout=json.dumps(parsed_orchestrator), stderr="")

        if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
            sessions_payload = {
                "sessions": [
                    {
                        "sessionId": child_session_id,
                        "key": child_session_key,
                        "transcriptPath": str(child_transcript),
                    }
                ]
            }
            return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

        raise AssertionError(f"Unexpected subprocess call: {cmd}")

    mock_run.side_effect = _side_effect

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "orchestrator-spawn",
            "--openclaw-home",
            str(openclaw_home),
            "--message",
            "printf a single line with the current probe request-id and nothing else",
        ],
    )

    assert result.exit_code == 0, result.output or result.stderr
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["orchestrator_session_id"] == parent_session_id
    assert payload["orchestrator_transcript_path"] == str(parent_transcript)
    assert payload["child_session_id"] == child_session_id
