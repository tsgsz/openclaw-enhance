"""Tests for pinning the OpenClaw runtime model in real-environment flows."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from openclaw_enhance.validation.model_pin import (
    PINNED_OPENCLAW_MODEL,
    get_primary_model,
    pinned_openclaw_runtime_model,
)
from openclaw_enhance.validation.runner import execute_command


def _write_config(path: Path, primary: str = "openai-codex/gpt-5.4") -> None:
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


class TestPinnedOpenClawRuntimeModel:
    def test_pins_and_restores_existing_openclaw_json(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".openclaw" / "openclaw.json"
        _write_config(config_path)
        original_text = config_path.read_text(encoding="utf-8")

        with pinned_openclaw_runtime_model(config_path) as configured_model:
            pinned = json.loads(config_path.read_text(encoding="utf-8"))
            defaults = pinned["agents"]["defaults"]
            assert defaults["model"]["primary"] == PINNED_OPENCLAW_MODEL
            assert defaults["model"]["fallbacks"] == []
            assert defaults["heartbeat"]["model"] == PINNED_OPENCLAW_MODEL
            assert defaults["subagents"]["model"] == PINNED_OPENCLAW_MODEL
            assert configured_model == PINNED_OPENCLAW_MODEL

        assert config_path.read_text(encoding="utf-8") == original_text

    def test_creates_required_model_structure_for_sparse_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".openclaw" / "openclaw.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("{}\n", encoding="utf-8")

        with pinned_openclaw_runtime_model(config_path):
            pinned = json.loads(config_path.read_text(encoding="utf-8"))
            assert pinned["agents"]["defaults"]["model"]["primary"] == PINNED_OPENCLAW_MODEL
            assert pinned["agents"]["defaults"]["models"][PINNED_OPENCLAW_MODEL] == {}

        assert json.loads(config_path.read_text(encoding="utf-8")) == {}

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_execute_command_pins_model_for_subprocess_and_restores(self, mock_run, tmp_path: Path) -> None:
        openclaw_home = tmp_path / ".openclaw"
        config_path = openclaw_home / "openclaw.json"
        _write_config(config_path, primary="google/gemini-3-flash-preview")
        original_model = get_primary_model(config_path)

        def _side_effect(*args, **kwargs):
            env = kwargs["env"]
            observed = json.loads(Path(env["OPENCLAW_CONFIG_PATH"]).read_text(encoding="utf-8"))
            assert observed["agents"]["defaults"]["model"]["primary"] == PINNED_OPENCLAW_MODEL
            return MagicMock(returncode=0, stdout="ok", stderr="")

        mock_run.side_effect = _side_effect

        result = execute_command("echo test", openclaw_home)

        assert result.exit_code == 0
        assert get_primary_model(config_path) == original_model
