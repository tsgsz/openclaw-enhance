import os
import plistlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from openclaw_enhance.install import install, uninstall


def _mock_launchctl_run() -> MagicMock:
    return MagicMock(returncode=0, stdout="", stderr="")


@pytest.fixture
def mock_openclaw_home(tmp_path: Path) -> Path:
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)
    (openclaw_home / "VERSION").write_text("2026.3.1\n", encoding="utf-8")
    (openclaw_home / "config.json").write_text('{"test": true}\n', encoding="utf-8")
    return openclaw_home


@pytest.fixture
def isolated_user_home(tmp_path: Path) -> Path:
    return tmp_path / "user_home"


def test_install_registers_monitor_launchagent_on_macos(
    mock_openclaw_home: Path,
    isolated_user_home: Path,
) -> None:
    with patch.object(sys, "platform", "darwin"):
        with patch("openclaw_enhance.install.monitor_service.subprocess.run") as mock_run:
            mock_run.return_value = _mock_launchctl_run()

            result = install(mock_openclaw_home, user_home=isolated_user_home)

    assert result.success
    assert "monitor:launchagent" in result.components_installed

    plist_path = (
        isolated_user_home / "Library" / "LaunchAgents" / "ai.openclaw.enhance.monitor.plist"
    )
    assert plist_path.exists()

    payload = plistlib.loads(plist_path.read_bytes())
    assert payload["Label"] == "ai.openclaw.enhance.monitor"
    assert payload["RunAtLoad"] is True
    assert payload["StartInterval"] == 60
    assert payload["ProgramArguments"][:3] == [
        sys.executable,
        "-m",
        "openclaw_enhance.monitor_runtime",
    ]
    assert str(mock_openclaw_home) in payload["ProgramArguments"]
    assert str(isolated_user_home / ".openclaw" / "openclaw-enhance") in payload["ProgramArguments"]

    commands = [call.args[0] for call in mock_run.call_args_list]
    assert ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)] in commands
    assert [
        "launchctl",
        "kickstart",
        "-k",
        f"gui/{os.getuid()}/ai.openclaw.enhance.monitor",
    ] in commands


def test_uninstall_removes_monitor_launchagent_on_macos(
    mock_openclaw_home: Path,
    isolated_user_home: Path,
) -> None:
    with patch.object(sys, "platform", "darwin"):
        with patch("openclaw_enhance.install.monitor_service.subprocess.run") as mock_run:
            mock_run.return_value = _mock_launchctl_run()
            install_result = install(mock_openclaw_home, user_home=isolated_user_home)
            assert install_result.success

            uninstall_result = uninstall(
                openclaw_home=mock_openclaw_home,
                user_home=isolated_user_home,
            )

    assert uninstall_result.success
    assert "monitor:launchagent" in uninstall_result.components_removed

    plist_path = (
        isolated_user_home / "Library" / "LaunchAgents" / "ai.openclaw.enhance.monitor.plist"
    )
    assert not plist_path.exists()

    commands = [call.args[0] for call in mock_run.call_args_list]
    assert ["launchctl", "bootout", f"gui/{os.getuid()}/ai.openclaw.enhance.monitor"] in commands


def test_uninstall_removes_monitor_logs_on_macos(
    mock_openclaw_home: Path,
    isolated_user_home: Path,
) -> None:
    with patch.object(sys, "platform", "darwin"):
        with patch("openclaw_enhance.install.monitor_service.subprocess.run") as mock_run:
            mock_run.return_value = _mock_launchctl_run()
            install_result = install(mock_openclaw_home, user_home=isolated_user_home)
            assert install_result.success

            logs_dir = isolated_user_home / ".openclaw" / "openclaw-enhance" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            (logs_dir / "monitor.log").write_text("monitor output\n", encoding="utf-8")
            (logs_dir / "monitor.err.log").write_text("monitor error\n", encoding="utf-8")

            uninstall_result = uninstall(
                openclaw_home=mock_openclaw_home,
                user_home=isolated_user_home,
            )

    assert uninstall_result.success
    assert not (logs_dir / "monitor.log").exists()
    assert not (logs_dir / "monitor.err.log").exists()


def test_install_rolls_back_monitor_launchagent_when_manifest_save_fails(
    mock_openclaw_home: Path,
    isolated_user_home: Path,
) -> None:
    with patch.object(sys, "platform", "darwin"):
        with patch("openclaw_enhance.install.monitor_service.subprocess.run") as mock_run:
            mock_run.return_value = _mock_launchctl_run()
            with patch("openclaw_enhance.install.installer.save_manifest") as mock_save:
                mock_save.side_effect = OSError("disk full")

                result = install(mock_openclaw_home, user_home=isolated_user_home)

    assert result.success is False
    plist_path = (
        isolated_user_home / "Library" / "LaunchAgents" / "ai.openclaw.enhance.monitor.plist"
    )
    assert not plist_path.exists()


def test_uninstall_cleans_orphaned_monitor_launchagent_without_manifest(
    mock_openclaw_home: Path,
    isolated_user_home: Path,
) -> None:
    plist_path = (
        isolated_user_home / "Library" / "LaunchAgents" / "ai.openclaw.enhance.monitor.plist"
    )
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist_path.write_text("orphaned plist\n", encoding="utf-8")

    logs_dir = isolated_user_home / ".openclaw" / "openclaw-enhance" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "monitor.log").write_text("monitor output\n", encoding="utf-8")

    with patch.object(sys, "platform", "darwin"):
        with patch("openclaw_enhance.install.monitor_service.subprocess.run") as mock_run:
            mock_run.return_value = _mock_launchctl_run()
            result = uninstall(
                openclaw_home=mock_openclaw_home,
                user_home=isolated_user_home,
            )

    assert result.success
    assert "monitor:launchagent" in result.components_removed
    assert not plist_path.exists()
    assert not (logs_dir / "monitor.log").exists()
