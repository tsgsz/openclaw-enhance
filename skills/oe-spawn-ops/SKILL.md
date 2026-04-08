---
name: oe-spawn-ops
version: 2.0.0
description: Spawn skill for ops tasks - command execution, deployment, infrastructure management, monitoring, and backup operations.
user-invocable: true
skill-type: spawn
tags: [ops, deployment, infrastructure, monitoring, backup]
allowed-tools: "Read, sessions_spawn, sessions_send, message"
metadata:
  architecture_version: "2.0"
  contract: "sessions_spawn with prompt+model only (no agentId)"
  model_tier: "mid"
  safety_level: "strict"
---

# OPS Spawn Skill (v2)

Spawn skill for operations tasks including command execution, deployment, infrastructure management, monitoring, and backup operations.

## When to Use

Use this skill when:
- User asks to run commands, execute scripts, build/deploy
- Task involves system operations, infrastructure, deployment
- Monitoring, backup, or maintenance operations
- Tags inferred: [ops]

## Model Tier

**Mid tier** - Ops tasks need reliability and balanced performance.

Use `oe-model-discover` to get available mid-tier models before spawning.

## Spawn Recipe

```python
def spawn_ops_session(task: str, context: dict = None) -> dict:
    """
    Spawn an ops subagent for command execution and system operations.
    
    Args:
        task: Full task description with context
        context: Optional context (cwd, env vars, etc.)
    
    Returns:
        sessions_spawn payload with prompt + model (no agentId)
    """
    # 1. Get model for mid tier
    from pathlib import Path
    import json
    
    cache_path = Path.home() / ".openclaw" / "openclaw-enhance" / "model_cache.json"
    
    if cache_path.exists():
        with open(cache_path) as f:
            models = json.load(f)
        mid_models = [m for m in models if m.get("tier") == "mid"]
        model = mid_models[0]["name"] if mid_models else "gpt-4o"
    else:
        model = "gpt-4o"  # Default fallback
    
    # 2. Build ops specialist prompt
    ops_prompt = build_ops_specialist_prompt(task, context)
    
    # 3. Return sessions_spawn payload (v2 contract: prompt + model only)
    return {
        "prompt": ops_prompt,
        "model": model
    }
```

## Ops Specialist Prompt Template

```python
def build_ops_specialist_prompt(task: str, context: dict = None) -> str:
    """Build the ops specialist prompt with safety constraints."""
    
    base_prompt = f"""You are an OPS SPECIALIST agent.

## Your Role
Execute system operations, command execution, deployment, infrastructure management, monitoring, and backup tasks.

## Working Directory
{context.get('cwd', 'default') if context else 'default'}

## Task
{task}

## Safety Rules (STRICT)
- DO NOT execute: rm -rf, rm -r /, dd if=/dev/zero, fork bomb
- DO NOT access production systems without explicit confirmation
- DO NOT modify system-critical files (/etc, /var, /usr/bin)
- ALWAYS confirm destructive commands before execution
- USE dry-run mode when available
- LOG all operations for audit trail

## Allowed Operations
- Build and compile commands (npm build, make, cargo build)
- Deployment scripts (deploy.sh, docker-compose up)
- Service management (systemctl, docker, pm2)
- Monitoring and diagnostics (top, htop, df, du, curl health endpoints)
- Backup operations (tar, rsync with --dry-run first)
- Database migrations with rollback plans

## Execution Guidelines
1. Understand the task fully before executing
2. Check current state before making changes
3. Use --dry-run for destructive operations first
4. Provide clear progress updates
5. Report results with exit codes and output summaries
"""
    
    return base_prompt
```

## Safety Constraints

| Operation Type | Allowed | Conditions |
|---------------|---------|------------|
| File deletion | ⚠️ Limited | Only in project dir, confirm first |
| System commands | ✅ Allowed | Non-destructive, logged |
| Production access | ❌ Blocked | Requires explicit confirmation |
| Database ops | ⚠️ Careful | Must have rollback plan |
| Service restart | ⚠️ Careful | Only dev/staging, confirm first |
| Backup | ✅ Allowed | Always use --dry-run first |

## Blocked Commands

The following commands are BLOCKED and must not be executed:

```python
BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/",           # Root deletion
    r"rm\s+-rf\s+/\.",         # System deletion
    r"dd\s+if=/dev/zero",      # Disk wipe
    r":\(\)\{",                # Fork bomb
    r"curl\s+.*\|\s*bash",     # Pipe to bash (dangerous)
    r"wget\s+.*\|\s*bash",     # Pipe to bash
    r"sudo\s+rm",              # Sudo delete
    r"chmod\s+-R\s+777",       # World-writable
    r">\s*/dev/sd",            # Direct disk write
]
```

## Execution Flow

```
User Request (ops tag)
        │
        ▼
┌─────────────────┐
│ Validate Task   │───► Check for blocked commands
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Select Model    │───► Mid tier via oe-model-discover
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Build Prompt    │───► Ops specialist template + safety
└─────────────────┘
        │
        ▼
sessions_spawn(prompt, model)
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Blocked command detected | Reject and explain why |
| Production access requested | Block + require confirmation |
| Command fails | Provide error details + suggest fix |
| Permission denied | Check sudo or suggest alternative |

## Example Usage

### Build task
- **User:** "Build the Docker image"
- **Tags:** [ops]
- **Model:** mid tier (gpt-4o)
- **Action:** `sessions_spawn(prompt="Build Docker image...", model="gpt-4o")`

### Deployment
- **User:** "Deploy to staging environment"
- **Tags:** [ops]
- **Model:** mid tier (gpt-4o)
- **Action:** `sessions_spawn(prompt="Deploy to staging...", model="gpt-4o")`

### Monitoring
- **User:** "Check service health status"
- **Tags:** [ops, monitoring]
- **Model:** mid tier (gpt-4o)
- **Action:** `sessions_spawn(prompt="Check service health...", model="gpt-4o")`

## Notes

- This skill spawns a subagent with the ops specialist prompt
- The subagent has access to Read, Write, Bash tools for operations
- Safety first: block destructive commands without confirmation
- Mid tier provides reliability for operational tasks
- Always log operations for audit trail
