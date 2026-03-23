# Domain Specialist System

## 架构

```
Main Session
    │
    ▼
oe-orchestrator (with oe-domain-router skill)
    │
    ├─► oe-specialist-ops (tunnels/backup/launchd)
    ├─► oe-specialist-finance (财务分析)
    ├─► oe-specialist-km (知识管理)
    ├─► oe-specialist-creative (创意内容)
    └─► oe-specialist-game-design (游戏设计)
```

## Domain 定义

| Domain | Agent | 适用场景 | 输出格式 |
|--------|-------|---------|---------|
| ops | oe-specialist-ops | tunnels/backup/launchd/服务诊断 | reports/ops/YYYYMMDD-HHMM/report.md |
| finance | oe-specialist-finance | 财务分析、投资决策 | reports/finance/YYYYMMDD-HHMM/report.md |
| km | oe-specialist-km | 知识管理、文档整理 | reports/km/YYYYMMDD-HHMM/plan.md |
| creative | oe-specialist-creative | 创意内容生成 | assets/YYYYMMDD-HHMM/ |
| game-design | oe-specialist-game-design | 游戏设计文档 | reports/game-design/YYYYMMDD-HHMM/report.md |

## 与通用 workers 的区别

| 特性 | 通用 Workers | Domain Specialists |
|------|-------------|-------------------|
| 路由 | oe-worker-dispatch | oe-domain-router |
| 职责 | 通用任务（搜索/编码/系统检查） | 领域特定任务 |
| 约束 | 工具限制 | 领域规则 + 工具限制 |
| 输出 | 灵活 | 固定格式 |
| 技能 | 通用技能 | 领域专属技能 |

## 实现状态

- [x] oe-domain-router skill 创建
- [x] oe-specialist-ops workspace 创建
- [ ] 其他 specialist workspaces 创建
- [ ] openclaw.json 注册
- [ ] legacy skills 废弃
- [ ] 集成测试
