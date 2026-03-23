# Domain Specialist Migration Guide

## 概述

将 legacy `specialist-*` agents 迁移到 openclaw-enhance 管理体系。

## 迁移目标

1. 将 domain routing 逻辑从 Main 移到 oe-orchestrator
2. 将 specialist-* agents 重命名为 oe-specialist-* 并纳入 OE 管理
3. 保持原有的 domain 协议和输出格式

## 迁移步骤

### Phase 1: 创建 oe-specialist-* workspaces

为每个 domain 创建对应的 workspace：

```
workspaces/
├── oe-specialist-ops/
│   ├── AGENTS.md
│   ├── TOOLS.md
│   └── skills/
├── oe-specialist-finance/
├── oe-specialist-km/
├── oe-specialist-creative/
└── oe-specialist-game-design/
```

### Phase 2: 创建 oe-domain-router skill

在 oe-orchestrator 中添加 domain routing 能力：

- 位置: `workspaces/oe-orchestrator/skills/oe-domain-router/`
- 职责: 识别 domain 并路由到对应 specialist

### Phase 3: 注册 agents 到 openclaw.json

```json
{
  "agents": [
    {
      "id": "oe-specialist-ops",
      "workspace": "~/.openclaw/openclaw-enhance/workspaces/oe-specialist-ops",
      "model": "litellm-local/gpt-4o-mini"
    }
    // ... 其他 specialists
  ]
}
```

### Phase 4: 更新 oe-orchestrator allowlist

允许 orchestrator spawn specialist agents：

```json
{
  "agents": [
    {
      "id": "oe-orchestrator",
      "subagents": {
        "allowAgents": [
          "oe-searcher",
          "oe-syshelper",
          "oe-script_coder",
          "oe-specialist-ops",
          "oe-specialist-finance",
          "oe-specialist-km",
          "oe-specialist-creative",
          "oe-specialist-game-design"
        ]
      }
    }
  ]
}
```

### Phase 5: 废弃 legacy skills

删除或标记为 deprecated：

- `~/.openclaw/workspace/skills/domain-ops/`
- `~/.openclaw/workspace/skills/domain-factory/`

## 验证

1. 测试 ops domain 任务是否正确路由到 oe-specialist-ops
2. 验证输出格式符合原有协议
3. 确认 sessions_send 回传机制正常工作

## 回滚计划

如果迁移失败，恢复 legacy skills：

```bash
# 从备份恢复
cp ~/.openclaw/workspace/skills/domain-ops/SKILL.md.backup \
   ~/.openclaw/workspace/skills/domain-ops/SKILL.md
```
