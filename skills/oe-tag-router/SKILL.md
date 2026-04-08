---
name: oe-tag-router
version: 2.0.0
description: MANDATORY tag-based router for v2 architecture. Analyzes task → assigns tags → matches skills → selects model tier. Main session is ROUTER ONLY.
user-invocable: true
skill-type: orch
tags: []
allowed-tools: "Read"
metadata:
  routing_model: "tag-based"
  architecture_version: "2.0"
  contract: "sessions_spawn with prompt+model only (no agentId)"
---

# Tag Router (v2)

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
- `message` (reply to user)

## Routing Pipeline (3-Stage)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  1. TAG INFER   │───►│  2. SKILL MATCH │───►│  3. MODEL TIER  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Stage 1: Tag Inference

Analyze task text and assign semantic tags:

| Tag | Keywords | Task Patterns |
|-----|----------|---------------|
| `research` | search, find, investigate, 搜索, 调研, 查找 | Information gathering, web search, data collection |
| `code` | write, implement, fix, create, 编写, 实现, 修复 | File modification, coding, debugging |
| `ops` | run, execute, build, deploy, 运行, 执行, 构建 | Command execution, system operations |
| `debug` | troubleshoot, error, issue, bug, 调试, 问题 | Diagnostic, error investigation |
| `write` | document, readme, doc, 文档, 说明 | Documentation, content creation |
| `review` | check, verify, review, audit, 检查, 审核 | Code review, verification |
| `plan` | plan, organize, design, 规划, 设计 | Multi-step planning, architecture |

**Inference Logic:**
```python
def infer_tags(task: str) -> list[str]:
    """Analyze task and return assigned tags."""
    tags = []
    task_lower = task.lower()
    
    # Research indicators
    if any(k in task_lower for k in ["search", "find", "investigate", "调研", "搜索", "查找", "research"]):
        tags.append("research")
    
    # Code indicators  
    if any(k in task_lower for k in ["write", "implement", "fix", "create", "code", "function", "class", "编写", "实现", "修复", "创建"]):
        tags.append("code")
    
    # Ops indicators
    if any(k in task_lower for k in ["run", "execute", "build", "deploy", "install", "运行", "执行", "构建", "部署"]):
        tags.append("ops")
    
    # Debug indicators
    if any(k in task_lower for k in ["debug", "troubleshoot", "error", "issue", "bug", "fix", "调试", "问题", "错误"]):
        tags.append("debug")
    
    # Write indicators
    if any(k in task_lower for k in ["document", "readme", "doc", "文档", "说明", "write.*doc"]):
        tags.append("write")
    
    # Review indicators
    if any(k in task_lower for k in ["review", "check", "verify", "audit", "检查", "审核", "review"]):
        tags.append("review")
    
    # Plan indicators
    if any(k in task_lower for k in ["plan", "design", "organize", "architecture", "规划", "设计", "架构"]):
        tags.append("plan")
    
    return tags if tags else ["code"]  # Default fallback
```

### Stage 2: Skill Matching

Map tags to candidate spawn skills:

| Tag | Candidate Skill | Description |
|-----|-----------------|-------------|
| `research` | `oe-spawn-search` | Web search, data gathering, investigation |
| `code` | `oe-spawn-coder` | File editing, code implementation |
| `ops` | `oe-spawn-ops` | Command execution, system operations |
| `debug` | `oe-spawn-debug` | Troubleshooting, error analysis |
| `write` | `oe-spawn-writer` | Documentation, content creation |
| `review` | `oe-spawn-reviewer` | Code review, verification |
| `plan` | `oe-spawn-planner` | Multi-step planning, architecture |

**Multi-Tag Handling:**
- If multiple tags match → spawn `oe-orchestrator` (complex multi-domain task)
- If single tag → spawn corresponding specialist
- If no tags match → default to `oe-spawn-coder`

### Stage 3: Model Tier Selection

Select model tier based on task complexity:

| Complexity | Criteria | Tier | Model Type |
|------------|----------|------|------------|
| **ROUTINE** | Single-step, well-defined, repetitive | cheap | Fast, cost-effective |
| **MODERATE** | Multi-step, requires coordination | mid | Balanced performance |
| **COMPLEX** | Novel problem, requires reasoning | premium | High capability |

**Complexity Detection:**

```python
def classify_complexity(task: str, tags: list[str]) -> str:
    """Classify task complexity for model selection."""
    task_lower = task.lower()
    
    # COMPLEX indicators
    complex_indicators = [
        "architecture", "design", "plan", "organize",
        "multi-step", "complex", "novel", "investigate deep",
        "architecture", "重构", "架构", "深度", "复杂"
    ]
    if any(i in task_lower for i in complex_indicators):
        return "complex"
    
    # Check for multi-domain (multiple tags)
    if len(tags) > 1:
        return "complex"
    
    # Check for multi-step language
    step_indicators = ["and then", "followed by", "first.*then", "步骤", "然后", "接着"]
    if any(i.replace(".*", "") in task_lower for i in step_indicators):
        return "moderate"
    
    # MODERATE indicators
    moderate_indicators = [
        "implement", "create", "build", "refactor",
        "实现", "创建", "构建", "重构"
    ]
    if any(i in task_lower for i in moderate_indicators):
        return "moderate"
    
    # Default to ROUTINE for simple tasks
    return "routine"
```

**Tier-to-Model Mapping:**

Use `oe-model-discover` skill to get available models for each tier:

| Tier | Selection Priority |
|------|-------------------|
| cheap | gpt-4o-mini, claude-3-haiku, gemini-2.0-flash, deepseek-chat |
| mid | gpt-4o, claude-3.5-sonnet, o3-mini, gemini-2.5-pro |
| premium | claude-opus-4-6, o1, gpt-4.5 |

## Routing Decision Flow

```
User Request
    │
    ▼
┌─────────────┐
│ Infer Tags  │───► [research, code, ops, debug, write, review, plan]
└─────────────┘
    │
    ▼
┌─────────────┐
│ Match Skill │───► oe-spawn-* or oe-orchestrator
└─────────────┘
    │
    ▼
┌─────────────┐
│ Model Tier  │───► cheap / mid / premium
└─────────────┘
    │
    ▼
sessions_spawn(prompt=task, model=selected_model)
```

## sessions_spawn Contract (v2)

**MUST USE:** `prompt` + `model` only. **NO agentId.**

```json
{
  "prompt": "<full task description with context>",
  "model": "<selected-model-name>"
}
```

**NOT:**
```json
{
  "task": "...",
  "agentId": "oe-orchestrator"   // ❌ v1 style - DO NOT USE
}
```

## Examples

### Simple research task
- **User:** "搜索最新的 Python 3.13 特性"
- **Tags:** [research]
- **Skill:** oe-spawn-search
- **Complexity:** routine
- **Model:** cheap tier (gpt-4o-mini)
- **Action:** `sessions_spawn(prompt=task, model="gpt-4o-mini")`

### Multi-step coding task
- **User:** "Implement a REST API with authentication and database models"
- **Tags:** [code, plan]
- **Skill:** oe-orchestrator (multi-domain)
- **Complexity:** complex
- **Model:** premium tier (claude-opus-4-6)
- **Action:** `sessions_spawn(prompt=task, model="claude-opus-4-6")`

### Debug request
- **User:** "Debug why my Flask app is returning 500 errors"
- **Tags:** [debug, code]
- **Skill:** oe-spawn-debug
- **Complexity:** moderate
- **Model:** mid tier (claude-3.5-sonnet)
- **Action:** `sessions_spawn(prompt=task, model="claude-3.5-sonnet")`

### Documentation task
- **User:** "Write API documentation for the user endpoints"
- **Tags:** [write]
- **Skill:** oe-spawn-writer
- **Complexity:** routine
- **Model:** cheap tier (gpt-4o-mini)
- **Action:** `sessions_spawn(prompt=task, model="gpt-4o-mini")`

### Complex system task
- **User:** "Design and implement a distributed task queue with Redis and monitoring"
- **Tags:** [plan, code, ops]
- **Skill:** oe-orchestrator (multi-domain)
- **Complexity:** complex
- **Model:** premium tier (claude-opus-4-6)
- **Action:** `sessions_spawn(prompt=task, model="claude-opus-4-6")`

## Pre-Spawn Checklist

Before calling `sessions_spawn`:

1. ✅ **Tags inferred** - Task analyzed and tags assigned
2. ✅ **Skill matched** - Target skill identified
3. ✅ **Model tier selected** - Complexity classified
4. ✅ **Model discovered** - Use oe-model-discover to get specific model name
5. ✅ **No agentId** - Using prompt+model contract only
6. ✅ **Context included** - Full task context in prompt

## Model Discovery Integration

Before spawning, discover available models:

```python
# Check model cache
from pathlib import Path
import json

cache_path = Path.home() / ".openclaw" / "openclaw-enhance" / "model_cache.json"

if cache_path.exists():
    models = json.loads(cache_path.read_text())
    
    # Get models for selected tier
    tier_models = [m for m in models if m.get("tier") == selected_tier]
    selected_model = tier_models[0]["name"] if tier_models else "gpt-4o-mini"
```

## Error Handling

| Scenario | Action |
|----------|--------|
| No models available for tier | Fallback to "gpt-4o-mini" |
| Model cache missing | Use oe-model-discover to refresh |
| Multi-tag conflict | Route to oe-orchestrator |
| Ambiguous task | Default to moderate tier + oe-spawn-coder |

## Routing Rules Summary

| Task Type | Tags | Target | Model Tier |
|-----------|------|--------|------------|
| Web search, research | [research] | oe-spawn-search | cheap |
| File editing, coding | [code] | oe-spawn-coder | moderate |
| Command execution | [ops] | oe-spawn-ops | cheap |
| Debugging | [debug] | oe-spawn-debug | moderate |
| Documentation | [write] | oe-spawn-writer | cheap |
| Code review | [review] | oe-spawn-reviewer | mid |
| Planning, architecture | [plan] | oe-spawn-planner | premium |
| Multi-domain tasks | [tag1, tag2, ...] | oe-orchestrator | premium |
