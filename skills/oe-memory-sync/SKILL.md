---
name: oe-memory-sync
version: 2.0.0
description: Memory synchronization skill for v2 architecture. Reads from main session, syncs relevant context to subagents, updates after completion.
user-invocable: false
skill-type: context
tags: []
allowed-tools: "Read"
metadata:
  architecture_version: "2.0"
  contract: "sessions_spawn with prompt+model only (no agentId)"
---

# Memory Sync (v2)

This skill handles memory synchronization between main session and subagents in v2 architecture.

## Contract: sessions_spawn (v2)

**MUST USE:** `prompt` + `model` only. **NO agentId.**

```json
{
  "prompt": "<task with context>",
  "model": "<selected-model>"
}
```

## Function 1: read_relevant_memories()

Read memories from main session that are relevant to the current task.

### Input
- task: Current task description
- session_id: Main session ID

### Output
- List of relevant memory entries
- Filtered by relevance score

### Implementation

```python
def read_relevant_memories(task: str, session_id: str) -> list[dict]:
    """Read memories relevant to current task from main session."""
    
    # Use sessions_history or memory tools to retrieve
    memories = sessions_history(session_id=session_id)
    
    # Score by relevance to task
    relevant = []
    task_keywords = set(task.lower().split())
    
    for mem in memories:
        mem_text = mem.get("content", "").lower()
        mem_keywords = set(mem_text.split())
        
        # Calculate overlap
        overlap = len(task_keywords & mem_keywords)
        if overlap > 0:
            relevant.append({
                "content": mem["content"],
                "relevance": overlap,
                "timestamp": mem.get("timestamp")
            })
    
    # Sort by relevance
    relevant.sort(key=lambda x: x["relevance"], reverse=True)
    return relevant[:5]  # Max 5 memories
```

## Function 2: sync_memories_to_subagent()

Sync relevant memories to subagent via prompt injection.

### Input
- memories: List of relevant memories
- model: Target model for subagent

### Output
- Formatted context string for prompt injection

### Implementation

```python
def sync_memories_to_subagent(memories: list[dict], model: str) -> str:
    """Format memories into context for subagent."""
    
    if not memories:
        return ""
    
    context_parts = ["## Relevant Context\n"]
    
    for mem in memories:
        context_parts.append(f"- {mem['content']}")
    
    context = "\n".join(context_parts)
    
    # Inject via sessions_spawn with prompt+model only
    sessions_spawn(
        prompt=f"<task>\n\n{context}",
        model=model
    )
    
    return context
```

## Function 3: update_memory()

Update memory after task completion.

### Input
- session_id: Main session
- task_result: Task completion summary
- artifacts: Created/modified files

### Output
- Memory entry updated

### Implementation

```python
def update_memory(session_id: str, task_result: str, artifacts: list[str]) -> dict:
    """Update memory with task completion info."""
    
    memory_entry = {
        "type": "task_completion",
        "result": task_result,
        "artifacts": artifacts,
        "session": session_id
    }
    
    # Store or append to session memory
    # (Implementation depends on storage mechanism)
    
    return memory_entry
```

## Usage Pattern

```
1. read_relevant_memories(task, main_session_id)
      │
      ▼
2. Format context from relevant memories
      │
      ▼
3. sessions_spawn(prompt=task+context, model=model)
      │
      ▼
4. update_memory(session_id, result, artifacts)
```

## Constraints

| Constraint | Rule |
|------------|------|
| Memory size | Keep lightweight (<5 entries) |
| Sensitive data | DO NOT sync credentials, keys, or secrets |
| agentId | NEVER specify - use prompt+model only |
| Context injection | Append to prompt, not separate field |

## Example: Synced Spawn

```python
# Step 1: Read relevant memories
memories = read_relevant_memories(
    task="Implement auth module",
    session_id="main_session"
)

# Step 2: Format context
context = sync_memories_to_subagent(memories, "claude-3.5-sonnet")

# Step 3: Spawn with context (prompt+model ONLY)
sessions_spawn(
    prompt="Implement auth module with JWT. Previous context: existing User model at src/models/user.py",
    model="claude-3.5-sonnet"
)

# Step 4: Update after completion
update_memory(
    session_id="main_session",
    task_result="Auth module implemented with JWT",
    artifacts=["src/auth/jwt.py", "src/models/user.py"]
)
```

## Error Handling

| Scenario | Action |
|----------|--------|
| No memories found | Proceed without context |
| Sensitive data detected | Strip before syncing |
| Memory read failure | Log and continue |
| Update failure | Log error, do not block |

(End of file - SKILL.md)