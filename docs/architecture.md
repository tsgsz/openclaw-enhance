# Architecture

This document describes the architecture of `openclaw-enhance`, a non-invasive control-plane package for OpenClaw.

> **Project State**: See [`opencode-iteration-handbook.md`](./opencode-iteration-handbook.md) for current design status, permanent progress, and required reading paths.

## Overview

`openclaw-enhance` augments OpenClaw's multitasking capabilities, long-running task handling, and operational visibility without modifying OpenClaw core source code. It uses OpenClaw's native extension points: skills, hooks, extensions, and agent workspaces.

## Design Principles

1. **Non-invasive**: No edits to OpenClaw source code or bundled runtime files
2. **Symmetric lifecycle**: One-click install and uninstall with rollback support
3. **Namespace isolation**: All assets prefixed with `oe-` and stored in dedicated managed namespace
4. **Native protocols**: Uses OpenClaw's native subagent announce chain for all communication
5. **CLI-first**: Prefers OpenClaw CLI commands over direct config file manipulation

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
           ▼          ▼          ▼          ▼
┌──────────────┐ ┌────────┐ ┌────────────┐ ┌──────────────┐
│ oe-searcher  │ │oe-sys- │ │oe-script_  │ │ oe-watchdog  │
│ (Research)   │ │helper  │ │ coder      │ │ (Monitor)    │
│              │ │(System)│ │ (Scripts)  │ │              │
└──────────────┘ └────────┘ └────────────┘ └──────────────┘
```

## Control Flow

### 1. Task Routing

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

The orchestrator is a full-capability agent that:
- Uses the same model class as main
- Always plans before acting (planning-with-files)
- Dispatches to specialized workers via native sessions_spawn and announce
- Synthesizes results from all workers

Skills are markdown contracts stored in `skills/` directories. The router skill (`oe-toolcall-router/SKILL.md`) guides decisions, while native `sessions_spawn` carries out execution.

**Local Skills:**
- `oe-project-registry`: Project discovery and workspace selection
- `oe-worker-dispatch`: Task assignment to appropriate workers
- `oe-agentos-practice`: AgentOS pattern implementation for coding
- `oe-git-context`: Git history injection for context

### Worker Agents

All workers operate via the native subagent announce chain.

| Worker | Role | Model | Access |
|--------|------|-------|--------|
| `oe-searcher` | Research, web search, documentation | Cheap | Sandbox R/W |
| `oe-syshelper` | System introspection (grep, ls, find) | Cheap | Read-only |
| `oe-script_coder` | Script development and testing | Codex-class | Sandbox R/W |
| `oe-watchdog` | Session monitoring, timeout handling | Any | Full access |

### Hooks

Location: `hooks/oe-subagent-spawn-enrich/`

Enriches `subagent_spawning` events with:
- `task_id`: Unique identifier
- `project`: Project context
- `parent_session`: Originating session
- `eta_bucket`: short/medium/long categorization
- `dedupe_key`: Duplicate detection key

### Extensions

Location: `extensions/openclaw-enhance-runtime/`

Thin TypeScript bridge for:
- Runtime state integration
- Hook event consumption
- OpenClaw plugin registration

### Runtime State Store

Location: `~/.openclaw/openclaw-enhance/state/runtime-state.json`

Stores:
- Task tracking metadata
- Timeout events (suspected/confirmed/cleared)
- Project registry cache
- Session mapping

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
~/.openclaw/workspace-openclaw-enhance-orchestrator/
~/.openclaw/workspace-openclaw-enhance-searcher/
~/.openclaw/workspace-openclaw-enhance-syshelper/
~/.openclaw/workspace-openclaw-enhance-script_coder/
~/.openclaw/workspace-openclaw-enhance-watchdog/
```

## Communication Protocol

### Native Subagent Announce Chain

The ONLY approved communication protocol between Orchestrator and workers:

```typescript
// Orchestrator dispatches
const result = await subagent.announce({
  agent: "oe-searcher",
  task: "Research React 19 features",
  context: { project: "my-app", parent_session: "sess_001" }
});

// Worker processes and returns
return {
  summary: "Found 5 key features...",
  artifacts: ["/path/to/research.md"],
  next_steps: ["Review feature X"]
};
```

**Why native announce only:**
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

Architecture Version: 1.0.0
Last Updated: 2026-03-13
