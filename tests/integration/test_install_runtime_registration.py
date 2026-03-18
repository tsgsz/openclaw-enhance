import json
from pathlib import Path
from unittest.mock import patch

import pytest

from openclaw_enhance.install import install
from openclaw_enhance.paths import managed_root, resolve_openclaw_config_path


@pytest.fixture
def mock_openclaw_home(tmp_path: Path) -> Path:
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)

    version_file = openclaw_home / "VERSION"
    version_file.write_text("2026.3.1\n")

    config_file = openclaw_home / "openclaw.json"
    config_file.write_text(json.dumps({"theme": "dark"}) + "\n")

    return openclaw_home


@pytest.fixture
def isolated_user_home(tmp_path: Path) -> Path:
    return tmp_path / "user_home"


def test_install_does_not_write_top_level_openclaw_enhance_key(
    mock_openclaw_home: Path,
    isolated_user_home: Path,
) -> None:
    result = install(mock_openclaw_home, user_home=isolated_user_home)
    assert result.success

    config_path = resolve_openclaw_config_path(mock_openclaw_home)
    assert config_path.name == "openclaw.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert "openclawEnhance" not in config, "Should not write top-level 'openclawEnhance' key"


def test_force_install_migrates_legacy_config(
    mock_openclaw_home: Path,
    isolated_user_home: Path,
) -> None:
    config_path = resolve_openclaw_config_path(mock_openclaw_home)
    config_path.write_text(json.dumps({"theme": "light", "openclawEnhance": {"legacy": True}}))

    result = install(mock_openclaw_home, user_home=isolated_user_home, force=True)
    assert result.success

    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert "openclawEnhance" not in config, (
        "Legacy 'openclawEnhance' key should be migrated/removed"
    )


def test_runtime_registration_uses_supported_shape(
    mock_openclaw_home: Path,
    isolated_user_home: Path,
) -> None:
    from openclaw_enhance.runtime.ownership import OWNED_AGENT_SPECS

    mock_result = type("Result", (), {"returncode": 0, "stdout": "[]", "stderr": ""})()
    with patch(
        "openclaw_enhance.install.installer._run_openclaw_cli",
        return_value=mock_result,
    ) as mock_cli:
        result = install(mock_openclaw_home, user_home=isolated_user_home)
    assert result.success

    expected_workspaces_root = managed_root(isolated_user_home) / "workspaces"
    for agent_id, workspace_name in OWNED_AGENT_SPECS:
        expected_workspace = str((expected_workspaces_root / workspace_name).absolute())
        mock_cli.assert_any_call(
            [
                "agents",
                "add",
                agent_id,
                "--workspace",
                expected_workspace,
                "--non-interactive",
            ]
        )

    config_path = resolve_openclaw_config_path(mock_openclaw_home)
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert "hooks" in config, "Top-level 'hooks' key should exist"
    assert "internal" in config["hooks"], "Top-level 'hooks.internal' should exist"
    internal_hooks = config["hooks"]["internal"]
    assert "entries" in internal_hooks, "Top-level 'hooks.internal.entries' should exist"
    assert isinstance(internal_hooks["entries"], dict), (
        "Top-level 'hooks.internal.entries' should be a record"
    )
    assert "oe-subagent-spawn-enrich" in internal_hooks["entries"], (
        "oe-subagent-spawn-enrich hook should be enabled under hooks.internal.entries"
    )
    assert internal_hooks["entries"]["oe-subagent-spawn-enrich"] == {"enabled": True}, (
        "oe-subagent-spawn-enrich hook entry should be enabled explicitly"
    )
    assert "oe-main-routing-gate" in internal_hooks["entries"], (
        "oe-main-routing-gate hook should be enabled under hooks.internal.entries"
    )
    assert internal_hooks["entries"]["oe-main-routing-gate"] == {"enabled": True}, (
        "oe-main-routing-gate hook entry should be enabled explicitly"
    )

    assert "load" in internal_hooks, "Top-level 'hooks.internal.load' should exist"
    assert "extraDirs" in internal_hooks["load"], (
        "Top-level 'hooks.internal.load.extraDirs' should exist"
    )
    expected_hook_dir = str(managed_root(isolated_user_home) / "hooks")
    assert expected_hook_dir in internal_hooks["load"]["extraDirs"], (
        "Managed hook directory should be registered for hook discovery"
    )

    assert "openclawEnhance" not in config, "Registration should not be under 'openclawEnhance'"


def test_install_preserves_foreign_hook_entry_configuration(
    mock_openclaw_home: Path,
    isolated_user_home: Path,
) -> None:
    config_path = resolve_openclaw_config_path(mock_openclaw_home)
    foreign_entry = {
        "enabled": False,
        "env": {"FOREIGN_FLAG": "1"},
    }
    config_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "internal": {
                        "entries": {"foreign-hook": foreign_entry},
                        "load": {"extraDirs": ["/foreign/hooks"]},
                    }
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = install(mock_openclaw_home, user_home=isolated_user_home)
    assert result.success

    config = json.loads(config_path.read_text(encoding="utf-8"))
    internal_hooks = config["hooks"]["internal"]

    assert internal_hooks["entries"]["foreign-hook"] == foreign_entry
    assert "/foreign/hooks" in internal_hooks["load"]["extraDirs"]


def test_runtime_registration_allows_main_to_spawn_oe_orchestrator(
    mock_openclaw_home: Path,
    isolated_user_home: Path,
) -> None:
    config_path = resolve_openclaw_config_path(mock_openclaw_home)
    config_path.write_text(
        json.dumps(
            {
                "agents": {
                    "defaults": {
                        "subagents": {
                            "allowAgents": ["orchestrator"],
                        }
                    },
                    "list": [
                        {
                            "id": "main",
                            "subagents": {
                                "allowAgents": ["orchestrator"],
                            },
                        }
                    ],
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = install(mock_openclaw_home, user_home=isolated_user_home)
    assert result.success

    config = json.loads(config_path.read_text(encoding="utf-8"))
    agents_obj = config["agents"]

    defaults_subagents = agents_obj.get("defaults", {}).get("subagents", {})
    assert "allowAgents" not in defaults_subagents

    main_entry = next(a for a in agents_obj["list"] if a.get("id") == "main")
    main_allow_agents = main_entry.get("subagents", {}).get("allowAgents", [])
    assert "orchestrator" in main_allow_agents
    assert "oe-orchestrator" in main_allow_agents
