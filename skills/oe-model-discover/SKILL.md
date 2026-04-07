---
name: oe-model-discover
version: 2.0.0
description: Discovers OpenClaw configured models from openclaw.json and caches tier assignments. Provides model selection intelligence for subagent dispatch decisions.
user-invocable: true
skill-type: utility
allowed-tools: "Read, Write"
metadata:
  cache_location: "~/.openclaw/openclaw-enhance/model_cache.json"
  uses_module: "openclaw_enhance.model_config"
---

# Model Discover

Discovers configured OpenClaw models and caches their tier assignments for intelligent subagent model selection.

## When to Use

Use this skill when:
- About to spawn a subagent and need to select an appropriate model
- Need to know available models for a specific tier (cheap/mid/premium)
- Building routing logic that considers model cost/performance
- Pre-spawn check: before dispatching to workers, discover what models are available

## Cache Location

```
~/.openclaw/openclaw-enhance/model_cache.json
```

Cache is written once and reused until explicitly refreshed.

## Discovery Function

```python
import json
from pathlib import Path
from openclaw_enhance.model_config import get_openclaw_models, infer_model_tier


def discover_models() -> list[dict]:
    """
    Discover all configured OpenClaw models and apply tier assignments.
    
    Returns:
        List of model dicts with 'name', 'provider', and 'tier' fields.
    """
    # 1. Get all configured models from openclaw.json
    models = get_openclaw_models()
    
    # 2. Apply tier assignment to each model
    for model in models:
        model_id = model.get("name", "")
        model["tier"] = infer_model_tier(model_id)
    
    # 3. Write to cache
    cache_path = Path.home() / ".openclaw" / "openclaw-enhance" / "model_cache.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(models, indent=2, ensure_ascii=False), encoding="utf-8")
    
    return models
```

## Tier Definitions

| Tier | Price Range | Models |
|------|------------|--------|
| cheap | <$0.50/M | gpt-4o-mini, claude-3-haiku, gemini-2.0-flash, deepseek-chat, qwen-2.5-coder-27b-instruct |
| mid | $0.50-5/M | gpt-4o, claude-3.5-sonnet, o3-mini, gemini-2.5-pro |
| premium | >=$5/M | claude-opus-4-6, o1, gpt-4.5 |

## Refresh Cache

To refresh the cache after configuration changes:

```python
from pathlib import Path

cache_path = Path.home() / ".openclaw" / "openclaw-enhance" / "model_cache.json"
if cache_path.exists():
    cache_path.unlink()  # Delete old cache

discover_models()  # Re-discover and cache
```

## Example Usage

### Before spawning a worker subagent:

```python
from pathlib import Path
import json

cache_path = Path.home() / ".openclaw" / "openclaw-enhance" / "model_cache.json"

if not cache_path.exists():
    discover_models()

with open(cache_path) as f:
    models = json.load(f)

# Filter by tier for cost-sensitive tasks
cheap_models = [m for m in models if m.get("tier") == "cheap"]
```

### Tier-aware routing logic:

```python
def select_model_for_task(task_complexity: str) -> str:
    """Select appropriate model based on task complexity."""
    cache_path = Path.home() / ".openclaw" / "openclaw-enhance" / "model_cache.json"
    
    if not cache_path.exists():
        discover_models()
    
    with open(cache_path) as f:
        models = json.load(f)
    
    if task_complexity == "simple":
        # Use cheap model for simple tasks
        cheap = [m for m in models if m.get("tier") == "cheap"]
        return cheap[0]["name"] if cheap else "gpt-4o-mini"
    elif task_complexity == "complex":
        # Use premium for complex reasoning
        premium = [m for m in models if m.get("tier") == "premium"]
        return premium[0]["name"] if premium else "claude-opus-4-6"
    else:
        # Default to mid-tier
        mid = [m for m in models if m.get("tier") == "mid"]
        return mid[0]["name"] if mid else "gpt-4o"
```

## Notes

- This skill reads from `~/.openclaw/openclaw.json` — does NOT call external APIs
- Tier assignments are inferred from the `MODEL_PRICING` constant in `model_config.py`
- Cache reduces repeated reads from openclaw.json during session
- Refresh cache if openclaw.json configuration has changed
