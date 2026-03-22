"""Integration tests for development mode install functionality."""

import json
from pathlib import Path

import pytest

from openclaw_enhance.install import install, uninstall
from openclaw_enhance.install.manifest import load_manifest
from openclaw_enhance.paths import managed_root



class TestDevModeInstall:
    """Tests for development mode installation."""

    def test_dev_mode_install_creates_symlinks(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Dev mode install should create symlinks instead of copying."""
        result = install(
            mock_openclaw_home,
            user_home=isolated_user_home,
            dev_mode=True,
        )

        assert result.success

        # Check that workspaces are symlinks
        target_root = managed_root(isolated_user_home)
        workspaces_dir = target_root / "workspaces"

        if workspaces_dir.exists():
            for workspace in workspaces_dir.iterdir():
                if workspace.name.startswith("."):
                    continue
                # Each workspace should be a symlink
                assert workspace.is_symlink(), f"{workspace} should be a symlink"

    def test_dev_mode_manifest_records_symlinks(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Dev mode should record is_symlink=True in manifest."""
        result = install(
            mock_openclaw_home,
            user_home=isolated_user_home,
            dev_mode=True,
        )

        assert result.success

        target_root = managed_root(isolated_user_home)
        manifest = load_manifest(target_root)

        assert manifest is not None

        # Find workspace components
        workspace_components = [c for c in manifest.components if c.name.startswith("workspace:")]

        # All workspace components should have is_symlink=True
        for component in workspace_components:
            assert component.is_symlink is True, f"{component.name} should have is_symlink=True"

    def test_normal_mode_manifest_records_no_symlinks(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Normal mode should record is_symlink=False in manifest."""
        result = install(
            mock_openclaw_home,
            user_home=isolated_user_home,
            dev_mode=False,
        )

        assert result.success

        target_root = managed_root(isolated_user_home)
        manifest = load_manifest(target_root)

        assert manifest is not None

        # Find workspace components
        workspace_components = [c for c in manifest.components if c.name.startswith("workspace:")]

        # All workspace components should have is_symlink=False
        for component in workspace_components:
            assert component.is_symlink is False, f"{component.name} should have is_symlink=False"


class TestDevModeUninstall:
    """Tests for development mode uninstallation."""

    def test_uninstall_removes_symlinks_not_sources(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Uninstall should remove symlinks but not delete source files."""
        # First, install in dev mode
        install_result = install(
            mock_openclaw_home,
            user_home=isolated_user_home,
            dev_mode=True,
        )
        assert install_result.success

        # Record source paths from manifest
        target_root = managed_root(isolated_user_home)
        manifest = load_manifest(target_root)
        source_paths = []
        for component in manifest.components:
            if component.source_path:
                source_paths.append(Path(component.source_path))

        # Verify sources exist
        for source_path in source_paths:
            assert source_path.exists(), f"Source {source_path} should exist before uninstall"

        # Now uninstall
        uninstall_result = uninstall(
            openclaw_home=mock_openclaw_home,
            user_home=isolated_user_home,
        )
        assert uninstall_result.success

        # Verify sources still exist (not deleted)
        for source_path in source_paths:
            assert source_path.exists(), f"Source {source_path} should still exist after uninstall"

        # Verify targets are removed
        assert not target_root.exists() or not any(target_root.iterdir())

    def test_uninstall_after_dev_mode_is_symmetric(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Install in dev mode then uninstall should leave clean state."""
        # Install
        install_result = install(
            mock_openclaw_home,
            user_home=isolated_user_home,
            dev_mode=True,
        )
        assert install_result.success

        # Uninstall
        uninstall_result = uninstall(
            openclaw_home=mock_openclaw_home,
            user_home=isolated_user_home,
        )
        assert uninstall_result.success

        # Verify clean state
        target_root = managed_root(isolated_user_home)

        # Either target_root doesn't exist or is empty
        if target_root.exists():
            contents = list(target_root.iterdir())
            assert len(contents) == 0, f"Target root should be empty, found: {contents}"


class TestDevModeChangesReflectImmediately:
    """Tests that changes in dev mode reflect immediately."""

    def test_workspace_changes_reflect_without_reinstall(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Changes to source files should reflect in target without reinstall."""
        # Install in dev mode
        result = install(
            mock_openclaw_home,
            user_home=isolated_user_home,
            dev_mode=True,
        )
        assert result.success

        # Modify a source file
        target_root = managed_root(isolated_user_home)
        workspaces_dir = target_root / "workspaces"

        if workspaces_dir.exists():
            for workspace in workspaces_dir.iterdir():
                if workspace.is_symlink():
                    # Find the AGENTS.md in source
                    source_agents = workspace.resolve() / "AGENTS.md"
                    target_agents = workspace / "AGENTS.md"

                    if source_agents.exists():
                        # Modify source
                        original_content = source_agents.read_text()
                        new_content = original_content + "\n# TEST MODIFICATION\n"
                        source_agents.write_text(new_content)

                        # Target should immediately reflect the change
                        assert target_agents.read_text() == new_content

                        # Cleanup
                        source_agents.write_text(original_content)
                        break
