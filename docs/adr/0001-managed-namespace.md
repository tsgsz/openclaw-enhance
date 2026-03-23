# ADR 0001: Managed Namespace

## Status

Accepted

## Context

`openclaw-enhance` needs to store configuration, runtime state, and workspace data without:
1. Modifying OpenClaw core source code
2. Polluting user's OpenClaw configuration
3. Making uninstallation difficult or error-prone
4. Conflicting with user-created agents and settings

The enhancement layer must coexist with OpenClaw cleanly, supporting one-click install and uninstall operations.

## Decision

We will use a **dedicated managed namespace** under `~/.openclaw/openclaw-enhance/` with strict prefix-based naming conventions.

### Namespace Structure

```
~/.openclaw/openclaw-enhance/
├── install-manifest.json          # Source of truth for installed components
├── state/
│   └── runtime-state.json        # Runtime tracking data
├── locks/
│   └── install.lock              # Installation operation lock
├── backups/
│   └── openclaw.json.bak         # Pre-install config backup
└── logs/
    ├── install.log               # Installation history
    └── monitor.log               # Runtime monitor logs
```

### Naming Conventions

All enhancement-owned assets use the `oe-` prefix:

- **Agents**: `oe-orchestrator`, `oe-searcher`, `oe-syshelper`, `oe-script_coder`, `oe-watchdog`, `oe-tool-recovery`
- **Skills**: `oe-eta-estimator`, `oe-toolcall-router`, `oe-timeout-state-sync`
- **Hooks**: `oe-subagent-spawn-enrich`
- **Workspaces**: `~/.openclaw/openclaw-enhance/workspaces/<role>/`

### Ownership Model

Enhancement-owned persistent state lives under the managed root and install manifest:

```json
{
  "install-manifest.json": "tracks enhancement-owned components",
  "runtime-state.json": "tracks runtime state",
  "hooks/": "contains synced hook assets"
}
```

Runtime-facing registration in `openclaw.json` must use only supported OpenClaw surfaces:

```json
{
  "agents": {
    "list": [
      {
        "id": "oe-orchestrator",
        "workspace": "~/.openclaw/openclaw-enhance/workspaces/oe-orchestrator",
        "agentDir": "~/.openclaw/openclaw-enhance/workspaces/oe-orchestrator"
      }
    ]
  },
  "hooks": {
    "internal": {
      "enabled": true,
      "entries": {
        "oe-subagent-spawn-enrich": {"enabled": true}
      },
      "load": {
        "extraDirs": ["~/.openclaw/openclaw-enhance/hooks"]
      }
    }
  }
}
```

`openclaw-enhance` must never introduce an unsupported top-level config namespace. It owns only the `oe-*` registrations it writes on supported surfaces and the files under `~/.openclaw/openclaw-enhance/`.

### Lifecycle Guarantees

**Install**:
1. Create namespace directory structure
2. Write install manifest
3. Sync worker workspaces and hook assets into the managed namespace
4. Copy skills to main workspace
5. Register `oe-*` agents on supported `agents.list` surfaces
6. Register `oe-subagent-spawn-enrich` on supported `hooks.internal` surfaces
7. Create config backup

**Uninstall**:
1. Remove enhancement-owned hook registrations from supported config surfaces
2. Remove enhancement-owned agent registrations from supported config surfaces
3. Remove synced hook assets
4. Remove skills from main workspace
5. Remove worker workspaces
6. Remove namespace directory
7. Release locks

**Rollback** (on install failure):
1. Restore config from backup
2. Remove partially installed components
3. Clean up namespace
4. Release lock

## Consequences

### Positive

- **Clean separation**: User and enhancement assets are clearly distinguished
- **Symmetric lifecycle**: Install and uninstall are predictable, reversible operations
- **Safe upgrades**: Can detect existing installation and upgrade in-place
- **Easy debugging**: All enhancement state in one location
- **No conflicts**: `oe-` prefix prevents naming collisions with user agents

### Negative

- **Longer paths**: Managed workspace paths are more verbose than a single top-level directory (for example `openclaw-enhance/workspaces/oe-orchestrator`)
- **Extra directory**: One more directory under `~/.openclaw/`
- **Config overhead**: Must track owned keys explicitly

### Neutral

- **Disk usage**: Small overhead for manifest and state files (~10KB)
- **Runtime overhead**: State lookups require JSON file reads

## Alternatives Considered

### 1. Scatter assets throughout OpenClaw directories

**Rejected**: Difficult to track and uninstall; risk of orphaning resources.

### 2. Use OpenClaw's built-in package manager

**Rejected**: OpenClaw doesn't have a package manager suitable for this use case; we need to manage multiple asset types (agents, skills, hooks, workspaces).

### 3. Store everything in openclaw.json

**Rejected**: Runtime state changes frequently; doesn't belong in version-controlled config file.

## Related Decisions

- [ADR 0002: Native Subagent Announce](0002-native-subagent-announce.md)
- [ADR 0003: Watchdog Authority](0003-watchdog-authority.md)

## References

- `src/openclaw_enhance/paths.py`
- `src/openclaw_enhance/runtime/ownership.py`
- `src/openclaw_enhance/install/manifest.py`

## Date

2026-03-13
