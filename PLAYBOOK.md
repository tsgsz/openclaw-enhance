## 概述
openclaw-enhance 是一个针对 OpenClaw 的非侵入式增强组件。它通过扩展点、钩子和 Skills，在不修改 OpenClaw 核心源码的前提下，实现了多任务并行处理、自动化运维监控以及操作透明化。

## v2 架构说明

**openclaw-enhance v2 采用纯 Skill 架构**：
- **无工作区 (Workspaces)**：v1 的 agent 工作区已归档至 `~/.openclaw/openclaw-enhance/v1-archive/`
- **无 Agent 注册**：不再使用 `oe-orchestrator`、`oe-searcher` 等托管 Agent
- **纯 Skill 路由**：所有路由逻辑通过 Skills 实现，使用 OpenClaw 原生的 `sessions_spawn` 机制

## 安装产物清单
```
~/.openclaw/
├── openclaw.json                    # 被修改：hooks.internal
├── openclaw-enhance/                # 托管命名空间
│   ├── PLAYBOOK.md                  # 本文件
│   ├── project-registry.json        # 项目注册表（自动生成）
│   ├── install-manifest.json        # 安装清单（组件、版本、回滚点）
│   │   └── runtime-state.json           # 运行时状态（超时、健康检查、ownership、restart_epoch）
│   ├── model-config.json           # ACP opencode 模型优先级配置
│   ├── model-cache.json             # 探查到的可用模型缓存（自动生成）
│   ├── governance/                  # 托管治理目录
│   │   └── archive/                 # 托管归档目录
│   ├── skills/                      # v2 Skills 安装目录
│   │   ├── oe-tag-router/          # 任务标签路由 Skill
│   │   ├── oe-spawn-search/        # 搜索派发 Skill
│   │   ├── oe-spawn-coder/         # 编码派发 Skill
│   │   ├── oe-spawn-ops/           # 运维派发 Skill
│   │   ├── oe-model-discover/      # 模型发现 Skill
│   │   ├── oe-eta-estimator/       # ETA 估算 Skill
│   │   ├── oe-timeout-state-sync/  # 超时状态同步 Skill
│   │   ├── oe-project-context/     # 项目上下文 Skill
│   │   ├── oe-git-context/         # Git 上下文 Skill
│   │   ├── oe-memory-sync/         # 记忆同步 Skill
│   │   └── oe-publish/             # 发布 Skill
│   ├── hooks/                       # Hook 实现
│   │   └── oe-subagent-spawn-enrich/# 子 Agent 派发增强钩子
│   └── logs/                        # 监控日志
│       ├── monitor.log
│       └── monitor.err.log
├── workspace/                       # 主工作区（被修改）
│   ├── AGENTS.md                    # 被注入工具限制（tool gate）
│   └── skills/                      # 主会话 Skill
│       └── oe-tag-router/           # 路由决策 Skill（主会话）
└── extensions/                      # OpenClaw 扩展目录
    └── oe-runtime/                  # 运行时桥接扩展
~/Library/LaunchAgents/              # (仅 macOS)
├── ai.openclaw.enhance.monitor.plist         # 后台监控服务（每60秒）
└── ai.openclaw.session-cleanup.plist         # 托管 session 清理服务（每小时）
```

## Skill 清单

### 主会话 Skills (安装在主工作区)
| Skill ID | 安装位置 | 作用 |
| :--- | :--- | :--- |
| oe-tag-router | 主工作区 | 强制主会话仅执行路由功能，所有具体执行均通过 sessions_spawn 完成 |
| oe-eta-estimator | 主工作区 | 人类直觉 ETA 协议：任务前报 ETA、延期三段式解释、完成晚点说明 |
| oe-timeout-state-sync | 主工作区 | 在主会话与运行时存储之间同步超时状态 |

### 全局 Skills (安装在 openclaw-enhance/skills/)
| Skill ID | 安装位置 | 作用 |
| :--- | :--- | :--- |
| oe-spawn-search | 全局 | 搜索研究任务派发，执行 Web 搜索与文档查找 |
| oe-spawn-coder | 全局 | 编码任务派发，编写代码并运行测试 |
| oe-spawn-ops | 全局 | 运维任务派发，tunnels/backup/launchd/服务检查 |
| oe-model-discover | 全局 | 探查环境中可用的模型并按优先级选择 |
| oe-project-context | 全局 | 项目发现和上下文注入 |
| oe-git-context | 全局 | Git 历史和上下文注入 |
| oe-memory-sync | 全局 | 获取 Main Session 上下文 |
| oe-publish | 全局 | 统一发布网关，将图片、Markdown、前端网页或目录快照发布到公网 |

## Hook 清单
| Hook ID | 触发时机 | 作用 |
| :--- | :--- | :--- |
| oe-subagent-spawn-enrich | subagent_spawning 时 | 注入 task_id、project、eta_bucket、dedupe_key；自动注册 ETA 到 TaskETARegistry |

**注意**: `oe-main-routing-gate` 钩子已在 v2 中移除（不再需要复杂任务路由注入）

## Extension 清单
- oe-runtime: before_tool_call 扩展。该扩展会阻止主会话使用 edit、write、exec 等被禁止的工具；同时提供内部标记（如 [Pasted ~]、<|tool_call...|>）的输出脱敏，并执行会话所有权（ownership）校验。

## 会话隔离与安全护栏 (Session Isolation & Safety Guardrails)

系统通过 `oe-runtime` 和 `oe-subagent-spawn-enrich` 实现了多层级的会话隔离与安全保护：

1. **所有权绑定 (Ownership Binding)**：
   - 建立 `(channel_type, channel_conversation_id) -> session_id` 的强绑定关系。
   - 确保不同渠道（如 Feishu vs Telegram）或不同对话的会话完全隔离，防止任务冲突。
2. **Fail-Closed 策略**：
   - 当身份信息缺失、格式错误（如非字符串 key）或存在歧义时，系统拒绝复用现有会话，强制进入安全失败模式。
3. **重启纪元 (Restart Epoch)**：
   - 每次系统重启都会递增 `restart_epoch`。
   - 旧的会话绑定在重启后被视为过期（stale），必须重新验证所有权后方可恢复，防止重启后的会话劫持。
4. **输出脱敏 (Output Sanitization)**：
   - 自动过滤 enhance 内部控制路径输出中的敏感标记，包括：`[Pasted ~]`、`<|tool_call...|>`、`<|thought...|>` 等。
   - 确保内部协议标记不会泄露给最终用户或干扰外部解析。

## 主会话工具限制（Tool Gate）
主会话（main）的 AGENTS.md 文件被注入了工具限制。系统禁止主会话使用 edit、write、exec、web_search 和 browser。主会话仅允许使用 read、memory_search 和 sessions_spawn 等工具。这一设计的目的是强制主会话扮演路由器的角色，将具体任务分发给专门的 Worker Skill。

## v2 路由模型

在 v2 架构中，路由完全通过 Skills 和 `sessions_spawn` 实现：

```
用户请求
    │
    ▼
主会话 (oe-tag-router Skill)
    │
    ├── 简单任务 (TOOLCALL ≤ 2) ────► 主会话直接处理
    │
    └── 复杂任务 (TOOLCALL > 2) ────► sessions_spawn 派发
                                         │
                                         ▼
                                   对应 Skill 派发
                                   (oe-spawn-search / oe-spawn-coder / oe-spawn-ops)
```

**关键区别 (v1 vs v2)**：
- v1：使用 `oe-orchestrator` Agent 进行编排，存在工作区同步和 Agent 注册
- v2：直接使用 `sessions_spawn` 派发到 Skill，完全基于 OpenClaw 原生机制

## openclaw.json 修改清单
| 配置路径 | 修改内容 |
| :--- | :--- |
| hooks.internal.entries | 启用 oe-subagent-spawn-enrich |
| hooks.internal.enabled | 设置为 true |
| hooks.internal.load.extraDirs | 添加 hooks 目录的路径 |
| plugins.entries.oe-runtime | 启用运行时扩展 |
| acp.enabled | 启用 ACP 外部 Harness 支持 |
| acp.defaultAgent | 默认 ACP Agent (opencode) |
| acp.allowedAgents | 允许的 ACP Agent 列表 [opencode, codex, claude] |

**注意**: v2 不再修改 `agents.list`，不再注册托管 Agent。

## Watchdog 监控机制

在 macOS 环境下，系统会安装两个托管 LaunchAgent：
- `ai.openclaw.enhance.monitor`：每 60 秒运行一次 `monitor_runtime`，负责超时检测与 watchdog 提醒。
- `ai.openclaw.session-cleanup`：每小时运行一次 `python -m openclaw_enhance.cleanup --execute --openclaw-home ... --json`，负责保守清理陈旧/孤儿 session 文件；若要清理 core sessions，需手动显式传 `--include-core-sessions`。

## ETA/Expectation Management Protocol（人类直觉 ETA 协议）

### 设计原则

主会话像一个有责任心的人一样管理用户的预期：
1. **做事前先报 ETA**：给出具体时间窗口，不是笼统的"等一会儿"
2. **延期时解释**：三段式（现在怎样 + 为什么慢了 + 还要多久）
3. **阻塞时区分**：明确说"不是单纯慢，是卡在 X"
4. **完成时交代**：如果比预估久，补一句原因总结

### 刷新策略：克制型

只在以下节点主动同步：
- **开始时**：报 next_update ETA
- **延期时**：三段式解释
- **阻塞时**：说明阻塞点
- **完成晚点时**：补原因总结

### 状态模型

| 状态 | 含义 | 用户可见行为 |
| :--- | :--- | :--- |
| `on_track` | 在 ETA 内 | 不打扰 |
| `delayed` | 超 ETA 但仍在推进 | 三段式延期解释 |
| `blocked` | 明确阻塞点 | 说清楚卡在哪 |
| `stalled` | 长时间无进展 | 疑似停滞提示 |
| `completed_late` | 已完成但晚于 ETA | 补原因总结 |
| `completed_on_time` | 按时完成 | 静默或简短确认 |

**关键转变**：`timeout` 不再是默认延期结果。`delayed` 和 `blocked` 都有明确的用户解释，只有 `stalled` 才接近"疑似停滞"语义。

### CLI 命令

| 命令 | 说明 |
| :--- | :--- |
| `python -m openclaw_enhance.cli eta register --task-id <id> --child <child_id> --parent <parent_id> --minutes <est>` | 注册任务 ETA |
| `python -m openclaw_enhance.cli eta update --task-id <id> --state delayed --reason "范围比预估大" --remaining 5` | 更新任务状态 |
| `python -m openclaw_enhance.cli eta status --task-id <id>` | 查看任务 ETA 状态 |

### 默认话术模板

**开始时**：
> 我来处理，预计 6-8 分钟。如果到时还没做完，我会回来说明现在卡在哪、还需要多久。

**延期时**：
> 我回来同步一下：这件事还在推进，不是卡死。比我刚预估的慢，原因是：范围比预估大。我重新估计还需要 5 分钟左右。

**阻塞时**：
> 我回来同步一下：现在不是单纯变慢，而是遇到了一个明确阻塞。阻塞点在：等待外部 API 返回。如果你还想继续自动处理，预计还需要 10 分钟左右。

**完成晚点时**：
> 好了，实际比我一开始估的时间长一点。主要原因是：中间多跑了一轮检查。现在我把完整结果给你。

## 项目注册系统
管理永久/临时项目的注册、发现和上下文注入。

项目类型：
- 永久项目：用户指定位置（~/workspace），关联 GitHub
- 临时项目：per-task，互不冲突

注册表位置：`~/.openclaw/openclaw-enhance/project-registry.json`

支持的项目类型：python, nodejs, rust, go, java, ruby, php, cpp。

占用锁：永久项目使用占用锁确保互斥访问。

## CLI 命令速查
| 命令 | 说明 |
| :--- | :--- |
| python -m openclaw_enhance.cli status | 查看安装状态 |
| python -m openclaw_enhance.cli doctor | 执行健康检查 |
| python -m openclaw_enhance.cli cleanup-sessions [--dry-run\|--execute] [--include-core-sessions] [--openclaw-home <path>] | 清理陈旧/孤儿 session 状态（默认 dry-run） |
| python -m openclaw_enhance.cli governance diagnose [--json] | 执行治理诊断 |
| python -m openclaw_enhance.cli governance healthcheck [--json] | 执行治理健康检查 |
| python -m openclaw_enhance.cli governance archive-sessions [--dry-run\|--execute] [--json] | 归档陈旧 session |
| python -m openclaw_enhance.cli governance safe-restart [--dry-run] [--json] | 安全重启治理入口 |
| python -m openclaw_enhance.cli governance restart-resume [--json] | 立即重启并返回 resume 信号，同时递增 `restart_epoch` 纪元 |
| python -m openclaw_enhance.cli governance subagents mark-done/mark-dead/set-status/set-eta/merge-state | 管理 legacy subagent 状态 |
| python -m openclaw_enhance.cli render-skill <name> | 查看指定 Skill 的合约内容 |
| python -m openclaw_enhance.cli validate-feature | 在真实环境中进行功能验证 |
| python -m openclaw_enhance.cli project list [--kind permanent\|temporary\|all] | 列出注册的项目 |
| python -m openclaw_enhance.cli project scan <path> [--register] | 扫描并检测项目类型 |
| python -m openclaw_enhance.cli project info <path> | 查看项目详情和 git 上下文 |
| python -m openclaw_enhance.cli project create <path> --name <name> --kind permanent\|temporary | 手动注册项目 |
| python -m openclaw_enhance.cli eta register --task-id <id> --child <child_id> --parent <parent_id> --minutes <est> | 注册任务 ETA 到 TaskETARegistry |
| python -m openclaw_enhance.cli eta update --task-id <id> --state delayed\|blocked\|stalled --reason <原因> --remaining <分钟> | 更新任务状态（延期/阻塞/停滞/完成） |
| python -m openclaw_enhance.cli eta status --task-id <id> | 查看任务当前 ETA 和状态 |

## 安装与卸载
安装命令：
`python -m openclaw_enhance.cli install`

卸载命令：
`python -m openclaw_enhance.cli uninstall`

## 版本
Playbook Version: 2.0.0
Milestone: v2 skill-only architecture COMPLETE
