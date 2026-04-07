---
name: oe-spawn-search
version: 2.0.0
description: Spawn skill for research tasks - web search, data gathering, investigation. Uses sessions_spawn with prompt+model contract.
user-invocable: true
skill-type: spawn
tags: [research, web_search, investigation]
allowed-tools: "sessions_spawn, sessions_list, sessions_send"
metadata:
  architecture_version: "2.0"
  contract: "sessions_spawn with prompt+model only (no agentId)"
  model_tier_routing: true
---

# oe-spawn-search (v2)

Spawn skill for research tasks - web search, information gathering, and investigation.

## Responsibilities

- Execute web search queries
- Gather information from multiple sources
- Investigate topics with depth
- Return structured findings

## When to Use

Use this skill when user requests:
- Search, find, lookup, investigate
- Research, gather, collect information
- Web queries for factual data
- Deep investigation on topics

## Model Tier Selection

| Task Complexity | Tier | Model Selection |
|----------------|------|----------------|
| Simple search, fact lookup | cheap | Fast, cost-effective model |
| Multi-source research | mid | Balanced capability |
| Deep investigation | mid | Higher reasoning model |

**Tier Selection Logic:**

```python
def select_tier_for_research(task: str) -> str:
    """Select model tier based on research complexity."""
    task_lower = task.lower()
    
    # Deep investigation signals → mid tier
    deep_signals = [
        "deep", "investigate", "analyze", "compare",
        "why", "how does", "原理", "分析", "深度调研"
    ]
    if any(s in task_lower for s in deep_signals):
        return "mid"
    
    # Simple search → cheap tier
    simple_signals = [
        "search", "find", "lookup", "查", "搜索", "查找"
    ]
    if any(s in task_lower for s in simple_signals):
        return "cheap"
    
    # Default: cheap for research tasks
    return "cheap"
```

## spawn_recipe()

Generate sessions_spawn call for research tasks:

```python
def spawn_recipe(task: str, context: str = "") -> dict:
    """
    Generate spawn recipe for research task.
    
    Args:
        task: Research task description
        context: Optional additional context
    
    Returns:
        dict with prompt and model for sessions_spawn
    """
    from pathlib import Path
    import json
    
    # 1. Determine tier
    tier = select_tier_for_research(task)
    
    # 2. Get model from cache
    cache_path = Path.home() / ".openclaw" / "openclaw-enhance" / "model_cache.json"
    
    if cache_path.exists():
        with open(cache_path) as f:
            models = json.load(f)
        tier_models = [m for m in models if m.get("tier") == tier]
        selected_model = tier_models[0]["name"] if tier_models else "gpt-4o-mini"
    else:
        # Fallback defaults
        selected_model = "gpt-4o-mini" if tier == "cheap" else "claude-3.5-sonnet"
    
    # 3. Build research specialist prompt
    prompt = build_research_prompt(task, context, selected_model)
    
    return {
        "prompt": prompt,
        "model": selected_model
    }
```

## build_research_prompt()

Research specialist prompt template:

```python
def build_research_prompt(task: str, context: str, model: str) -> str:
    """
    Build prompt for research specialist subagent.
    
    Args:
        task: The research task
        context: Additional context
        model: Selected model for capability matching
    
    Returns:
        Formatted prompt for research subagent
    """
    prompt = f"""## Research Task

### Query
{task}

### Context
{context or "None provided"}

### Instructions
1. Use web_search and web_fetch tools to gather information
2. Verify information from multiple sources when possible
3. Return structured findings with source attribution

### Output Format
Return findings in this structure:
- **Summary**: Brief answer to the query
- **Sources**: List of sources with URLs
- **Details**: Key findings from research

### Model Context
You are operating with {model}. Use your capabilities effectively for this research task.
"""
    return prompt
```

## Security Principles

1. **Minimal Context**: Only include necessary information in prompt
2. **No Parent Memory**: Do not inject parent session memory
3. **Structured Output**: Require specific format for findings
4. **Source Attribution**: Mandate source references

## sessions_spawn Contract (v2)

**MUST USE:**
```json
{
  "prompt": "<research specialist prompt>",
  "model": "<selected-model>"
}
```

**NOT:**
```json
{
  "task": "...",
  "agentId": "oe-searcher"  // ❌ v1 style - DO NOT USE
}
```

## Example Usage

### Simple Search
- **User:** "搜索 Python 3.13 新特性"
- **Tier:** cheap
- **Model:** gpt-4o-mini
- **Spawn:** `sessions_spawn(prompt=..., model="gpt-4o-mini")`

### Deep Investigation
- **User:** "深度调研 Claude and GPT-4 的技术架构差异"
- **Tier:** mid
- **Model:** claude-3.5-sonnet
- **Spawn:** `sessions_spawn(prompt=..., model="claude-3.5-sonnet")`

## Pre-Spawn Checklist

Before calling `sessions_spawn`:

1. ✅ Task analyzed - Research intent confirmed
2. ✅ Tier selected - Complexity classified
3. ✅ Model discovered - From model cache or fallback
4. ✅ Prompt constructed - Research specialist template
5. ✅ No agentId - Using prompt+model only
6. ✅ Context minimalized - Only required context

(End of SKILL.md)