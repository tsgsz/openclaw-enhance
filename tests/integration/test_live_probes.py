"""Tests for live validation probes."""

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from openclaw_enhance.validation.live_probes import cli


@pytest.fixture
def mock_openclaw_home(tmp_path: Path) -> Path:
    """Create a mock OpenClaw home directory."""
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)
    return openclaw_home


def test_dev_symlink_probe_fails_when_no_symlinks(mock_openclaw_home: Path):
    """Probe should fail if no symlinks are found in workspaces."""
    workspaces_dir = mock_openclaw_home / "openclaw-enhance" / "workspaces"
    workspaces_dir.mkdir(parents=True)

    # Create a regular directory instead of a symlink
    (workspaces_dir / "oe-orchestrator").mkdir()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dev-symlink",
            "--openclaw-home",
            str(mock_openclaw_home),
            "--workspace",
            "oe-orchestrator",
        ],
    )

    assert result.exit_code != 0
    assert '"reason": "workspace_not_symlink"' in result.output


def test_dev_symlink_probe_succeeds_with_symlink(mock_openclaw_home: Path, tmp_path: Path):
    """Probe should succeed and print paths if symlink exists."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    workspaces_dir = mock_openclaw_home / "openclaw-enhance" / "workspaces"
    workspaces_dir.mkdir(parents=True)

    target_link = workspaces_dir / "oe-orchestrator"
    os.symlink(source_dir, target_link)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dev-symlink",
            "--openclaw-home",
            str(mock_openclaw_home),
            "--workspace",
            "oe-orchestrator",
        ],
    )

    assert result.exit_code == 0
    assert str(target_link) in result.output
    assert str(source_dir) in result.output
