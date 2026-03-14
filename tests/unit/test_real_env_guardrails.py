"""Unit tests for baseline state capture and cleanup verification."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from openclaw_enhance.validation.guardrails import (
    BaselineState,
    ForeignStateError,
    capture_baseline_state,
    verify_cleanup_success,
    verify_ownership,
)


@pytest.fixture
def mock_openclaw_home(tmp_path):
    """Create mock OpenClaw home directory."""
    home = tmp_path / ".openclaw"
    home.mkdir()
    return home


@pytest.fixture
def mock_managed_root(tmp_path):
    """Create mock managed root directory."""
    root = tmp_path / ".openclaw" / "openclaw-enhance"
    root.mkdir(parents=True)
    return root


def test_capture_baseline_state_not_installed(mock_openclaw_home):
    """Test capturing baseline when not installed."""
    with patch("openclaw_enhance.validation.guardrails.managed_root") as mock_root:
        mock_root.return_value = mock_openclaw_home / "openclaw-enhance"
        with patch("openclaw_enhance.validation.guardrails.load_manifest") as mock_load:
            mock_load.return_value = None

            state = capture_baseline_state(mock_openclaw_home)

            assert state.openclaw_home == mock_openclaw_home
            assert not state.is_installed
            assert state.owned_by_checkout


def test_capture_baseline_state_installed_owned(mock_openclaw_home, mock_managed_root):
    """Test capturing baseline when installed and owned."""
    # Create symlink to indicate dev mode
    workspaces_dir = mock_managed_root / "workspaces"
    workspaces_dir.mkdir()
    workspace_link = workspaces_dir / "oe-orchestrator"
    workspace_link.symlink_to(mock_openclaw_home / "src")

    with patch("openclaw_enhance.validation.guardrails.managed_root") as mock_root:
        mock_root.return_value = mock_managed_root
        with patch("openclaw_enhance.validation.guardrails.load_manifest") as mock_load:
            mock_manifest = MagicMock()
            mock_load.return_value = mock_manifest

            state = capture_baseline_state(mock_openclaw_home)

            assert state.is_installed
            assert state.owned_by_checkout


def test_capture_baseline_state_installed_foreign(mock_openclaw_home, mock_managed_root):
    """Test capturing baseline when installed but foreign."""
    # No symlinks, indicates production install from different checkout
    workspaces_dir = mock_managed_root / "workspaces"
    workspaces_dir.mkdir()
    (workspaces_dir / "oe-orchestrator").mkdir()

    with patch("openclaw_enhance.validation.guardrails.managed_root") as mock_root:
        mock_root.return_value = mock_managed_root
        with patch("openclaw_enhance.validation.guardrails.load_manifest") as mock_load:
            mock_manifest = MagicMock()
            mock_load.return_value = mock_manifest

            state = capture_baseline_state(mock_openclaw_home)

            assert state.is_installed
            assert not state.owned_by_checkout


def test_capture_config_state_exists(mock_openclaw_home):
    """Test capturing config state when config exists."""
    config_path = mock_openclaw_home / "config.json"
    config_path.write_text('{"openclawEnhance": {"agents": {"enabled": true}}}')

    with patch("openclaw_enhance.validation.guardrails.managed_root") as mock_root:
        mock_root.return_value = mock_openclaw_home / "openclaw-enhance"
        with patch("openclaw_enhance.validation.guardrails.load_manifest") as mock_load:
            mock_load.return_value = None

            state = capture_baseline_state(mock_openclaw_home)

            assert state.config_state["exists"]
            assert state.config_state["has_enhance_namespace"]


def test_verify_ownership_owned(mock_openclaw_home):
    """Test verify_ownership with owned state."""
    state = BaselineState(
        openclaw_home=mock_openclaw_home,
        is_installed=True,
        owned_by_checkout=True,
        config_state={},
        managed_root_state={},
    )

    assert verify_ownership(state)


def test_verify_ownership_foreign_raises(mock_openclaw_home):
    """Test verify_ownership raises on foreign state."""
    state = BaselineState(
        openclaw_home=mock_openclaw_home,
        is_installed=True,
        owned_by_checkout=False,
        config_state={},
        managed_root_state={},
    )

    with pytest.raises(ForeignStateError, match="foreign state"):
        verify_ownership(state)


def test_verify_cleanup_success_not_installed(mock_openclaw_home):
    """Test cleanup verification when not installed initially."""
    initial = BaselineState(
        openclaw_home=mock_openclaw_home,
        is_installed=False,
        owned_by_checkout=True,
        config_state={},
        managed_root_state={},
    )
    final = BaselineState(
        openclaw_home=mock_openclaw_home,
        is_installed=False,
        owned_by_checkout=True,
        config_state={},
        managed_root_state={},
    )

    assert verify_cleanup_success(initial, final)


def test_verify_cleanup_success_owned_cleaned(mock_openclaw_home):
    """Test cleanup verification when owned and cleaned."""
    initial = BaselineState(
        openclaw_home=mock_openclaw_home,
        is_installed=True,
        owned_by_checkout=True,
        config_state={},
        managed_root_state={},
    )
    final = BaselineState(
        openclaw_home=mock_openclaw_home,
        is_installed=False,
        owned_by_checkout=True,
        config_state={},
        managed_root_state={},
    )

    assert verify_cleanup_success(initial, final)


def test_verify_cleanup_success_foreign_unchanged(mock_openclaw_home):
    """Test cleanup verification leaves foreign state unchanged."""
    initial = BaselineState(
        openclaw_home=mock_openclaw_home,
        is_installed=True,
        owned_by_checkout=False,
        config_state={"exists": True},
        managed_root_state={},
    )
    final = BaselineState(
        openclaw_home=mock_openclaw_home,
        is_installed=True,
        owned_by_checkout=False,
        config_state={"exists": True},
        managed_root_state={},
    )

    assert verify_cleanup_success(initial, final)
