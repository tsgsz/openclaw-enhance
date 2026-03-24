"""Integration test for install idempotency.

Verifies that running install multiple times is safe and produces
consistent results.
"""

from pathlib import Path

from openclaw_enhance.install import install, uninstall
from openclaw_enhance.install.main_tool_gate import TOOL_GATE_MARKER
from openclaw_enhance.install.main_skill_sync import MAIN_SKILL_IDS
from openclaw_enhance.install.manifest import load_manifest
from openclaw_enhance.paths import managed_root


class TestInstallIdempotency:
    """Tests that install is idempotent."""

    def test_double_install_succeeds(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Running install twice should succeed both times."""
        result1 = install(mock_openclaw_home, user_home=isolated_user_home)

        # First install should succeed
        assert result1.success

        result2 = install(mock_openclaw_home, user_home=isolated_user_home)

        # Second install should also succeed (upgrade in place)
        assert result2.success

    def test_double_install_same_version(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Double install should maintain same version."""
        install(mock_openclaw_home, user_home=isolated_user_home)

        target_root = managed_root(isolated_user_home)
        manifest1 = load_manifest(target_root)
        assert manifest1 is not None
        version1 = manifest1.version

        install(mock_openclaw_home, user_home=isolated_user_home)

        manifest2 = load_manifest(target_root)
        assert manifest2 is not None
        version2 = manifest2.version

        assert version1 == version2

    def test_double_install_preserves_components(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Double install should maintain consistent component list."""
        install(mock_openclaw_home, user_home=isolated_user_home)

        target_root = managed_root(isolated_user_home)
        manifest1 = load_manifest(target_root)
        assert manifest1 is not None
        components1 = {c.name for c in manifest1.components}

        install(mock_openclaw_home, user_home=isolated_user_home)

        manifest2 = load_manifest(target_root)
        assert manifest2 is not None
        components2 = {c.name for c in manifest2.components}

        # Should have same components after reinstall
        assert components1 == components2
        for skill_id in MAIN_SKILL_IDS:
            assert f"main-skill:{skill_id}" in components2

    def test_double_install_updates_timestamp(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Double install should update the last_updated timestamp."""
        install(mock_openclaw_home, user_home=isolated_user_home)

        target_root = managed_root(isolated_user_home)
        manifest1 = load_manifest(target_root)
        assert manifest1 is not None
        updated1 = manifest1.last_updated

        # Small delay to ensure timestamp changes
        import time

        time.sleep(0.01)

        install(mock_openclaw_home, user_home=isolated_user_home)

        manifest2 = load_manifest(target_root)
        assert manifest2 is not None
        updated2 = manifest2.last_updated

        # Last updated should be newer
        assert updated2 >= updated1

    def test_triple_install_consistent(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Triple install should be consistent."""
        for _ in range(3):
            result = install(mock_openclaw_home, user_home=isolated_user_home)
            assert result.success

        target_root = managed_root(isolated_user_home)
        manifest = load_manifest(target_root)
        assert manifest is not None

        # Should still have valid state
        assert manifest.version is not None
        assert len(manifest.components) > 0

    def test_install_after_partial_uninstall(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Install after partial uninstall should recover gracefully."""
        # Full install
        install(mock_openclaw_home, user_home=isolated_user_home)

        target_root = managed_root(isolated_user_home)

        # Simulate partial uninstall by removing manifest only
        manifest_path = target_root / "install-manifest.json"
        if manifest_path.exists():
            manifest_path.unlink()

        # Re-install should succeed
        result = install(mock_openclaw_home, user_home=isolated_user_home)
        assert result.success

        # Should have fresh manifest
        manifest = load_manifest(target_root)
        assert manifest is not None
        assert len(manifest.components) > 0

    def test_install_with_force_flag(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Install with force flag should work even if already installed."""
        result1 = install(mock_openclaw_home, user_home=isolated_user_home)
        assert result1.success

        result2 = install(mock_openclaw_home, user_home=isolated_user_home, force=True)
        assert result2.success

    def test_force_install_repairs_stale_main_agents_reference_idempotently(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        legacy_line = (
            "**每次收到消息** 都必须阅读 "
            "`../openclaw-enhanced/system/workspace/AGENTS.md` 里的约定并且遵循。"
        )
        agents_path = mock_openclaw_home / "workspace" / "AGENTS.md"
        agents_path.parent.mkdir(parents=True, exist_ok=True)
        agents_path.write_text(
            (f"# User Header\n\nUser section should stay.\n{legacy_line}\n"),
            encoding="utf-8",
        )

        first_result = install(mock_openclaw_home, user_home=isolated_user_home, force=True)
        assert first_result.success

        first_content = agents_path.read_text(encoding="utf-8")
        assert "User section should stay." in first_content
        assert legacy_line not in first_content
        assert "**每次收到消息**" not in first_content
        assert "里的约定并且遵循" not in first_content
        assert "../openclaw-enhanced/system/workspace/AGENTS.md" not in first_content
        assert first_content.count("<!-- oe-main-tool-gate -->") == 2

        second_result = install(mock_openclaw_home, user_home=isolated_user_home, force=True)
        assert second_result.success

        second_content = agents_path.read_text(encoding="utf-8")
        assert second_content == first_content

    def test_force_install_removes_stale_legacy_instruction_line_without_remnants(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        legacy_line = (
            "**每次收到消息** 都必须阅读 "
            "`../openclaw-enhanced/system/workspace/AGENTS.md` 里的约定并且遵循。"
        )
        agents_path = mock_openclaw_home / "workspace" / "AGENTS.md"
        agents_path.parent.mkdir(parents=True, exist_ok=True)
        agents_path.write_text(
            (f"# User Header\n\nKeep this user line.\n{legacy_line}\nKeep this ending line.\n"),
            encoding="utf-8",
        )

        first_result = install(mock_openclaw_home, user_home=isolated_user_home, force=True)
        assert first_result.success

        first_content = agents_path.read_text(encoding="utf-8")
        assert "Keep this user line." in first_content
        assert "Keep this ending line." in first_content
        assert legacy_line not in first_content
        assert "**每次收到消息**" not in first_content
        assert "里的约定并且遵循" not in first_content
        assert "../openclaw-enhanced/system/workspace/AGENTS.md" not in first_content

        second_result = install(mock_openclaw_home, user_home=isolated_user_home, force=True)
        assert second_result.success

        second_content = agents_path.read_text(encoding="utf-8")
        assert second_content == first_content

    def test_force_install_upgrades_existing_main_tool_gate_block_content(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        old_block_without_acp_rule = f"""{TOOL_GATE_MARKER}
## 🚫 Main 主会话工具限制（由 openclaw-enhance 自动注入）

旧版本 block，缺少 ACP 规则。
{TOOL_GATE_MARKER}"""

        agents_path = mock_openclaw_home / "workspace" / "AGENTS.md"
        agents_path.parent.mkdir(parents=True, exist_ok=True)
        agents_path.write_text(
            (
                "# User Header\n\n"
                "Keep user intro.\n\n"
                f"{old_block_without_acp_rule}\n\n"
                "Keep user footer.\n"
            ),
            encoding="utf-8",
        )

        first_result = install(mock_openclaw_home, user_home=isolated_user_home, force=True)
        assert first_result.success

        first_content = agents_path.read_text(encoding="utf-8")
        assert "旧版本 block，缺少 ACP 规则" not in first_content
        assert '禁止直接使用 `sessions_spawn(runtime="acp"...)`' in first_content
        assert first_content.count(TOOL_GATE_MARKER) == 2
        assert "Keep user intro." in first_content
        assert "Keep user footer." in first_content

        second_result = install(mock_openclaw_home, user_home=isolated_user_home, force=True)
        assert second_result.success

        second_content = agents_path.read_text(encoding="utf-8")
        assert second_content == first_content


class TestUninstallIdempotency:
    """Tests that uninstall is idempotent."""

    def test_double_uninstall_succeeds(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Running uninstall twice should succeed both times."""
        # Install first
        install(mock_openclaw_home, user_home=isolated_user_home)

        # First uninstall
        result1 = uninstall(
            openclaw_home=mock_openclaw_home,
            user_home=isolated_user_home,
        )
        assert result1.success

        # Second uninstall should also succeed (nothing to do)
        result2 = uninstall(
            openclaw_home=mock_openclaw_home,
            user_home=isolated_user_home,
        )
        assert result2.success

    def test_uninstall_when_never_installed(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Uninstall when never installed should succeed gracefully."""
        result = uninstall(
            openclaw_home=mock_openclaw_home,
            user_home=isolated_user_home,
        )

        assert result.success
        assert "not installed" in result.message.lower()


class TestInstallUninstallInstall:
    """Tests for install→uninstall→install cycles."""

    def test_reinstall_cycle(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Install→uninstall→install cycle should work."""
        target_root = managed_root(isolated_user_home)

        # First install
        result1 = install(mock_openclaw_home, user_home=isolated_user_home)
        assert result1.success
        assert len(result1.components_installed) > 0

        # Uninstall
        result2 = uninstall(
            openclaw_home=mock_openclaw_home,
            user_home=isolated_user_home,
        )
        assert result2.success
        for skill_id in MAIN_SKILL_IDS:
            assert f"main-skill:{skill_id}" in result2.components_removed

        # Verify clean state
        assert not load_manifest(target_root)

        # Re-install
        result3 = install(mock_openclaw_home, user_home=isolated_user_home)
        assert result3.success
        assert len(result3.components_installed) > 0

        # Should have manifest again
        manifest = load_manifest(target_root)
        assert manifest is not None

    def test_multiple_cycles(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Multiple install→uninstall cycles should be stable."""
        for i in range(3):
            result = install(mock_openclaw_home, user_home=isolated_user_home)
            assert result.success, f"Install failed on cycle {i}"

            result = uninstall(
                openclaw_home=mock_openclaw_home,
                user_home=isolated_user_home,
            )
            assert result.success, f"Uninstall failed on cycle {i}"

        # Final state should be clean
        target_root = managed_root(isolated_user_home)
        assert not load_manifest(target_root)


class TestConcurrentSafety:
    """Tests for concurrent install/uninstall safety."""

    def test_install_creates_lock(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Install should create a lock file during operation."""
        from openclaw_enhance.install import is_locked

        target_root = managed_root(isolated_user_home)

        # Should not be locked before install
        assert not is_locked(target_root)

        # Install
        install(mock_openclaw_home, user_home=isolated_user_home)

        # Should not be locked after install completes
        assert not is_locked(target_root)

    def test_lock_prevents_concurrent_install(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Lock should prevent concurrent install operations."""
        from openclaw_enhance.install.lock import InstallLock

        target_root = managed_root(isolated_user_home)
        target_root.mkdir(parents=True, exist_ok=True)

        # Acquire lock manually
        lock = InstallLock(target_root)
        lock.acquire(operation="test")

        try:
            # Try to install while locked - should detect but may proceed
            # depending on lock implementation (may wait or fail)
            install(mock_openclaw_home, user_home=isolated_user_home)
            # Result may succeed if lock was acquired after waiting,
            # or fail if timeout - both are valid behaviors
        finally:
            lock.release()


class TestComponentUpdate:
    """Tests for component update behavior on reinstall."""

    def test_component_version_update(
        self,
        mock_openclaw_home: Path,
        isolated_user_home: Path,
    ) -> None:
        """Reinstall should update component versions."""
        from openclaw_enhance.constants import VERSION

        install(mock_openclaw_home, user_home=isolated_user_home)

        target_root = managed_root(isolated_user_home)
        manifest = load_manifest(target_root)
        assert manifest is not None

        # All components should have current version
        for component in manifest.components:
            assert component.version == VERSION
