from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from openclaw_enhance.monitor_runtime import main, resolve_user_home


def test_resolve_user_home_from_openclaw_home() -> None:
    openclaw_home = Path("/tmp/example/.openclaw")

    resolved = resolve_user_home(openclaw_home=openclaw_home, state_root=None)

    assert resolved == Path("/tmp/example").resolve()


def test_resolve_user_home_from_state_root() -> None:
    state_root = Path("/tmp/example/.openclaw/openclaw-enhance")

    resolved = resolve_user_home(openclaw_home=None, state_root=state_root)

    assert resolved == Path("/tmp/example").resolve()


def test_resolve_user_home_defaults_to_none() -> None:
    assert resolve_user_home(openclaw_home=None, state_root=None) is None


def test_main_runs_cleanup_after_monitor_mode() -> None:
    args = Namespace(
        verbose=False,
        process_pending=False,
        openclaw_home=None,
        state_root=None,
        default_timeout=300,
        grace_period=60,
        check_interval=60,
        once=True,
    )

    with patch("openclaw_enhance.monitor_runtime.parse_args", return_value=args):
        with patch("openclaw_enhance.monitor_runtime.setup_detector") as mock_setup:
            with patch("openclaw_enhance.monitor_runtime.run_monitor_mode", return_value=0):
                with patch(
                    "openclaw_enhance.monitor_runtime.run_cleanup_mode",
                    return_value=0,
                ) as mock_cleanup:
                    mock_setup.return_value = MagicMock()
                    exit_code = main()

    assert exit_code == 0
    mock_cleanup.assert_called_once_with(args)
