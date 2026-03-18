---
name: oe-main-routing-gate
description: Provide progressive escalation advisory based on task complexity.
metadata: { "openclaw": { "emoji": "🧭", "events": ["message:preprocessed"] } }
---

# oe-main-routing-gate

Provides progressive escalation advisory for main-session requests that appear to require
multi-step work or complex synthesis.

## Trigger

- Event: `message:preprocessed`
- Scope: `agent:main:*` sessions only

## Behavior

Analyzes incoming requests for complexity indicators:

**Complex Task Patterns:**
- 研究/分析/生成/制作
- 写报告/做PPT/整理大纲
- 多步骤任务（含"并"、"且"等连接词）
- 长消息（多句子）

**Advisory Logic:**
- First advisory: Prepend suggestion to use `sessions_spawn` with `agentId: "oe-orchestrator"`
- Advisory counter: Tracks up to 2 advisories per session
- Non-blocking: Agent can still proceed in main if it chooses

## Advisory Message

```
[ROUTING-ADVISORY]
This request involves multi-step work or synthesis.
Advisory #N/2: Consider using sessions_spawn with agentId='oe-orchestrator'
for better parallel execution and resource management.

If you proceed in main, monitor tool usage and escalate if needed.
```

## Safety

- Simple queries ("查小说", "搜索XX") are NOT flagged
- Non-main sessions are untouched
- Agent retains decision authority
- No forced escalation
