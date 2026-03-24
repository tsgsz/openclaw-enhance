from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from openclaw_enhance.paths import resolve_main_workspace

TOOL_GATE_MARKER = "<!-- oe-main-tool-gate -->"
_STALE_OE_MAIN_AGENTS_REF = "openclaw-enhanced/system/workspace/AGENTS.md"
_STALE_OE_LEGACY_LINE_SNIPPETS: tuple[str, ...] = (
    "**每次收到消息** 都必须阅读 `../openclaw-enhanced/system/workspace/AGENTS.md` 里的约定并且遵循。",
    "**每次收到消息** 都必须阅读 `../` 里的约定并且遵循。",
)

TOOL_GATE_BLOCK = f"""{TOOL_GATE_MARKER}
## 🚫 Main 主会话工具限制（由 openclaw-enhance 自动注入）

严禁 Main 主会话直接使用以下工具：
- `edit` / `write` — 禁止修改或创建任何文件
- `exec` — 禁止执行任何命令（重启服务、安装包、运行脚本等）
- `web_search` / `web_fetch` — 禁止做大量搜索研究
- `browser` / `playwright` — 禁止浏览器操作

**Main 主会话只允许使用：**
- `read` / `memory_search` — 只读访问
- `sessions_spawn` — 派发任务给子 Agent（核心工具）
- `sessions_list` / `sessions_history` / `session_status` / `sessions_send` — 会话管理
- `agents_list` — 查看可用 Agent
- `message` — 回复用户

**当用户要求任何需要修改文件、执行命令、搜索研究的任务时：**
1. 必须使用 `sessions_spawn` 派发给 `oe-orchestrator`
2. 绝对不要自己动手，即使任务看起来很简单
3. 如果你调用 `edit`/`exec`/`write`/`web_search`/`web_fetch`，立刻停止，改用 `sessions_spawn`

**重要：Session 上下文优先级规则：**  # ruff: noqa: E501
4. **Session 内上下文的优先级高于 memory_search**。当你需要理解用户当前的问题或请求时，优先读取当前 session 中的上下文（对话历史、用户正在回复的消息、正在讨论的文件内容等），而不是先去 memory_search 查历史记忆。不要在还没吃干净当前 session 上下文之前就跳去 `memory_search`。  # ruff: noqa: E501

**严禁直接调用 ACP：**  # ruff: noqa: E501
5. **禁止直接使用 `sessions_spawn(runtime="acp"...)`**。所有 ACP 相关任务（如调用 codex、opencode 等外部 coding harness）必须通过 `sessions_spawn(runtime="subagent", agentId="oe-orchestrator")` 分发给 oe-orchestrator，由 orchestrator 决定如何调用 ACP。绝对不要自己直接调用 `runtime="acp"`。  # ruff: noqa: E501

{TOOL_GATE_MARKER}"""  # noqa: E501


def _repair_known_stale_main_agents_refs(content: str) -> tuple[str, bool]:
    repaired_lines: list[str] = []
    changed = False

    for line in content.splitlines(keepends=True):
        should_drop_line = False

        if (
            _STALE_OE_MAIN_AGENTS_REF in line
            and "每次收到消息" in line
            and "里的约定并且遵循" in line
        ):
            should_drop_line = True
        else:
            for stale_line in _STALE_OE_LEGACY_LINE_SNIPPETS:
                if stale_line in line:
                    should_drop_line = True
                    break

        if should_drop_line:
            changed = True
            continue

        repaired_lines.append(line)

    if not changed:
        return content, False

    return "".join(repaired_lines), True


def _replace_existing_tool_gate_block_with_canonical(content: str) -> tuple[str, bool]:
    marker_count = content.count(TOOL_GATE_MARKER)
    if marker_count < 2:
        return content, False

    start = content.index(TOOL_GATE_MARKER)
    end = content.index(TOOL_GATE_MARKER, start + len(TOOL_GATE_MARKER)) + len(TOOL_GATE_MARKER)
    existing_block = content[start:end]
    if existing_block == TOOL_GATE_BLOCK:
        return content, False

    updated = content[:start] + TOOL_GATE_BLOCK + content[end:]
    return updated, True


def inject_main_tool_gate(
    openclaw_home: Path,
    config: Mapping[str, Any] | None,
    env: Mapping[str, str] | None,
) -> bool:
    workspace_path = resolve_main_workspace(openclaw_home, config=config, env=env)
    agents_md = workspace_path / "AGENTS.md"

    if not agents_md.exists():
        return False

    content = agents_md.read_text(encoding="utf-8")
    content, repaired = _repair_known_stale_main_agents_refs(content)

    content, refreshed = _replace_existing_tool_gate_block_with_canonical(content)

    if TOOL_GATE_MARKER in content:
        if repaired or refreshed:
            agents_md.write_text(content, encoding="utf-8")
            return True
        return False

    updated = content.rstrip() + "\n\n" + TOOL_GATE_BLOCK + "\n"
    agents_md.write_text(updated, encoding="utf-8")
    return True


def remove_main_tool_gate(
    openclaw_home: Path,
    config: Mapping[str, Any] | None,
    env: Mapping[str, str] | None,
) -> bool:
    workspace_path = resolve_main_workspace(openclaw_home, config=config, env=env)
    agents_md = workspace_path / "AGENTS.md"

    if not agents_md.exists():
        return False

    content = agents_md.read_text(encoding="utf-8")

    if TOOL_GATE_MARKER not in content:
        return False

    start = content.index(TOOL_GATE_MARKER)
    end = content.index(TOOL_GATE_MARKER, start + len(TOOL_GATE_MARKER)) + len(TOOL_GATE_MARKER)
    updated = content[:start].rstrip() + content[end:].lstrip("\n")
    agents_md.write_text(updated, encoding="utf-8")
    return True
