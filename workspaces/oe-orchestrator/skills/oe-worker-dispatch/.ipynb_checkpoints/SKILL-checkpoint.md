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

## Agent Types

### searcher
**Purpose**: Research, documentation lookup, web search

**Characteristics**:
- Model: Cheap/fast (no code generation needed)
- Tools: websearch, webfetch, Read (for docs)
- Use for: Library research, API documentation, best practices

**Example Tasks**:
- "Find FastAPI authentication best practices"
- "Look up Pydantic validator examples"
- "Research Python async patterns"

### syshelper
**Purpose**: System introspection and file operations

**Characteristics**:
- Model: Cheap/fast
- Tools: Glob, Grep, Read, Bash (read-only), session_*
- Use for: Finding files, searching code, exploring structure

**Example Tasks**:
- "Find all test files in the project"
- "Search for 'TODO' comments"
- "List all Python files with 'auth' in the name"

### script_coder
**Purpose**: Script development and testing

**Characteristics**:
- Model: Codex-class (code generation)
- Tools: Read, Write, Bash, Glob
- Use for: Writing scripts, small utilities, automation

**Example Tasks**:
- "Create a script to validate project structure"
- "Write a Python utility for git statistics"
- "Generate test data script"

### watchdog
**Purpose**: Session monitoring and diagnostics

**Characteristics**:
- Model: Any (judgment tasks)
- Tools: session_list, session_read, session_info, call_omo_agent
- Use for: Monitoring timeouts, checking session health, recovery

**Example Tasks**:
- "Monitor session sess_abc123 for completion"
- "Check if any sessions have timed out"
- "Alert on hung sessions"

## Dispatch Patterns

### Sequential Dispatch
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

### Hierarchical Dispatch
```
Orchestrator
    ↓
Agent A (coordinator)
    ├──→ Agent A1
    ├──→ Agent A2
    └──→ Agent A3
```

Use when:
- Task needs coordination
- Sub-tasks have sub-tasks
- Complex decomposition required

## Usage

### Dispatch Single Task
```python
dispatch_task(
    agent_type="searcher",
    task="Research FastAPI dependency injection",
    context={
        "project_type": "python",
        "priority": "high"
    },
    timeout_minutes=10
)
```

### Dispatch Multiple Tasks (Parallel)
```python
dispatch_parallel(
    tasks=[
        {"agent": "searcher", "task": "Research topic A"},
        {"agent": "searcher", "task": "Research topic B"},
        {"agent": "syshelper", "task": "Find related files"},
    ],
    max_concurrent=3
)
```

### Dispatch with Monitoring
```python
dispatch_with_watchdog(
    agent_type="script_coder",
    task="Long-running code generation",
    watchdog_config={
        "check_interval_seconds": 60,
        "timeout_alert_threshold": 30
    }
)
```

## Result Synthesis

### Synthesis Strategies

1. **Concatenation**: Simple append for independent results
2. **Merge**: Combine overlapping information
3. **Summarize**: Extract key points from verbose outputs
4. **Prioritize**: Rank results by relevance/confidence
5. **Cross-reference**: Validate across multiple agents

### Synthesis Template
```markdown
## Summary
[High-level overview]

## Detailed Results

### From [Agent Type] - [Task Name]
[Agent output]

### From [Agent Type] - [Task Name]
[Agent output]

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
```python
try:
    result = dispatch_task(...)
except AgentTimeout:
    # Retry with longer timeout
    result = dispatch_task(..., timeout_minutes=extended)
except AgentError as e:
    # Log and escalate
    log_error(e)
    escalate_to_main(e)
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
- Override via `max_concurrent` parameter

## Best Practices

1. **Match agent to task**: Don't use script_coder for simple searches
2. **Set appropriate timeouts**: Balance speed vs. completion
3. **Provide full context**: Agents need background to succeed
4. **Use parallel dispatch**: For independent tasks
5. **Synthesize don't concatenate**: Add value in synthesis step
6. **Handle failures gracefully**: Partial results are better than none
7. **Monitor long tasks**: Use watchdog for tasks > 10 minutes

## Integration

### With oe-project-registry
Project metadata informs agent selection and context

### With oe-eta-estimator
ETA estimates determine timeout configuration

### With planning-with-files
Task plans guide dispatch decisions

## Example: Complete Workflow

```python
# 1. Assess task
assessment = TaskAssessment(
    description="Refactor auth module",
    estimated_toolcalls=8,
    requires_parallel=True,
    complexity_score=4
)

# 2. Plan
plan = create_task_plan(assessment)

# 3. Dispatch parallel research
research_results = dispatch_parallel([
    {"agent": "searcher", "task": "Research auth patterns"},
    {"agent": "syshelper", "task": "Find auth files"},
    {"agent": "searcher", "task": "Look up test examples"},
])

# 4. Dispatch coding (sequential, depends on research)
code_result = dispatch_task(
    agent_type="script_coder",
    task="Refactor auth based on research",
    context=research_results
)

# 5. Synthesize
final_result = synthesize_results([
    research_results,
    code_result
])
```
