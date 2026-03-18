---
name: oe-subagent-spawn-enrich
description: Enrich and normalize subagent spawn events for OpenClaw Enhance.
metadata: { "openclaw": { "emoji": "🔗", "events": ["subagent_spawning"] } }
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
| `task_id` | string | Unique identifier for this task invocation |
| `project` | string | Project context from runtime state |
| `parent_session` | string | Parent session ID that initiated the spawn |
| `eta_bucket` | string | Categorized ETA: "short" (<5min), "medium" (5-30min), "long" (>30min) |
| `dedupe_key` | string | Deterministic key for duplicate detection |

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
    "project": "my-project",
    "parent_session": "sess_parent_001",
    "eta_bucket": "medium",
    "dedupe_key": "my-project:oe-orchestrator:auth-ref:20240115"
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
  };
}
```

## Error Handling

The hook is designed to be non-blocking:
- Enrichment failures are logged but don't prevent spawn
- Missing context fields use sensible defaults
- Invalid durations default to "medium" bucket

## Integration Notes

- This hook is part of the native subagent announce chain
- Enriched data is available to downstream hooks and extensions
- The extension bridge (`openclaw-enhance-runtime`) consumes this data
- No direct runtime modifications required
