"""CLI smoke tests for openclaw_enhance."""

import subprocess
import sys

import pytest


class TestCLIHelp:
    """Tests for CLI --help command."""

    def test_help_exits_zero(self):
        """CLI --help should exit with code 0."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_help_shows_commands(self):
        """CLI --help should show available commands."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert "install" in result.stdout
        assert "uninstall" in result.stdout
        assert "doctor" in result.stdout
        assert "status" in result.stdout


class TestCLICommandsExist:
    """Tests that CLI commands exist and exit cleanly."""

    @pytest.mark.parametrize("command", ["install", "uninstall", "doctor", "status"])
    def test_command_help_exits_zero(self, command):
        """Each command's --help should exit with code 0."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", command, "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Command '{command} --help' failed: {result.stderr}"
        )

    @pytest.mark.parametrize("command", ["install", "uninstall", "doctor", "status"])
    def test_command_exists_in_help(self, command):
        """Each command should be listed in main help."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert command in result.stdout, f"Command '{command}' not found in help output"
