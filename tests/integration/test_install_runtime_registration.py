import json
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from openclaw_enhance.install import install
from openclaw_enhance.paths import managed_root, resolve_openclaw_config_path


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

    # Use conftest.py mock which handles plugin registration
    result = install(mock_openclaw_home, user_home=isolated_user_home)
    assert result.success

    config_path = resolve_openclaw_config_path(mock_openclaw_home)
    config = json.loads(config_path.read_text(encoding="utf-8"))

    # Verify agents were registered in config
    agents_obj = config.get("agents", {})
    agent_list = agents_obj.get("list", [])
    registered_agent_ids = {a.get("id") for a in agent_list}
    for agent_id, _ in OWNED_AGENT_SPECS:
        assert agent_id in registered_agent_ids, f"Agent {agent_id} should be registered"

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


def test_runtime_registration_reconciles_subagent_spawn_tool_allowlist_idempotently(
    mock_openclaw_home: Path,
    isolated_user_home: Path,
) -> None:
    config_path = resolve_openclaw_config_path(mock_openclaw_home)
    config_path.write_text(
        json.dumps(
            {
                "tools": {
                    "subagents": {
                        "tools": {
                            "allow": ["sessions_send", "custom_tool"],
                        }
                    }
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    first_result = install(mock_openclaw_home, user_home=isolated_user_home)
    assert first_result.success

    first_config = json.loads(config_path.read_text(encoding="utf-8"))
    first_allow_tools = first_config["tools"]["subagents"]["tools"].get("allow", [])

    assert "sessions_send" in first_allow_tools
    assert "custom_tool" in first_allow_tools
    assert "sessions_spawn" in first_allow_tools
    assert first_allow_tools.count("sessions_spawn") == 1

    second_result = install(mock_openclaw_home, user_home=isolated_user_home)
    assert second_result.success

    second_config = json.loads(config_path.read_text(encoding="utf-8"))
    second_allow_tools = second_config["tools"]["subagents"]["tools"].get("allow", [])

    assert second_allow_tools.count("sessions_spawn") == 1
    assert "sessions_send" in second_allow_tools
    assert "custom_tool" in second_allow_tools


def test_runtime_registration_reconciles_defaults_subagent_max_spawn_depth_without_writing_per_agent_key(
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
                            "maxSpawnDepth": 1,
                            "customPolicy": {"preserve": True},
                        }
                    },
                    "list": [
                        {
                            "id": "main",
                            "subagents": {
                                "allowAgents": ["orchestrator", "oe-orchestrator"],
                                "customPolicy": {"preserve": True},
                            },
                        }
                    ],
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    first_result = install(mock_openclaw_home, user_home=isolated_user_home)
    assert first_result.success

    first_config = json.loads(config_path.read_text(encoding="utf-8"))
    defaults_subagents = first_config["agents"]["defaults"]["subagents"]
    main_entry = next(a for a in first_config["agents"]["list"] if a.get("id") == "main")
    main_subagents = main_entry.get("subagents", {})

    assert defaults_subagents.get("maxSpawnDepth") == 2
    assert defaults_subagents.get("customPolicy") == {"preserve": True}
    assert "maxSpawnDepth" not in main_subagents
    assert main_subagents.get("customPolicy") == {"preserve": True}
    assert "orchestrator" in main_subagents.get("allowAgents", [])
    assert "oe-orchestrator" in main_subagents.get("allowAgents", [])

    second_result = install(mock_openclaw_home, user_home=isolated_user_home)
    assert second_result.success

    second_config = json.loads(config_path.read_text(encoding="utf-8"))
    second_defaults_subagents = second_config["agents"]["defaults"]["subagents"]
    second_main_entry = next(a for a in second_config["agents"]["list"] if a.get("id") == "main")
    second_main_subagents = second_main_entry.get("subagents", {})

    assert second_defaults_subagents.get("maxSpawnDepth") == 2
    assert second_defaults_subagents.get("customPolicy") == {"preserve": True}
    assert "maxSpawnDepth" not in second_main_subagents
    assert second_main_subagents.get("customPolicy") == {"preserve": True}


def test_runtime_registration_pins_orchestrator_subagent_model_for_handoff(
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
                            "model": "minimax/MiniMax-M2.1",
                            "maxConcurrent": 8,
                        }
                    },
                    "list": [
                        {
                            "id": "main",
                            "subagents": {
                                "allowAgents": ["oe-orchestrator"],
                            },
                        },
                        {
                            "id": "oe-orchestrator",
                            "subagents": {},
                        },
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
    defaults_subagents = config["agents"]["defaults"]["subagents"]
    main_entry = next(a for a in config["agents"]["list"] if a.get("id") == "main")
    orchestrator_entry = next(
        a for a in config["agents"]["list"] if a.get("id") == "oe-orchestrator"
    )
    main_subagents = main_entry.get("subagents", {})
    orchestrator_subagents = orchestrator_entry.get("subagents", {})

    assert defaults_subagents.get("model") == "minimax/MiniMax-M2.1"
    assert "model" not in main_subagents
    assert orchestrator_subagents.get("model") == "litellm-local/gpt-5.4"
    assert "oe-orchestrator" in main_subagents.get("allowAgents", [])


def test_install_reconciles_orchestrator_subagent_model_after_late_cli_config_clobber(
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
                            "model": "minimax/MiniMax-M2.7",
                        }
                    },
                    "list": [
                        {
                            "id": "main",
                            "subagents": {
                                "allowAgents": ["oe-orchestrator"],
                            },
                        },
                        {
                            "id": "oe-orchestrator",
                            "subagents": {},
                        },
                    ],
                },
                "plugins": {"allow": [], "entries": {}},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def _run_openclaw_cli_with_late_clobber(args, check=True):
        if args[:2] == ["agents", "list"]:
            return CompletedProcess(args=args, returncode=0, stdout="[]", stderr="")

        if args[:2] == ["agents", "add"]:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            agents = cfg.setdefault("agents", {})
            agent_list = agents.setdefault("list", [])
            agent_id = args[2]
            if not any(isinstance(a, dict) and a.get("id") == agent_id for a in agent_list):
                agent_list.append({"id": agent_id})
            config_path.write_text(json.dumps(cfg) + "\n", encoding="utf-8")
            return CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        if args[:2] == ["plugins", "list"]:
            return CompletedProcess(args=args, returncode=0, stdout="[]", stderr="")

        if args[:2] == ["plugins", "install"]:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            plugins = cfg.setdefault("plugins", {})
            allow = plugins.setdefault("allow", [])
            entries = plugins.setdefault("entries", {})
            if "oe-runtime" not in allow:
                allow.append("oe-runtime")
            entries["oe-runtime"] = {"enabled": True}
            config_path.write_text(json.dumps(cfg) + "\n", encoding="utf-8")
            return CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        if args[:3] == ["plugins", "enable", "acpx"]:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            agents = cfg.get("agents", {})
            agent_list = agents.get("list", [])
            for entry in agent_list:
                if isinstance(entry, dict) and entry.get("id") == "oe-orchestrator":
                    subagents = entry.get("subagents", {})
                    if isinstance(subagents, dict):
                        subagents.pop("model", None)
            config_path.write_text(json.dumps(cfg) + "\n", encoding="utf-8")
            return CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        return CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    with patch(
        "openclaw_enhance.install.installer._run_openclaw_cli",
        side_effect=_run_openclaw_cli_with_late_clobber,
    ):
        result = install(mock_openclaw_home, user_home=isolated_user_home)

    assert result.success

    final_config = json.loads(config_path.read_text(encoding="utf-8"))
    defaults_subagents = final_config["agents"]["defaults"]["subagents"]
    main_entry = next(a for a in final_config["agents"]["list"] if a.get("id") == "main")
    orchestrator_entry = next(
        a for a in final_config["agents"]["list"] if a.get("id") == "oe-orchestrator"
    )
    main_subagents = main_entry.get("subagents", {})
    orchestrator_subagents = orchestrator_entry.get("subagents", {})

    assert defaults_subagents.get("model") == "minimax/MiniMax-M2.7"
    assert "model" not in main_subagents
    assert orchestrator_subagents.get("model") == "litellm-local/gpt-5.4"
