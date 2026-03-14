"""Tests for development mode install functionality."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from openclaw_enhance.install.installer import _sync_workspaces, preflight_checks
from openclaw_enhance.install.main_skill_sync import sync_main_skills
from openclaw_enhance.install.manifest import ComponentInstall, InstallManifest


class TestPreflightChecks:
    """Tests for preflight_checks with dev_mode."""

    def test_dev_mode_blocked_on_windows(self, tmp_path):
        """Test that dev mode is blocked on Windows."""
        with patch.object(sys, "platform", "win32"):
            with patch("openclaw_enhance.install.installer.validate_environment") as mock_validate:
                mock_validate.return_value = None

                result = preflight_checks(
                    openclaw_home=tmp_path / ".openclaw",
                    dev_mode=True,
                )

                assert result.passed is False
                assert "Windows" in result.errors[0]
                assert "not supported" in result.errors[0]

    def test_dev_mode_allowed_on_darwin(self, tmp_path):
        """Test that dev mode is allowed on macOS."""
        with patch.object(sys, "platform", "darwin"):
            with patch("openclaw_enhance.install.installer.validate_environment") as mock_validate:
                mock_validate.return_value = None

                result = preflight_checks(
                    openclaw_home=tmp_path / ".openclaw",
                    dev_mode=True,
                )

                # Should not fail due to dev_mode
                assert "Windows" not in str(result.errors)

    def test_dev_mode_allowed_on_linux(self, tmp_path):
        """Test that dev mode is allowed on Linux."""
        with patch.object(sys, "platform", "linux"):
            with patch("openclaw_enhance.install.installer.validate_environment") as mock_validate:
                mock_validate.return_value = None

                result = preflight_checks(
                    openclaw_home=tmp_path / ".openclaw",
                    dev_mode=True,
                )

                # Should not fail due to dev_mode
                assert "Windows" not in str(result.errors)


class TestSyncWorkspaces:
    """Tests for _sync_workspaces with dev_mode."""

    def test_sync_workspaces_creates_symlinks_in_dev_mode(self, tmp_path):
        """Test that _sync_workspaces creates symlinks when dev_mode=True."""
        # Create mock source workspace
        source_workspace = tmp_path / "source" / "workspaces" / "test-workspace"
        source_workspace.mkdir(parents=True)
        (source_workspace / "AGENTS.md").write_text("# Test")

        manifest = InstallManifest()
        target_root = tmp_path / "target"

        with patch(
            "openclaw_enhance.install.installer.WORKSPACES_DIR",
            source_workspace.parent,
        ):
            with patch("openclaw_enhance.install.installer.list_workspaces") as mock_list:
                mock_list.return_value = ["test-workspace"]

                components = _sync_workspaces(
                    manifest=manifest,
                    target_root=target_root,
                    dev_mode=True,
                )

        # Check that symlink was created
        target_path = target_root / "workspaces" / "test-workspace"
        assert target_path.is_symlink()
        assert target_path.resolve() == source_workspace.resolve()

        # Check component has is_symlink=True
        assert len(components) == 1
        assert components[0].is_symlink is True
        assert components[0].name == "workspace:test-workspace"

    def test_sync_workspaces_copies_in_production_mode(self, tmp_path):
        """Test that _sync_workspaces copies files when dev_mode=False."""
        # Create mock source workspace
        source_workspace = tmp_path / "source" / "workspaces" / "test-workspace"
        source_workspace.mkdir(parents=True)
        (source_workspace / "AGENTS.md").write_text("# Test")

        manifest = InstallManifest()
        target_root = tmp_path / "target"

        with patch(
            "openclaw_enhance.install.installer.WORKSPACES_DIR",
            source_workspace.parent,
        ):
            with patch("openclaw_enhance.install.installer.list_workspaces") as mock_list:
                mock_list.return_value = ["test-workspace"]

                components = _sync_workspaces(
                    manifest=manifest,
                    target_root=target_root,
                    dev_mode=False,
                )

        # Check that directory was copied (not symlink)
        target_path = target_root / "workspaces" / "test-workspace"
        assert target_path.exists()
        assert not target_path.is_symlink()
        assert (target_path / "AGENTS.md").exists()

        # Check component has is_symlink=False
        assert len(components) == 1
        assert components[0].is_symlink is False

    def test_sync_workspaces_removes_existing_symlink(self, tmp_path):
        """Test that _sync_workspaces removes existing symlink before creating new one."""
        source_workspace = tmp_path / "source" / "workspaces" / "test-workspace"
        source_workspace.mkdir(parents=True)
        (source_workspace / "AGENTS.md").write_text("# Test")

        # Create existing symlink
        target_root = tmp_path / "target"
        target_path = target_root / "workspaces" / "test-workspace"
        target_path.parent.mkdir(parents=True)
        target_path.symlink_to(tmp_path / "old-location")

        manifest = InstallManifest()

        with patch(
            "openclaw_enhance.install.installer.WORKSPACES_DIR",
            source_workspace.parent,
        ):
            with patch("openclaw_enhance.install.installer.list_workspaces") as mock_list:
                mock_list.return_value = ["test-workspace"]

                _sync_workspaces(
                    manifest=manifest,
                    target_root=target_root,
                    dev_mode=True,
                )

        # Check that new symlink points to correct location
        assert target_path.is_symlink()
        assert target_path.resolve() == source_workspace.resolve()


class TestComponentInstall:
    """Tests for ComponentInstall with is_symlink field."""

    def test_component_install_default_is_symlink_false(self):
        """Test that is_symlink defaults to False."""
        from datetime import datetime

        component = ComponentInstall(
            name="test",
            version="1.0.0",
            install_time=datetime.utcnow(),
        )

        assert component.is_symlink is False

    def test_component_install_can_set_is_symlink_true(self):
        """Test that is_symlink can be set to True."""
        from datetime import datetime

        component = ComponentInstall(
            name="test",
            version="1.0.0",
            install_time=datetime.utcnow(),
            is_symlink=True,
        )

        assert component.is_symlink is True

    def test_component_install_serialization_includes_is_symlink(self):
        """Test that is_symlink is included in serialization."""
        from datetime import datetime

        component = ComponentInstall(
            name="test",
            version="1.0.0",
            install_time=datetime.utcnow(),
            is_symlink=True,
        )

        data = component.to_dict()
        assert "is_symlink" in data
        assert data["is_symlink"] is True

    def test_component_install_deserialization_defaults_is_symlink_false(self):
        """Test that deserialization defaults is_symlink to False for old data."""
        data = {
            "name": "test",
            "version": "1.0.0",
            "install_time": "2024-01-01T00:00:00",
        }

        component = ComponentInstall.from_dict(data)
        assert component.is_symlink is False

    def test_component_install_deserialization_reads_is_symlink(self):
        """Test that deserialization reads is_symlink from data."""
        data = {
            "name": "test",
            "version": "1.0.0",
            "install_time": "2024-01-01T00:00:00",
            "is_symlink": True,
        }

        component = ComponentInstall.from_dict(data)
        assert component.is_symlink is True
