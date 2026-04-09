"""CLI smoke tests for openclaw_enhance."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def run_cli_subprocess(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"src{os.pathsep}{existing_pythonpath}" if existing_pythonpath else "src"
    return subprocess.run(
        [sys.executable, "-m", "openclaw_enhance.cli", *args],
        capture_output=True,
        text=True,
        env=env,
    )


class TestCLIHelp:
    """Tests for CLI --help command."""

    def test_help_exits_zero(self):
        """CLI --help should exit with code 0."""
        result = run_cli_subprocess("--help")
        assert result.returncode == 0

    def test_help_shows_commands(self):
        """CLI --help should show available commands."""
        result = run_cli_subprocess("--help")
        assert "install" in result.stdout
        assert "uninstall" in result.stdout
        assert "doctor" in result.stdout
        assert "status" in result.stdout


class TestCLICommandsExist:
    """Tests that CLI commands exist and exit cleanly."""

    @pytest.mark.parametrize(
        "command",
        [
            "install",
            "uninstall",
            "doctor",
            "status",
            "governance",
            "validate-feature",
            "render-skill",
            "render-hook",
            "docs-check",
        ],
    )
    def test_command_help_exits_zero(self, command):
        """Each command's --help should exit with code 0."""
        result = run_cli_subprocess(command, "--help")
        assert result.returncode == 0, f"Command '{command} --help' failed: {result.stderr}"

    @pytest.mark.parametrize(
        "command",
        [
            "install",
            "uninstall",
            "doctor",
            "status",
            "governance",
            "validate-feature",
            "render-skill",
            "render-hook",
            "docs-check",
        ],
    )
    def test_command_exists_in_help(self, command):
        """Each command should be listed in main help."""
        result = run_cli_subprocess("--help")
        assert command in result.stdout, f"Command '{command}' not found in help output"


class TestCleanupModuleEntryPoint:
    def test_cleanup_module_help_exits_zero(self):
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            f"src{os.pathsep}{existing_pythonpath}" if existing_pythonpath else "src"
        )
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cleanup", "--help"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0
        assert "cleanup-sessions" in result.stdout or "--execute" in result.stdout


class TestCLIDoctorPythonValidation:
    """Tests for doctor command Python validation."""

    def test_doctor_validates_python_version_via_validate_environment(
        self,
        mock_openclaw_home: Path,
        cli_runner,
    ):
        """Doctor command should validate Python version via validate_environment."""
        from click.testing import CliRunner

        from openclaw_enhance.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["doctor", "--openclaw-home", str(mock_openclaw_home)],
        )

        assert result.exit_code == 0
        assert "Doctor checks passed" in result.output

    def test_doctor_fails_on_unsupported_python_version(
        self,
        mock_openclaw_home: Path,
    ):
        """Doctor command should fail on unsupported Python version."""
        from types import SimpleNamespace

        from click.testing import CliRunner

        from openclaw_enhance.cli import cli

        # Mock Python version to be unsupported (3.9)
        old_version_info = SimpleNamespace(
            major=3, minor=9, micro=0, releaselevel="final", serial=0
        )

        with patch("sys.version_info", old_version_info):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["doctor", "--openclaw-home", str(mock_openclaw_home)],
            )

            assert result.exit_code != 0
            assert "python" in result.output.lower() or "unsupported" in result.output.lower()
            assert "3.10" in result.output or "3.9" in result.output


class TestCLIValidateFeature:
    def test_validate_feature_help_shows_options(self):
        result = run_cli_subprocess("validate-feature", "--help")
        assert result.returncode == 0
        assert "--feature-class" in result.stdout
        assert "--report-slug" in result.stdout
        assert "--openclaw-home" in result.stdout
        assert "--reports-dir" in result.stdout
