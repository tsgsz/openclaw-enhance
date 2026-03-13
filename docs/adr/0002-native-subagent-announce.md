# ADR 0002: Native Subagent Announce Chain

## Status

Accepted

## Context

The orchestrator needs to communicate with worker agents (searcher, syshelper, script_coder, watchdog). We need a communication protocol that:

1. Works within OpenClaw's architecture
2. Doesn't require custom infrastructure
3. Provides lifecycle management (spawn, monitor, cleanup)
4. Supports timeout and error handling
5. Doesn't introduce external dependencies

Several communication patterns were considered: custom HTTP API, message queue, shared file-based RPC, and OpenClaw's native subagent mechanism.

**Skill-First Boundary**: Skills (markdown contracts) define *when* and *why* to spawn subagents, but never wrap the native primitive. The `sessions_spawn` tool is the ONLY execution mechanism—skills guide decisions, native primitives execute.

## Decision

We will use **OpenClaw's native subagent announce chain** as the ONLY communication protocol between orchestrator and workers.

### Mechanism

OpenClaw provides a `subagent.announce()` mechanism:

```typescript
// Orchestrator dispatches work
const result = await subagent.announce({
  agent: "oe-searcher",
  task: "Research Python async frameworks",
  context: {
    project: "my-project",
    parent_session: current_session_id,
    estimated_duration: 10
  }
});

// Worker processes and returns structured result
return {
  summary: "Found 3 major frameworks...",
  artifacts: ["/path/to/research.md"],
  recommendations: ["Use asyncio for..."]
};
```

### Architecture

```
Orchestrator Session
        │
        │ subagent.announce({ agent: "oe-searcher", ... })
        ▼
Worker Session (oe-searcher)
        │
        │ Processes task
        ▼
Returns result to Orchestrator
        │
        ▼
Orchestrator synthesizes with other worker results
```

### Protocol Contract

**Input to worker**:
```typescript
interface WorkerTask {
  task: string;                    // Task description
  context: {
    project?: string;             // Project context
    parent_session: string;       // Originating session ID
    artifacts?: string[];         // Relevant file paths
  };
}
```

**Output from worker**:
```typescript
interface WorkerResult {
  summary: string;                // Brief result summary
  details?: string;               // Detailed output
  artifacts: string[];            // Created/modified files
  recommendations?: string[];     // Suggested next steps
  errors?: string[];              // Any errors encountered
}
```

### Timeout Handling

OpenClaw's native mechanism provides:
- Built-in timeout configuration
- Automatic cleanup on timeout
- Error propagation to parent

We enhance this with:
- Pre-flight ETA estimation
- Watchdog monitoring for long tasks
- State synchronization via `oe-timeout-state-sync`

## Consequences

### Positive

- **Native integration**: Uses OpenClaw's built-in capabilities
- **No infrastructure**: No HTTP servers, message queues, or databases needed
- **Lifecycle management**: OpenClaw handles spawn, monitor, and cleanup
- **Error handling**: Built-in timeout and error propagation
- **Security**: Runs within OpenClaw's sandbox model

### Negative

- **Limited visibility**: Harder to debug than HTTP requests with logs
- **Single point**: If OpenClaw's subagent system has issues, we have no alternative
- **Coupling**: Tightly coupled to OpenClaw's API and behavior

### Neutral

- **Performance**: Similar to HTTP for local IPC
- **Scalability**: Limited by OpenClaw's concurrency model (acceptable for our use case)

## Alternatives Considered

### 1. Custom HTTP API

**Rejected**: Requires running HTTP servers, adds complexity, needs authentication, not aligned with OpenClaw's design.

### 2. Message Queue (Redis/RabbitMQ)

**Rejected**: External dependency, operational overhead, overkill for local agent communication.

### 3. File-based RPC

**Rejected**: Race conditions, polling overhead, complex locking, fragile.

### 4. Direct function calls

**Rejected**: Doesn't support separate worker processes/sessions; no isolation between agents.

## Design Principles Upheld

1. **Non-invasive**: Uses OpenClaw's official API
2. **No custom infrastructure**: Leverages existing capabilities
3. **Symmetric lifecycle**: Workers are proper OpenClaw subagents with full lifecycle

## Implementation Notes

### Worker Dispatch Skill

The `oe-worker-dispatch` skill in the orchestrator workspace encapsulates announce logic:

```markdown
## Dispatch Rules

1. Research tasks → oe-searcher
2. System introspection → oe-syshelper
3. Script development → oe-script_coder
4. Monitoring/diagnostics → oe-watchdog

## Context Passing

Always include:
- project: Current project context
- parent_session: Originating session ID
- artifacts: Relevant file paths
```

### Error Handling

Workers must return structured errors:

```typescript
{
  summary: "Task failed",
  errors: ["File not found: /path/to/file"],
  artifacts: [],
  recommendations: ["Check file path and retry"]
}
```

### Parallel Dispatch

Orchestrator can dispatch multiple workers in parallel:

```typescript
const [researchResult, systemResult] = await Promise.all([
  subagent.announce({ agent: "oe-searcher", task: researchTask }),
  subagent.announce({ agent: "oe-syshelper", task: systemTask })
]);
```

## Related Decisions

- [ADR 0001: Managed Namespace](0001-managed-namespace.md)
- [ADR 0003: Watchdog Authority](0003-watchdog-authority.md)

## References

- `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`
- `src/openclaw_enhance/skills_catalog.py`
- OpenClaw docs: `docs/tools/subagents.md`

## Date

2026-03-13
