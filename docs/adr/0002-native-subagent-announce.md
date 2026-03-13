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

**Turn-Yield Synchronization**: The `sessions_yield` primitive is used EXCLUSIVELY by the orchestrator to mark round boundaries in its bounded orchestration loop. It is a synchronization primitive, not a result transport mechanism. Workers remain single-round executors and never use yield.

## Decision

We will use **OpenClaw's native subagent announce chain** as the ONLY communication protocol between orchestrator and workers.

### Mechanism

OpenClaw provides native primitives for worker execution and orchestrator turn management:

- **`sessions_spawn`**: Creates worker subagent sessions
- **`announce`**: Returns worker results to parent
- **`sessions_yield`**: Ends orchestrator turn to await results

#### Worker Execution

The orchestrator dispatches work to workers via native `sessions_spawn`. Workers complete their task and return results through the native `announce` mechanism. No custom transport or wrapper code is used.

**Input fields passed to workers**:

| Field | Type | Description |
|-------|------|-------------|
| `task` | string | Task description |
| `context.project` | string | Project context |
| `context.parent_session` | string | Originating session ID |
| `context.artifacts` | string[] | Relevant file paths |

**Output fields returned by workers**:

| Field | Type | Description |
|-------|------|-------------|
| `summary` | string | Brief result summary |
| `details` | string | Detailed output |
| `artifacts` | string[] | Created/modified files |
| `recommendations` | string[] | Suggested next steps |
| `errors` | string[] | Any errors encountered |

#### Orchestrator Round Boundary

After dispatching one or more workers, the orchestrator calls `sessions_yield` to end its current turn. OpenClaw collects worker results via the native announce chain and re-activates the orchestrator in the next turn with auto-announced results. Workers do not use `sessions_yield`; they remain single-round executors.

### Architecture: Bounded Orchestration Loop

The orchestrator operates in a bounded loop (max 3-5 rounds) rather than a linear flow:

```
Dispatch (sessions_spawn) ──► Yield (sessions_yield) ──┐
      ▲                                                │
      │                                                ▼
Evaluate Progress ◄── Collect Results (auto-announce) ──┘
      │
      └──► Terminal (Complete/Blocked/Exhausted)
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
4. **Native Primitives**: `sessions_spawn` remains the sole worker execution path; `sessions_yield` provides native turn synchronization.

## Implementation Notes

### Worker Dispatch Skill

The `oe-worker-dispatch` skill in the orchestrator workspace encapsulates announce logic:

```markdown
## Dispatch Rules

| Task Type | Worker |
|-----------|--------|
| Research | oe-searcher |
| System introspection | oe-syshelper |
| Script development | oe-script_coder |
| Monitoring/diagnostics | oe-watchdog |

## Context Passing

All dispatches must include:
- `project`: Current project context
- `parent_session`: Originating session ID
- `artifacts`: Relevant file paths

### Error Handling

Workers must return structured error information including: failure summary, error list, affected artifacts, and recommended recovery actions. See skill documentation for complete error contract.

### Parallel Dispatch

Orchestrator may dispatch multiple workers within a single round. Each dispatch creates an independent worker session. Results are collected via auto-announce after `sessions_yield`. Parallel dispatch is subject to the same deduplication guards and bounded round limits as sequential dispatch.

## Related Decisions

- [ADR 0001: Managed Namespace](0001-managed-namespace.md)
- [ADR 0003: Watchdog Authority](0003-watchdog-authority.md)

## References

- `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`
- `src/openclaw_enhance/skills_catalog.py`
- OpenClaw docs: `docs/tools/subagents.md`

## Date

2026-03-13
