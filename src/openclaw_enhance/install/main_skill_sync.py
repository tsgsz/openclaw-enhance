from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from openclaw_enhance.constants import VERSION
from openclaw_enhance.install.manifest import ComponentInstall
from openclaw_enhance.paths import main_workspace_skills_dir, resolve_main_workspace
from openclaw_enhance.skills_catalog import _skill_contract_path

MAIN_SKILL_IDS: tuple[str, ...] = (
    "oe-eta-estimator",
    "oe-tag-router",
    "oe-timeout-state-sync",
)


def sync_main_skills(
    openclaw_home: Path,
    config: Mapping[str, Any] | None,
    env: Mapping[str, str] | None,
    dev_mode: bool = False,
) -> list[ComponentInstall]:
    workspace_path = resolve_main_workspace(openclaw_home, config=config, env=env)
    workspace_path.mkdir(parents=True, exist_ok=True)

    skills_dir = main_workspace_skills_dir(workspace_path)
    skills_dir.mkdir(parents=True, exist_ok=True)

    components: list[ComponentInstall] = []
    for skill_id in MAIN_SKILL_IDS:
        source_path = _skill_contract_path(skill_id)
        if not source_path.is_file():
            raise FileNotFoundError(f"Skill contract not found: {source_path}")

        target_path = skills_dir / skill_id / "SKILL.md"
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if target_path.exists() or target_path.is_symlink():
            target_path.unlink()

        if dev_mode:
            target_path.symlink_to(source_path.absolute())
        else:
            shutil.copy2(source_path, target_path)

        components.append(
            ComponentInstall(
                name=f"main-skill:{skill_id}",
                version=VERSION,
                install_time=datetime.utcnow(),
                source_path=str(source_path.absolute()),
                target_path=str(target_path.absolute()),
                is_symlink=dev_mode,
            )
        )

    return components
