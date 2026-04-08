---
name: oe-subagent-spawn-enrich
description: Enrich and normalize subagent spawn events for OpenClaw Enhance v2.
metadata: { "openclaw": { "emoji": "🔗", "events": ["subagent_spawning"] }, "version": "2.0.0" }
---

# oe-subagent-spawn-enrich

OpenClaw-native hook for enriching subagent spawn events with enhanced metadata.

## Purpose

This hook intercepts `subagent_spawning` events and enriches them with additional context
to enable better task tracking, deduplication, and runtime integration.

## Event Subscription

```yaml
hooks:
  - event: subagent_spawning
    handler: oe-subagent-spawn-enrich
    priority: 100  # Early in chain
```

## Enrichment Fields

The hook adds the following fields to the spawn event:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | UUID v4 format: `task_{8-4-4-4-12}` |
| `project` | string | Resolved project identifier (canonical path or "default") |
| `parent_session` | string | Parent session ID that initiated the spawn |
| `eta_bucket` | string | Categorized ETA: "short" (<5min), "medium" (5-30min), "long" (>30min) |
| `dedupe_key` | string | Deterministic hash for duplicate detection |
| `project_context` | object | Full project metadata (see below) |

### `task_id` Format (v2)

```
task_XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
```

UUID v4 format generated with proper version and variant bits.

### `project_context` Shape

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | string | Canonical project path or "default" |
| `project_name` | string | Human-readable project name or "default" |
| `project_type` | string | "python", "nodejs", etc. or "unknown" |
| `project_kind` | string | "permanent", "temporary", or "default" |

Resolution chain:
1. If `context.project` is explicitly set (non-empty, non-"default"): use it, look up registry for metadata
2. Else if `active_project` in `~/.openclaw/openclaw-enhance/runtime-state.json`: use it, look up registry
3. Else: fall back to `"default"` with `project_type: "unknown"`, `project_kind: "default"`

All file reads are wrapped in try/catch — missing files never cause errors.

## Example Enriched Event

```json
{
  "event": "subagent_spawning",
  "timestamp": "2024-01-15T10:30:00Z",
  "payload": {
    "subagent_type": "oe-orchestrator",
    "task_description": "Refactor auth module",
    "estimated_toolcalls": 5,
    "task_id": "task_abc123_xyz789",
    "project": "/Users/dev/workspace/my-project",
    "parent_session": "sess_parent_001",
    "eta_bucket": "medium",
    "dedupe_key": "/Users/dev/workspace/my-project:oe-orchestrator:auth-ref:20240115",
    "project_context": {
      "project_id": "/Users/dev/workspace/my-project",
      "project_name": "my-project",
      "project_type": "python",
      "project_kind": "permanent"
    }
  }
}
```

## Dedupe Key Format

```
{project}:{subagent_type}:{task_hash}:{date}
```

- `project`: Project identifier from runtime state
- `subagent_type`: Type of subagent being spawned
- `task_hash`: First 8 chars of SHA256(task_description)
- `date`: YYYYMMDD format for daily deduplication scope

## ETA Buckets

| Bucket | Duration | Typical Use Case |
|--------|----------|------------------|
| `short` | < 5 minutes | Quick lookups, single file edits |
| `medium` | 5-30 minutes | Multi-file changes, moderate complexity |
| `long` | > 30 minutes | Complex refactors, research tasks |

## Handler Interface

```typescript
interface SpawnEnrichInput {
  event: 'subagent_spawning';
  payload: {
    subagent_type: string;
    task_description: string;
    estimated_toolcalls?: number;
    estimated_duration_minutes?: number;
  };
  context: {
    session_id: string;
    project?: string;
    parent_session?: string;
  };
}

interface SpawnEnrichOutput {
  enriched_payload: {
    task_id: string;
    project: string;
    parent_session: string;
    eta_bucket: 'short' | 'medium' | 'long';
    dedupe_key: string;
    project_context: {
      project_id: string;
      project_name: string;
      project_type: string;
      project_kind: string;
    };
  };
}
```

## Blocking Logic

Writer agents (`oe-script_coder`) require a valid project context. If no project is discovered (project_kind is "default"), the hook returns `unsafe: true` with a block reason:

```json
{
  "unsafe": true,
  "enriched_payload": {
    "unsafe_reason": "BLOCKED: Cannot spawn oe-script_coder without a valid project. Project is 'default'. Use oe-project-registry to discover or register a project first."
  }
}
```

This prevents writer agents from operating without proper project context, ensuring file operations are scoped to registered projects per the README requirement.

## Error Handling

The hook is designed to be non-blocking for non-writer agents:
- Enrichment failures are logged but don't prevent spawn
- Missing context fields use sensible defaults
- Invalid durations default to "medium" bucket
- Writer agents with "default" project are blocked via `unsafe: true`

## Integration Notes

- This hook is part of the native subagent announce chain
- Enriched data is available to downstream hooks and extensions
- The extension bridge (`openclaw-enhance-runtime`) consumes this data
- No direct runtime modifications required
