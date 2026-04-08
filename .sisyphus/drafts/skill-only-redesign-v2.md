# openclaw-enhance v2: Skill-Only Redesign

**Date**: 2026-04-07
**Status**: Draft - Pending User Approval
**Version**: 2.0.0 (breaking change from v1 agent-based model)

---

## TL;DR

从"维护 agents 替你工作"转向"提供可组合的 skill 配方，教会你自己的 main agent"。移除所有 agent/workspace 模型，改为纯 skills + hooks + 极少量 extensions 的架构。用户通过选择加载哪些 skills 来定制自己的 agent soul。

---

## Context

### Why Redesign

v1 架构维护成本过高：
- 11 个 agents（6 核心 + 5 领域专家）需要持续更新和维护能力定义
- workspace/AGENTS.md/TOOLS.md 体系复杂，用户难以自定义
- agent 能力边界模糊，职责重叠

### Design Intent

用户定义自己的 SOUL（加载哪些 skills），系统提供可组合的 skill 配方。Main agent 的行为由加载的 skills 决定，而非固定的 agent 定义。

---

## Architecture

### Components

| 组件 | 形式 | 职责 |
|------|------|------|
| **Skill Contracts** | `.md` 文件 + `lib/` 代码 | 决策逻辑 + spawn 配方 |
| **Hook** | TypeScript | 全局 enrichment + 安全过滤 |
| **Extension** | TypeScript | Tool gate（阻塞 forbidden 工具） |
| **Manifest** | JSON | 记录安装状态 |

### 目录结构

```
~/.openclaw/openclaw-enhance/
├── manifest.json              # 记录安装了什么、去哪里
├── skills/                    # 全局 skills（所有 workspace 共享）
│   ├── oe-model-discover/     # Utility: 模型自动发现
│   ├── oe-eta-estimator/      # Utility: ETA 估算
│   ├── oe-timeout-state-sync/ # Utility: 超时状态同步
│   ├── oe-tag-router/         # Orch: 标签推理 + 匹配引擎
│   ├── oe-spawn-search/       # Orch: research 标签 → spawn 配方
│   ├── oe-spawn-coder/       # Orch: code 标签 → spawn 配方
│   ├── oe-spawn-ops/          # Orch: ops 标签 → spawn 配方
│   ├── oe-project-context/    # Utility: 项目上下文注入
│   ├── oe-git-context/        # Utility: Git 历史上下文
│   ├── oe-memory-sync/        # Utility: 记忆读取
│   └── oe-publish/            # Utility: 发布工具
└── hooks/                     # Hook 资产
    └── oe-subagent-spawn-enrich/   # 全局 enrichment

~/.openclaw/workspace/{main}/skills/   # Main 专属 skills（默认安装位置）
```

### Skill 分类

| 类型 | 示例 | 触发方式 |
|------|------|---------|
| **Utility Skills** | `oe-eta-estimator`, `oe-timeout-state-sync`, `oe-project-context`, `oe-git-context`, `oe-memory-sync`, `oe-publish` | 始终被动注入，不参与标签匹配 |
| **Orch Skills** | `oe-tag-router`, `oe-spawn-*` | 参与标签路由决策 |

### SOUL（README Prompt）

不再作为 skill，改为在 README 里提供一段 SOUL prompt：

> **Main Agent SOUL**：
> - 你**禁止自己直接执行**大段任务（>5 tool calls 或 >15 分钟）
> - 所有复杂任务必须通过 `sessions_spawn` 分发给 sub-agent
> - 你只做**路由 + 组合**：分析任务 → 打标签 → spawn → 合并结果
> - ETA 必须预先声明

---

## Skill Contracts

### Skill 结构

```
skill-name/
├── SKILL.md           # 主文件：frontmatter + 决策逻辑 + spawn 配方
├── lib/               # 可选：JS 辅助库
│   ├── spawn-helper.js
│   └── cost-estimator.js
└── references/        # 可选：参考数据
    └── model-pricing.md
```

### Frontmatter 格式

```yaml
---
name: oe-spawn-search
version: 1.0.0
description: 教会 main 在需要研究/搜索时 spawn researcher
tags: [research, web_search, investigation]  # 标签路由
models:
  default: gpt-4o-mini
  reasoning: gpt-4o
triggers:
  - "research"
  - "search"
  - "investigate"
  - "look up"
  - "find information"
allowed-tools: "Read, WebSearch, sessions_spawn"
skill-type: orch  # orch | utility
install-location: global  # global | main
---
```

### Spawn Skills（标签驱动）

每个 spawn skill 定义：
- 匹配什么标签
- 用什么模型
- 构造什么 prompt
- 传入什么 context

```markdown
# Spawn Searcher

## 标签匹配
- `research` → 本 skill
- `web_search` → 本 skill
- `investigation` → 本 skill

## 模型选择
- 简单研究：minimax-2.7 -> kimi2.5
- 深度研究：claudeopus -> gpt -> minimax2.7 -> kimi2.5

## Spawn 配方

当检测到 `research` 标签时：
```
sessions_spawn({
  task: """
  You are a research specialist.

  Task: {task_description}

  Context:
  - Project: {project_context}
  - Research depth: {depth}

  Output: Structured findings with sources.
  """,
  model: "{selected_model}",
  context: {
    tags: ["research"],
    skill: "oe-spawn-search",
    project: "{project}"
  }
})
```

---

## Hooks

### oe-subagent-spawn-enrich

**作用**：所有 spawn 事件的全局 enrichment 层

**功能**：
1. 注入 `task_id`（唯一标识）
2. 注入 `eta_bucket`（short/medium/long）
3. 注入 `dedupe_key`（防止重复分发）
4. 注入 `ownership`（channel_type, channel_conversation_id）
5. 注入 `project_context`（从项目注册表获取）

**与 Skill 的分工**：
- Hook = 全局安全/隔离层（所有 spawn 都经过）
- Skill = 业务分发逻辑（标签匹配、prompt 构造）

---

## Extension

### oe-runtime

**作用**：Tool gate + 输出消毒

**功能**：
1. 阻塞 main session 的 forbidden 工具（edit/write/exec 等直接文件操作）
2. 返回引导信息：`Use sessions_spawn to delegate work`
3. 消毒内部协议标记（`[Pasted ~]`, `<|tool_call...|>`）
4. Session 隔离验证

---

## 安装与卸载

### CLI 命令

```bash
# 安装所有 skills 到 main workspace
python -m openclaw_enhance.cli install --target main

# 安装所有 skills 到全局
python -m openclaw_enhance.cli install --target global

# 安装特定 skill
python -m openclaw_enhance.cli install --skill oe-spawn-search --target main

# 卸载
python -m openclaw_enhance.cli uninstall --target main

# 查看状态
python -m openclaw_enhance.cli status
```

### Manifest 格式

```json
{
  "version": "2.0.0",
  "skills": {
    "oe-model-discover": { "location": "global", "version": "1.0.0" },
    "oe-tag-router": { "location": "main", "version": "1.0.0" },
    "oe-spawn-search": { "location": "global", "version": "1.0.0" }
  },
  "hooks": {
    "oe-subagent-spawn-enrich": { "enabled": true }
  },
  "extension": {
    "oe-runtime": { "enabled": true }
  }
}
```

---

## 参考的社区技能（自己实现）

### 参考但不整合

| 社区技能 | 参考内容 | 自己实现方式 |
|---------|---------|------------|
| **SwitchBoard** | Tier-based 模型路由 | 自己实现 `oe-model-discover` + `oe-tag-router` |
| **Subagent-Architecture** | Spawn 模板模式 | 自己实现 `oe-spawn-*` skills |

### 模型自动发现（自己实现）

**核心思想**：不硬编码模型列表。通过 OpenRouter API 动态获取可用模型，按价格自动分层。

#### 模型发现流程

**核心**：发现 OpenClaw 当前已有的模型，不依赖外部 API。

```
1. 从 OpenClaw 配置和环境获取可用模型列表
   - 读取 openclaw.json 中的 model 配置
   - 从环境变量/配置中获取已配置的 API keys
   - 检查可用的 provider endpoints

2. 按价格手动分层（市场定价相对稳定）
   Tier 0 (Free): price = 0
   Tier 1 (Cheap): price < $0.50/M tokens
   Tier 2 (Mid): $0.50/M ≤ price < $5/M
   Tier 3 (Premium): price ≥ $5/M

3. 模型能力判断
   - 从模型 ID 推断能力（ opus > sonnet > haiku, gpt-4 > gpt-3.5）
   - 上下文长度查表
   - 工具支持情况

4. 用户可覆盖默认分层
```

#### Tier 分配算法

```python
# 手动维护的模型价格表（参考市场定价，定期更新）
MODEL_PRICING = {
    # Tier 0 (Free)
    "free": [],
    # Tier 1 (Cheap < $0.50/M)
    "cheap": [
        "gpt-4o-mini", "gpt-4o-mini-2024-07-18",
        "claude-3-haiku", "claude-3-haiku-20240229",
        "gemini-2.0-flash", "gemini-2.0-flash-lite",
        "deepseek-chat", "qwen-2.5-coder-27b-instruct",
    ],
    # Tier 2 (Mid $0.50 - $5/M)
    "mid": [
        "gpt-4o", "gpt-4o-2024-05-13",
        "claude-3.5-sonnet", "claude-3.5-sonnet-20241022",
        "o3-mini", "o3-mini-2025-01-31",
        "gemini-2.5-pro", "gemini-2.5-pro-2025-01-23",
    ],
    # Tier 3 (Premium >= $5/M)
    "premium": [
        "claude-opus-4-6", "claude-opus-4-5-20250514",
        "o1", "o1-2024-12-17",
        "gpt-4.5", "gpt-4.5-turbo-2024-05-12",
    ],
}

def assign_tier(model_id):
    for tier, models in MODEL_PRICING.items():
        if model_id in models:
            return tier
    # 未知模型：根据模型名称推断
    return infer_tier(model_id)

def select_model(task_type, available_models):
    candidates = [m for m in available_models]
    
    if task_type == "routine":
        # 选最便宜的
        return min(candidates, key=lambda m: get_price(m))
    elif task_type == "moderate":
        # 选中间价位
        tier = get_tier(m)
        if tier in ("cheap", "mid"):
            return m
        return candidates[0]
    elif task_type == "complex":
        # 选最好的
        return max(candidates, key=lambda m: get_price(m))
```

#### 配置项

```yaml
# openclaw.json
model_tier:
  # 用户可覆盖默认分层
  overrides:
    "my-custom-model": "cheap"  # 将自定义模型加入便宜层
  preferences:
    default_tier: "mid"  # 默认使用中间层
    fallback_tier: "cheap"  # 高级模型不可用时降级
```

#### Spawn Skills 参考 Subagent-Architecture 模式

自己实现的 `oe-spawn-*` skills 采用以下模式：

1. **Security Proxy Pattern**: 最小 context，工具白名单，输出消毒
2. **Researcher Pattern**: 多源验证，结构化输出
3. **Phased Pattern**: 分阶段执行（简单任务跳过）
4. **Cost-aware**: spawn 前成本估算

---

## 移除的内容（v1 → v2）

| v1 组件 | v2 状态 | 原因 |
|---------|--------|------|
| oe-orchestrator | ❌ 移除 | 路由逻辑分散到 skills |
| oe-searcher | ❌ 移除 | spawn recipe 替代 |
| oe-syshelper | ❌ 移除 | spawn recipe 替代 |
| oe-script_coder | ❌ 移除 | spawn recipe 替代 |
| oe-watchdog | ❌ 移除 | spawn recipe 替代 |
| oe-tool-recovery | ❌ 移除 | 简化为 hook 逻辑 |
| oe-specialist-* | ❌ 移除 | 通用标签路由替代 |
| workspaces/ | ❌ 移除 | 无 agent 定义需求 |
| AgentOS patterns | ❌ 移除 | 用户自定义代码模式 |
| oe-domain-router | ❌ 移除 | 简化为 `oe-tag-router` |
| oe-worker-dispatch | ❌ 移除 | spawn skills 替代 |
| oe-soul (as skill) | ❌ 移除 | 改为 README SOUL prompt |

---

## 实现优先级

### Phase 1: Foundation
1. Manifest 系统 + CLI install/uninstall
2. Hook: `oe-subagent-spawn-enrich`（重写适配 v2）
3. Extension: `oe-runtime`（从 v1 迁移）
4. `oe-model-discover`（发现 OpenClaw 已有模型，按价格分层）
5. Utility Skills: `oe-eta-estimator`, `oe-timeout-state-sync`

### Phase 2: Core Orch
6. `oe-model-discover` skill（发现 OpenClaw 已有模型）
7. `oe-tag-router` skill（参考 SwitchBoard，自己实现）
8. `oe-spawn-search` skill（参考 subagent-architecture，自己实现）
9. README SOUL prompt 编写

### Phase 3: Context Skills
8. `oe-project-context`
9. `oe-git-context`
10. `oe-memory-sync`

### Phase 4: Additional Spawn Skills
11. `oe-spawn-coder`
12. `oe-spawn-ops`
13. `oe-publish`

---

## Success Criteria

1. **零 agent 依赖**：系统不维护任何 agent 定义
2. **可组合性**：用户可选择加载哪些 skills
3. **标签路由**：spawn 决策基于动态标签匹配
4. **Context 纯净**：sub-agent 不继承父 session 的 orch 逻辑
5. **模型自动发现**：通过 OpenRouter API 动态获取，不硬编码模型列表
6. **一键安装/卸载**：所有 skills 通过 CLI 管理
7. **向后兼容**：OpenClaw 原生使用方式不变
8. **SOUL 即 Prompt**：main 行为规则通过 README prompt 提供，非 skill

---

## References

- [SwitchBoard Skill](https://github.com/openclaw/skills/tree/main/skills/gigabit-eth/router) - 模型分层思路参考（自己实现）
- [Subagent Architecture](https://github.com/openclaw/skills/tree/main/skills/donovanpankratz-del/subagent-architecture) - spawn 模式参考（自己实现）
- [OpenClaw Skills Registry](https://github.com/VoltAgent/awesome-openclaw-skills) - 社区技能生态参考
- [Skill-based Task Routing Proposal](https://github.com/openclaw/openclaw/issues/50073) - 路由设计参考
