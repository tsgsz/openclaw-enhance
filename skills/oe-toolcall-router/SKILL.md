---
name: oe-toolcall-router
version: 2.0.0
description: MANDATORY router. Main session is a ROUTER ONLY - all execution MUST go through sessions_spawn.
user-invocable: true
allowed-tools: "Read"
metadata:
  routing_heuristics:
    max_toolcalls: 0
    escalation_threshold: 0
---

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

## Routing Decision

For ANY user request that requires file modification, command execution, research, or analysis:

1. Immediately use `sessions_spawn` with `agentId: "oe-orchestrator"`
2. Do NOT attempt to do the work yourself
3. Do NOT use `edit`/`exec`/`write` even for "simple" tasks

## Escalation Command

```json
{
  "task": "<restate user request clearly>",
  "agentId": "oe-orchestrator"
}
```

## Examples

### Config change request
- User: "把 litellm 里的 vertex 模型加到 openclaw"
- Action: `sessions_spawn` to `oe-orchestrator`
- NOT: Use `edit` to modify openclaw.json yourself

### Research request
- User: "搜索东南亚 iGaming 行业现状"
- Action: `sessions_spawn` to `oe-orchestrator`
- NOT: Use `web_search` yourself

### Code task
- User: "写一个 hello world"
- Action: `sessions_spawn` to `oe-orchestrator`
- NOT: Use `write`/`exec` yourself

### Simple query (stays in main)
- User: "今天天气怎么样"
- Action: Reply directly (no tools needed)

### Read-only check (stays in main)
- User: "看看 openclaw.json 里有什么模型"
- Action: Use `read` to check, then reply
