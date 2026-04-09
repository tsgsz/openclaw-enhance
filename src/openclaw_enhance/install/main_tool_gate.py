from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from openclaw_enhance.paths import resolve_main_workspace

TOOL_GATE_MARKER = "<!-- oe-main-tool-gate -->"

TOOL_GATE_BLOCK = f"""{TOOL_GATE_MARKER}
## 🚫 Main 主会话工具限制（由 openclaw-enhance 自动注入）

严禁 Main 主会话直接使用以下工具：
- `edit` / `write` — 禁止修改或创建任何文件
- `exec` — 禁止执行任何命令（重启服务、安装包、运行脚本等）
- `web_search` / `web_fetch` — 禁止做大量搜索研究
- `browser` / `playwright` — 禁止浏览器操作

**Main 主会话只允许使用：**
- `read` / `memory_search` — 只读访问
- `sessions_spawn` — 派发任务给 Skill（核心工具）
- `sessions_list` / `sessions_history` / `session_status` / `sessions_send` — 会话管理
- `agents_list` — 查看可用 Agent
- `message` — 回复用户

**当用户要求任何需要修改文件、执行命令、搜索研究的任务时：**
1. 必须使用 `sessions_spawn` 派发给对应的 Skill（oe-spawn-search, oe-spawn-coder, oe-spawn-ops 等）
2. 绝对不要自己动手，即使任务看起来很简单
3. 如果你调用 `edit`/`exec`/`write`/`web_search`/`web_fetch`，立刻停止，改用 `sessions_spawn`
{TOOL_GATE_MARKER}"""


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

    if TOOL_GATE_MARKER in content:
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
