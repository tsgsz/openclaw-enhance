from pathlib import Path

from openclaw_enhance import paths


def test_managed_root_is_under_openclaw_home() -> None:
    fake_home = Path("/tmp/test-home")

    actual = paths.managed_root(fake_home)

    assert actual == fake_home / ".openclaw" / "openclaw-enhance"


def test_config_file_and_runtime_state_paths_use_managed_root() -> None:
    fake_home = Path("/tmp/another-home")

    assert paths.runtime_state_file(fake_home) == (
        fake_home / ".openclaw" / "openclaw-enhance" / "runtime-state.json"
    )
    assert paths.config_backup_file(fake_home) == (
        fake_home / ".openclaw" / "openclaw-enhance" / "config.json.bak"
    )


def test_ensure_managed_directories_creates_root(tmp_path: Path) -> None:
    fake_home = tmp_path / "home"
    root = paths.managed_root(fake_home)

    created = paths.ensure_managed_directories(fake_home)

    assert created == root
    assert root.exists()
    assert root.is_dir()
