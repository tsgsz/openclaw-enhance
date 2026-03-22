## 概述
openclaw-enhance 是一个针对 OpenClaw 的非侵入式增强组件。它通过扩展点、钩子和独立工作区，在不修改 OpenClaw 核心源码的前提下，实现了多任务并行处理、自动化运维监控以及操作透明化。

## 安装产物清单
```
~/.openclaw/
├── openclaw.json                    # 被修改：agents.list, hooks.internal
├── openclaw-enhance/                # 托管命名空间
│   ├── PLAYBOOK.md                  # 本文件
│   ├── project-registry.json        # 项目注册表（自动生成）
│   ├── install-manifest.json        # 安装清单（组件、版本、回滚点）
│   ├── runtime-state.json           # 运行时状态（超时、健康检查）
│   ├── workspaces/                  # 6 个 Worker Agent 工作区
│   │   ├── oe-orchestrator/         # 编排调度 Agent
│   │   ├── oe-searcher/             # 搜索研究 Agent
│   │   ├── oe-syshelper/            # 系统自省 Agent
│   │   ├── oe-script_coder/         # 脚本开发 Agent
│   │   ├── oe-watchdog/             # 会话监控 Agent
│   │   └── oe-tool-recovery/        # 工具故障恢复 Agent
│   ├── hooks/                       # Hook 实现
│   │   ├── oe-main-routing-gate/    # 复杂任务路由钩子
│   │   └── oe-subagent-spawn-enrich/# 子 Agent 派发增强钩子
│   └── logs/                        # 监控日志
│       ├── monitor.log
│       └── monitor.err.log
├── workspace/                       # 主工作区（被修改）
│   ├── AGENTS.md                    # 被注入工具限制（tool gate）
│   └── skills/                      # 主会话 Skill
│       ├── oe-toolcall-router/      # 路由决策 Skill
│       ├── oe-eta-estimator/        # 任务时长估算 Skill
│       └── oe-timeout-state-sync/   # 超时状态同步 Skill
└── extensions/                      # OpenClaw 扩展目录
    └── oe-runtime/                  # 运行时桥接扩展
~/Library/LaunchAgents/              # (仅 macOS)
└── ai.openclaw.enhance.monitor.plist # 后台监控服务（每60秒）
```

## Agent 清单
| Agent ID | 职责 | 模型策略 | 权限 |
| :--- | :--- | :--- | :--- |
| oe-orchestrator | 编排调度，负责计划、派发与结果合成 | 最强模型 | 全权限 |
| oe-searcher | 搜索研究，执行 Web 搜索与文档查找 | 廉价模型 | 只读 |
| oe-syshelper | 系统自省，执行 grep、ls、find 等操作 | 廉价模型 | 只读 |
| oe-script_coder | 脚本开发，编写代码并运行测试 | 标准模型 | 沙箱读写 |
| oe-watchdog | 会话监控，负责超时检测与主动提醒 | 廉价模型 | 仅限运行时状态 |
| oe-tool-recovery | 工具故障恢复，进行诊断并提供修复建议 | 推理模型 | 只读 |

**外部 ACP Harness** (通过 orchestrator 调度):
| Agent ID | 职责 | 触发条件 | 运行模式 |
| :--- | :--- | :--- | :--- |
| opencode | OpenCode CLI 外部开发环境 | 用户明确请求 "用 opencode" 或正式开发流程 | ACP runtime, persistent |
| codex | Codex CLI 外部开发环境 | 用户明确请求 | ACP runtime |
| claude | Claude Code 外部开发环境 | 用户明确请求 | ACP runtime |

## Hook 清单
| Hook ID | 触发时机 | 作用 |
| :--- | :--- | :--- |
| oe-main-routing-gate | message preprocessed 时 | 检测复杂任务，注入路由建议 |
| oe-subagent-spawn-enrich | subagent_spawning 时 | 注入 task_id、project、eta_bucket、dedupe_key |

## Skill 清单
| Skill ID | 安装位置 | 作用 |
| :--- | :--- | :--- |
| oe-toolcall-router | 主工作区 | 强制主会话仅执行路由功能，所有具体执行均通过 sessions_spawn 完成 |
| oe-eta-estimator | 主工作区 | 估算任务的时长与复杂度 |
| oe-timeout-state-sync | 主工作区 | 在主会话与运行时存储之间同步超时状态 |

## Extension 清单
- oe-runtime: before_tool_call 扩展。该扩展会阻止主会话使用 edit、write、exec 等被禁止的工具。

## 主会话工具限制（Tool Gate）
主会话（main）的 AGENTS.md 文件被注入了工具限制。系统禁止主会话使用 edit、write、exec、web_search 和 browser。主会话仅允许使用 read、memory_search 和 sessions_spawn 等工具。这一设计的目的是强制主会话扮演路由器的角色，将具体任务分发给专门的 Worker Agent。

## ACP 外部 Harness 路由

当用户请求涉及外部开发环境（opencode、codex、claude）时，系统通过以下路径路由：

```
用户: "用 opencode 修复..."
  ↓
Main Session (检测到 ACP 意图)
  ↓
sessions_spawn → oe-orchestrator
  ↓
Orchestrator 识别 ACP 分支
  ↓
sessions_spawn({ runtime: "acp", agentId: "opencode", mode: "persistent" })
  ↓
ACP Harness (opencode) 执行具体开发工作
  ↓
结果通过 announce 返回给 Orchestrator
  ↓
Orchestrator 汇总结果并返回给 Main
```

**配置要求**：
- `openclaw.json` 中 `acp.enabled: true`
- ACPX 插件已安装且 Gateway 已重启
- 用户明确请求 "用 opencode" 或任务需要正式开发流程（issue → worktree → PR → CI → merge）

**验证状态**：✅ Main → orch → opencode 全链路已验证

## openclaw.json 修改清单
| 配置路径 | 修改内容 |
| :--- | :--- |
| agents.list | 添加 6 个托管 Agent（managed agents） |
| agents.list[main].subagents.allowAgents | 添加 oe-orchestrator |
| hooks.internal.entries | 启用 oe-subagent-spawn-enrich 和 oe-main-routing-gate |
| hooks.internal.enabled | 设置为 true |
| hooks.internal.load.extraDirs | 添加 hooks 目录的路径 |
| plugins.entries.oe-runtime | 启用运行时扩展 |
| acp.enabled | 启用 ACP 外部 Harness 支持 |
| acp.defaultAgent | 默认 ACP Agent (opencode) |
| acp.allowedAgents | 允许的 ACP Agent 列表 [opencode, codex, claude] |

## Watchdog 监控机制
在 macOS 环境下，LaunchAgent 每 60 秒运行一次 monitor_runtime。该程序会检测超时的会话，并将结果写入 runtime-state.json。oe-watchdog 在确认超时后会向用户发送提醒。

## 项目注册系统
管理永久/临时项目的注册、发现和上下文注入。

项目类型：
- 永久项目：用户指定位置（~/workspace），关联 GitHub，同时只允许一个 orch 操作。
- 临时项目：Orchestrator 创建，per-task，互不冲突。

注册表位置：`~/.openclaw/openclaw-enhance/project-registry.json`

支持的项目类型：python, nodejs, rust, go, java, ruby, php, cpp。

占用锁：永久项目使用占用锁确保互斥访问。

## CLI 命令速查
| 命令 | 说明 |
| :--- | :--- |
| python -m openclaw_enhance.cli status | 查看安装状态 |
| python -m openclaw_enhance.cli doctor | 执行健康检查 |
| python -m openclaw_enhance.cli cleanup-sessions [--dry-run\|--execute] [--include-core-sessions] | 清理陈旧/孤儿 session 状态（默认 dry-run） |
| python -m openclaw_enhance.cli render-skill <name> | 查看指定 Skill 的合约内容 |
| python -m openclaw_enhance.cli render-workspace <name> | 查看工作区的配置信息 |
| python -m openclaw_enhance.cli validate-feature | 在真实环境中进行功能验证 |
| python -m openclaw_enhance.cli project list [--kind permanent\|temporary\|all] | 列出注册的项目 |
| python -m openclaw_enhance.cli project scan <path> [--register] | 扫描并检测项目类型 |
| python -m openclaw_enhance.cli project info <path> | 查看项目详情和 git 上下文 |
| python -m openclaw_enhance.cli project create <path> --name <name> --kind permanent\|temporary | 手动注册项目 |

## 安装与卸载
安装命令：
`python -m openclaw_enhance.cli install`

卸载命令：
`python -m openclaw_enhance.cli uninstall`

## 版本
Playbook Version: 1.0.0
