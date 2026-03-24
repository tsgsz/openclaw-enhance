from pathlib import Path

from openclaw_enhance.install.main_tool_gate import (
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


def test_inject_main_tool_gate_repairs_stale_openclaw_enhanced_reference(
    mock_openclaw_home: Path,
) -> None:
    agents_path = _write_workspace_agents(
        mock_openclaw_home,
        "# Main Workspace\n\nPlease follow ../openclaw-enhanced/system/workspace/AGENTS.md\n",
    )

    changed = inject_main_tool_gate(
        openclaw_home=mock_openclaw_home,
        config={},
        env={},
    )

    assert changed is True
    content = agents_path.read_text(encoding="utf-8")
    assert "../openclaw-enhanced/system/workspace/AGENTS.md" not in content
    assert "openclaw-enhance/system/workspace/AGENTS.md" not in content
    assert TOOL_GATE_MARKER in content


def test_inject_main_tool_gate_preserves_unrelated_content_when_repairing(
    mock_openclaw_home: Path,
) -> None:
    user_content = "## User Notes\nDo not alter this section.\n"
    agents_path = _write_workspace_agents(
        mock_openclaw_home,
        (
            "# Main\n\n"
            f"{user_content}\n"
            "See ../openclaw-enhanced/system/workspace/AGENTS.md for reference.\n"
        ),
    )

    inject_main_tool_gate(
        openclaw_home=mock_openclaw_home,
        config={},
        env={},
    )

    content = agents_path.read_text(encoding="utf-8")
    assert user_content in content


def test_inject_main_tool_gate_idempotent_after_repair(
    mock_openclaw_home: Path,
) -> None:
    agents_path = _write_workspace_agents(
        mock_openclaw_home,
        "legacy path ../openclaw-enhanced/system/workspace/AGENTS.md\n",
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


def test_remove_main_tool_gate_keeps_repaired_path(
    mock_openclaw_home: Path,
) -> None:
    agents_path = _write_workspace_agents(
        mock_openclaw_home,
        "ref ../openclaw-enhanced/system/workspace/AGENTS.md\n",
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
    assert "../openclaw-enhanced/system/workspace/AGENTS.md" not in content
    assert "openclaw-enhance/system/workspace/AGENTS.md" not in content
