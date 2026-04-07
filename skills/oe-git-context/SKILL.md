---
name: oe-git-context
version: 2.0.0
description: Injects git context into subagent spawn prompts. Provides branch, recent commits, and repo state info for better task context.
user-invocable: true
skill-type: context
tags: []
allowed-tools: "Bash"
metadata:
  architecture_version: "2.0"
  contract: "sessions_spawn with prompt+model only (no agentId)"
  purpose: "git context injection for subagent tasks"
---

# Git Context (v2)

Injects git context into subagent spawn prompts to provide workers with repository state information.

## Purpose

When the orchestrator spawns subagents for tasks within a git repository, this skill provides:
- Current branch name
- Recent commit history
- Repository state (clean/dirty, untracked files)

This helps subagents understand the context they're working in, especially for:
- Code review tasks (what changed recently)
- Bug fixes (what commits might have introduced the issue)
- Feature implementation (branch context)
- Refactoring (commit history context)

## Functions

### get_git_context()

Returns current git context information.

**Returns:**
```python
{
    "branch": "feature/new-login",
    "recent_commits": [
        "abc1234 Add user authentication flow",
        "def5678 Fix login button styling",
        "ghi9012 Initial commit"
    ],
    "repo_state": "dirty",  # or "clean"
    "untracked_files": ["src/new-feature.ts"],
    "staged_files": ["README.md"],
    "modified_files": ["src/auth.ts"]
}
```

**Implementation:**
```python
import subprocess
from pathlib import Path

def get_git_context() -> dict:
    """Get current git context for the repository."""
    context = {
        "branch": "unknown",
        "recent_commits": [],
        "repo_state": "unknown",
        "untracked_files": [],
        "staged_files": [],
        "modified_files": []
    }
    
    # Get current branch
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            context["branch"] = result.stdout.strip()
    except Exception:
        pass
    
    # Get recent commits (last 5)
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            context["recent_commits"] = [
                line.strip() for line in result.stdout.strip().split("\n") if line
            ]
    except Exception:
        pass
    
    # Get repo state
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
            
            for line in lines:
                if not line:
                    continue
                status = line[:2]
                filename = line[3:]
                
                if status == "??":
                    context["untracked_files"].append(filename)
                elif status.startswith("-"):
                    context["modified_files"].append(filename)
                elif status in ["M ", "MM", " A", "AA"]:
                    context["staged_files"].append(filename)
                elif status == "M " or status == " M":
                    context["modified_files"].append(filename)
            
            context["repo_state"] = "dirty" if lines else "clean"
    except Exception:
        pass
    
    return context
```

### inject_git_context(prompt: str) -> str

Injects git context into a spawn prompt.

**Args:**
- `prompt`: Original task prompt for the subagent

**Returns:**
- Enhanced prompt with git context prepended

**Implementation:**
```python
def inject_git_context(prompt: str) -> str:
    """Inject git context into spawn prompt."""
    context = get_git_context()
    
    context_section = f"""## Git Context
- Branch: {context['branch']}
- State: {context['repo_state']}
"""
    
    if context['recent_commits']:
        commits_str = "\n".join([f"  - {c}" for c in context['recent_commits'][:3]])
        context_section += f"- Recent commits:\n{commits_str}\n"
    
    if context['modified_files']:
        files_str = ", ".join(context['modified_files'][:5])
        context_section += f"- Modified files: {files_str}\n"
    
    if context['untracked_files']:
        files_str = ", ".join(context['untracked_files'][:5])
        context_section += f"- Untracked files: {files_str}\n"
    
    return f"{context_section}\n{prompt}"
```

## sessions_spawn Contract (v2)

**MUST USE:** `prompt` + `model` only. **NO agentId.**

```json
{
  "prompt": "<git context>\n\n<task description>",
  "model": "<selected-model-name>"
}
```

**Example with git context:**
```python
# Before spawning, inject git context
context = get_git_context()
enhanced_prompt = inject_git_context(original_task)

# Spawn with enhanced prompt
sessions_spawn(
    prompt=enhanced_prompt,
    model="claude-3.5-sonnet"
)
```

## Usage Pattern

```python
# 1. Get original task from user
original_task = "Fix the login timeout issue in src/auth.ts"

# 2. Inject git context
enhanced_task = inject_git_context(original_task)

# 3. Spawn subagent with enhanced prompt
# (NO agentId - use prompt+model contract only)
sessions_spawn(
    prompt=enhanced_task,
    model="gpt-4o"
)
```

**Resulting prompt sent to subagent:**
```markdown
## Git Context
- Branch: feature/auth-fix
- State: dirty
- Recent commits:
  - abc1234 Fix session timeout handling
  - def5678 Add logout functionality
  - ghi9012 Refactor auth middleware
- Modified files: src/auth.ts, tests/auth.test.ts

Fix the login timeout issue in src/auth.ts
```

## Lightweight Design

This skill is designed to be lightweight:

1. **Timeout protection**: All git commands have 5-second timeout
2. **Limited output**: Only fetches last 5 commits, limited file lists
3. **Error resilience**: Continues even if git commands fail
4. **No credentials**: Never exposes sensitive git config or tokens

## Integration

Use this skill when:
- Spawning code-related subagents
- Debugging issues that might relate to recent changes
- Performing code reviews
- Implementing features in a specific branch context

The git context helps subagents make better decisions by understanding:
- What branch they're on
- What recent changes exist
- Whether there are uncommitted changes that might affect their work