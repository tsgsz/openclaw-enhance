# Validation Report: backfill-routing-yield

- **Date**: 2026-03-14
- **Feature Class**: workspace-routing
- **Environment**: macOS /Users/tsgsz/.openclaw
- **Conclusion**: PASS

## Baseline State

- OpenClaw Home: `/Users/tsgsz/.openclaw`
- Installed: False
- Config Exists: False

## Execution Log

### Command 1: ✓ PASS

```bash
python -m openclaw_enhance.cli render-workspace oe-orchestrator
```

- Exit Code: 0
- Duration: 0.08s

**stdout:**
```
# Workspace: oe-orchestrator

**Path:** `/Users/tsgsz/workspace/openclaw-enhance/workspaces/oe-orchestrator`

# Orchestrator Agent Configuration

This AGENTS.md defines the capabilities and constraints for the `oe-orchestrator` workspace.

## Role

The Orchestrator is a high-capability agent responsible for:
- **Project Discovery**: Identifying and cataloging projects within the workspace
- **Workspace Selection**: Determining the appropriate workspace for tasks
- **Task Splitting**: Breaking complex tasks into manageable subtasks
- **Worker Dispatch**: Distributing work to specialized subagents via native `announce` mechanism
- **Result Synthesis**: Aggregating and synthesizing results from child agents
- **Git Context Injection**: Providing rich git history and context to workers

## Capabilities

### Core Responsibilities
1. **Task Assessment**: Evaluate incoming tasks for complexity, parallelism needs, and duration
2. **Strategic Planning**: Create execution plans using file-based planning when appropriate
3. **Resource Management**: Select optimal workspaces and agent configurations
4. **Quality Assurance**: Verify child agent outputs and ensure completeness
5. **Progress Tracking**: Monitor subagent progress and handle timeouts

### Native Subagent Dispatch
The Orchestrator uses the native `announce` mechanism to dispatch work:

```
Orchestrator
    ↓ announce
Subagent (specialized)
    ↓ return result
Orchestrator ← synthesize results
```

### Worker Selection (Catalog-Driven)

The Orchestrator discovers and selects workers dynamically from their `AGENTS.md` frontmatter:

1. **Enumerate**: Scan `workspaces/*/AGENTS.md` for available workers
2. **Parse**: Extract routing metadata (capabilities, constraints, cost) from YAML frontmatter to build candidate catalog
3. **Filter**: Apply hard constraints based on task requirements (e.g., `mutation_mode: read_only` for safe exploration)
4. **Rank**: Select by least-privilege rules (narrowest scope, lowest cost, best capability match)
5. **Dispatch**: Spawn selected worker via `sessions_spawn`

**Current Built-in Workers** (non-authoritative examples):
- `searcher`: Research, web search, documentation lookup (cheap model + read-only)
- `syshelper`: System introspection, grep, file listing (cheap model + read-only)
- `script_coder`: Script development and testing (standard model + repo write + requires tests)
- `watchdog`: Session monitoring, timeout detection, diagnostics (specialized monitoring role)
- `tool_recovery`: Leaf-node recovery specialist for failed tool calls (reasoning model + read-only)

**Note**: Worker capabilities are defined in their respective `AGENTS.md` frontmatter, not in this list. This section provides examples only; the Orchestrator must discover actual worker metadata at runtime.

## Constraints

### Tool Usage
- **Read/Write**: Full access for planning files and project metadata
- **Bash**: Limited to project discovery and git operations
- **Native subagent**: Primary dispatch mechanism - use `announce` for all worker tasks
- **LSP**: Available for code intelligence when needed

### Workspace Boundaries
- Operates within `workspaces/oe-orchestrator/`
- Skills located in `workspaces/oe-orchestrator/skills/`
- Respects project boundaries defined in project registry

### Decision Authority
- Can create subtasks but not modify main session state
- Can recommend workspace selection but final choice rests with user
- Must escalate configuration changes to main session

## Workflow

### Bounded Round-Based Orchestration Loop

The Orchestrator uses a **bounded multi-round loop** to handle complex tasks that require iterative refinement. This replaces the previous one-shot fan-out/fan-in model with an event-driven approach using `sessions_yield` as the round-boundary synchronization primitive.

#### Round Lifecycle

Each orchestration proceeds through bounded rounds:

```
Assess → PlanRound → DispatchRound → YieldForResults → CollectResults → EvaluateProgress
                                                                     ↓
                                     Complete ←── No more work needed
                                     Blocked ←── Needs main decision
                                     Re-dispatch ←── More rounds needed
```

**Round States:**

1. **Assess**: Evaluate incoming task complexity using `oe-eta-estimator`
2. **PlanRound**: Create execution plan for the current round
3. **DispatchRound**: Spawn worker subagents via native `sessions_spawn`
4. **YieldForResults**: Call `sessions_yield` to end current turn cleanly
5. **CollectResults**: Receive auto-announced worker results on next turn
6. **EvaluateProgress**: Analyze results, update state, decide next action

**Decision outcomes from EvaluateProgress:**
- **Complete**: Sufficient results gathered, synthesize and return to main
- **Blocked**: External decision needed, yield checkpoint to main
- **Re-dispatch**: Schedule next round with refined tasks
- **Recovery Dispatch**: Tool-usage failure detected; dispatch `oe-tool-recovery`
- **Recovery-Assisted Retry**: Retry original worker with `recovered_method` (max 1 retry)
- **Escalated**: Recovery failed or retry failed; terminate with escalation

#### Orchestrator-Owned Loop State

Each orchestration maintains explicit state:

| Field | Purpose |
|-------|---------|
| `task_id` | Unique identifier for this orchestration |
| `round_index` | Current round number (0-indexed) |
| `max_rounds` | Maximum allowed rounds (default: 3, hard cap: 5) |
| `pending_dispatches` | Workers dispatched in current round awaiting results |
| `received_results` | Results collected from completed workers |
| `blocked_items` | Issues requiring external intervention |
| `dedupe_keys` | Identifiers to prevent duplicate dispatches |
| `recovery_attempts` | Dict mapping `failed_step_id` -> count (max 1 per step) |
| `recovered_methods` | Dict mapping `failed_step_id` -> `RecoveredMethod` object |
| `recovery_in_progress` | Boolean flag to prevent nested recovery |
| `termination_state` | One of: `active`, `completed`, `blocked`, `exhausted`, `escalated` |
| `termination_reason` | Human-readable explanation of termination |

#### Loop Controls (Mandatory)

- **Max rounds**: Default 3, hard cap 5. Orchestration must terminate if limit reached.
- **Max dispatches per round**: Default 3, hard cap 5 concurrent workers.
- **Incrementality rule**: New round only if it narrows uncertainty or adds new evidence.
- **Duplicate dispatch guard**: Same worker + objective + context cannot be resent without new evidence.
- **Blocker escalation**: If two consecutive evaluations show no progress, terminate as `blocked`.
- **Recovery Cap**: Max ONE recovery-assisted retry per failed step.
- **No Recovery Loops**: Recovery worker failure or retry failure escalates immediately; do NOT re-enter recovery for the same step.
- **No Worker Handoff**: Recovery dispatch does NOT create worker-to-worker handoff; the Orchestrator remains the sole dispatcher.

#### Tool Recovery Flow

The Orchestrator manages tool-usage failures (e.g., `tool_not_found`, `invalid_parameters`, `permission_denied`, `tool_execution_error`) via a specialized recovery branch:

1. **Detection**: `EvaluateProgress` identifies a tool-usage failure in worker results.
2. **Eligibility Check**: Verify `recovery_attempts[failed_step_id]` is 0 and `recovery_in_progress` is false.
3. **Recovery Dispatch**: Spawn `oe-tool-recovery` via `sessions_spawn` with the failed context.
4. **Yield**: Call `sessions_yield` to await recovery results.
5. **Integration**: On next turn, validate `RecoveredMethod`, store in `recovered_methods`, and increment `recovery_attempts`.
6. **Assisted Retry**: Re-dispatch the original worker using the `exact_invocation` from `RecoveredMethod`.
7. **Escalation**: If recovery fails, or the assisted retry fails, terminate the orchestration as `escalated`.

#### Native Primitive Usage

- **`sessions_spawn`**: Create worker subagents (only execution path for workers)
- **`sessions_yield`**: End orchestrator turn to await auto-announced results
- **`announce`**: Workers return results via native mechanism

**Important**: `sessions_yield` is used ONLY by the orchestrator at round boundaries. Workers remain single-round executors and do not use yield.

### Checkpoint Visibility (Semi-Visible Model)

Main session receives checkpoints only at milestone events:

**Main sees:**
- `started`: Orchestration begins
- `meaningful_progress`: Significant phase completed (optional, suppress routine rounds)
- `blocked`: Requires main decision or intervention
- `terminal`: Completion or exhaustion

**Main does NOT see:**
- Individual worker results within a round
- Routine round boundaries
- Internal re-dispatch decisions

### Deprecated: One-Shot Escalation Path

The previous linear escalation path has been replaced by the bounded loop above. Complex tasks now proceed through iterative rounds rather than single-pass dispatch.

## Collaboration

### With Main Session
- Receives escalated tasks from main
- Returns synthesized results to main
- Does not modify main session configuration

### With Subagents
- Dispatches via native `announce` mechanism
- Provides full context including git history
- Expects structured results from workers

### With Watchdog
- Can spawn watchdog for long-running tasks
- Receives timeout notifications
- Coordinates recovery actions

## Output Format

All Orchestrator responses should include:
1. **Summary**: Brief description of what was done
2. **Results**: Synthesized output from all workers
3. **Artifacts**: Paths to created/modified files
4. **Next Steps**: Recommendations for follow-up

## Skills Available

- `oe-project-registry`: Project discovery and management
- `oe-worker-dispatch`: Subagent task assignment
- `oe-agentos-practice`: AgentOS pattern implementation
- `oe-git-context`: Git history and context injection
- `planning-with-files`: File-based task planning
- `dispatching-parallel-agents`: Parallel subagent coordination

## Version

Version: 1.0.0
Last Updated: 2026-03-13


---

# Orchestrator Tools Configuration

This TOOLS.md defines the available tools and their usage patterns for the `oe-orchestrator` workspace.

## Core Tools

### Read
**Purpose**: Read files and directories to gather context

**Usage Patterns**:
- Read project configuration files (`pyproject.toml`, `package.json`)
- Read planning files from `.sisyphus/plans/`
- Read skill definitions from `workspaces/oe-orchestrator/skills/`
- Read project metadata from registry

**Best Practices**:
- Always check file existence before reading
- Use offset/limit for large files
- Read AGENTS.md and TOOLS.md of target workspaces before dispatch

### Write
**Purpose**: Create and update files

**Usage Patterns**:
- Create task plans in `.sisyphus/plans/`
- Write subagent instructions
- Update project registry
- Create result synthesis documents

**Constraints**:
- Never overwrite without reading first
- Always include proper headers/metadata
- Use atomic writes when possible

### Bash
**Purpose**: Execute shell commands

**Usage Patterns**:
- Project discovery: `find`, `ls`, `git status`
- Git operations: `git log`, `git diff`, `git branch`
- Environment checks: `python --version`, `node --version`

**Security**:
- Read-only commands preferred
- Avoid destructive operations
- Validate inputs to prevent injection

### Glob
**Purpose**: Find files matching patterns

**Usage Patterns**:
- Find all projects: `**/pyproject.toml`
- Find skill files: `**/SKILL.md`
- Find test files: `**/test_*.py`
- Find planning files: `.sisyphus/**/*.md`

### Grep
**Purpose**: Search file contents

**Usage Patterns**:
- Search for dependencies in config files
- Find TODO comments across projects
- Locate specific function implementations
- Search for error patterns in logs

## LSP Tools

### lsp_goto_definition
**Purpose**: Jump to symbol definition

**Usage**: Navigate to function/class definitions when analyzing code

### lsp_find_references
**Purpose**: Find all usages of a symbol

**Usage**: Assess impact of changes before dispatching refactoring tasks

### lsp_symbols
**Purpose**: Get file outline or search workspace symbols

**Usage**: Understand file structure and find symbols quickly

### lsp_diagnostics
**Purpose**: Check for errors/warnings

**Usage**: Validate code health before and after changes

## Agent Management Tools

### call_omo_agent
**Purpose**: Spawn specialized subagents

**Usage Patterns**:
- Spawn `searcher` for research tasks
- Spawn `syshelper` for system introspection
- Spawn `script_coder` for script development
- Spawn `watchdog` for monitoring

**Parameters**:
- `description`: Clear task description
- `prompt`: Detailed instructions for the agent
- `run_in_background`: Set to `true` for async execution

**Best Practices**:
- Use `run_in_background=True` for parallel tasks
- Include full context in prompt
- Set clear expectations for output format

### background_output
**Purpose**: Retrieve results from background agents

**Usage Patterns**:
- Poll for completion status
- Retrieve partial results for progress updates
- Get final output after agent completes

### background_cancel
**Purpose**: Cancel running background tasks

**Usage Patterns**:
- Cancel tasks exceeding ETA
- Clean up on error conditions
- Stop parallel tasks when one fails

## Workspace Tools

### skill
**Purpose**: Load and execute skills

**Usage Patterns**:
- Load `oe-project-registry` for project discovery
- Load `oe-worker-dispatch` for subagent management
- Load `oe-git-context` for git operations
- Load `planning-with-files` for task planning

## Session Tools

### session_list
**Purpose**: List OpenCode sessions

**Usage**: Monitor active sessions for watchdog functionality

### session_read
**Purpose**: Read session history

**Usage**: Analyze past interactions for context

### session_search
**Purpose**: Search session messages

**Usage**: Find specific conversations or patterns

### session_info
**Purpose**: Get session metadata

**Usage**: Check session status and activity

## Web Tools

### webfetch
**Purpose**: Fetch web content

**Usage**: Retrieve documentation, API specs, or examples

### websearch_web_search_exa
**Purpose**: Search the web

**Usage**: Research topics, find libraries, look up best practices

### grep_app_searchGitHub
**Purpose**: Search GitHub code

**Usage**: Find real-world code examples for implementation patterns

### context7_resolve-library-id / context7_query-docs
**Purpose**: Query library documentation

**Usage**: Get up-to-date API documentation and examples

## Tool Selection Guide

### When to Use Each Tool

| Task Type | Primary Tools | Secondary Tools |
|-----------|--------------|-----------------|
| Project Discovery | Glob, Read | Bash, Grep |
| Task Planning | Write, Read | skill(planning-with-files) |
| Code Analysis | Read, lsp_symbols | lsp_goto_definition, lsp_find_references |
| Worker Dispatch | call_omo_agent | background_output, background_cancel |
| Result Synthesis | Read, Write | Grep, Glob |
| Git Context | Bash(git) | Read, Grep |
| Research | websearch_web_search_exa | webfetch, grep_app_searchGitHub |
| Monitoring | session_list, session_info | call_omo_agent(watchdog) |

## Output Formats

### Task Plan Format
```markdown
# Task Plan: [Name]

## Overview
Brief description

## Steps
1. [Step 1]
2. [Step 2]
...

## ETA
Estimated duration

## Subagents
- Agent 1: Task description
- Agent 2: Task description
```

### Dispatch Request Format
```yaml
agent_type: [searcher|syshelper|script_coder|watchdog]
task: Clear description
context:
  - Relevant file paths
  - Key constraints
  - Expected output
output_format: Structured format specification
timeout: Estimated duration
```

### Result Synthesis Format
```markdown
## Summary
Brief overview of completed work

## Results
### From [Agent 1]
- Result item 1
- Result item 2

### From [Agent 2]
- Result item 1

## Artifacts
- `/path/to/file1` - Description
- `/path/to/file2` - Description

## Next Steps
1. Recommended action 1
2. Recommended action 2
```

## Constraints

1. **Never modify main session state directly**
2. **Always validate inputs before bash commands**
3. **Use LSP tools for code intelligence over manual parsing**
4. **Prefer native subagent dispatch for parallel work**
5. **Always include ETA estimates with dispatches**


---

# Workspace Skills

## oe-agentos-practice

---
name: oe-agentos-practice
version: 1.0.0
description: AgentOS pattern implementation for coding tasks
author: openclaw-enhance
tags: [orchestrator, agentos, patterns, coding, best-practices]
---

# oe-agentos-practice

Skill for implementing AgentOS patterns and best practices in coding tasks.

## Purpose

AgentOS patterns provide structured approaches to common coding tasks. This skill helps the Orchestrator:
- Apply consistent patterns across projects
- Ensure code quality and maintainability
- Follow established conventions
- Generate boilerplate efficiently

## When to Use

Use this skill when:
- Starting new features or modules
- Refactoring existing code
- Creating tests or documentation
- Setting up project structure
- Implementing common patterns

## Core Patterns

### 1. Skill-Based Development

**Pattern**: Encapsulate capabilities in reusable skills

```python
# Structure
skills/
  my-skill/
    SKILL.md          # Contract and documentation
    implementation/   # Code (if needed)
    tests/            # Tests for the skill
```

**Usage**:
- Define clear contracts in SKILL.md
- Version skills independently
- Test skills in isolation
- Document usage examples

### 2. File-Based Planning

**Pattern**: Use files for task planning and tracking

```
.sisyphus/
  plans/
    feature-x.md      # The plan
  notepads/
    feature-x/
      learnings.md    # Patterns discovered
      issues.md       # Problems encountered
      decisions.md    # Architectural choices
```

**Usage**:
- Create plan before complex work
- Record learnings during implementation
- Document decisions with rationale
- Track issues for resolution

### 3. Atomic Commits

**Pattern**: Each commit does one thing completely

```
✓ feat(auth): add JWT token validation
✓ test(auth): add tests for JWT validation
✓ refactor(auth): extract token parsing to helper
✗ feat(auth): add JWT and fix logout bug
```

**Usage**:
- One logical change per commit
- Commit passes tests
- Clear commit messages
- Related changes grouped

### 4. Test-First Development

**Pattern**: Write tests before implementation

```python
# 1. Write test (fails)
def test_calculate_total():
    assert calculate_total([1, 2, 3]) == 6

# 2. Implement (passes)
def calculate_total(items):
    return sum(items)

# 3. Refactor (still passes)
def calculate_total(items: list[int]) -> int:
    return sum(items)
```

**Usage**:
- Red-Green-Refactor cycle
- Tests define requirements
- Refactor with confidence
- Maintain coverage

### 5. Incremental Implementation

**Pattern**: Build features in small, working increments

```
Increment 1: Basic structure (compiles/runs)
Increment 2: Core functionality (basic cases work)
Increment 3: Error handling (edge cases covered)
Increment 4: Optimization (performance improved)
```

**Usage**:
- Each increment is deployable
- Get feedback early
- Reduce risk
- Easier debugging

## Coding Conventions

### Python

**Project Structure**:
```
project/
  src/
    package/
      __init__.py
      module.py
  tests/
    unit/
    integration/
  docs/
  pyproject.toml
```

**Code Style**:
- Use `ruff` for linting/formatting
- Type hints required for public APIs
- Docstrings: Google style
- Maximum line length: 100

**Testing**:
- `pytest` for test framework
- Tests in `tests/` directory
- Mirror source structure in tests
- Use fixtures for common setup

### JavaScript/TypeScript

**Project Structure**:
```
project/
  src/
  tests/
  dist/
  package.json
  tsconfig.json
```

**Code Style**:
- Use `eslint` and `prettier`
- Prefer TypeScript
- Explicit return types on exports

## Implementation Workflows

### New Feature Workflow

1. **Plan**: Create `.sisyphus/plans/feature.md`
2. **Design**: Document approach in decisions.md
3. **Interface**: Define public API first
4. **Tests**: Write tests for the interface
5. **Implement**: Code to pass tests
6. **Refactor**: Clean up while tests pass
7. **Document**: Update docs with examples
8. **Review**: Self-review against checklist

### Refactoring Workflow

1. **Identify**: Find code to refactor
2. **Test Coverage**: Ensure tests exist
3. **Characterization**: Write tests for current behavior
4. **Small Steps**: One refactoring at a time
5. **Verify**: Tests pass after each step
6. **Commit**: Commit after each refactoring

### Bug Fix Workflow

1. **Reproduce**: Create failing test
2. **Isolate**: Find minimal reproduction
3. **Fix**: Make minimal change to fix
4. **Test**: Ensure test passes
5. **Regression**: Check for similar bugs
6. **Document**: Update changelog/issue

## Code Generation Templates

### Python Module Template
```python
"""Brief module description.

Longer description if needed.
"""

from __future__ import annotations

__all__ = ["public_function"]


def public_function(arg: str) -> str:
    """Short description.
    
    Longer description.
    
    Args:
        arg: Description of arg
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When arg is invalid
        
    Example:
        >>> public_function("test")
        'result'
    """
    return arg.upper()
```

### Test Template
```python
"""Tests for module_name."""

import pytest

from package.module import function


class TestFunctionName:
    """Test cases for function_name."""
    
    def test_happy_path(self):
        """Test normal operation."""
        result = function("input")
        assert result == "expected"
    
    def test_edge_case_empty(self):
        """Test with empty input."""
        result = function("")
        assert result == ""
    
    def test_error_invalid_input(self):
        """Test error handling."""
        with pytest.raises(ValueError, match="expected message"):
            function(None)
```

## Quality Checklists

### Before Committing Code
- [ ] Tests pass (`pytest`)
- [ ] Linting passes (`ruff`)
- [ ] Type checking passes (`mypy`)
- [ ] Docstrings complete
- [ ] No debug code left
- [ ] Commit message follows convention

### Before Creating PR
- [ ] All tests pass
- [ ] Code reviewed (self or peer)
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] No merge conflicts

### Before Marking Complete
- [ ] Feature works as specified
- [ ] Edge cases handled
- [ ] Error messages helpful
- [ ] Performance acceptable
- [ ] No known issues

## Integration

### With oe-worker-dispatch
Use script_coder agents for implementation following these patterns

### With oe-project-registry
Apply patterns appropriate to project type

### With planning-with-files
Record patterns used in notepads

## Example: Complete Feature Implementation

```
1. Create plan
   .sisyphus/plans/user-auth.md
   
2. Design decisions
   .sisyphus/notepads/user-auth/decisions.md
   - "Using JWT for stateless auth"
   - "Token expiry: 24 hours"
   
3. Define interface
   src/auth/interface.py
   
4. Write tests
   tests/unit/test_auth.py
   
5. Implement
   src/auth/jwt_handler.py
   
6. Refactor
   Extract common utilities
   
7. Document
   docs/auth.md
   
8. Review
   Check against quality checklist
```


---

## oe-git-context

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


---

## oe-project-registry

---
name: oe-project-registry
version: 1.0.0
description: Project discovery and management for the Orchestrator
author: openclaw-enhance
tags: [orchestrator, project, discovery, registry]
---

# oe-project-registry

Skill for discovering, registering, and managing projects within the OpenClaw workspace.

## Purpose

The Orchestrator needs to understand the project landscape to make intelligent decisions about:
- Where to execute tasks
- What type of project is being worked on
- Which workspace configuration to apply
- How to route subagents

## When to Use

Use this skill when:
- Starting work in an unknown directory
- Need to identify project type (Python, Node.js, Rust, etc.)
- Determining workspace selection for tasks
- Creating new projects
- Listing available projects

## Capabilities

### Project Discovery
Automatically detect project types by examining:
- `pyproject.toml` → Python project
- `package.json` → Node.js project
- `Cargo.toml` → Rust project
- `go.mod` → Go project
- `pom.xml` / `build.gradle` → Java project
- `Gemfile` → Ruby project
- `composer.json` → PHP project
- `Makefile` / `CMakeLists.txt` → C/C++ project

### Project Registry
Maintain a registry of discovered projects:
```json
{
  "projects": [
    {
      "id": "unique-project-id",
      "name": "Project Name",
      "type": "python",
      "path": "/absolute/path",
      "workspace": "oe-orchestrator",
      "detected_at": "2026-03-13T10:00:00Z",
      "metadata": {
        "python_version": "3.12",
        "dependencies": ["fastapi", "pydantic"],
        "test_framework": "pytest"
      }
    }
  ]
}
```

### Workspace Selection
Recommend appropriate workspace based on:
- Project type
- Task requirements
- Available skills
- Resource constraints

## Usage

### Discover Projects
```python
# Scan directory for projects
projects = discover_projects("/path/to/scan")

# Returns list of Project objects
[
  Project(
    id="proj-001",
    name="openclaw-enhance",
    type="python",
    path="/home/user/workspace/openclaw-enhance",
    workspace="oe-orchestrator"
  )
]
```

### Register Project
```python
# Manually register a project
register_project(
  path="/path/to/project",
  name="My Project",
  workspace="oe-orchestrator"
)
```

### Get Project Info
```python
# Retrieve project details
project = get_project("proj-001")
# Returns Project object with full metadata
```

### Select Workspace
```python
# Recommend workspace for task
workspace = select_workspace(
  project_id="proj-001",
  task_type="refactoring",
  complexity="high"
)
# Returns: "oe-orchestrator" or other appropriate workspace
```

## Project Types

| Indicator File | Project Type | Default Workspace |
|----------------|--------------|-------------------|
| `pyproject.toml` | python | oe-orchestrator |
| `setup.py` | python | oe-orchestrator |
| `package.json` | nodejs | oe-orchestrator |
| `Cargo.toml` | rust | oe-orchestrator |
| `go.mod` | golang | oe-orchestrator |
| `pom.xml` | java-maven | oe-orchestrator |
| `build.gradle` | java-gradle | oe-orchestrator |
| `Gemfile` | ruby | oe-orchestrator |
| `composer.json` | php | oe-orchestrator |
| `Makefile` | c/cpp | oe-orchestrator |
| `CMakeLists.txt` | c/cpp | oe-orchestrator |
| `requirements.txt` | python-legacy | oe-orchestrator |

## Registry Storage

The project registry is stored at:
```
~/.openclaw/openclaw-enhance/project-registry.json
```

## Integration

### With oe-worker-dispatch
Project metadata informs agent selection and configuration

### With oe-git-context
Git history is scoped to the selected project

### With planning-with-files
Project type determines planning templates

## Best Practices

1. **Scan before starting work** in unfamiliar directories
2. **Register projects explicitly** when auto-detection fails
3. **Update registry** when project structure changes
4. **Validate paths** before accessing projects
5. **Cache results** for frequently accessed projects

## Example Workflow

```
User: "Work on the auth module"
  ↓
Orchestrator: "Let me discover available projects"
  ↓
[Scan current directory]
  ↓
Found: openclaw-enhance (Python)
  ↓
"Working on openclaw-enhance. What would you like to do with the auth module?"
```


---

## oe-worker-dispatch

---
name: oe-worker-dispatch
version: 1.0.0
description: Subagent task dispatch and result synthesis for the Orchestrator
author: openclaw-enhance
tags: [orchestrator, dispatch, subagent, workers, parallel]
---

# oe-worker-dispatch

Skill for dispatching tasks to specialized subagents and synthesizing their results.

## Purpose

The Orchestrator delegates work to specialized subagents via the native `announce` mechanism. This skill provides:
- Task-to-agent matching
- Dispatch configuration
- Result collection
- Output synthesis
- Error handling

## When to Use

Use this skill when:
- Task complexity requires multiple agents
- Parallel execution can speed up work
- Specialized expertise is needed (search, scripting, etc.)
- Monitoring long-running tasks
- Aggregating results from multiple sources

## Discovery-First Worker Routing

The Orchestrator discovers and selects workers dynamically from their `AGENTS.md` frontmatter rather than using hardcoded descriptions. This enables the system to adapt as workers evolve without modifying dispatch logic.

### Worker Discovery Workflow

To discover worker manifests and route tasks dynamically:

```
Enumerate → Parse → Catalog → Filter → Rank → Dispatch
```

#### 1. Enumerate Worker Manifests

First, discover worker manifests by scanning available workspaces:

Discover all available workers by scanning `workspaces/*/AGENTS.md`:

```python
# Pseudocode for discovery
workspaces = list_workspaces()  # ['oe-searcher', 'oe-syshelper', ...]
manifests = [parse_agent_manifest(read(f"workspaces/{w}/AGENTS.md")) 
             for w in workspaces]
```

**Note**: `oe-orchestrator` is excluded from worker selection (it's the dispatcher, not a worker).

#### 2. Parse Frontmatter

Each worker's `AGENTS.md` contains YAML frontmatter with routing metadata:

```yaml
---
schema_version: 1
agent_id: oe-searcher
workspace: oe-searcher
routing:
  description: "Research-focused agent for web search and documentation"
  capabilities: [research, documentation]
  accepts: [research_tasks, documentation_queries]
  rejects: [file_modifications, code_implementation]
  mutation_mode: read_only
  can_spawn: false
  requires_tests: false
  cost_tier: cheap
  model_tier: cheap
  tool_classes: [web_search, web_fetch, code_search]
---
```

#### 3. Build Candidate Catalog

Parse all manifests into a catalog of eligible workers:

```python
catalog = [manifest for manifest in manifests if manifest.is_valid]
```

Invalid manifests (missing required fields, unknown enum values) are excluded from selection.

#### 4. Hard-Filter by Constraints

Apply hard constraints based on task requirements:

| Task Requirement | Filter Criteria |
|------------------|-----------------|
| Need file write | `mutation_mode: repo_write` only |
| Read-only safe | `mutation_mode: read_only` or `none` |
| Session access | `session_access: read_only` or `runtime_only` |
| Can spawn subagents | `can_spawn: true` |
| Requires tests | `requires_tests: true` |
| Network research | `network_access: web_research` |

**Example**: For a "find all TODO comments" task:
- Must support: `read_only` or `none` mutation
- Prefers: `code_search` tool class
- Excludes: workers with `mutation_mode: repo_write`

#### 5. Rank by Least-Privilege Rules

Apply least-privilege ranking to select the narrowest capable worker:

For remaining candidates, rank by narrowest scope first:

**Priority Order:**
1. **Narrowest mutation scope**: `read_only` > `sandbox_write` > `repo_write`
2. **Lowest cost**: `cheap` > `standard` > `premium`
3. **Fewest capabilities**: Single-purpose workers > general workers
4. **Tool class match**: Exact match > partial match

**Example Rankings:**
- "Find TODOs in codebase": `oe-syshelper` (read-only, code search) > `oe-script_coder` (repo write)
- "Research async patterns": `oe-searcher` (web research) > `oe-script_coder` (can do it but overkill)
- "Fix bug and add tests": `oe-script_coder` (repo write, requires_tests)

#### 6. Special-Case Branches

Some workers have dedicated routing paths outside normal scoring:

##### Tool Recovery Branch
**Trigger**: Tool-usage failure (`tool_not_found`, `invalid_parameters`, `permission_denied`, `tool_execution_error`)

**Flow**:
1. Detect failure in worker results
2. Check recovery eligibility (max 1 retry per failed step)
3. Dispatch `oe-tool-recovery` with failure context
4. Receive `RecoveredMethod` with corrected invocation
5. Retry original worker OR escalate if recovery fails

**Note**: `oe-tool-recovery` is never selected through normal ranking—it's only dispatched for recovery scenarios.

##### Watchdog Branch
**Trigger**: Timeout monitoring, session health checks

**Flow**:
1. Long-running task detected
2. Spawn `oe-watchdog` to monitor progress
3. Watchdog alerts on timeout or issues
4. Orchestrator handles timeout response

**Note**: `oe-watchdog` is typically spawned alongside main workers, not as primary task executor.

### Dispatch Decision Examples

**Example 1: Research task**
```
Task: "Find best practices for Python logging"
Enumerate: All 5 workers
Filter: None require write access
Rank: oe-searcher (research, cheap) > oe-syshelper (can search but less focused)
Dispatch: oe-searcher
```

**Example 2: Code modification**
```
Task: "Fix the auth bug and add tests"
Enumerate: All 5 workers
Filter: Requires mutation_mode: repo_write, requires_tests: true
Rank: oe-script_coder (only match)
Dispatch: oe-script_coder
```

**Example 3: Exploration task**
```
Task: "What files import the database module?"
Enumerate: All 5 workers
Filter: Read-only sufficient
Rank: oe-syshelper (introspection, read-only, cheap) > oe-searcher (could grep but not its focus)
Dispatch: oe-syshelper
```

## Dispatch Patterns

### Iterative Round-Based Dispatch (v2)

For complex tasks requiring multiple refinement rounds, use the bounded iterative pattern:

```
Round N: Plan → Dispatch → Yield → Collect → Evaluate
                                              ↓
                    Complete ←── No more work
                    Blocked  ←── Needs decision
                    Next Round ←── Refine and continue
```

**Round Structure:**

1. **Plan Round**: Define specific objectives for this round
2. **Dispatch Workers**: Spawn agents via `sessions_spawn` with unique dispatch identities
3. **Yield for Results**: Call `sessions_yield` to cleanly end turn
4. **Collect via Announce**: Receive results on next turn via auto-announce
5. **Evaluate Progress**: Classify results, update state, decide next action

**Important**: After calling `sessions_yield`, wait for auto-announced results. Do not poll or query session state while waiting.

#### Dispatch Identity & Deduplication

Each dispatch within a round must have:
- **Unique dispatch_id**: `round-{N}-{worker}-{objective}` format
- **Dedupe key**: Hash of (task_context, worker_type, objective)
- **Expected result schema**: What constitutes completion for this dispatch

**Duplicate Dispatch Guard:**
- Same dedupe key cannot be resent without new evidence
- If result is late/missing, check `pending_dispatches` before re-dispatching
- Document reason for any re-dispatch in round state

#### Failure Classification

Worker results are classified into four categories:

| Category | Signal | Action |
|----------|--------|--------|
| **Retriable** | Transient failure, incomplete context | Limit 1 retry with clarified instructions |
| **Tool-Usage Failure** | tool_not_found, invalid_parameters, permission_denied, tool_execution_error | Route to oe-tool-recovery (max 1 attempt per failed step) |
| **Reroutable** | Wrong worker chosen, task too large | Change worker or decompose into subtasks |
| **Escalated** | Design conflict, needs main decision | Yield `blocked` checkpoint to main |

#### Recovery Dispatch

When a **Tool-Usage Failure** (tool-usage failure) is detected, the Orchestrator dispatches to `oe-tool-recovery` to generate a `RecoveredMethod` (recovered_method).

**Context Passed to Recovery Worker:**
- `failed_step`: Identity of the failed step
- `tool_name`: Name of the tool that failed
- `failure_reason`: Error message or signal from the worker
- `exact_invocation`: The failed tool call string

**Handoff & Re-entry:**
1. **Dispatch**: Orchestrator spawns `oe-tool-recovery` with the failure context via `sessions_spawn`.
2. **Yield**: Orchestrator calls `sessions_yield` to await the recovery suggestion.
3. **Evaluate**: Orchestrator receives `RecoveredMethod` and evaluates the `retry_owner` decision.
4. **Retry**: If `retry_owner` is `self`, the Orchestrator re-dispatches the original worker with the `exact_invocation` from the recovery result.
5. **Reroute**: If `retry_owner` is `script_coder`, `searcher`, or `syshelper`, the Orchestrator dispatches to that agent type instead.
6. **Orchestrator Owned**: If `retry_owner` is `orchestrator`, the Orchestrator handles the retry directly.
7. **Escalate**: If recovery fails or the assisted retry fails, the Orchestrator terminates as `escalated`.

**Constraints:**
- **Max 1 recovery-assisted retry** per failed step.
- **No worker-to-worker handoff**: Recovery worker never communicates with the failed worker (explicitly forbid direct handoff).
- **No business task execution**: Recovery worker only diagnoses and suggests; it never performs the original task.
- **Leaf-node only**: Recovery worker cannot spawn other agents.

#### Recovery Flow Examples

**Scenario 1: Tool-not-found**
- **Signal**: Worker reports `tool 'websearch' not found`.
- **Recovery**: `oe-tool-recovery` identifies that `websearch_web_search_exa` should be used instead.
- **Action**: Orchestrator re-dispatches worker with corrected tool call.

**Scenario 2: Invalid-parameter**
- **Signal**: `Edit` tool fails with `oldString not found`.
- **Recovery**: `oe-tool-recovery` reads the file and provides the exact `oldString` with correct indentation.
- **Action**: Orchestrator re-dispatches worker with corrected parameters.

**Scenario 3: Recovery failure escalation**
- **Signal**: `oe-tool-recovery` cannot find a solution or the assisted retry fails.
- **Action**: Orchestrator terminates orchestration as `escalated`.

#### Checkpoint Visibility to Main

Orchestrator reports to main only at milestones:

**Always report:**
- `started`: Orchestration begins
- `blocked`: External decision required
- `terminal`: Complete, exhausted, or escalated

**Conditionally report:**
- `meaningful_progress`: After round N if significant new findings/artifacts

**Never report:**
- Individual worker success within a round
- Routine round boundaries
- Internal re-dispatch decisions

### Sequential Dispatch (Legacy Pattern)
```
Task A → Agent 1 → Result 1
              ↓
Task B → Agent 2 → Result 2
              ↓
        Synthesis
```

Use when:
- Tasks have dependencies
- Results of one inform the next
- Order matters

### Parallel Dispatch
```
Task A → Agent 1 → Result 1 ─┐
                             ├──→ Synthesis
Task B → Agent 2 → Result 2 ─┘
```

Use when:
- Tasks are independent
- Speed is important
- No dependencies between tasks

### Hierarchical Dispatch (v1 NOT Supported)

**⚠️ Worker-Level Orchestration Disabled in v1**

Workers remain **single-round executors** and cannot spawn or orchestrate other workers. All multi-level coordination must be handled by the orchestrator within the bounded loop.

**v1 Constraint**: Only the orchestrator may dispatch workers. Workers complete their task and return results directly.

## Native Subagent Dispatch

All dispatch is done through OpenClaw's native `sessions_spawn` tool. Do NOT create wrapper functions.

### Single Task Dispatch

Use `sessions_spawn` to dispatch to a specific agent:

```json
{
  "task": "Research FastAPI dependency injection patterns",
  "agentId": "oe-searcher",
  "label": "auth-research"
}
```

### Parallel Task Dispatch

Spawn multiple agents in parallel using separate `sessions_spawn` calls:

```json
// Spawn 1: Research topic A
{
  "task": "Research topic A",
  "agentId": "oe-searcher",
  "label": "research-a"
}

// Spawn 2: Research topic B
{
  "task": "Research topic B",
  "agentId": "oe-searcher",
  "label": "research-b"
}

// Spawn 3: Find related files
{
  "task": "Find related files",
  "agentId": "oe-syshelper",
  "label": "file-discovery"
}
```

### Dispatch with Monitoring

For long-running tasks, spawn a watchdog alongside the worker:

```json
// Main worker
{
  "task": "Long-running code generation task",
  "agentId": "oe-script_coder",
  "label": "code-gen",
  "runTimeoutSeconds": 1800
}

// Watchdog (optional, for monitoring)
{
  "task": "Monitor code-gen task for timeout",
  "agentId": "oe-watchdog",
  "label": "code-gen-monitor"
}
```

## Result Synthesis

### Synthesis Strategies

1. **Concatenation**: Simple append for independent results
2. **Merge**: Combine overlapping information
3. **Summarize**: Extract key points from verbose outputs
4. **Prioritize**: Rank results by relevance/confidence
5. **Cross-reference**: Validate across multiple agents

### Synthesis Template

When synthesizing results from multiple subagents:

```markdown
## Summary
[High-level overview]

## Detailed Results

### From [Agent Type] - [Task Name]
[Agent output from announce]

### From [Agent Type] - [Task Name]
[Agent output from announce]

## Synthesis
[Combined insights, conflicts resolved, conclusions drawn]

## Artifacts
- [File paths created/modified]

## Next Steps
1. [Action item 1]
2. [Action item 2]
```

## Error Handling

### Agent Failure

When a subagent fails (announces failure or times out):

1. Check announce status for error details
2. Retry with adjusted parameters if transient
3. Escalate to main if unrecoverable

```markdown
## Agent Failure Response

**Failed Agent**: [agent type]
**Error**: [from announce]
**Action**: [retry/escalate/alternative]
```

### Partial Results

When some agents succeed and others fail:
1. Capture successful results
2. Log failures with context
3. Synthesize available results
4. Report gaps to user

### Recovery Strategies
- **Retry**: Transient failures (network, etc.)
- **Fallback**: Alternative agent types
- **Decomposition**: Split failed task into smaller pieces
- **Escalation**: Hand to main session if unrecoverable

## Configuration

### Agent Timeouts
| Agent Type | Default Timeout | Max Timeout |
|------------|----------------|-------------|
| searcher | 5 min | 15 min |
| syshelper | 3 min | 10 min |
| script_coder | 10 min | 30 min |
| watchdog | 60 min | unlimited |

### Concurrency Limits
- Default: 3 concurrent agents
- Max: 5 concurrent agents
- Override via `maxConcurrent` in spawn calls

## Best Practices

1. **Match agent to task**: Don't use script_coder for simple searches
2. **Set appropriate timeouts**: Balance speed vs. completion
3. **Provide full context**: Agents need background to succeed
4. **Use parallel dispatch**: For independent tasks
5. **Synthesize don't concatenate**: Add value in synthesis step
6. **Handle failures gracefully**: Partial results are better than none
7. **Monitor long tasks**: Use watchdog for tasks > 10 minutes
8. **Never wrap sessions_spawn**: Use native tool directly

## Integration

### With oe-project-registry
Project metadata informs agent selection and context

### With oe-eta-estimator
ETA estimates determine timeout configuration

### With planning-with-files
Task plans guide dispatch decisions

## Example: Complete Workflow

**Scenario**: Refactor auth module

1. **Assess task**
   - Estimated toolcalls: 8
   - Requires parallel: Yes
   - Action: Plan and dispatch

2. **Plan**
   - Create task plan using planning-with-files
   - Identify subtasks: research, file discovery, implementation

3. **Dispatch parallel research** (native sessions_spawn)
   - Spawn searcher: "Research auth patterns"
   - Spawn syshelper: "Find auth files"
   - Spawn searcher: "Look up test examples"
   - Wait for all to announce results

4. **Dispatch coding** (sequential, depends on research)
   - Spawn script_coder: "Refactor auth based on research"
   - Include research results in task context

5. **Synthesize**
   - Collect all announce results
   - Apply synthesis template
   - Return final result to main


---
```

### Command 2: ✓ PASS

```bash
cd /Users/tsgsz/workspace/openclaw-enhance && pytest tests/integration/test_orchestrator_dispatch_contract.py::TestBoundedLoopContract -q --tb=no
```

- Exit Code: 0
- Duration: 0.45s

**stdout:**
```
.............                                                                                                                                                                                                                                         [100%]
13 passed in 0.16s
```
