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

## Bounded Orchestration Loop

The Orchestrator uses a bounded multi-round loop for complex work:

```
Assess -> PlanRound -> DispatchRound -> YieldForResults -> CollectResults -> EvaluateProgress
                                                                 ↓
                                         Complete  <- No more work needed
                                         Blocked   <- Needs main-session decision
                                         Re-dispatch <- Another round adds new evidence
```

### Round Outcomes

`EvaluateProgress` must classify each round into one of these outcomes:

- **Complete**: Enough evidence gathered; synthesize and return to main.
- **Blocked**: External decision required; surface a checkpoint.
- **Re-dispatch**: Another round is justified by new evidence or narrowed uncertainty.
- **Recovery Dispatch**: Tool-usage failure requires `oe-tool-recovery`.
- **Recovery-Assisted Retry**: Retry the original worker with a `RecoveredMethod`.
- **Escalated**: Recovery failed or retry failed; stop the orchestration.

### Orchestrator-Owned State

The loop state belongs to the Orchestrator, not to `AGENTS.md` body text:

| Field | Purpose |
|-------|---------|
| `task_id` | Unique identifier for this orchestration |
| `round_index` | Current round number |
| `max_rounds` | default: 3, hard cap: 5 |
| `pending_dispatches` | Workers currently outstanding |
| `received_results` | Results collected from completed workers |
| `blocked_items` | External decisions required from main |
| `dedupe_keys` | Prevent duplicate dispatches without new evidence |
| `recovery_attempts` | Per-step retry counter (max 1) |
| `recovered_methods` | Stored `RecoveredMethod` objects by failed step |
| `recovery_in_progress` | Prevent nested recovery dispatch |
| `termination_state` | `active`, `completed`, `blocked`, `exhausted`, `escalated` |
| `termination_reason` | Human-readable reason for termination |

### Loop Controls

- **Max rounds**: Default 3, hard cap 5.
- **Max dispatches per round**: Default 3, hard cap 5 concurrent workers.
- **Incrementality rule**: Only open a new round if it adds new evidence or reduces uncertainty.
- **Duplicate dispatch guard**: Same worker + objective + context cannot be resent without new evidence.
- **Blocker escalation**: Two consecutive no-progress evaluations should terminate as `blocked`.
- **Recovery Cap**: Max ONE recovery-assisted retry per failed step.
- **No Recovery Loops**: Recovery worker failure or retry failure escalates immediately.
- **No Worker Handoff**: Recovery never creates worker-to-worker handoff; the Orchestrator remains the sole dispatcher.

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

### Native Primitive Usage

- **`sessions_spawn`**: The only dispatch path for worker sessions.
- **`sessions_yield`**: The round-boundary wait primitive used by the Orchestrator.
- **`announce`**: Worker result delivery path back into the orchestration loop.

Workers remain single-round executors. They do not use `sessions_yield` themselves.

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

## Dispatch Context Enrichment

Before calling `sessions_spawn`, enrich the task prompt with relevant context from existing skills. This ensures workers have the information needed to succeed.

### Context Sources

| Context | Source Skill | What to Include |
|---------|-------------|------------------|
| Main session history | `oe-memory-sync` | Parent conversation summary, user intent |
| Git context | `oe-git-context` | Recent commits, changed files, related history |
| Project info | `oe-project-registry` | Project type, path, branch status, coding conventions |

### Enrichment Flow

```
Before sessions_spawn:
    │
    ▼
1. Load project context ──► oe-project-registry
    │                          (project path, type, branch, status)
    ▼
2. Load git context ─────► oe-git-context
    │                          (recent commits, changed files)
    ▼
3. Load memory context ───► oe-memory-sync
    │                          (parent session summary)
    ▼
4. Synthesize enriched task
    │
    ▼
sessions_spawn(task=<enriched_task>, ...)
```

### Enriched Task Format

```markdown
## Task
{original_task_description}

## Project Context
- Path: {project_path}
- Type: {project_type}
- Branch: {branch_name} ({clean/dirty})

## Git Context
{recent_commits_formatted}

## Main Session Context
{parent_session_summary}

## Guidance
- Work in: {project_path}
- Follow project conventions
```

### Implementation Pattern

```python
async def dispatch_with_context(worker_type, task, context_hints=None):
    """Dispatch task with enriched context from skills."""
    
    context_hints = context_hints or {}
    project_path = context_hints.get("project_path", detect_project())
    
    # 1. Get project context
    project_info = get_project_info(project_path)
    project_ctx = f"""\
- Path: {project_info.path}
- Type: {project_info.type}
- Branch: {project_info.branch} ({project_info.status})
"""
    
    # 2. Get git context (selective - only relevant files)
    related_files = context_hints.get("related_files", infer_related_files(task))
    git_ctx = gather_git_context(project_path, files=related_files, depth=5)
    
    # 3. Get memory context
    memory_ctx = await sync_main_context()
    parent_summary = memory_ctx.get("parent_history_summary", "N/A")
    
    # 4. Compose enriched task
    enriched_task = f"""\
## Task
{task}

## Project Context
{project_ctx}

## Git Context
{git_ctx.format_compact()}

## Main Session Context
{parent_summary}

## Guidance
- Work in: {project_info.path}
- Follow project conventions for {project_info.type}
"""
    
    # 5. Dispatch with enriched task
    await sessions_spawn(
        agent=worker_type,
        task=enriched_task,
        label=context_hints.get("label"),
    )
```

### Context Selection Guidelines

| Worker Type | Priority Context |
|-------------|------------------|
| `oe-script_coder` | Git changes, project type, coding conventions |
| `oe-searcher` | Main session intent, topic context |
| `oe-syshelper` | Project structure, file locations |
| `oe-watchdog` | Session state, timeout expectations |

### What NOT to Include

- Full blame history (too verbose)
- Unrelated project memories
- Conflicting information from multiple sources
- Credentials or sensitive data

### Integration with Skills

- **`oe-memory-sync`**: Call `sync_main_context()` to get parent session summary
- **`oe-git-context`**: Call `gather_git_context()` with related files
- **`oe-project-registry`**: Call `get_project_info()` or `detect_project()`

## Best Practices

1. **Match agent to task**: Don't use script_coder for simple searches
2. **Set appropriate timeouts**: Balance speed vs. completion
3. **Provide full context**: Agents need background to succeed
4. **Use parallel dispatch**: For independent tasks
5. **Synthesize don't concatenate**: Add value in synthesis step
6. **Handle failures gracefully**: Partial results are better than none
7. **Monitor long tasks**: Use watchdog for tasks > 10 minutes
8. **Never wrap sessions_spawn**: Use native tool directly
9. **Enrich dispatch context**: Always inject project, git, and memory context

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
