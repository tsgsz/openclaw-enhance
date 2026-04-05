# Architecture

This document describes the architecture of `openclaw-enhance`, a non-invasive control-plane package for OpenClaw.

> **Project State**: See [`opencode-iteration-handbook.md`](./opencode-iteration-handbook.md) for current design status, permanent progress, and required reading paths.

## Overview

`openclaw-enhance` augments OpenClaw's multitasking capabilities, long-running task handling, and operational visibility without modifying OpenClaw core source code. It uses OpenClaw's native extension points: skills, hooks, extensions, and agent workspaces.

## Design Principles

1. **Non-invasive**: No edits to OpenClaw source code or bundled runtime files (install-time workspace configuration is allowed)
2. **Symmetric lifecycle**: One-click install and uninstall with rollback support
3. **Namespace isolation**: All assets prefixed with `oe-` and stored in dedicated managed namespace
4. **Native protocols**: Uses OpenClaw's native subagent announce chain for all communication
5. **CLI-first**: Prefers OpenClaw CLI commands over direct config file manipulation
6. **Extension-based intrusion**: Tool Gate, hooks, and skills modify behavior via OpenClaw's native extension mechanisms

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Layer                            │
│                   (Your OpenClaw Main)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Main Session Skills                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐  │
│  │ oe-eta-         │ │ oe-toolcall-    │ │ oe-timeout-  │  │
│  │ estimator       │ │ router          │ │ state-sync   │  │
│  └─────────────────┘ └─────────────────┘ └──────────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │ Complex tasks (TOOLCALL > 2)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   oe-orchestrator                            │
│              (Planning + Dispatch Agent)                     │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐  │
│  │ oe-project-     │ │ oe-worker-      │ │ oe-agentos-  │  │
│  │ registry        │ │ dispatch        │ │ practice     │  │
│  └─────────────────┘ └─────────────────┘ └──────────────┘  │
│  ┌─────────────────┐                                        │
│  │ oe-git-context  │                                        │
│  └─────────────────┘                                        │
└──────────┬──────────┬──────────┬──────────┬─────────────────┘
           │          │          │          │
            ▼          ▼          ▼          ▼          ▼
┌──────────────┐ ┌────────┐ ┌────────────┐ ┌──────────────┐ ┌──────────────┐
│ oe-searcher  │ │oe-sys- │ │oe-script_  │ │ oe-watchdog  │ │oe-tool-      │
│ (Research)   │ │helper  │ │ coder      │ │ (Monitor)    │ │recovery      │
│              │ │(System)│ │ (Scripts)  │ │              │ │(Recovery)   │
└──────────────┘ └────────┘ └────────────┘ └──────────────┘ └──────────────┘
```

## Control Flow

### 1. Task Routing & Bounded Orchestration Loop

```
User Request
    │
    ▼
┌──────────────────────────────────────┐
│ Main Session with Enhancement Skills │
└──────────────────────────────────────┘
    │
    ├── Simple task (TOOLCALL ≤ 2) ────► Handle locally
    │
    └── Complex task (TOOLCALL > 2) ───► oe-orchestrator
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │ Assess complexity│
                                    │ Create Plan      │
                                    └────────┬─────────┘
                                             │
                                             ▼
                                     ┌──────────────────┐
                          ┌──────────┤  Dispatch Round  │◄─────────┐
                          │          │ (sessions_spawn) │          │
                          │          └────────┬─────────┘          │
                          │                   │                    │
                          │                   ▼                    │
                          │          ┌──────────────────┐          │
                          │          │   Yield Turn     │          │
                          │          │ (sessions_yield) │          │
                          │          └────────┬─────────┘          │
                          │                   │                    │
                          │                   ▼                    │
                          │          ┌──────────────────┐          │
                          │          │ Collect Results  │          │
                          │          │ (auto-announce)  │          │
                          │          └────────┬─────────┘          │
                          │                   │                    │
                          │                   ▼                    │
                          │          ┌──────────────────┐          │
                          │          │ Evaluate Progress│──────────┘
                          │          │ (Check Recovery) │
                          │          └────────┬─────────┘
                          │                   │
                          └───────────────────┼────────────────────┐
                                              ▼                    ▼
                                     ┌──────────────────┐   ┌──────────────┐
                                     │ Synthesize       │   │ Blocked/     │
                                     │ Return to main   │   │ Exhausted    │
                                     └──────────────────┘   └──────────────┘

### 1.1 Tool-Failure Recovery Flow

When `Evaluate Progress` detects a tool failure, it triggers the recovery branch:

```
Evaluate Progress (Failure Detected)
    │
    ▼
Check Eligibility (Attempts < 1)
    │
    ▼
sessions_spawn → oe-tool-recovery
    │
    ▼
sessions_yield (Wait for Recovery)
    │
    ▼
Collect RecoveredMethod
    │
    ▼
Retry Original Worker (Max 1)
    │
    ▼
Complete or Escalate
```
```

User Request
    │
    ▼
┌──────────────────────────────────────┐
│ Main Session with Enhancement Skills │
└──────────────────────────────────────┘
    │
    ├── Simple task (TOOLCALL ≤ 2) ────► Handle locally
    │
    └── Complex task (TOOLCALL > 2) ───► oe-orchestrator
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │ Assess complexity│
                                    │ Plan execution   │
                                    │ Dispatch workers │
                                    └──────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
            ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
            │ oe-searcher  │          │oe-syshelper  │          │oe-script_    │
            │ Research     │          │System intros │          │coder         │
            └──────────────┘          └──────────────┘          └──────────────┘
                    │                         │                         │
                    └─────────────────────────┴─────────────────────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │ Synthesize       │
                                    │ Return to main   │
                                    └──────────────────┘
```

### 2. Timeout Monitoring

```
┌─────────────────┐
│ monitor_runtime │  (runs every minute via cron/systemd)
│   script        │
└────────┬────────┘
         │ Detects timeout suspicion
         ▼
┌─────────────────┐
│  Runtime Store  │  (~/.openclaw/openclaw-enhance/state/)
│  (state.json)   │
└────────┬────────┘
         │ Writes timeout_suspected event
         ▼
┌─────────────────┐
│  oe-watchdog    │  (confirms or rejects)
│  (diagnosis)    │
└────────┬────────┘
         │ If confirmed: sends reminder + updates state
         ▼
┌─────────────────┐
│ Original Session│  (receives timeout notification)
└─────────────────┘
```

### 3. Governance Admin Surface

The legacy scripts under `~/.openclaw/workspace/scripts/governance/` are not intended to remain the primary operator surface. `openclaw-enhance` now owns the supported governance/admin commands directly.

```
Legacy governance scripts
        │
        ├── diagnose / healthcheck / restart / subagent bookkeeping
        ▼
python -m openclaw_enhance.cli governance ...
        │
        ├── diagnose
        ├── healthcheck
        ├── archive-sessions
        ├── safe-restart
        ├── restart-resume
        └── subagents mark-done|mark-dead|set-status|set-eta|merge-state

Continuous watch/stuck monitoring remains project-managed through:

python -m openclaw_enhance.monitor_runtime ...
```

This preserves ADR 0003: `oe-watchdog` keeps narrow runtime-only authority, while destructive or administrative operations remain explicit CLI/admin commands.

## Components

### Main Session Skills

Located in `skills/` and installed into main workspace:

| Skill | Purpose |
|-------|---------|
| `oe-eta-estimator` | Estimates task duration and complexity |
| `oe-toolcall-router` | Routes complex tasks (TOOLCALL > 2) to orchestrator |
| `oe-timeout-state-sync` | Synchronizes timeout state between main and orchestrator |

### Orchestrator

Location: `workspaces/oe-orchestrator/`

The orchestrator is a high-capability agent that:
- Uses the same model class as main
- Always plans before acting (planning-with-files)
- Operates in a **bounded multi-round loop** (max 3-5 rounds)
- Dispatches to specialized workers via native `sessions_spawn` and `announce`
- Uses `sessions_yield` as a turn-boundary synchronization primitive
- Synthesizes results from all workers

Skills are markdown contracts stored in `skills/` directories. The router skill (`oe-toolcall-router/SKILL.md`) guides decisions, while native `sessions_spawn` carries out execution.

**Local Skills:**
- `oe-project-registry`: Project discovery and workspace selection
- `oe-worker-dispatch`: Task assignment to appropriate workers
- `oe-agentos-practice`: AgentOS pattern implementation for coding
- `oe-git-context`: Git history injection for context

### Worker Agents

All workers operate via the native subagent announce chain. Worker capabilities are **discovered dynamically** from AGENTS.md frontmatter (routing metadata) and `TOOLS.md` (exact tool definitions).

| Worker | Role | Model | Access | Routing Metadata Source |
|--------|------|-------|--------|-------------------------|
| `oe-searcher` | Research, web search, documentation | Cheap | Read-only | `workspaces/oe-searcher/AGENTS.md` frontmatter |
| `oe-syshelper` | System introspection (grep, ls, find) | Cheap | Read-only | `workspaces/oe-syshelper/AGENTS.md` frontmatter |
| `oe-script_coder` | Script development and testing | Standard | Repo write | `workspaces/oe-script_coder/AGENTS.md` frontmatter |
| `oe-watchdog` | Session monitoring, timeout handling | Standard | Runtime only | `workspaces/oe-watchdog/AGENTS.md` frontmatter |
| `oe-tool-recovery` | Tool failure diagnosis and recovery | Standard | Read-only | `workspaces/oe-tool-recovery/AGENTS.md` frontmatter |

**Worker Discovery Flow**:
1. Orchestrator enumerates `workspaces/*/AGENTS.md` files
2. Parses YAML frontmatter to extract routing metadata (capabilities, constraints, cost)
3. Applies hard filters (e.g., `mutation_mode: read_only` for safe tasks)
4. Ranks candidates by least-privilege rules
5. Dispatches selected worker via `sessions_spawn`

### Hooks

Location: `hooks/oe-subagent-spawn-enrich/`

Enriches `subagent_spawning` events with:
- `task_id`: Unique identifier
- `project`: Project context
- `parent_session`: Originating session
- `eta_bucket`: short/medium/long categorization
- `ownership`: Channel identity metadata (`channel_type`, `channel_conversation_id`)
- `restart_epoch`: Current system restart epoch
- `dedupe_key`: Channel-aware duplicate detection key (includes `channel_type` to prevent cross-channel collisions)

### Extensions

Location: `extensions/openclaw-enhance-runtime/`

Thin TypeScript bridge for:
- **Runtime state integration**: Synchronizes `runtime-state.json` with OpenClaw's internal state.
- **Hook event consumption**: Processes enriched spawn events.
- **Output Sanitization**: Automatically strips internal protocol markers (e.g., `[Pasted ~]`, `<|tool_call...|>`) from enhance-controlled outward paths.
- **Session Ownership Validation**: Implements `isMainSession` and `before_tool_call` checks to enforce session isolation and fail-closed security.
- **OpenClaw plugin registration**: Registers the enhancement layer as a native OpenClaw extension.

### Runtime State Store

Location: `~/.openclaw/openclaw-enhance/state/runtime-state.json`

Stores:
- Task tracking metadata (including `ownership` metadata)
- Timeout events (suspected/confirmed/cleared)
- Project registry cache
- Session mapping
- `restart_epoch`: Monotonically increasing counter for system restarts to invalidate stale session bindings.

## Session Ownership Model

To ensure secure session isolation in multi-user or multi-channel environments, `openclaw-enhance` implements a formal ownership mapping:

### Identity Mapping
The system maps external identities to OpenClaw sessions:
`(channel_type, channel_conversation_id) -> session_id`

### Binding Lifecycle
1. **Creation**: When a new session is spawned, the `oe-subagent-spawn-enrich` hook captures the channel identity and binds it to the `session_id`.
2. **Validation**: The `oe-runtime` extension intercepts `before_tool_call` and `isMainSession` checks to verify that the current requester owns the target session.
3. **Invalidation**: Upon system restart, the `restart_epoch` is incremented. All existing bindings from previous epochs are marked as "stale" and require re-validation before reuse.

### Fail-Closed Security
If ownership is ambiguous (e.g., a restart occurred but no ownership metadata is provided), the system defaults to a "fail-closed" state, rejecting the session reuse to prevent potential hijacking.

## Managed Namespace

All enhancement-owned assets live under:

```
~/.openclaw/openclaw-enhance/
├── install-manifest.json      # Installed components
├── state/
│   └── runtime-state.json     # Runtime tracking
├── locks/
│   └── install.lock           # Installation lock
├── backups/
│   └── openclaw.json.bak      # Pre-install backup
└── logs/
    └── install.log            # Installation logs
```

**Agent Workspaces:**
```
~/.openclaw/openclaw-enhance/workspaces/oe-orchestrator/
~/.openclaw/openclaw-enhance/workspaces/oe-searcher/
~/.openclaw/openclaw-enhance/workspaces/oe-syshelper/
~/.openclaw/openclaw-enhance/workspaces/oe-script_coder/
~/.openclaw/openclaw-enhance/workspaces/oe-watchdog/
```

## Communication Protocol

### Native Primitives (Spawn & Yield)

The ONLY approved communication and synchronization protocol between Orchestrator and workers:

1. **`sessions_spawn`**: The sole mechanism for creating worker subagents.
2. **`sessions_yield`**: Orchestrator-only primitive to end a turn and await worker results.
3. **`announce`**: Native mechanism for workers to return results to the orchestrator.

```typescript
// Orchestrator dispatches
await subagent.announce({
  agent: "oe-searcher",
  task: "Research React 19 features",
  context: { project: "my-app", parent_session: "sess_001" }
});

// Orchestrator yields turn
await sessions_yield();

// Worker processes and returns (auto-announced on next turn)
return {
  summary: "Found 5 key features...",
  artifacts: ["/path/to/research.md"],
  next_steps: ["Review feature X"]
};
```

**Why native primitives only:**
- Aligns with OpenClaw's design
- Provides automatic lifecycle management
- Built-in timeout and error handling
- No custom infrastructure needed

## Support Matrix

| Component | Version/Platform |
|-----------|------------------|
| OpenClaw | `>=2026.3.11 <2026.4.0` |
| Platforms | macOS (darwin), Linux |
| Windows/WSL | **Not supported** in v1 |

## Security Model

1. **Namespace isolation**: All assets prefixed with `oe-`
2. **Ownership tracking**: Config mutations only on owned keys
3. **Atomic operations**: Backup before modify, rollback on failure
4. **Authority boundaries**: Watchdog cannot kill processes or edit user repos
5. **Symmetric uninstall**: Complete removal of all owned assets

## Performance Considerations

1. **Main stays thin**: Simple tasks never touch orchestrator
2. **Worker specialization**: Cheap models for rote work
3. **Native protocols**: No HTTP overhead or queue latency
4. **Lazy loading**: Runtime state only accessed when needed
5. **Deduplication**: Spawn events include dedupe keys

## Version

Architecture Version: 1.2.0
Last Updated: 2026-04-05
