---
name: oe-project-context
version: 2.0.0
description: Project context injection for subagent prompts. Loads metadata from project registry and injects into spawn prompts for context-aware task delegation.
user-invocable: true
skill-type: context
tags: []
allowed-tools: "Read"
metadata:
  architecture_version: "2.0"
  contract: "sessions_spawn with prompt+model only (no agentId)"
  context_source: "project-registry"
---

# Project Context (v2)

Injects project metadata into subagent prompts to provide context-aware task delegation.

## Contract

This skill follows the v2 sessions_spawn contract:
- **MUST**: Use `prompt` + `model` only
- **MUST NOT**: Specify `agentId` in spawn calls

```python
# CORRECT v2 contract
sessions_spawn(prompt="<task with injected context>", model="gpt-4o")

# WRONG v1 style (DO NOT USE)
sessions_spawn(task="...", agentId="oe-searcher")
```

## Functions

### load_project_metadata()

Loads project metadata from the project registry.

```python
from pathlib import Path
import json

def load_project_metadata(project_name: str = None) -> dict:
    """Load project metadata from registry.
    
    Args:
        project_name: Optional project name. If None, uses current project.
        
    Returns:
        Project metadata dict with: name, path, type, description, artifacts
    """
    registry_path = Path.home() / ".openclaw" / "openclaw-enhance" / "project-registry.json"
    
    if not registry_path.exists():
        return {"error": "Registry not found", "projects": []}
    
    registry = json.loads(registry_path.read_text())
    projects = registry.get("projects", [])
    
    if project_name:
        return next((p for p in projects if p.get("name") == project_name), None)
    
    # Return current project (first in list or explicitly marked)
    current = next((p for p in projects if p.get("is_current")), None)
    return current or projects[0] if projects else None
```

### inject_project_context()

Injects project context into spawn prompts.

```python
def inject_project_context(task: str, project_metadata: dict = None) -> str:
    """Inject project context into task prompt.
    
    Args:
        task: Original task description
        project_metadata: Project metadata from load_project_metadata()
        
    Returns:
        Task string with injected project context
    """
    if not project_metadata:
        project_metadata = load_project_metadata()
    
    if not project_metadata or project_metadata.get("error"):
        # No project context available, return original task
        return task
    
    context_parts = [
        f"## Project Context",
        f"**Name**: {project_metadata.get('name', 'unknown')}",
        f"**Type**: {project_metadata.get('type', 'general')}",
        f"**Path**: {project_metadata.get('path', 'N/A')}",
    ]
    
    if project_metadata.get("description"):
        context_parts.append(f"**Description**: {project_metadata['description']}")
    
    if project_metadata.get("artifacts"):
        artifacts = ", ".join(project_metadata["artifacts"])
        context_parts.append(f"**Artifacts**: {artifacts}")
    
    context_block = "\n".join(context_parts)
    
    return f"{context_block}\n\n## Task\n{task}"
```

### Context Caching

Caches project context to avoid repeated registry reads.

```python
from functools import lru_cache
import time

_context_cache = {"data": None, "timestamp": 0}
_CACHE_TTL = 60  # seconds

def _get_cached_context(project_name: str = None) -> dict:
    """Get cached project context or load fresh."""
    global _context_cache
    
    now = time.time()
    if (_context_cache["data"] and 
        now - _context_cache["timestamp"] < __CACHE_TTL):
        return _context_cache["data"]
    
    # Load fresh and cache
    metadata = load_project_metadata(project_name)
    _context_cache = {"data": metadata, "timestamp": now}
    return metadata

def invalidate_context_cache():
    """Invalidate context cache to force refresh."""
    global _context_cache
    _context_cache = {"data": None, "timestamp": 0}
```

## Usage in sessions_spawn

### Before Spawn (v2 Pattern)

```python
# 1. Load project metadata
project_meta = load_project_metadata()

# 2. Inject context into task
task_with_context = inject_project_context(
    task="Search for Python async best practices",
    project_metadata=project_meta
)

# 3. Spawn with prompt+model only (NO agentId)
sessions_spawn(
    prompt=task_with_context,
    model="gpt-4o-mini"
)
```

### Context Structure

The injected context follows this schema:

```
## Project Context
**Name**: my-project
**Type**: permanent|temporary
**Path**: /path/to/project
**Description**: Project description (if available)
**Artifacts**: relevant-file1.py, relevant-file2.md

## Task
[Original task description]
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Registry not found | Return task without context |
| Project not found | Return task without context |
| Invalid metadata | Return task without context |
| Cache expired | Auto-refresh from registry |

## Security Rules

- **MUST NOT**: Include credentials, tokens, or secrets in context
- **MUST NOT**: Hardcode project paths in skill code
- **MUST**: Use registry as single source of truth
- **SHOULD**: Sanitize any user-provided project names

## Integration with Tag Router

This skill integrates with `oe-tag-router`:

1. Tag router identifies task type → determines spawn target
2. This skill adds project context to the prompt
3. Combined: context-aware + type-aware spawning

```python
# Combined flow
tags = infer_tags(user_request)  # from oe-tag-router
project_ctx = load_project_metadata()  # from oe-project-context

prompt = inject_project_context(user_request, project_ctx)
model = select_model_by_complexity(user_request, tags)

sessions_spawn(prompt=prompt, model=model)
```

## Related Skills

- `oe-tag-router` - Tag-based routing for v2
- `oe-worker-dispatch` - Worker dispatch with context
- `oe-model-discover` - Model discovery for tier selection