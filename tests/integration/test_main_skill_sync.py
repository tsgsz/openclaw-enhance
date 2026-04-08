"""Integration tests for install-time main skill synchronization."""

import json
import os
from pathlib import Path

from openclaw_enhance.install import install
from openclaw_enhance.install.manifest import load_manifest

MAIN_SKILL_IDS = [
    "oe-eta-estimator",
    "oe-tag-router",
    "oe-timeout-state-sync",
]


def _create_openclaw_home(
    tmp_path: Path,
    config: dict,
    *,
    config_filename: str = "openclaw.json",
    legacy_config: dict | None = None,
) -> Path:
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)
    (openclaw_home / "VERSION").write_text("2026.3.1\n")
    (openclaw_home / config_filename).write_text(json.dumps(config) + "\n")
    if legacy_config is not None:
        (openclaw_home / "config.json").write_text(json.dumps(legacy_config) + "\n")
    os.environ["TEST_OPENCLAW_HOME"] = str(openclaw_home)
    return openclaw_home


def _assert_skill_tree_contains_main_skills(skills_dir: Path) -> None:
    assert skills_dir.exists()
    assert skills_dir.is_dir()

    for skill_id in MAIN_SKILL_IDS:
        skill_file = skills_dir / skill_id / "SKILL.md"
        assert skill_file.exists()
        assert skill_file.is_file()
        assert skill_file.read_text(encoding="utf-8").strip()


def _assert_manifest_registers_main_skills(user_home: Path) -> None:
    manifest = load_manifest(user_home / ".openclaw" / "openclaw-enhance")
    assert manifest is not None

    component_names = {component.name for component in manifest.components}
    for skill_id in MAIN_SKILL_IDS:
        assert f"main-skill:{skill_id}" in component_names


def _assert_manifest_marks_main_skills_as_symlinks(user_home: Path) -> None:
    manifest = load_manifest(user_home / ".openclaw" / "openclaw-enhance")
    assert manifest is not None

    main_skill_components = [
        component for component in manifest.components if component.name.startswith("main-skill:")
    ]
    assert len(main_skill_components) == len(MAIN_SKILL_IDS)
    assert all(component.is_symlink for component in main_skill_components)


def test_install_syncs_main_skills_to_config_defined_workspace(tmp_path: Path) -> None:
    user_home = tmp_path / "user-home"
    configured_workspace = tmp_path / "custom-main-workspace"
    openclaw_home = _create_openclaw_home(
        tmp_path,
        {
            "agent": {
                "workspace": str(configured_workspace),
            }
        },
    )

    result = install(openclaw_home=openclaw_home, user_home=user_home)

    assert result.success
    _assert_skill_tree_contains_main_skills(configured_workspace / "skills")
    _assert_manifest_registers_main_skills(user_home)


def test_install_syncs_main_skills_to_relative_config_workspace_under_openclaw_home(
    tmp_path: Path,
) -> None:
    user_home = tmp_path / "user-home"
    relative_workspace = "workspace-main-custom"
    openclaw_home = _create_openclaw_home(
        tmp_path,
        {
            "agent": {
                "workspace": relative_workspace,
            }
        },
    )

    result = install(openclaw_home=openclaw_home, user_home=user_home)

    assert result.success
    _assert_skill_tree_contains_main_skills(openclaw_home / relative_workspace / "skills")
    _assert_manifest_registers_main_skills(user_home)


def test_install_syncs_main_skills_to_default_workspace_fallback(tmp_path: Path) -> None:
    user_home = tmp_path / "user-home"
    openclaw_home = _create_openclaw_home(tmp_path, {"test": True})

    result = install(openclaw_home=openclaw_home, user_home=user_home)

    assert result.success
    _assert_skill_tree_contains_main_skills(openclaw_home / "workspace" / "skills")
    _assert_manifest_registers_main_skills(user_home)


def test_install_syncs_main_skills_to_agents_defaults_workspace(tmp_path: Path) -> None:
    user_home = tmp_path / "user-home"
    configured_workspace = tmp_path / "agents-default-main-workspace"
    openclaw_home = _create_openclaw_home(
        tmp_path,
        {
            "agents": {
                "defaults": {
                    "workspace": str(configured_workspace),
                }
            }
        },
    )

    result = install(openclaw_home=openclaw_home, user_home=user_home)

    assert result.success
    _assert_skill_tree_contains_main_skills(configured_workspace / "skills")
    _assert_manifest_registers_main_skills(user_home)


def test_install_syncs_main_skills_to_relative_agents_defaults_workspace_under_openclaw_home(
    tmp_path: Path,
) -> None:
    user_home = tmp_path / "user-home"
    relative_workspace = "workspace-from-defaults"
    openclaw_home = _create_openclaw_home(
        tmp_path,
        {
            "agents": {
                "defaults": {
                    "workspace": relative_workspace,
                }
            }
        },
    )

    result = install(openclaw_home=openclaw_home, user_home=user_home)

    assert result.success
    _assert_skill_tree_contains_main_skills(openclaw_home / relative_workspace / "skills")
    _assert_manifest_registers_main_skills(user_home)


def test_install_syncs_main_skills_to_profile_workspace_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    user_home = tmp_path / "user-home"
    openclaw_home = _create_openclaw_home(tmp_path, {"test": True})
    monkeypatch.setenv("OPENCLAW_PROFILE", "staging")

    result = install(openclaw_home=openclaw_home, user_home=user_home)

    assert result.success
    _assert_skill_tree_contains_main_skills(openclaw_home / "workspace-staging" / "skills")
    _assert_manifest_registers_main_skills(user_home)


def test_install_prefers_openclaw_json_workspace_over_config_json(tmp_path: Path) -> None:
    user_home = tmp_path / "user-home"
    openclaw_json_workspace = tmp_path / "openclaw-json-workspace"
    config_json_workspace = tmp_path / "config-json-workspace"
    openclaw_home = _create_openclaw_home(
        tmp_path,
        {"agent": {"workspace": str(openclaw_json_workspace)}},
        legacy_config={"agent": {"workspace": str(config_json_workspace)}},
    )

    result = install(openclaw_home=openclaw_home, user_home=user_home)

    assert result.success
    _assert_skill_tree_contains_main_skills(openclaw_json_workspace / "skills")
    assert not (config_json_workspace / "skills").exists()
    _assert_manifest_registers_main_skills(user_home)


def test_install_dev_mode_symlinks_main_skills_in_resolved_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    user_home = tmp_path / "user-home"
    openclaw_home = _create_openclaw_home(tmp_path, {"test": True})
    monkeypatch.setenv("OPENCLAW_PROFILE", "qa")

    result = install(openclaw_home=openclaw_home, user_home=user_home, dev_mode=True)

    assert result.success
    skills_dir = openclaw_home / "workspace-qa" / "skills"
    _assert_skill_tree_contains_main_skills(skills_dir)
    for skill_id in MAIN_SKILL_IDS:
        skill_file = skills_dir / skill_id / "SKILL.md"
        assert skill_file.is_symlink()
    _assert_manifest_marks_main_skills_as_symlinks(user_home)
