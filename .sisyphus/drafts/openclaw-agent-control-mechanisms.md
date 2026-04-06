# OpenClaw Agent 行为控制机制调研

> 调研日期: 2026-04-06
> 优先级原则: 越简单的方法优先级越高

---

## 概述

本调研旨在梳理 OpenClaw 中所有可用于控制 agent 行为的手段，按**简单程度**、**直观程度**和**强制力**分类，供在 `openclaw-enhance` 项目中实现时参考。

---

## 控制手段分类

### Tier 1: 简单 + 直观 + 强强制力 (优先采用)

#### 1. Tool Gate (主会话工具限制)

| 属性 | 评分 |
|------|------|
| **复杂度** | ⭐ 简单 |
| **直观性** | ✅ 直观 |
| **强制力** | 🔴 强 |

**作用原理**:
在 Main 会话的 `AGENTS.md` 中注入工具限制块，明确禁止使用: `edit`, `write`, `exec`, `web_search`, `web_fetch`, `browser`, `playwright`
仅允许: `read`, `memory_search`, `sessions_spawn`, `session_*` 等路由类工具

**实现位置**:
- 安装时注入: `src/openclaw_enhance/install/main_tool_gate.py`
- 运行时执行: `extensions/openclaw-enhance-runtime/index.ts` (before_tool_call hook)

**示例** (注入到 AGENTS.md 的内容):
```markdown
## 🚫 Main 主会话工具限制

严禁 Main 主会话直接使用以下工具：
- `edit` / `write` — 禁止修改或创建任何文件
- `exec` — 禁止执行任何命令
- `web_search` / `web_fetch` — 禁止自行进行网络研究
- `browser` / `playwright` — 禁止浏览器自动化

Main 会话仅允许：
- `read` — 读取文件（仅限查看）
- `memory_search` — 搜索记忆
- `sessions_spawn` — 分发给子agent
- `session_list/history/status` — 监控会话
- `sessions_send` — 与子agent通信
- `agents_list` — 列出可用agent
- `message` — 回复用户
```

**优缺点**:
- ✅ 实现简单 - 纯文本配置
- ✅ 直观易懂 - 显式列出允许/禁止列表
- ✅ 强制力强 - OpenClaw 会在解析 AGENTS.md 时强制执行
- ❌ 仅限于工具层面，不能控制业务逻辑

---

#### 2. Workspace AGENTS.md (Agent 权限边界)

| 属性 | 评分 |
|------|------|
| **复杂度** | ⭐ 简单 |
| **直观性** | ✅ 直观 |
| **强制力** | 🟡 中 |

**作用原理**:
每个 workspace 拥有独立的 `AGENTS.md`，通过 YAML frontmatter 定义角色、能力边界和工具权限。OpenClaw 根据 workspace 配置执行权限校验。

**实现位置**:
- `workspaces/oe-searcher/AGENTS.md`
- `workspaces/oe-syshelper/AGENTS.md`
- `workspaces/oe-watchdog/AGENTS.md`

**示例** (oe-searcher 的 frontmatter):
```yaml
---
name: oe-searcher
routing:
  mutation_mode: read_only
  can_spawn: false
  rejects:
    - file_modifications
    - code_implementation
    - subagent_spawning
---
```

**示例** (oe-watchdog 的权限控制):
```yaml
authority:
  permitted:
    - read_runtime_state      # ✅ 读取运行时状态
    - write_timeout_status   # ✅ 写入超时状态
    - send_session_message   # ✅ 发送会话消息
  prohibited:
    - kill_processes         # ❌ 禁止杀进程
    - edit_user_repos        # ❌ 禁止编辑用户代码
    - modify_non_owned_config # ❌ 禁止修改非自有配置
```

**优缺点**:
- ✅ 简单 - YAML 配置，无需代码
- ✅ 直观 - 清晰的角色和能力定义
- ✅ 可组合 - 每个 agent 独立配置
- 🟡 强制力中等 - 依赖 OpenClaw 的解析和执行

---

#### 3. Skill 约束 (技能契约)

| 属性 | 评分 |
|------|------|
| **复杂度** | ⭐⭐ 简单到中等 |
| **直观性** | ✅ 直观 |
| **强制力** | 🟡 中 |

**作用原理**:
Skill 是 Markdown 契约文件，定义 agent 的行为模式和约束。Agent 被期望遵循 skill 中的指令。Skill 通过 `sessions_spawn` 的上下文传递给子 agent。

**实现位置**:
- `skills/oe-toolcall-router/SKILL.md`
- `skills/oe-eta-estimator/SKILL.md`

**示例** (oe-toolcall-router 强制路由):
```markdown
# Toolcall Router

Main session is a **router only**. It does NOT execute tasks directly.

## Iron Rule

Main session is FORBIDDEN from using these tools:
- `edit`, `write`, `exec`, `process`, `browser`, `playwright`
- `web_search`, `web_fetch` (for research tasks)

Main session is ONLY allowed to use:
- `read` (read-only file access)
- `memory_search` (search memories)
- `sessions_spawn` (delegate to subagents)
- `sessions_list`, `sessions_history`, `session_status` (monitor sessions)
- `sessions_send` (communicate with subagents)
- `agents_list` (list available agents)
- `message` (reply to user)
```

**优缺点**:
- ✅ 简单 - Markdown 格式，人类可读
- ✅ 直观 - 自然语言描述行为规范
- ✅ 灵活 - 可定义复杂的决策逻辑
- 🟡 强制力中等 - 依赖 agent 遵循指令（非强制性拦截）

---

### Tier 2: 中等复杂度

#### 4. Hook 系统 (事件拦截)

| 属性 | 评分 |
|------|------|
| **复杂度** | ⭐⭐⭐ 中等 |
| **直观性** | ✅ 直观 |
| **强制力** | 🟡 中 ( advisory) / 🔴 强 ( blocking) |

**作用原理**:
Hook 拦截 OpenClaw 的特定事件（`message:preprocessed`, `subagent_spawning`），可以注入建议或阻止操作。

**两种模式**:
1. **Advisory (建议模式)** - 提供建议，agent 可选择不听
2. **Blocking (阻止模式)** - 返回 `unsafe: true`，阻止操作执行

**实现位置**:
- `hooks/oe-main-routing-gate/HOOK.md`
- `hooks/oe-subagent-spawn-enrich/HOOK.md`

**示例 1** (oe-main-routing-gate - 建议模式):
```yaml
---
name: oe-main-routing-gate
description: Provide progressive escalation advisory based on task complexity.
metadata: { "openclaw": { "emoji": "🧭", "events": ["message:preprocessed"] } }
---

# oe-main-routing-gate

## Trigger
- Event: `message:preprocessed`
- Scope: `agent:main:*` sessions only

## Behavior
Analyzes incoming requests for complexity indicators:
- 研究/分析/生成/制作
- 写报告/做PPT/整理大纲
- 多步骤任务

## Advisory Message
[ROUTING-ADVISORY]
This request involves multi-step work or synthesis.
Consider using sessions_spawn with agentId='oe-orchestrator'
```

**示例 2** (oe-subagent-spawn-enrich - 阻止模式):
```yaml
## Blocking Logic

Writer agents (oe-script_coder) require a valid project context.
If no project is discovered (project_kind is "default"), the hook returns:

{
  "unsafe": true,
  "enriched_payload": {
    "unsafe_reason": "BLOCKED: Cannot spawn oe-script_coder without a valid project..."
  }
}
```

**优缺点**:
- ✅ 灵活 - 可针对不同事件类型定制响应
- ✅ 强制力可选 - advisory 建议或 blocking 阻止
- ⭐⭐ 实现中等 - 需要了解 OpenClaw 事件系统
- ❌ 不够直观 - 需要理解事件和 hook 机制

---

#### 5. Runtime Extension (运行时扩展)

| 属性 | 评分 |
|------|------|
| **复杂度** | ⭐⭐⭐ 中等 |
| **直观性** | ❌ 不够直观 |
| **强制力** | 🔴 强 |

**作用原理**:
注册为 OpenClaw 扩展，通过 `before_tool_call` 拦截每个工具调用。检查是否为 Main 会话，若是则用自定义消息阻止被禁止的工具。

**实现位置**:
`extensions/openclaw-enhance-runtime/index.ts`

**代码示例**:
```typescript
// before_tool_call hook
export async function before_tool_call(params: BeforeToolCallParams) {
  const { tool_name, session_id } = params;
  
  if (isMainSession(session_id)) {
    const forbidden = ['edit', 'write', 'exec', 'web_search', ...];
    if (forbidden.includes(tool_name)) {
      return {
        block: true,
        blockReason: `CRITICAL RULE VIOLATION: The 'main' session is strictly 
          FORBIDDEN from using the '${tool_name}' tool...`
      };
    }
  }
}
```

**优缺点**:
- ✅ 强制力最强 - 在工具调用层面直接拦截
- ✅ 实时生效 - 无需重启 agent
- ⭐⭐ 实现中等 - 需要 TypeScript 扩展开发
- ❌ 不直观 - 扩展机制隐藏，不明显
- ❌ 维护成本 - 扩展代码需要随 OpenClaw 更新

---

### Tier 3: 高复杂度

#### 6. Session Isolation & Ownership Binding (会话隔离和所有权绑定)

| 属性 | 评分 |
|------|------|
| **复杂度** | ⭐⭐⭐⭐ 复杂 |
| **直观性** | ❌ 不直观 |
| **强制力** | 🔴 强 |

**作用原理**:
通过 `(channel_type, channel_conversation_id) -> session_id` 的强绑定，防止会话劫持。每次重启递增 `restart_epoch`，使旧绑定失效。

**实现位置**:
- `src/openclaw_enhance/runtime/session_isolation.py`
- `extensions/openclaw-enhance-runtime/src/runtime-bridge.ts`

**机制**:
1. **Ownership Binding**: 外部身份映射到 OpenClaw 会话
2. **Fail-Closed**: 身份验证失败时默认拒绝会话复用
3. **Restart Epoch**: 每次重启递增 epoch，旧绑定失效

**优缺点**:
- ✅ 安全性最高 - 防止会话劫持和跨渠道冲突
- ⭐⭐⭐⭐ 实现复杂 - 涉及多个组件
- ❌ 不直观 - 概念抽象，维护难度大

---

#### 7. Output Sanitization (输出清理)

| 属性 | 评分 |
|------|------|
| **复杂度** | ⭐ 简单 |
| **直观性** | ✅ 直观 |
| **强制力** | 🟡 中 |

**作用原理**:
在 agent 输出发送给用户前，自动剥离内部协议标记（如 `[Pasted ~]`, `<|tool_call...|>`）

**实现位置**:
`extensions/openclaw-enhance-runtime/src/runtime-bridge.ts`

**代码示例**:
```typescript
export function sanitizeEnhanceOutwardText(text: string): string {
  const markers = ['[Pasted ~]', '<|tool_call', '<|thought'];
  for (const marker of markers) {
    text = text.replace(new RegExp(marker, 'g'), '');
  }
  return text;
}
```

**优缺点**:
- ✅ 实现简单 - 纯字符串替换
- ✅ 直观易懂 - 清理逻辑清晰
- 🟡 强制力中等 - 仅过滤特定标记

---

## 总结表格

| 方法 | 复杂度 | 直观性 | 强制力 | 推荐优先级 |
|------|--------|--------|--------|-----------|
| **Tool Gate** | ⭐ 简单 | ✅ 直观 | 🔴 强 | 🥇 最高 |
| **Workspace AGENTS.md** | ⭐ 简单 | ✅ 直观 | 🟡 中 | 🥇 最高 |
| **Skill 约束** | ⭐⭐ 简单 | ✅ 直观 | 🟡 中 | 🥇 最高 |
| **Output Sanitization** | ⭐ 简单 | ✅ 直观 | 🟡 中 | 🥈 高 |
| **Hook (advisory)** | ⭐⭐⭐ 中等 | ✅ 直观 | 🟡 中 | 🥈 高 |
| **Hook (blocking)** | ⭐⭐⭐ 中等 | ⚠️ 一般 | 🔴 强 | 🥈 高 |
| **Runtime Extension** | ⭐⭐⭐ 中等 | ❌ 不直观 | 🔴 强 | 🥉 中 |
| **Session Isolation** | ⭐⭐⭐⭐ 复杂 | ❌ 不直观 | 🔴 强 | 🥉 低 |

---

## 在 openclaw-enhance 中的应用

当前 `openclaw-enhance` 项目已实现的控制手段:

| 手段 | 文件位置 | 状态 |
|------|----------|------|
| Tool Gate | `src/openclaw_enhance/install/main_tool_gate.py` | ✅ 已实现 |
| Runtime Extension | `extensions/openclaw-enhance-runtime/` | ✅ 已实现 |
| Workspace AGENTS.md | `workspaces/*/AGENTS.md` | ✅ 已实现 |
| Skill 约束 | `skills/*/SKILL.md` | ✅ 已实现 |
| Hook (routing-gate) | `hooks/oe-main-routing-gate/` | ✅ 已实现 |
| Hook (spawn-enrich) | `hooks/oe-subagent-spawn-enrich/` | ✅ 已实现 |
| Session Isolation | `src/openclaw_enhance/runtime/session_isolation.py` | ✅ 已实现 |
| Output Sanitization | `extensions/openclaw-enhance-runtime/src/runtime-bridge.ts` | ✅ 已实现 |

---

## 建议添加到 AGENTS.md 的内容

在 AGENTS.md 中新增 "Agent 行为控制机制" 章节，按照上述优先级列表说说明已实现和可用的控制手段。