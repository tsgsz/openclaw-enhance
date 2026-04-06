# OpenCode Agent Instructions

## Mission

`openclaw-enhance` augments OpenClaw with multi-task handling and operational visibility **without modifying OpenClaw core source code**. Uses OpenClaw's native extension points: skills, hooks, extensions, and agent workspaces.

## Non-Invasive Boundaries (Hard Rules)

1. **No OpenClaw source code edits** — all capabilities via plugins, hooks, skills, agents
2. **No runtime file modifications** — never modify main's `AGENTS.md`, `TOOLS.md`, or config at runtime (install-time modifications are allowed and documented)
3. **CLI-first operations** — prefer OpenClaw CLI over direct config edits
4. **Minimal workflow intrusion** — provide tools without changing OpenClaw's core logic (hooks and skills extend behavior via native extension points)

## Required Reading Order

**Before ANY design or development work:**

1. **Read this file** (`AGENTS.md`) — you're here
2. **Read the handbook** (`docs/opencode-iteration-handbook.md`) — current architecture state and permanent progress
3. **Read relevant workspace `AGENTS.md`** — for workspace-specific work (see hierarchy below)
4. **Read domain-specific docs** — architecture, operations, install as needed

**Never start coding before completing steps 1-2.**

## Source of Truth Map

| Topic | Canonical Document |
|-------|-------------------|
| Project intent | `README.md` (Chinese, original) |
| Current architecture | `docs/architecture.md` |
| Runtime behavior | `docs/operations.md` |
| Installation/uninstall | `docs/install.md` |
| Routing/transport boundaries | `docs/adr/0002-native-subagent-announce.md` |
| Watchdog authority | `docs/adr/0003-watchdog-authority.md` |
| Current design status | `docs/opencode-iteration-handbook.md` |
| Workspace-specific rules | `workspaces/{name}/AGENTS.md` |
| Worker routing metadata | AGENTS.md frontmatter in each workspace |
| Worker tool definitions | `workspaces/{name}/TOOLS.md` |
| System capability playbook | `PLAYBOOK.md` (安装时部署到 `~/.openclaw/openclaw-enhance/PLAYBOOK.md`) |
| Project registry state | `project-registry.json` (at `~/.openclaw/openclaw-enhance/project-registry.json`) |
| Agent control mechanisms | `.sisyphus/drafts/openclaw-agent-control-mechanisms.md` |

## Agent Behavior Control Mechanisms

OpenClaw provides multiple mechanisms to control and constrain agent behavior. These are listed by **priority** (simple → complex, intuitive → obscure):

### Tier 1: Simple + Intuitive + Strong Enforcement (Preferred)

#### 1. Tool Gate (Main Session Tool Restrictions)
| Complexity | Intuitiveness | Enforcement |
|------------|---------------|-------------|
| ⭐ Simple | ✅ Intuitive | 🔴 Strong |

**作用**: 在 Main 会话的 `AGENTS.md` 中注入工具限制块，明确禁止/允许特定工具。

**实现**: `src/openclaw_enhance/install/main_tool_gate.py`

```markdown
## 🚫 Main 主会话工具限制

严禁 Main 主会话直接使用以下工具：
- `edit` / `write` — 禁止修改或创建任何文件
- `exec` — 禁止执行任何命令
- `web_search` / `web_fetch` — 禁止自行进行网络研究

Main 会话仅允许：
- `read` — 读取文件（仅限查看）
- `sessions_spawn` — 分发给子agent
- `message` — 回复用户
```

---

#### 2. Workspace AGENTS.md (Agent Permission Boundaries)
| Complexity | Intuitiveness | Enforcement |
|------------|---------------|-------------|
| ⭐ Simple | ✅ Intuitive | 🟡 Medium |

**作用**: 每个 workspace 拥有独立的 `AGENTS.md`，通过 YAML frontmatter 定义角色和能力边界。

**实现**: `workspaces/*/AGENTS.md`

```yaml
authority:
  permitted:
    - read_runtime_state
    - send_session_message
  prohibited:
    - kill_processes
    - edit_user_repos
    - modify_non_owned_config
```

---

#### 3. Skill 约束 (Skill Contracts)
| Complexity | Intuitiveness | Enforcement |
|------------|---------------|-------------|
| ⭐⭐ Simple-Medium | ✅ Intuitive | 🟡 Medium |

**作用**: Skill 是 Markdown 契约文件，定义 agent 的行为模式和约束。

**实现**: `skills/*/SKILL.md`

```markdown
## Iron Rule

Main session is FORBIDDEN from using these tools:
- `edit`, `write`, `exec`
- `web_search`, `web_fetch`

Main session is ONLY allowed to use:
- `read`, `sessions_spawn`, `message`
```

---

### Tier 2: Medium Complexity

#### 4. Hook 系统 (Event Interception)
| Complexity | Intuitiveness | Enforcement |
|------------|---------------|-------------|
| ⭐⭐⭐ Medium | ✅/⚠️ Varies | 🟡 Medium (advisory) / 🔴 Strong (blocking) |

**作用**: Hook 拦截 OpenClaw 事件，可提供建议(advisory)或阻止(blocking)操作。

**两种模式**:
- **Advisory**: 提供建议，agent 可选择不听从
- **Blocking**: 返回 `unsafe: true`，阻止操作执行

**实现**: `hooks/oe-main-routing-gate/HOOK.md`, `hooks/oe-subagent-spawn-enrich/HOOK.md`

```yaml
# Advisory example
event: message:preprocessed
behavior: 检测复杂任务，建议使用 sessions_spawn

# Blocking example
event: subagent_spawning
response:
  unsafe: true
  reason: "BLOCKED: Cannot spawn oe-script_coder without valid project..."
```

---

#### 5. Runtime Extension (运行时扩展)
| Complexity | Intuitiveness | Enforcement |
|------------|---------------|-------------|
| ⭐⭐⭐ Medium | ❌ Not intuitive | 🔴 Strong |

**作用**: 注册为 OpenClaw 扩展，通过 `before_tool_call` 在工具调用层面直接拦截。

**实现**: `extensions/openclaw-enhance-runtime/index.ts`

```typescript
// before_tool_call hook - 强制拦截
if (isMainSession(session_id) && forbidden.includes(tool_name)) {
  return { block: true, blockReason: "..." };
}
```

---

### Tier 3: High Complexity

#### 6. Session Isolation & Ownership Binding
| Complexity | Intuitiveness | Enforcement |
|------------|---------------|-------------|
| ⭐⭐⭐⭐ Complex | ❌ Not intuitive | 🔴 Strong |

**作用**: 通过 `(channel_type, channel_conversation_id) -> session_id` 强绑定防止会话劫持。

**实现**: `src/openclaw_enhance/runtime/session_isolation.py`

---

#### 7. Output Sanitization
| Complexity | Intuitiveness | Enforcement |
|------------|---------------|-------------|
| ⭐ Simple | ✅ Intuitive | 🟡 Medium |

**作用**: 自动剥离内部协议标记（`[Pasted ~]`, `<|tool_call...|>`）

**实现**: `extensions/openclaw-enhance-runtime/src/runtime-bridge.ts`

---

### Summary Table

| Method | Complexity | Intuitiveness | Enforcement | Priority |
|--------|------------|---------------|-------------|----------|
| **Tool Gate** | ⭐ Simple | ✅ Intuitive | 🔴 Strong | 🥇 |
| **Workspace AGENTS.md** | ⭐ Simple | ✅ Intuitive | 🟡 Medium | 🥇 |
| **Skill 约束** | ⭐⭐ Simple | ✅ Intuitive | 🟡 Medium | 🥇 |
| **Output Sanitization** | ⭐ Simple | ✅ Intuitive | 🟡 Medium | 🥈 |
| **Hook (advisory)** | ⭐⭐⭐ Medium | ✅ Intuitive | 🟡 Medium | 🥈 |
| **Hook (blocking)** | ⭐⭐⭐ Medium | ⚠️ Varies | 🔴 Strong | 🥈 |
| **Runtime Extension** | ⭐⭐⭐ Medium | ❌ Not intuitive | 🔴 Strong | 🥉 |
| **Session Isolation** | ⭐⭐⭐⭐ Complex | ❌ Not intuitive | 🔴 Strong | 🥉 |

**Recommendation**: Prefer Tier 1 methods (Tool Gate, Workspace AGENTS.md, Skills) for most use cases. Use higher tiers only when Tier 1 methods are insufficient.

### Workspace AGENTS.md 精简原则

**Skill 是 Native 机制**：Skill 文件存在于 `skills/` 或 `workspaces/*/skills/` 目录下，OpenClaw 会自动发现和加载。**不需要在 AGENTS.md 里手动声明 Skills**。

**Body 应只包含**：
- Frontmatter（核心元数据，保留完整）
- 一句话 Role 说明

**Body 应删除**：
- `## Session Startup` — TOOLS.md 加载是 native 机制
- `## Skills` — Skill 文件存在即自动加载，无需声明
- `## Boundaries` — Frontmatter 的 `rejects`/`mutation_mode` 已定义
- `## Version` — 无实际作用
- 中文冗余描述 — Frontmatter `description` 已定义

## Session State vs Permanent Memory

**`.sisyphus/*` is session execution state ONLY** — not permanent architectural truth:
- `.sisyphus/plans/*.md` — active/completed plan tracking
- `.sisyphus/boulder.json` — current session pointer
- `.sisyphus/evidence/*` — task execution artifacts

**Permanent project memory lives in:**
- `docs/opencode-iteration-handbook.md` — durable design state and progress
- `docs/adr/*.md` — architectural decision records
- `docs/*.md` — canonical system documentation

## Workspace AGENTS.md Hierarchy

**Rule**: Workspace-specific work follows nearest `AGENTS.md`:
- `workspaces/oe-orchestrator/AGENTS.md` — full-capability planning + dispatch
- `workspaces/oe-searcher/AGENTS.md` — read-only research, web search
- `workspaces/oe-syshelper/AGENTS.md` — read-only introspection
- `workspaces/oe-tool-recovery/AGENTS.md` — tool failure recovery specialist
- `workspaces/oe-script_coder/AGENTS.md` — code development with tests
- `workspaces/oe-watchdog/AGENTS.md` — session monitoring, narrow authority

## Pre-Design Checklist

Before proposing any design change:
- [ ] Read handbook current design status section
- [ ] Read relevant ADRs for boundary constraints
- [ ] Check if change affects routing (must respect `sessions_spawn` native execution)
- [ ] Check if change affects worker boundaries (must respect workspace `AGENTS.md`)

## Pre-Development Checklist

Before implementing any code:
- [ ] Confirm design follows skill-first routing model
- [ ] Confirm design respects native `sessions_spawn` / announce execution
- [ ] Verify no runtime file modifications to main OpenClaw
- [ ] Check workspace-specific `AGENTS.md` if touching worker code
- [ ] Run `python -m openclaw_enhance.cli docs-check` to validate doc alignment

## Current Architecture Milestone

**Completed**: `session-isolation-restart-guardrails` — Mandatory real-environment validation and report generation is the merge gate for all features. Session isolation and restart safety are now enforced.

**See handbook for full current state, orchestration loop rules, and invariants.**

## Post-Development Checklist (MANDATORY)

After completing any feature development:
- [ ] Unit tests pass
- [ ] Integration tests pass
  - [ ] **Real-environment validation loop completed**
  - [ ] Feature class identified (see `docs/testing-playbook.md`)
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class <class> --report-slug <slug>` passes
  - [ ] Validation report saved to `docs/reports/`
- [ ] `python -m openclaw_enhance.cli docs-check` passes
- [ ] **PLAYBOOK.md 已更新**（如果本次变更影响了以下任何内容）：
  - Agent 新增/删除/职责变更
  - Hook 新增/删除/行为变更
  - Skill 新增/删除/行为变更
  - Extension 变更
  - openclaw.json 配置修改项变更
  - 安装产物（新增/删除文件或目录）
  - 工具限制（Tool Gate）规则变更
  - Watchdog/监控机制变更
  - CLI 命令新增/删除

**Critical Rule**: Features cannot be merged without a successful real-environment validation report in `docs/reports/`. Unit/integration tests verify code correctness, but only real-environment testing verifies actual functionality in the OpenClaw environment.

**Critical Rule**: `PLAYBOOK.md` 是系统能力的权威清单，安装时会部署到 `~/.openclaw/openclaw-enhance/PLAYBOOK.md` 供 AI 和人类查阅。每次 commit 前必须检查是否需要同步更新。

See `docs/testing-playbook.md` for the feature-class matrix and detailed validation procedures.
