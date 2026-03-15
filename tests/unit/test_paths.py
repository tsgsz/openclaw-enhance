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


def test_resolve_main_workspace_prefers_agent_workspace() -> None:
    openclaw_home = Path("/tmp/openclaw-home")
    config = {
        "agent": {"workspace": "~/custom-agent-workspace"},
        "agents": {"defaults": {"workspace": "~/default-workspace"}},
    }

    resolved = paths.resolve_main_workspace(
        openclaw_home, config=config, env={"OPENCLAW_PROFILE": "dev"}
    )

    assert resolved == Path.home() / "custom-agent-workspace"


def test_resolve_main_workspace_uses_agents_defaults_workspace() -> None:
    openclaw_home = Path("/tmp/openclaw-home")
    config = {"agents": {"defaults": {"workspace": "~/agents-default-workspace"}}}

    resolved = paths.resolve_main_workspace(openclaw_home, config=config, env={})

    assert resolved == Path.home() / "agents-default-workspace"


def test_resolve_main_workspace_uses_profile_fallback() -> None:
    openclaw_home = Path("/tmp/openclaw-home")

    resolved = paths.resolve_main_workspace(
        openclaw_home, config={}, env={"OPENCLAW_PROFILE": "staging"}
    )

    assert resolved == openclaw_home / "workspace-staging"


def test_resolve_main_workspace_uses_plain_fallback_for_default_profile() -> None:
    openclaw_home = Path("/tmp/openclaw-home")

    resolved = paths.resolve_main_workspace(
        openclaw_home, config={}, env={"OPENCLAW_PROFILE": "default"}
    )

    assert resolved == openclaw_home / "workspace"


def test_resolve_main_workspace_uses_plain_fallback_without_profile() -> None:
    openclaw_home = Path("/tmp/openclaw-home")

    resolved = paths.resolve_main_workspace(openclaw_home, config={}, env={})

    assert resolved == openclaw_home / "workspace"


def test_main_workspace_skills_dir_does_not_create_directories(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace-does-not-exist"

    skills_dir = paths.main_workspace_skills_dir(workspace)

    assert skills_dir == workspace / "skills"
    assert not workspace.exists()
    assert not skills_dir.exists()


def test_resolve_openclaw_config_path_prefers_openclaw_json(tmp_path: Path) -> None:
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir()

    openclaw_json = openclaw_home / "openclaw.json"
    config_json = openclaw_home / "config.json"
    openclaw_json.write_text("{}")
    config_json.write_text("{}")

    result = paths.resolve_openclaw_config_path(openclaw_home)
    assert result == openclaw_json


def test_resolve_openclaw_config_path_falls_back_to_config_json(tmp_path: Path) -> None:
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir()

    config_json = openclaw_home / "config.json"
    config_json.write_text("{}")

    result = paths.resolve_openclaw_config_path(openclaw_home)
    assert result == config_json


def test_resolve_openclaw_config_path_returns_config_json_when_neither_exists(
    tmp_path: Path,
) -> None:
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir()

    result = paths.resolve_openclaw_config_path(openclaw_home)
    assert result == openclaw_home / "config.json"
