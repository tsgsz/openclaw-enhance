from pathlib import Path

from openclaw_enhance.monitor_runtime import resolve_user_home


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
