# Workspace AGENTS.md 精简计划

## 目标
精简 6 个 workspace 的 AGENTS.md，删除废话，保留核心元数据。

## 变更文件
1. `workspaces/oe-orchestrator/AGENTS.md`
2. `workspaces/oe-watchdog/AGENTS.md`
3. `workspaces/oe-tool-recovery/AGENTS.md`
4. `workspaces/oe-searcher/AGENTS.md`
5. `workspaces/oe-syshelper/AGENTS.md`
6. `workspaces/oe-script_coder/AGENTS.md`
7. `AGENTS.md` (项目主文件 - 添加 Skill Native 说明)

## 变更内容

### 1. 项目主 AGENTS.md - 添加 Skill Native 说明

在 "Agent Behavior Control Mechanisms" 章节的 Tier 1 方法后，添加：

```markdown
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
```

### 2. 各 Workspace AGENTS.md 精简模板

**精简前**: 约 50-70 行
**精简后**: 约 25-30 行

#### oe-orchestrator (当前 72 行 → 目标 30 行)

```markdown
---
schema_version: 1
agent_id: oe-orchestrator
workspace: oe-orchestrator
routing:
  description: High-capability dispatcher for project discovery, worker routing, result synthesis, and publishing operations.
  capabilities: [introspection, documentation, monitoring, recovery, publishing]
  accepts: [complex_tasks, multi_agent_tasks, orchestration_requests]
  rejects: [direct_worker_execution, main_session_mutation]
  output_kind: orchestration_report
  mutation_mode: repo_write
  can_spawn: true
  requires_tests: false
  session_access: read_only
  network_access: web_research
  repo_scope: full_repo
  cost_tier: premium
  model_tier: premium
  duration_band: long
  parallel_safe: false
  priority_boost: 3
  tool_classes: [repo_write, code_search, orchestration]
---

# oe-orchestrator

Dispatcher for complex tasks — selects workers, manages orchestration rounds, and synthesizes results.
```

#### oe-watchdog (当前 57 行 → 目标 28 行)

```markdown
---
schema_version: 1
agent_id: oe-watchdog
workspace: oe-watchdog
routing:
  description: Monitoring agent for timeout detection, status tracking, and reminder delivery.
  capabilities: [monitoring]
  accepts: [monitoring_tasks, health_check_requests]
  rejects: [file_modifications, code_changes, test_execution, git_operations]
  output_kind: monitoring_report
  mutation_mode: runtime_only
  can_spawn: false
  requires_tests: false
  session_access: runtime_only
  network_access: none
  repo_scope: none
  cost_tier: cheap
  model_tier: cheap
  duration_band: short
  parallel_safe: true
  priority_boost: 2
  tool_classes: [session_inspect, state_write]
---

# oe-watchdog

Monitors session timeouts and delivers health check reminders.
```

#### oe-tool-recovery (当前 55 行 → 目标 28 行)

```markdown
---
schema_version: 1
agent_id: oe-tool-recovery
workspace: oe-tool-recovery
routing:
  description: Leaf-node recovery specialist for failure diagnosis and recovery suggestions.
  capabilities: [recovery]
  accepts: [failed_tool_context]
  rejects: [business_task_execution, file_modifications, agent_spawning]
  output_kind: recovery_suggestion
  mutation_mode: read_only
  can_spawn: false
  requires_tests: false
  session_access: none
  network_access: web_research
  repo_scope: selected_files
  cost_tier: standard
  model_tier: standard
  duration_band: medium
  parallel_safe: true
  priority_boost: 1
  tool_classes: [web_search, doc_fetch, code_search]
---

# oe-tool-recovery

Diagnoses failed tool calls and provides recovery suggestions.
```

#### oe-searcher (当前 55 行 → 目标 28 行)

```markdown
---
schema_version: 1
agent_id: oe-searcher
workspace: oe-searcher
routing:
  description: Research-focused agent for web search, documentation lookup, and code examples.
  capabilities: [research, documentation]
  accepts: [research_tasks, documentation_queries, library_discovery]
  rejects: [file_modifications, code_implementation, subagent_spawning]
  output_kind: research_report
  mutation_mode: read_only
  can_spawn: false
  requires_tests: false
  session_access: none
  network_access: web_research
  repo_scope: none
  cost_tier: cheap
  model_tier: cheap
  duration_band: medium
  parallel_safe: true
  priority_boost: 0
  tool_classes: [web_search, web_fetch, code_search]
---

# oe-searcher

Performs web searches and documentation lookups for research tasks.
```

#### oe-syshelper (当前 56 行 → 目标 28 行)

```markdown
---
schema_version: 1
agent_id: oe-syshelper
workspace: oe-syshelper
routing:
  description: System introspection agent for file exploration, session analysis, and code search.
  capabilities: [introspection]
  accepts: [introspection_tasks, session_summaries, symbol_lookups]
  rejects: [file_modifications, state_changes, subagent_spawning]
  output_kind: introspection_report
  mutation_mode: read_only
  can_spawn: false
  requires_tests: false
  session_access: read_only
  network_access: none
  repo_scope: selected_files
  cost_tier: cheap
  model_tier: cheap
  duration_band: short
  parallel_safe: true
  priority_boost: 0
  tool_classes: [code_search, session_inspect]
---

# oe-syshelper

Explores file structures, analyzes session history, and searches code.
```

#### oe-script_coder (当前 55 行 → 目标 28 行)

```markdown
---
schema_version: 1
agent_id: oe-script_coder
workspace: oe-script_coder
routing:
  description: Development-focused agent for script writing, test creation, and debugging.
  capabilities: [code_generation, testing]
  accepts: [coding_tasks, test_creation, bug_fixes]
  rejects: [system_level_changes, session_inspection, background_task_management]
  output_kind: code_and_tests
  mutation_mode: repo_write
  can_spawn: false
  requires_tests: true
  session_access: none
  network_access: none
  repo_scope: full_repo
  cost_tier: standard
  model_tier: standard
  duration_band: long
  parallel_safe: false
  priority_boost: 1
  tool_classes: [repo_write, bash_exec, test_runner, code_search]
---

# oe-script_coder

Writes scripts, creates tests, and implements code modules.
```

## 执行命令

```bash
# 查看当前行数
wc -l workspaces/*/AGENTS.md AGENTS.md

# 精简后验证
wc -l workspaces/*/AGENTS.md AGENTS.md
```

## 预期结果

| 文件 | 精简前 | 精简后 | 减少 |
|------|--------|--------|------|
| oe-orchestrator | 72 行 | 30 行 | -58% |
| oe-watchdog | 57 行 | 28 行 | -51% |
| oe-tool-recovery | 55 行 | 28 行 | -49% |
| oe-searcher | 55 行 | 28 行 | -49% |
| oe-syshelper | 56 行 | 28 行 | -50% |
| oe-script_coder | 55 行 | 28 行 | -49% |
| **总计** | **350 行** | **~170 行** | **~51%** |

## 验证清单

- [ ] Frontmatter 完整保留
- [ ] Role 部分精简为一句话
- [ ] 删除 Session Startup
- [ ] 删除 Skills 列表
- [ ] 删除 Boundaries 章节
- [ ] 删除 Version footer
- [ ] 删除中文冗余描述
