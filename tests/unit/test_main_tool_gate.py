from pathlib import Path

from openclaw_enhance.install.main_tool_gate import (
    TOOL_GATE_BLOCK,
    TOOL_GATE_MARKER,
    inject_main_tool_gate,
    remove_main_tool_gate,
)


def _write_workspace_agents(openclaw_home: Path, content: str) -> Path:
    workspace = openclaw_home / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    agents_path = workspace / "AGENTS.md"
    agents_path.write_text(content, encoding="utf-8")
    return agents_path


def test_inject_main_tool_gate_removes_known_legacy_instruction_line(
    mock_openclaw_home: Path,
) -> None:
    legacy_line = "**每次收到消息** 都必须阅读 `../openclaw-enhanced/system/workspace/AGENTS.md` 里的约定并且遵循。"
    agents_path = _write_workspace_agents(
        mock_openclaw_home,
        f"# Main Workspace\n\n{legacy_line}\n",
    )

    changed = inject_main_tool_gate(
        openclaw_home=mock_openclaw_home,
        config={},
        env={},
    )

    assert changed is True
    content = agents_path.read_text(encoding="utf-8")
    assert legacy_line not in content
    assert "**每次收到消息**" not in content
    assert "里的约定并且遵循" not in content
    assert TOOL_GATE_MARKER in content


def test_inject_main_tool_gate_preserves_unrelated_content_when_repairing(
    mock_openclaw_home: Path,
) -> None:
    legacy_line = "**每次收到消息** 都必须阅读 `../openclaw-enhanced/system/workspace/AGENTS.md` 里的约定并且遵循。"
    user_content = "## User Notes\nDo not alter this section.\n"
    agents_path = _write_workspace_agents(
        mock_openclaw_home,
        (f"# Main\n\n{user_content}\n{legacy_line}\nThis user-managed line should remain.\n"),
    )

    inject_main_tool_gate(
        openclaw_home=mock_openclaw_home,
        config={},
        env={},
    )

    content = agents_path.read_text(encoding="utf-8")
    assert user_content in content
    assert "This user-managed line should remain." in content
    assert legacy_line not in content


def test_inject_main_tool_gate_idempotent_after_repair(
    mock_openclaw_home: Path,
) -> None:
    legacy_line = "**每次收到消息** 都必须阅读 `../openclaw-enhanced/system/workspace/AGENTS.md` 里的约定并且遵循。"
    agents_path = _write_workspace_agents(
        mock_openclaw_home,
        f"{legacy_line}\n",
    )

    first_changed = inject_main_tool_gate(
        openclaw_home=mock_openclaw_home,
        config={},
        env={},
    )
    assert first_changed is True
    first_content = agents_path.read_text(encoding="utf-8")

    second_changed = inject_main_tool_gate(
        openclaw_home=mock_openclaw_home,
        config={},
        env={},
    )
    second_content = agents_path.read_text(encoding="utf-8")

    assert second_changed is False
    assert second_content == first_content
    assert second_content.count(TOOL_GATE_MARKER) == 2


def test_remove_main_tool_gate_keeps_non_legacy_content(
    mock_openclaw_home: Path,
) -> None:
    legacy_line = "**每次收到消息** 都必须阅读 `../openclaw-enhanced/system/workspace/AGENTS.md` 里的约定并且遵循。"
    agents_path = _write_workspace_agents(
        mock_openclaw_home,
        f"保留行\n{legacy_line}\n",
    )

    inject_main_tool_gate(
        openclaw_home=mock_openclaw_home,
        config={},
        env={},
    )

    removed = remove_main_tool_gate(
        openclaw_home=mock_openclaw_home,
        config={},
        env={},
    )
    content = agents_path.read_text(encoding="utf-8")

    assert removed is True
    assert TOOL_GATE_MARKER not in content
    assert "保留行" in content
    assert legacy_line not in content
    assert "**每次收到消息**" not in content


def test_inject_main_tool_gate_removes_stale_legacy_instruction_line_cleanly(
    mock_openclaw_home: Path,
) -> None:
    legacy_line = "**每次收到消息** 都必须阅读 `../openclaw-enhanced/system/workspace/AGENTS.md` 里的约定并且遵循。"
    agents_path = _write_workspace_agents(
        mock_openclaw_home,
        (f"# Main Workspace\n\n保留这一行。\n{legacy_line}\n以及这一行也要保留。\n"),
    )

    changed = inject_main_tool_gate(
        openclaw_home=mock_openclaw_home,
        config={},
        env={},
    )

    assert changed is True
    content = agents_path.read_text(encoding="utf-8")
    assert legacy_line not in content
    assert "**每次收到消息**" not in content
    assert "里的约定并且遵循" not in content
    assert "保留这一行。" in content
    assert "以及这一行也要保留。" in content


def test_inject_main_tool_gate_upgrades_existing_marker_block_to_canonical(
    mock_openclaw_home: Path,
) -> None:
    old_block_without_acp_rule = f"""{TOOL_GATE_MARKER}
## 🚫 Main 主会话工具限制（由 openclaw-enhance 自动注入）

旧版本缺少 ACP 规则。
{TOOL_GATE_MARKER}"""

    agents_path = _write_workspace_agents(
        mock_openclaw_home,
        (
            "# Main Workspace\n\n"
            "用户自定义前置内容\n\n"
            f"{old_block_without_acp_rule}\n\n"
            "用户自定义后置内容\n"
        ),
    )

    changed = inject_main_tool_gate(
        openclaw_home=mock_openclaw_home,
        config={},
        env={},
    )

    assert changed is True
    content = agents_path.read_text(encoding="utf-8")
    assert "旧版本缺少 ACP 规则" not in content
    assert '禁止直接使用 `sessions_spawn(runtime="acp"...)`' in content
    assert content.count(TOOL_GATE_MARKER) == 2
    assert "用户自定义前置内容" in content
    assert "用户自定义后置内容" in content
    assert TOOL_GATE_BLOCK in content
