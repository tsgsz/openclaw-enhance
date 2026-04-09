# Architecture

This document describes the architecture of `openclaw-enhance`, a non-invasive control-plane package for OpenClaw.

> **Project State**: See [`opencode-iteration-handbook.md`](./opencode-iteration-handbook.md) for current design status, permanent progress, and required reading paths.

## Overview

`openclaw-enhance` augments OpenClaw's multitasking capabilities, long-running task handling, and operational visibility without modifying OpenClaw core source code. It uses OpenClaw's native extension points: skills, hooks, and extensions.

## v2 Architecture

**openclaw-enhance v2 采用纯 Skill 架构**：
- **无工作区 (Workspaces)**：v1 的 agent 工作区已归档至 `~/.openclaw/openclaw-enhance/v1-archive/`
- **无 Agent 注册**：不再使用 `oe-orchestrator`、`oe-searcher` 等托管 Agent
- **纯 Skill 路由**：所有路由逻辑通过 Skills 实现，使用 OpenClaw 原生的 `sessions_spawn` 机制

## Design Principles

1. **Non-invasive**: No edits to OpenClaw source code or bundled runtime files
2. **Symmetric lifecycle**: One-click install and uninstall with rollback support
3. **Namespace isolation**: All assets prefixed with `oe-` and stored in dedicated managed namespace
4. **Native protocols**: Uses OpenClaw's native `sessions_spawn` for all task dispatch
5. **CLI-first**: Prefers OpenClaw CLI commands over direct config file manipulation
6. **Skill-based routing**: Task routing via Skills, not dedicated Agent workspaces

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Layer                            │
│                   (Your OpenClaw Main)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Main Session Skills                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐    │
│  │ oe-tag-router   │ │ oe-eta-        │ │ oe-timeout-  │    │
│  │ (Tag & Route)   │ │ estimator      │ │ state-sync   │    │
│  └─────────────────┘ └─────────────────┘ └──────────────┘    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼ sessions_spawn
┌─────────────────────────────────────────────────────────────┐
│                    Global Skills                             │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐    │
│  │ oe-spawn-search │ │ oe-spawn-coder │ │ oe-spawn-ops │    │
│  │ (Research)      │ │ (Scripts)      │ │ (Ops)        │    │
│  └─────────────────┘ └─────────────────┘ └──────────────┘    │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐    │
│  │ oe-model-       │ │ oe-project-    │ │ oe-git-      │    │
│  │ discover        │ │ context        │ │ context      │    │
│  └─────────────────┘ └─────────────────┘ └──────────────┘    │
│  ┌─────────────────┐ ┌─────────────────┐                    │
│  │ oe-memory-sync  │ │ oe-publish     │                    │
│  └─────────────────┘ └─────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

## Control Flow

### Task Routing

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
    └── Complex task (TOOLCALL > 2) ────► sessions_spawn
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │ Tag-based        │
                                    │ Routing          │
                                    └────────┬─────────┘
                                             │
                   ┌─────────────────────────┼─────────────────────────┐
                   ▼                         ▼                         ▼
           ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
           │oe-spawn-    │          │oe-spawn-     │          │oe-spawn-     │
           │search       │          │coder         │          │ops           │
           │(Research)   │          │(Scripts)     │          │(Ops)         │
           └──────────────┘          └──────────────┘          └──────────────┘
```

### Timeout Monitoring

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
│  Timeout        │  (confirms or rejects)
│  Detector       │
└────────┬────────┘
         │ If confirmed: sends reminder + updates state
         ▼
┌─────────────────┐
│ Original Session│  (receives timeout notification)
└─────────────────┘
```

## Components

### Main Session Skills

Located in `skills/` and installed into main workspace:

| Skill | Purpose |
|-------|---------|
| `oe-tag-router` | Routes tasks to appropriate spawn skills |
| `oe-eta-estimator` | Estimates task duration and complexity |
| `oe-timeout-state-sync` | Synchronizes timeout state between main and runtime |

### Global Skills

Located in `~/.openclaw/openclaw-enhance/skills/`:

| Skill | Purpose |
|-------|---------|
| `oe-spawn-search` | Task dispatch for research and web search |
| `oe-spawn-coder` | Task dispatch for code writing and testing |
| `oe-spawn-ops` | Task dispatch for operations (tunnels, backup, launchd) |
| `oe-model-discover` | Discover available models and select by priority |
| `oe-project-context` | Project discovery and workspace selection |
| `oe-git-context` | Git history injection for context |
| `oe-memory-sync` | Main Session memory/context synchronization |
| `oe-publish` | Unified publish gateway for content |

### Hooks

Location: `hooks/oe-subagent-spawn-enrich/`

Enriches `subagent_spawning` events with:
- `task_id`: Unique identifier
- `project`: Project context
- `parent_session`: Originating session
- `eta_bucket`: short/medium/long categorization
- `ownership`: Channel identity metadata (`channel_type`, `channel_conversation_id`)
- `restart_epoch`: Current system restart epoch
- `dedupe_key`: Channel-aware duplicate detection key

### Extensions

Location: `extensions/openclaw-enhance-runtime/`

Thin TypeScript bridge for:
- **Runtime state integration**: Synchronizes `runtime-state.json` with OpenClaw's internal state.
- **Hook event consumption**: Processes enriched spawn events.
- **Output Sanitization**: Automatically strips internal protocol markers.
- **Session Ownership Validation**: Implements `isMainSession` and `before_tool_call` checks.
- **OpenClaw plugin registration**: Registers the enhancement layer as a native OpenClaw extension.

### Runtime State Store

Location: `~/.openclaw/openclaw-enhance/state/runtime-state.json`

Stores:
- Task tracking metadata (including `ownership` metadata)
- Timeout events (suspected/confirmed/cleared)
- Project registry cache
- Session mapping
- `restart_epoch`: Monotonically increasing counter for system restarts.

## Session Ownership Model

To ensure secure session isolation in multi-user or multi-channel environments, `openclaw-enhance` implements a formal ownership mapping:

### Identity Mapping
The system maps external identities to OpenClaw sessions:
`(channel_type, channel_conversation_id) -> session_id`

### Binding Lifecycle
1. **Creation**: When a new session is spawned, the `oe-subagent-spawn-enrich` hook captures the channel identity and binds it to the `session_id`.
2. **Validation**: The `oe-runtime` extension intercepts `before_tool_call` and `isMainSession` checks to verify ownership.
3. **Invalidation**: Upon system restart, the `restart_epoch` is incremented. All existing bindings are marked as "stale".

### Fail-Closed Security
If ownership is ambiguous, the system defaults to a "fail-closed" state.

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
├── skills/                    # v2 Skills
└── logs/
    └── install.log            # Installation logs
```

## Communication Protocol

### Native Primitives

The ONLY approved communication protocol:

1. **`sessions_spawn`**: The mechanism for creating task dispatches.
2. **`sessions_yield`**: Wait for results from spawned session.
3. **`announce`**: Return results from spawned session.

```typescript
// Main session dispatches
await sessions_spawn({
  skill: "oe-spawn-coder",
  task: "Write tests for auth module",
  context: { project: "my-app" }
});

// Wait for results
await sessions_yield();

// Worker processes and returns
return {
  summary: "Wrote 5 test cases...",
  artifacts: ["/path/to/tests.ts"],
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
| Windows/WSL | **Not supported** |

## Security Model

1. **Namespace isolation**: All assets prefixed with `oe-`
2. **Ownership tracking**: Config mutations only on owned keys
3. **Atomic operations**: Backup before modify, rollback on failure
4. **Tool Gate**: Main session restricted from edit/write/exec tools
5. **Symmetric uninstall**: Complete removal of all owned assets

## Performance Considerations

1. **Main stays thin**: Simple tasks never touch spawn skills
2. **Tag-based routing**: Fast routing decision without agent instantiation
3. **Native protocols**: No HTTP overhead or queue latency
4. **Lazy loading**: Runtime state only accessed when needed
5. **Deduplication**: Spawn events include dedupe keys

## Version

Architecture Version: 2.0.0
Last Updated: 2026-04-09
