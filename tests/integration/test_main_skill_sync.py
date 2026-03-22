"""Integration tests for install-time main skill synchronization."""

import json
from pathlib import Path

from openclaw_enhance.install import install
from openclaw_enhance.install.manifest import load_manifest

MAIN_SKILL_IDS = [
    "oe-eta-estimator",
    "oe-toolcall-router",
    "oe-timeout-state-sync",
]


def _create_openclaw_home(tmp_path: Path, config: dict) -> Path:
    import os

    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)
    (openclaw_home / "VERSION").write_text("2026.3.1\n")
    (openclaw_home / "openclaw.json").write_text(json.dumps(config) + "\n")
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


def test_install_syncs_main_skills_to_default_workspace_fallback(tmp_path: Path) -> None:
    user_home = tmp_path / "user-home"
    openclaw_home = _create_openclaw_home(tmp_path, {"test": True})

    result = install(openclaw_home=openclaw_home, user_home=user_home)

    assert result.success
    _assert_skill_tree_contains_main_skills(openclaw_home / "workspace" / "skills")
    _assert_manifest_registers_main_skills(user_home)
