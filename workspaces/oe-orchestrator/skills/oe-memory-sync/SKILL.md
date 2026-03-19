---
name: oe-memory-sync
version: 1.0.0
description: Main session context fetching for orchestrator startup
author: openclaw-enhance
tags: [orchestrator, memory, context, session, main]
---

# oe-memory-sync

Skill for fetching and synchronizing Main session context into the Orchestrator at startup.

## Purpose

When the Orchestrator starts (via `sessions_spawn` from Main), it needs to understand:
- What the user was discussing with Main before spawning Orch
- Key decisions or context from the conversation
- Main's memory files that might be relevant
- Current project context

This skill enables Orchestrator to proactively fetch this context at session start.

## When to Use

Use this skill when:
- Orchestrator session is starting (first turn)
- Task requires understanding prior conversation context
- Need to know user's goals/preferences from Main session
- Project context is unclear from task description alone

## Context Sources

### 1. Parent Session History

The `parent_session` ID is passed via spawn enrichment hook. Use `sessions_history` tool:

```python
# Get parent session messages
parent_history = sessions_history(parent_session_id)

# Extract key information:
# - User's original request
# - Main's analysis/responses
# - Any decisions made
# - Files mentioned or created
```

### 2. Main Workspace Memory Files

Main stores memories in `~/.openclaw/memory/` directory:

```python
# Common memory file patterns:
# - ~/.openclaw/memory/YYYY-MM-DD.md (daily memories)
# - ~/.openclaw/memory/projects/{project}/notes.md

# Read recent memory files to understand:
# - Ongoing projects
# - User preferences
# - Past decisions
```

### 3. Runtime State

Orchestrator can check `runtime-state.json` for:

```python
runtime_state = read("~/.openclaw/openclaw-enhance/runtime-state.json")
# Fields:
# - active_project: Currently active project
# - project_occupancy: Which orch owns which project
# - last_updated_utc: When state was last modified
```

### 4. Project Registry

For the active project, fetch details from `project-registry.json`:

```python
registry = read("~/.openclaw/openclaw-enhance/project-registry.json")
# Contains:
# - Project paths
# - Project types (permanent/temporary)
# - Git associations
```

## Usage Pattern

### Session Startup Flow

```
Orchestrator Session Start
    │
    ▼
Load oe-memory-sync skill
    │
    ▼
Extract parent_session from context
    │
    ▼
Fetch Parent History ──► sessions_history(parent_session)
    │
    ▼
Fetch Main Memory ──► read memory/*.md files
    │
    ▼
Fetch Project Context ──► runtime-state.json + project-registry.json
    │
    ▼
Synthesize Context
    │
    ▼
Inject into task understanding
```

### Implementation

```python
async def sync_main_context():
    """Fetch and synthesize Main session context."""
    
    # 1. Get parent session ID from spawn context
    parent_session = context.get("parent_session")
    if not parent_session:
        return {"status": "no_parent", "context": {}}
    
    # 2. Fetch parent session history
    history = sessions_history(parent_session, limit=50)
    history_summary = summarize_conversation(history)
    
    # 3. Fetch main memory files
    memory_files = glob(f"{main_workspace}/memory/*.md")
    memory_content = read_multiple(memory_files, limit=10)  # Recent 10
    
    # 4. Fetch project context
    runtime_state = read(runtime_state_path)
    registry = read(project_registry_path)
    active_project = runtime_state.get("active_project")
    project_info = registry.get_project(active_project) if active_project else None
    
    # 5. Synthesize into context
    context = {
        "parent_history_summary": history_summary,
        "main_memory": memory_content,
        "active_project": project_info,
        "parent_session_id": parent_session,
    }
    
    return context
```

## Context Injection

After fetching, inject the context into Orchestrator's understanding:

```python
def inject_orch_context(context):
    """Inject fetched context into Orchestrator prompt."""
    return f"""
## Main Session Context

### Prior Conversation Summary
{context['parent_history_summary']}

### Relevant Memory
{context['main_memory']}

### Active Project
{format_project_info(context['active_project'])}

### Task
{current_task_description}

Use the above context to better understand the user's intent and
provide more informed orchestration decisions.
"""
```

## Summarization Strategy

### Parent History Summary

Don't include full history — summarize key points:

```python
def summarize_conversation(history):
    """Extract key points from conversation history."""
    key_points = []
    
    for msg in history:
        if msg.role == "user":
            # Capture user's original request
            key_points.append(f"User request: {truncate(msg.content, 200)}")
        elif msg.role == "assistant" and msg.content:
            # Capture Main's significant responses
            if is_significant(msg):
                key_points.append(f"Main response: {truncate(msg.content, 200)}")
    
    return "\n".join(key_points[-10:])  # Last 10 significant points
```

### Memory Prioritization

Focus on recent and relevant memories:

1. **Today's memories** (highest priority)
2. **This week's memories** (high priority)
3. **Project-specific memories** (medium priority)
4. **Old memories** (low priority, skip unless directly relevant)

## Integration

### With oe-project-registry

Use project registry to identify which project context to fetch:
- Permanent projects have stable paths and git associations
- Temporary projects may have ephemeral context

### With oe-worker-dispatch

The fetched context should inform:
- Worker selection (what context matters for this task)
- Dispatch instructions (what context to pass to workers)
- Result synthesis (how to incorporate context into final answer)

### With planning-with-files

Memory context should be available when creating task plans:
```python
# In planning phase
context = await sync_main_context()
plan = create_plan(task, context=context)
```

## Safety

### Read-Only Operations

This skill only reads:
- `sessions_history()` - conversation history
- `read()` - memory files, state files
- `glob()` - finding memory files

### No Modifications

This skill never:
- Modifies session history
- Edits memory files
- Changes runtime state
- Sends messages to Main

## Error Handling

| Scenario | Response |
|----------|----------|
| No parent_session | Return empty context, log warning |
| Parent session not found | Log error, continue without history |
| Memory files missing | Continue without memory, log info |
| Runtime state unavailable | Use defaults, log warning |

## Example

```python
# Orchestrator session start
async def on_session_start():
    # Fetch Main context
    ctx = await sync_main_context()
    
    if ctx["parent_history_summary"]:
        print(f"📋 Parent conversation context available")
        print(f"   Project: {ctx['active_project']}")
    
    # Now proceed with task understanding
    task = current_task()
    enhanced_task = inject_orch_context(ctx, task)
    
    # Continue with orchestration...
```

## Output Schema

```yaml
context:
  parent_session_id: string
  parent_history_summary: string
  main_memory: string
  active_project:
    name: string
    path: string
    type: permanent | temporary
  timestamp: ISO8601
  status: complete | partial | unavailable
```
