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
