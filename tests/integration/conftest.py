"""Shared fixtures for integration tests."""

import json
import os
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest


def _mock_run_openclaw_cli(args, check=True):
    stdout = ""

    if args[0] == "plugins" and args[1] == "list":
        stdout = "[]"
    elif args[0] == "plugins" and args[1] == "install":
        openclaw_home = _find_openclaw_home()
        if openclaw_home:
            _update_plugins_config(openclaw_home)
    elif args[0] == "agents" and args[1] == "add":
        # args: ["agents", "add", agent_id, "--workspace", workspace_path, "--non-interactive"]
        if len(args) >= 4:
            agent_id = args[2]
            openclaw_home = _find_openclaw_home()
            if openclaw_home:
                _add_agent_to_config(openclaw_home, agent_id)

    return CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")


def _find_openclaw_home():
    test_home = os.environ.get("TEST_OPENCLAW_HOME")
    if test_home:
        return Path(test_home)
    return None


def _update_plugins_config(openclaw_home: Path):
    config_path = openclaw_home / "openclaw.json"
    if config_path.exists():
        config = json.loads(config_path.read_text())
        if "plugins" not in config:
            config["plugins"] = {"allow": [], "entries": {}}
        if "oe-runtime" not in config["plugins"].get("allow", []):
            config["plugins"]["allow"] = config["plugins"].get("allow", []) + ["oe-runtime"]
        if "oe-runtime" not in config["plugins"].get("entries", {}):
            config["plugins"]["entries"]["oe-runtime"] = {"enabled": True}
        config_path.write_text(json.dumps(config))


def _add_agent_to_config(openclaw_home: Path, agent_id: str):
    config_path = openclaw_home / "openclaw.json"
    if config_path.exists():
        config = json.loads(config_path.read_text())
        if "agents" not in config:
            config["agents"] = {"list": []}
        if "list" not in config["agents"]:
            config["agents"]["list"] = []
        # Check if agent already exists
        existing = [a for a in config["agents"]["list"] if a.get("id") == agent_id]
        if not existing:
            config["agents"]["list"].append({"id": agent_id})
        config_path.write_text(json.dumps(config))


@pytest.fixture(autouse=True)
def _stub_openclaw_cli():
    launchctl_result = MagicMock(returncode=0, stdout="", stderr="")
    with (
        patch(
            "openclaw_enhance.install.installer._run_openclaw_cli",
            side_effect=_mock_run_openclaw_cli,
        ),
        patch(
            "openclaw_enhance.install.monitor_service._run_launchctl",
            return_value=launchctl_result,
        ),
    ):
        yield


@pytest.fixture
def mock_openclaw_home(tmp_path: Path) -> Path:
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)

    version_file = openclaw_home / "VERSION"
    version_file.write_text("2026.3.1\n")

    config_file = openclaw_home / "openclaw.json"
    config_file.write_text(
        json.dumps({"theme": "dark", "plugins": {"allow": [], "entries": {}}}) + "\n"
    )

    os.environ["TEST_OPENCLAW_HOME"] = str(openclaw_home)

    return openclaw_home


@pytest.fixture
def isolated_user_home(tmp_path: Path) -> Path:
    return tmp_path / "user_home"
