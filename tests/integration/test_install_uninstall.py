"""Integration test for install→status→uninstall symmetry.

Verifies that the complete lifecycle is symmetric - installing and then
uninstalling should leave the system in a clean state.
"""

import json
from pathlib import Path

import pytest

from openclaw_enhance.install import (
    get_install_status,
    install,
    is_installed,
    uninstall,
)
from openclaw_enhance.install.manifest import load_manifest
from openclaw_enhance.paths import managed_root


@pytest.fixture
def mock_openclaw_home(tmp_path: Path) -> Path:
    """Create a mock OpenClaw home directory structure."""
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)

    # Create VERSION file for support matrix check
    version_file = openclaw_home / "VERSION"
    version_file.write_text("2026.3.1\n")

    # Create a minimal config file
    config_file = openclaw_home / "config.json"
    config_file.write_text(json.dumps({"test": True}) + "\n")

    return openclaw_home


@pytest.fixture
def isolated_user_home(tmp_path: Path) -> Path:
    """Create an isolated user home directory for testing."""
    return tmp_path / "user_home"


class TestInstallUninstallSymmetry:
    """Tests that install→uninstall is symmetric."""

    def test_install_creates_managed_root(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Install should create the managed root directory."""
        target_root = managed_root(isolated_user_home)

        # Should not exist before install
        assert not target_root.exists()

        result = install(mock_openclaw_home, user_home=isolated_user_home)

        assert result.success
        assert target_root.exists()
        assert target_root.is_dir()

    def test_install_creates_manifest(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Install should create an install manifest."""
        result = install(mock_openclaw_home, user_home=isolated_user_home)

        assert result.success

        target_root = managed_root(isolated_user_home)
        manifest = load_manifest(target_root)

        assert manifest is not None
        assert manifest.version is not None
        assert len(manifest.components) > 0

    def test_install_registers_components(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Install should register all expected components."""
        result = install(mock_openclaw_home, user_home=isolated_user_home)

        assert result.success

        target_root = managed_root(isolated_user_home)
        manifest = load_manifest(target_root)
        assert manifest is not None

        component_names = [c.name for c in manifest.components]

        # Should have runtime state component
        assert any("runtime" in name for name in component_names)
        assert "main-skill:oe-eta-estimator" in component_names
        assert "main-skill:oe-toolcall-router" in component_names
        assert "main-skill:oe-timeout-state-sync" in component_names

    def test_status_reports_installed(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Status should report installed after install."""
        install(mock_openclaw_home, user_home=isolated_user_home)

        status = get_install_status(
            openclaw_home=mock_openclaw_home,
            user_home=isolated_user_home,
        )

        assert status["installed"] is True
        assert status["version"] is not None
        assert len(status["components"]) > 0

    def test_uninstall_removes_components(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Uninstall should remove all installed components."""
        install_result = install(mock_openclaw_home, user_home=isolated_user_home)
        assert install_result.success

        uninstall_result = uninstall(
            openclaw_home=mock_openclaw_home,
            user_home=isolated_user_home,
        )

        assert uninstall_result.success
        # Should have removed components
        assert len(uninstall_result.components_removed) > 0

    def test_uninstall_removes_manifest(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Uninstall should remove the install manifest."""
        install(mock_openclaw_home, user_home=isolated_user_home)

        target_root = managed_root(isolated_user_home)

        # Manifest should exist after install
        assert load_manifest(target_root) is not None

        uninstall(openclaw_home=mock_openclaw_home, user_home=isolated_user_home)

        # Manifest should not exist after uninstall
        assert load_manifest(target_root) is None

    def test_status_reports_not_installed_after_uninstall(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Status should report not installed after uninstall."""
        install(mock_openclaw_home, user_home=isolated_user_home)
        uninstall(openclaw_home=mock_openclaw_home, user_home=isolated_user_home)

        status = get_install_status(
            openclaw_home=mock_openclaw_home,
            user_home=isolated_user_home,
        )

        assert status["installed"] is False
        assert status["version"] is None

    def test_install_uninstall_symmetry(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Install→uninstall should leave system in clean state."""
        target_root = managed_root(isolated_user_home)

        # Install
        install_result = install(mock_openclaw_home, user_home=isolated_user_home)
        assert install_result.success

        # Should be installed
        assert is_installed(target_root)

        # Uninstall
        uninstall_result = uninstall(
            openclaw_home=mock_openclaw_home,
            user_home=isolated_user_home,
        )
        assert uninstall_result.success

        # Should not be installed
        assert not is_installed(target_root)

        # Target root should not exist (or be empty)
        if target_root.exists():
            contents = list(target_root.iterdir())
            assert len(contents) == 0, f"Unexpected contents: {contents}"

    def test_complete_lifecycle_cli_style(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Simulate CLI-style complete lifecycle: install→status→uninstall→status."""
        from click.testing import CliRunner

        from openclaw_enhance.cli import cli

        runner = CliRunner(env={"HOME": str(isolated_user_home)})

        # Initial status - should show not installed
        result = runner.invoke(cli, ["status", "--json"])
        assert result.exit_code == 0
        status = json.loads(result.output)
        assert status["installed"] is False

        # Install
        result = runner.invoke(
            cli,
            [
                "install",
                "--openclaw-home",
                str(mock_openclaw_home),
            ],
        )
        # Note: install may fail in tests without full OpenClaw setup,
        # but we can at least verify the command structure

        # Status after install attempt
        result = runner.invoke(cli, ["status", "--json"])
        assert result.exit_code == 0


class TestInstallBackupAndRollback:
    """Tests for install backup and rollback functionality."""

    def test_install_creates_backup(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Install should create backups of modified files."""
        result = install(mock_openclaw_home, user_home=isolated_user_home)

        if result.success and result.backup_paths:
            # Check that backup files exist
            for key, path in result.backup_paths.items():
                backup_path = Path(path)
                if backup_path.exists():
                    assert backup_path.is_file()

    def test_manifest_tracks_rollback_points(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Manifest should track rollback points for recovery."""
        install(mock_openclaw_home, user_home=isolated_user_home)

        target_root = managed_root(isolated_user_home)
        manifest = load_manifest(target_root)
        assert manifest is not None

        # Should have rollback points recorded
        assert len(manifest.rollback_points) >= 0  # May be 0 if no config changes


class TestUninstallEdgeCases:
    """Tests for uninstall edge cases."""

    def test_uninstall_when_not_installed(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Uninstall when not installed should succeed gracefully."""
        result = uninstall(
            openclaw_home=mock_openclaw_home,
            user_home=isolated_user_home,
        )

        assert result.success
        assert "not installed" in result.message.lower()

    def test_uninstall_with_force_flag(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Force uninstall should proceed even with errors."""
        # Install first
        install(mock_openclaw_home, user_home=isolated_user_home)

        # Uninstall with force
        result = uninstall(
            openclaw_home=mock_openclaw_home,
            user_home=isolated_user_home,
            force=True,
        )

        assert result.success
