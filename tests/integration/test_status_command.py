"""Integration tests for the status command.

Tests the `openclaw-enhance status` command and its JSON output format.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from openclaw_enhance.cli import cli
from openclaw_enhance.install import get_install_status, install, uninstall
from openclaw_enhance.install.main_skill_sync import MAIN_SKILL_IDS


class TestStatusCommandCLI:
    """Tests for the status command via CLI."""

    def test_status_command_exits_zero(self):
        """Status command should exit with code 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0, f"Status command failed: {result.output}"

    def test_status_shows_install_path(self):
        """Status should show installation path."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "Installation Path:" in result.output

    def test_status_shows_installed_flag(self):
        """Status should show whether installed."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "Installed:" in result.output

    def test_status_json_format(self):
        """Status --json should output valid JSON."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--json"])

        assert result.exit_code == 0

        # Should be valid JSON
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_status_json_has_required_fields(self):
        """Status JSON should have required fields."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--json"])

        data = json.loads(result.output)

        assert "install_path" in data
        assert "installed" in data
        assert "version" in data
        assert "components" in data
        assert "locked" in data

    def test_status_json_installed_is_boolean(self):
        """Status JSON 'installed' field should be boolean."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--json"])

        data = json.loads(result.output)

        assert isinstance(data["installed"], bool)

    def test_status_json_locked_is_boolean(self):
        """Status JSON 'locked' field should be boolean."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--json"])

        data = json.loads(result.output)

        assert isinstance(data["locked"], bool)

    def test_status_json_components_is_list(self):
        """Status JSON 'components' field should be a list."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--json"])

        data = json.loads(result.output)

        assert isinstance(data["components"], list)


class TestStatusCommandSubprocess:
    """Tests for the status command via subprocess."""

    def test_status_subprocess_exits_zero(self):
        """Status command via subprocess should exit 0."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "status"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_status_json_subprocess(self):
        """Status --json via subprocess should return valid JSON."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "status", "--json"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert "install_path" in data


class TestStatusWithInstall:
    """Tests for status command after install/uninstall operations."""

    @pytest.fixture
    def mock_openclaw_home(self, tmp_path: Path) -> Path:
        """Create a mock OpenClaw home directory."""
        openclaw_home = tmp_path / ".openclaw"
        openclaw_home.mkdir(parents=True)

        # Create VERSION file
        version_file = openclaw_home / "VERSION"
        version_file.write_text("2026.3.1\n")

        # Create config file
        config_file = openclaw_home / "config.json"
        config_file.write_text(json.dumps({"test": True}) + "\n")

        return openclaw_home

    @pytest.fixture
    def isolated_user_home(self, tmp_path: Path) -> Path:
        """Create an isolated user home directory."""
        return tmp_path / "user_home"

    def test_status_after_install_shows_installed(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ):
        """Status should show installed after installation."""
        # Install first
        install_result = install(mock_openclaw_home, user_home=isolated_user_home)
        assert install_result.success

        # Check status
        status = get_install_status(user_home=isolated_user_home)

        assert status["installed"] is True
        assert status["version"] is not None
        assert len(status["components"]) > 0
        for skill_id in MAIN_SKILL_IDS:
            assert f"main-skill:{skill_id}" in status["components"]

    def test_status_after_uninstall_shows_not_installed(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ):
        """Status should show not installed after uninstall."""
        # Install then uninstall
        install(mock_openclaw_home, user_home=isolated_user_home)
        uninstall(openclaw_home=mock_openclaw_home, user_home=isolated_user_home)

        # Check status
        status = get_install_status(user_home=isolated_user_home)

        assert status["installed"] is False
        assert len(status["components"]) == 0

    def test_status_shows_components_after_install(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ):
        """Status should list installed components."""
        install_result = install(mock_openclaw_home, user_home=isolated_user_home)

        status = get_install_status(user_home=isolated_user_home)

        assert status["installed"] is True
        assert len(status["components"]) == len(install_result.components_installed)
        for skill_id in MAIN_SKILL_IDS:
            assert f"main-skill:{skill_id}" in status["components"]

    def test_status_json_lists_main_skill_components(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ):
        """Status --json should expose installed main-skill components."""
        install_result = install(mock_openclaw_home, user_home=isolated_user_home)
        assert install_result.success

        runner = CliRunner(env={"HOME": str(isolated_user_home)})
        result = runner.invoke(cli, ["status", "--json"])
        assert result.exit_code == 0

        status = json.loads(result.output)
        for skill_id in MAIN_SKILL_IDS:
            assert f"main-skill:{skill_id}" in status["components"]

    def test_status_version_matches_install(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ):
        """Status version should match installed version."""
        from openclaw_enhance.constants import VERSION

        install(mock_openclaw_home, user_home=isolated_user_home)

        status = get_install_status(user_home=isolated_user_home)

        assert status["version"] == VERSION


class TestStatusEdgeCases:
    """Tests for status command edge cases."""

    def test_status_with_corrupted_manifest(self, tmp_path: Path):
        """Status should handle corrupted manifest gracefully."""
        from openclaw_enhance.install.manifest import MANIFEST_FILENAME
        from openclaw_enhance.paths import managed_root

        user_home = tmp_path / "user_home"
        target_root = managed_root(user_home)
        target_root.mkdir(parents=True)

        # Create corrupted manifest
        manifest_path = target_root / MANIFEST_FILENAME
        manifest_path.write_text("not valid json {{{")

        status = get_install_status(user_home=user_home)

        # Should handle gracefully
        assert "installed" in status
        assert isinstance(status["installed"], bool)

    def test_status_with_empty_manifest(self, tmp_path: Path):
        """Status should handle empty manifest gracefully."""
        from openclaw_enhance.install.manifest import MANIFEST_FILENAME
        from openclaw_enhance.paths import managed_root

        user_home = tmp_path / "user_home"
        target_root = managed_root(user_home)
        target_root.mkdir(parents=True)

        # Create empty manifest
        manifest_path = target_root / MANIFEST_FILENAME
        manifest_path.write_text("")

        status = get_install_status(user_home=user_home)

        # Should handle gracefully
        assert "installed" in status

    def test_status_with_missing_directory(self, tmp_path: Path):
        """Status should handle missing managed directory."""
        user_home = tmp_path / "nonexistent"

        status = get_install_status(user_home=user_home)

        assert status["installed"] is False
        assert len(status["components"]) == 0


class TestStatusLockDetection:
    """Tests for status lock detection."""

    def test_status_shows_locked_when_install_in_progress(
        self,
        tmp_path: Path,
    ):
        """Status should show locked when install lock is held."""
        from openclaw_enhance.install.lock import InstallLock
        from openclaw_enhance.paths import managed_root

        user_home = tmp_path / "user_home"
        target_root = managed_root(user_home)
        target_root.mkdir(parents=True)

        # Acquire lock
        lock = InstallLock(target_root)
        lock.acquire(operation="test-install")

        try:
            status = get_install_status(user_home=user_home)

            assert status["locked"] is True
            assert status["lock_info"] is not None
            assert status["lock_info"]["operation"] == "test-install"
        finally:
            lock.release()

    def test_status_shows_unlocked_when_no_lock(
        self,
        tmp_path: Path,
    ):
        """Status should show unlocked when no lock exists."""
        from openclaw_enhance.paths import managed_root

        user_home = tmp_path / "user_home"
        target_root = managed_root(user_home)
        target_root.mkdir(parents=True)

        status = get_install_status(user_home=user_home)

        assert status["locked"] is False


class TestStatusInstallTime:
    """Tests for status install time reporting."""

    def test_status_shows_install_time_after_install(
        self,
        tmp_path: Path,
    ):
        """Status should show install time after installation."""
        from datetime import datetime

        from openclaw_enhance.constants import VERSION
        from openclaw_enhance.install.manifest import (
            ComponentInstall,
            InstallManifest,
            save_manifest,
        )
        from openclaw_enhance.paths import managed_root

        user_home = tmp_path / "user_home"
        target_root = managed_root(user_home)
        target_root.mkdir(parents=True)

        # Create a valid manifest
        manifest = InstallManifest(
            version=VERSION,
            install_time=datetime.now(),
            components=[
                ComponentInstall(
                    name="test-component",
                    version=VERSION,
                    install_time=datetime.now(),
                )
            ],
        )

        save_manifest(manifest, target_root)

        status = get_install_status(user_home=user_home)

        assert status["installed"] is True
        assert status["install_time"] is not None

    def test_status_shows_install_time_or_na(self):
        """Status should show a valid install time or N/A."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        if "Install Time:" in result.output:
            # Either N/A (not installed) or a timestamp (installed)
            line = [l for l in result.output.splitlines() if "Install Time:" in l][0]
            value = line.split("Install Time:")[1].strip()
            assert value == "N/A" or len(value) > 10  # ISO timestamp is >10 chars


class TestStatusCommandHelp:
    """Tests for status command help."""

    def test_status_help_exits_zero(self):
        """Status --help should exit 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])

        assert result.exit_code == 0

    def test_status_help_shows_json_option(self):
        """Status help should mention --json option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])

        assert "--json" in result.output or "json" in result.output.lower()


class TestStatusConsistency:
    """Tests for consistency between CLI and programmatic status."""

    def test_cli_and_programmatic_status_match(
        self,
        tmp_path: Path,
    ):
        """CLI and programmatic status should return consistent results."""
        from datetime import datetime

        from openclaw_enhance.constants import VERSION
        from openclaw_enhance.install.manifest import (
            ComponentInstall,
            InstallManifest,
            save_manifest,
        )
        from openclaw_enhance.paths import managed_root

        user_home = tmp_path / "user_home"
        target_root = managed_root(user_home)
        target_root.mkdir(parents=True)

        # Create a valid manifest
        manifest = InstallManifest(
            version=VERSION,
            install_time=datetime.now(),
            components=[
                ComponentInstall(
                    name="test-component",
                    version=VERSION,
                    install_time=datetime.now(),
                )
            ],
        )

        save_manifest(manifest, target_root)

        # Get status programmatically
        prog_status = get_install_status(user_home=user_home)

        # Get status via CLI
        runner = CliRunner(env={"HOME": str(user_home)})
        result = runner.invoke(cli, ["status", "--json"])
        cli_status = json.loads(result.output)

        # Results should match
        assert prog_status["installed"] == cli_status["installed"]
        assert prog_status["version"] == cli_status["version"]
        assert len(prog_status["components"]) == len(cli_status["components"])
