---
name: oe-git-context
version: 1.0.0
description: Git history and context injection for worker tasks
author: openclaw-enhance
tags: [orchestrator, git, context, history, workers]
---

# oe-git-context

Skill for extracting and injecting git context into worker tasks.

## Purpose

Git history provides crucial context for coding tasks. This skill:
- Extracts relevant git history
- Identifies recent changes and authors
- Finds related commits and files
- Injects context into worker prompts
- Tracks changes during task execution

## When to Use

Use this skill when:
- Starting work on existing code
- Debugging issues (find when introduced)
- Understanding code evolution
- Reviewing changes before/after work
- Providing context to subagents
- Tracking task-related changes

## Capabilities

### Context Extraction

#### Recent History
```bash
# Last N commits
git log -n 10 --oneline

# Recent commits with stats
git log -n 5 --stat

# Recent changes to specific file
git log -n 5 --follow -- src/module.py
```

#### File History
```bash
# Who changed this file
git log --follow --format="%h %an %s" -- src/file.py

# When was line added
git blame -L 10,20 src/file.py

# File evolution
git log --follow -p -- src/file.py
```

#### Branch Information
```bash
# Current branch
git branch --show-current

# Branches containing commit
git branch --contains abc123

# Branch divergence
git log --oneline --graph --left-right main...feature
```

### Context Types

#### 1. Recent Changes Context
Provides overview of recent activity

```markdown
## Recent Changes (Last 5 commits)

| Commit | Author | Message | Date |
|--------|--------|---------|------|
| abc123 | Alice | feat(auth): add OAuth support | 2 hours ago |
| def456 | Bob | fix(api): handle null responses | 5 hours ago |
| ... | ... | ... | ... |

### Files Changed Recently
- src/auth/oauth.py (added)
- src/api/handlers.py (modified)
- tests/test_oauth.py (added)
```

#### 2. File-Specific Context
Provides history for specific files being worked on

```markdown
## File History: src/auth/oauth.py

### Evolution
1. **Initial commit** (2 weeks ago) - Basic OAuth structure
2. **Add token refresh** (1 week ago) - Refresh token support
3. **Error handling** (3 days ago) - Better error messages
4. **OAuth support** (2 hours ago) - Added OAuth2 flow

### Authors
- Alice: 5 commits
- Bob: 2 commits

### Related Files (changed together)
- src/auth/token.py
- src/config/auth.py
```

#### 3. Related Commits Context
Finds commits related to a topic

```markdown
## Related Commits for "authentication"

Commits mentioning auth/authentication:
- abc123: feat(auth): add OAuth support
- def789: refactor(auth): extract auth logic
- xyz789: test(auth): add auth tests
```

#### 4. Line-Level Context
Blame information for specific code sections

```markdown
## Code Context (lines 45-55)

```python
def validate_token(token: str) -> bool:  # Alice, 2 days ago
    """Validate JWT token."""                   # Alice, 2 days ago
    try:                                        # Bob, 1 week ago
        payload = decode(token)                 # Alice, 2 days ago
        return payload["exp"] > time.time()    # Alice, 2 days ago
    except JWTError:                            # Bob, 1 week ago
        return False                            # Bob, 1 week ago
```

- Last modified by: Alice
- Context: "Add token validation"
- Related PR: #123
```

## Usage

### Extract Context for Task
```python
context = extract_git_context(
    project_path="/path/to/project",
    files=["src/auth/oauth.py", "src/api/handlers.py"],
    context_types=["recent", "file_history", "related"],
    depth=10  # commits to include
)
```

### Inject into Worker Prompt
```python
worker_prompt = f"""
{task_description}

## Git Context
{format_git_context(context)}

## Task
Implement the feature considering the above context.
"""
```

### Track Changes During Task
```python
# Before starting
baseline = get_git_snapshot(project_path)

# ... task execution ...

# After completing
changes = get_changes_since(baseline)
```

## Context Injection Strategies

### Strategy 1: Full History
Include complete recent history
- **Best for**: New contributors, complex tasks
- **Cost**: Higher token usage
- **Format**: All recent commits + file histories

### Strategy 2: Focused History
Include only relevant commits
- **Best for**: Focused changes, experienced developers
- **Cost**: Moderate token usage
- **Format**: Commits touching relevant files only

### Strategy 3: Summary Only
High-level overview
- **Best for**: Quick tasks, familiar codebase
- **Cost**: Low token usage
- **Format**: Statistics and key changes only

## Worker Integration

### searcher
```python
# Search task with git context
prompt = f"""
Research best practices for OAuth implementation.

Context: We're adding OAuth to an existing auth system.
Recent auth-related changes:
{git_context.recent_auth_commits}
"""
```

### script_coder
```python
# Coding task with git context
prompt = f"""
Add refresh token support to the OAuth implementation.

Current OAuth code (from git history):
{git_context.file_history('src/auth/oauth.py')}

Recent related changes:
{git_context.recent_changes}
"""
```

### syshelper
```python
# File exploration with git context
prompt = f"""
Find all files that changed in the last OAuth PR.

Reference commit: {git_context.recent_auth_commit}
Changed files: {git_context.changed_files}
"""
```

## Best Practices

1. **Selective Context**: Don't include all history - focus on relevant commits
2. **Recency Bias**: Recent changes are more relevant than old ones
3. **Author Awareness**: Note who made changes for potential questions
4. **Related Files**: Files changed together are often logically related
5. **Baseline Snapshots**: Record git state at task start for comparison

## Safety

### Read-Only Operations
All git operations in this skill are read-only:
- `git log`
- `git blame`
- `git show`
- `git diff`
- `git status`

### No Modifications
This skill never:
- Creates commits
- Changes branches
- Modifies files
- Runs `git checkout`, `git reset`, etc.

## Integration

### With oe-project-registry
Get project path from registry for context extraction

### With oe-worker-dispatch
Inject context into worker prompts automatically

### With planning-with-files
Include git context in task plans for reference

## Example: Complete Workflow

```python
# 1. Get project info
project = get_project("proj-001")

# 2. Extract context for task
context = extract_git_context(
    project_path=project.path,
    files=["src/auth/oauth.py"],
    context_types=["recent", "file_history"]
)

# 3. Create worker prompt with context
prompt = f"""
Add OAuth2 refresh token support.

Current implementation context:
{format_context(context)}

Requirements:
- Support refresh token flow
- Maintain backward compatibility
- Add appropriate tests
"""

# 4. Dispatch to worker
result = dispatch_task(
    agent_type="script_coder",
    task=prompt
)

# 5. Track changes
changes = get_task_changes(project.path)
```

## Output Formats

### Markdown Format
Default human-readable format with tables and sections

### JSON Format
Machine-readable for programmatic processing
```json
{
  "recent_commits": [...],
  "file_history": {
    "src/file.py": [...]
  },
  "related_commits": [...],
  "authors": {...}
}
```

### Compact Format
Token-optimized for LLM consumption
```
Recent: abc123 feat(auth): OAuth, def456 fix(api): nulls
Files: src/auth/oauth.py (Alice 5x, Bob 2x)
```
