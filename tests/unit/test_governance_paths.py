from pathlib import Path

import openclaw_enhance.governance.paths as governance_paths


def test_legacy_governance_paths_follow_workspace_convention(monkeypatch) -> None:
    fake_home = Path("/tmp/fake-home")
    monkeypatch.setattr(governance_paths.Path, "home", staticmethod(lambda: fake_home))

    assert governance_paths.legacy_workspace_root() == fake_home / ".openclaw" / "workspace"
    assert (
        governance_paths.legacy_governance_dir()
        == fake_home / ".openclaw" / "workspace" / "scripts" / "governance"
    )
    assert (
        governance_paths.legacy_subagents_file()
        == fake_home / ".openclaw" / "workspace" / "sub_agents.json"
    )
    assert (
        governance_paths.legacy_subagents_state_file()
        == fake_home / ".openclaw" / "workspace" / "sub_agents_state.json"
    )


def test_managed_archive_root_defaults_under_managed_root(monkeypatch) -> None:
    fake_home = Path("/tmp/fake-home")
    monkeypatch.setattr(governance_paths.Path, "home", staticmethod(lambda: fake_home))

    assert (
        governance_paths.managed_governance_root()
        == fake_home / ".openclaw" / "openclaw-enhance" / "governance"
    )
    assert (
        governance_paths.managed_archive_root()
        == fake_home / ".openclaw" / "openclaw-enhance" / "governance" / "archive"
    )


def test_managed_archive_root_honors_explicit_user_home() -> None:
    explicit_home = Path("/tmp/explicit-user")

    assert (
        governance_paths.managed_governance_root(explicit_home)
        == explicit_home / ".openclaw" / "openclaw-enhance" / "governance"
    )
    assert (
        governance_paths.managed_archive_root(explicit_home)
        == explicit_home / ".openclaw" / "openclaw-enhance" / "governance" / "archive"
    )
