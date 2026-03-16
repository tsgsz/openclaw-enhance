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
