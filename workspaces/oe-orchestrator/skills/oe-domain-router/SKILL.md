---
name: oe-domain-router
version: 1.0.0
description: Domain specialist routing for oe-orchestrator. Maps domain-specific tasks to specialized agents.
---

# oe-domain-router

Orchestrator 用于识别领域专家任务并路由到对应的 oe-specialist-* agent。

## 领域映射

| Domain | Agent | 职责 |
|--------|-------|------|
| finance | oe-specialist-finance | 财务分析、报表、投资决策 |
| ops | oe-specialist-ops | 运维诊断、tunnels/backup/launchd/服务检查 |
| km | oe-specialist-km | 知识管理、文档整理 |
| creative | oe-specialist-creative | 创意内容生成 |
| game-design | oe-specialist-game-design | 游戏设计文档 |

## 何时使用

- 用户任务明确属于某个高约束领域
- 需要领域特定的工具、技能或约束
- 任务需要专门的输出格式或验证规则

## Dispatch 协议

### 1. 项目选择（Orchestrator 负责）

```bash
python3 ~/.openclaw/openclaw-enhance/scripts/project_select.py \
  --task "<user_task>" \
  [--name "<project_name>"]
```

返回：`project_root` 和建议的 `output_relpath`

### 2. sessions_spawn 模板

```text
[Domain Specialist Task]

domain: <finance|ops|km|creative|game-design>
project_root: <abs path or empty>
output_relpath: <rel path or empty>

User task:
<paste user task verbatim>

Hard requirements:
1) Call session_status and parse session_id from sessionKey suffix
2) Write intermediate work to: sessions/session_<session_id>/out/
3) If project_root provided: write final artifact to <project_root>/<output_relpath>
4) Read sub_agents_state.json to find from_session_id
5) sessions_send summary (<= 20 lines) to from_session_id with:
   - type: "specialist_done"
   - status: completed|blocked|partial
   - artifacts: ["<abs paths>"]
   - summary: "<Status/Evidence/Decisions/Output path>"
6) Final reply: ANNOUNCE_SKIP
```

### 3. 输出路径默认值

- finance: `reports/finance/<YYYYMMDD-HHMM>/report.md`
- ops: `reports/ops/<YYYYMMDD-HHMM>/report.md`
- km: `reports/km/<YYYYMMDD-HHMM>/plan.md`
- creative: `assets/<YYYYMMDD-HHMM>/`
- game-design: `reports/game-design/<YYYYMMDD-HHMM>/report.md`

## Orchestrator 使用流程

1. 识别任务属于哪个 domain
2. 调用 project_select.py 获取 project_root
3. 构造 task prompt（使用上述模板）
4. sessions_spawn(agentId="oe-specialist-<domain>", task=...)
5. 等待 sessions_send 回传
6. 汇总结果返回给 Main

## 与 oe-worker-dispatch 的关系

- oe-worker-dispatch: 通用 worker 路由（searcher/syshelper/script_coder）
- oe-domain-router: 领域专家路由（specialist-*）
- 两者互补，不冲突
