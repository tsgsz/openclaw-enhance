"""Tests that live probes pin the OpenClaw runtime model."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from openclaw_enhance.validation.live_probes import cli
from openclaw_enhance.validation.model_pin import PINNED_OPENCLAW_MODEL


def _write_probe_config(path: Path, primary: str = "openai-codex/gpt-5.4") -> None:
    payload = {
        "agents": {
            "defaults": {
                "model": {
                    "primary": primary,
                    "fallbacks": ["google/gemini-3-flash-preview"],
                },
                "heartbeat": {"model": "MiniMax2.1"},
                "subagents": {"model": "MiniMax2.1"},
            }
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class TestRoutingYieldModelPin:
    @patch("openclaw_enhance.validation.live_probes._runtime_identity_confirmed", return_value=True)
    @patch("openclaw_enhance.validation.live_probes._get_transcript_path")
    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_routing_yield_pins_model_for_openclaw_subprocess(
        self,
        mock_run,
        mock_transcript_path,
        _mock_identity,
        tmp_path: Path,
    ) -> None:
        openclaw_home = tmp_path / ".openclaw"
        config_path = openclaw_home / "openclaw.json"
        _write_probe_config(config_path)
        original_text = config_path.read_text(encoding="utf-8")

        transcript_path = tmp_path / "transcript.jsonl"
        transcript_path.write_text("{}\n", encoding="utf-8")
        mock_transcript_path.return_value = transcript_path

        workspace_dir = str(openclaw_home / "openclaw-enhance" / "workspaces" / "oe-orchestrator")
        agent_output = {
            "result": {
                "meta": {
                    "agentMeta": {"sessionId": "session-123"},
                    "systemPromptReport": {
                        "workspaceDir": workspace_dir,
                        "tools": {"entries": [{"name": "sessions_yield"}]},
                    },
                }
            }
        }

        def _side_effect(cmd, **kwargs):
            if cmd == ["which", "openclaw"]:
                return MagicMock(returncode=0, stdout="/usr/local/bin/openclaw\n", stderr="")
            if cmd[:4] == ["openclaw", "agent", "--agent", "oe-orchestrator"]:
                observed = json.loads(config_path.read_text(encoding="utf-8"))
                assert observed["agents"]["defaults"]["model"]["primary"] == PINNED_OPENCLAW_MODEL
                assert observed["agents"]["defaults"]["heartbeat"]["model"] == PINNED_OPENCLAW_MODEL
                assert observed["agents"]["defaults"]["subagents"]["model"] == PINNED_OPENCLAW_MODEL
                return MagicMock(returncode=0, stdout=json.dumps(agent_output), stderr="")
            raise AssertionError(f"Unexpected subprocess call: {cmd}")

        mock_run.side_effect = _side_effect

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "routing-yield",
                "--openclaw-home",
                str(openclaw_home),
                "--message",
                "test message",
            ],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["configured_model"] == PINNED_OPENCLAW_MODEL
        assert payload["config_path"] == str(config_path)
        assert config_path.read_text(encoding="utf-8") == original_text

    @patch(
        "openclaw_enhance.validation.live_probes._runtime_identity_confirmed", return_value=False
    )
    @patch("openclaw_enhance.validation.live_probes._get_transcript_path")
    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_routing_yield_accepts_stale_identity_when_runtime_surface_is_valid(
        self,
        mock_run,
        mock_transcript_path,
        _mock_identity,
        tmp_path: Path,
    ) -> None:
        openclaw_home = tmp_path / ".openclaw"
        config_path = openclaw_home / "openclaw.json"
        _write_probe_config(config_path)

        transcript_path = tmp_path / "transcript.jsonl"
        transcript_path.write_text("{}\n", encoding="utf-8")
        mock_transcript_path.return_value = transcript_path

        workspace_dir = str(openclaw_home / "openclaw-enhance" / "workspaces" / "oe-orchestrator")
        agent_output = {
            "result": {
                "meta": {
                    "agentMeta": {"sessionId": "session-123"},
                    "systemPromptReport": {
                        "workspaceDir": workspace_dir,
                        "tools": {"entries": [{"name": "sessions_yield"}]},
                    },
                }
            }
        }

        def _side_effect(cmd, **_kwargs):
            if cmd == ["which", "openclaw"]:
                return MagicMock(returncode=0, stdout="/usr/local/bin/openclaw\n", stderr="")
            if cmd[:4] == ["openclaw", "agent", "--agent", "oe-orchestrator"]:
                return MagicMock(returncode=0, stdout=json.dumps(agent_output), stderr="")
            raise AssertionError(f"Unexpected subprocess call: {cmd}")

        mock_run.side_effect = _side_effect

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "routing-yield",
                "--openclaw-home",
                str(openclaw_home),
                "--message",
                "test message",
            ],
        )

        assert result.exit_code == 0, result.output


class TestMainEscalationModelPin:
    @patch("openclaw_enhance.validation.live_probes._get_transcript_path")
    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_main_escalation_pins_model_and_emits_dual_evidence_payload(
        self,
        mock_run,
        mock_transcript_path,
        tmp_path: Path,
    ) -> None:
        openclaw_home = tmp_path / ".openclaw"
        config_path = openclaw_home / "openclaw.json"
        _write_probe_config(config_path)
        original_text = config_path.read_text(encoding="utf-8")

        main_transcript = tmp_path / "main-transcript.jsonl"
        main_transcript.write_text(
            '{"tool":"sessions_spawn","agentId":"oe-orchestrator"}\n',
            encoding="utf-8",
        )

        def _transcript_side_effect(agent_id, session_id, *_args, **_kwargs):
            if agent_id == "main" and session_id == "main-session-123":
                return main_transcript
            if agent_id == "oe-orchestrator" and session_id == "orch-session-456":
                return orchestrator_transcript
            raise AssertionError(f"Unexpected transcript lookup: {(agent_id, session_id)}")

        mock_transcript_path.side_effect = _transcript_side_effect

        orchestrator_transcript = tmp_path / "orchestrator-transcript.jsonl"
        orchestrator_transcript.write_text('{"event":"spawned"}\n', encoding="utf-8")

        main_output = {
            "result": {
                "meta": {
                    "agentMeta": {"sessionId": "main-session-123"},
                }
            }
        }

        def _side_effect(cmd, **_kwargs):
            if cmd == ["openclaw", "agent", "--help"]:
                return MagicMock(
                    returncode=0, stdout="Usage: openclaw agent [OPTIONS]\n", stderr=""
                )
            if cmd[:4] == ["openclaw", "agent", "--agent", "main"]:
                probe_message = cmd[cmd.index("-m") + 1]
                with main_transcript.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"task": probe_message}) + "\n")
                with orchestrator_transcript.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"task": probe_message}) + "\n")
                observed = json.loads(config_path.read_text(encoding="utf-8"))
                assert observed["agents"]["defaults"]["model"]["primary"] == PINNED_OPENCLAW_MODEL
                assert observed["agents"]["defaults"]["heartbeat"]["model"] == PINNED_OPENCLAW_MODEL
                assert observed["agents"]["defaults"]["subagents"]["model"] == PINNED_OPENCLAW_MODEL
                return MagicMock(returncode=0, stdout=json.dumps(main_output), stderr="")
            if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
                sessions_payload = {
                    "sessions": [
                        {
                            "sessionId": "orch-session-456",
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
                "main-escalation",
                "--openclaw-home",
                str(openclaw_home),
                "--message",
                "route this heavy task",
            ],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["marker"] == "PROBE_MAIN_ESCALATION_OK"
        assert payload["main_session_id"] == "main-session-123"
        assert payload["orchestrator_session_id"] == "orch-session-456"
        assert payload["main_session_evidence"] == {
            "session_id": "main-session-123",
            "transcript_path": str(main_transcript),
            "handoff_confirmed": True,
        }
        assert payload["proof_request_id"]
        assert payload["orchestrator_session_evidence"] == {
            "session_id": "orch-session-456",
            "transcript_path": str(orchestrator_transcript),
        }
        assert payload["configured_model"] == PINNED_OPENCLAW_MODEL
        assert config_path.read_text(encoding="utf-8") == original_text

    @patch("openclaw_enhance.validation.live_probes._get_transcript_path")
    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_main_escalation_missing_orchestrator_transcript_emits_machine_reason(
        self,
        mock_run,
        mock_transcript_path,
        tmp_path: Path,
    ) -> None:
        openclaw_home = tmp_path / ".openclaw"
        _write_probe_config(openclaw_home / "openclaw.json")

        main_transcript = tmp_path / "main-transcript.jsonl"
        main_transcript.write_text(
            '{"tool":"sessions_spawn","agentId":"oe-orchestrator"}\n',
            encoding="utf-8",
        )
        mock_transcript_path.return_value = main_transcript

        main_output = {
            "result": {
                "meta": {
                    "agentMeta": {"sessionId": "main-session-123"},
                }
            }
        }

        def _side_effect(cmd, **_kwargs):
            if cmd == ["openclaw", "agent", "--help"]:
                return MagicMock(
                    returncode=0, stdout="Usage: openclaw agent [OPTIONS]\n", stderr=""
                )
            if cmd[:4] == ["openclaw", "agent", "--agent", "main"]:
                probe_message = cmd[cmd.index("-m") + 1]
                with main_transcript.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"task": probe_message}) + "\n")
                return MagicMock(returncode=0, stdout=json.dumps(main_output), stderr="")
            if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
                return MagicMock(returncode=0, stdout=json.dumps({"sessions": []}), stderr="")
            raise AssertionError(f"Unexpected subprocess call: {cmd}")

        mock_run.side_effect = _side_effect

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "main-escalation",
                "--openclaw-home",
                str(openclaw_home),
                "--message",
                "route this heavy task",
            ],
        )

        assert result.exit_code == 2
        payload = json.loads(result.stderr)
        assert payload["ok"] is False
        assert payload["probe"] == "main-escalation"
        assert payload["reason"] == "missing_transcript_evidence"
