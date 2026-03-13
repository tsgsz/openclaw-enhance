---
name: oe-toolcall-router
version: 1.0.0
description: Routes tasks to main or escalates to oe-orchestrator based on heuristics. Keeps main thin - simple tasks stay local, heavy tasks escalate.
user-invocable: true
allowed-tools: "Read, Write, Bash"
metadata:
  routing_heuristics:
    max_toolcalls: 2
    max_duration_minutes: 30
    escalation_threshold: 2
    parallel_escalation: true
    long_running_threshold_minutes: 30
---

# Toolcall Router

Route tasks between main session and oe-orchestrator.

## Philosophy

Keep `main` thin and responsive:
- **Simple tasks**: Stay in main (≤2 toolcalls, no parallelism)
- **Heavy tasks**: Escalate to oe-orchestrator (native subagent path)

## Routing Heuristics

### Stay in Main (route)

| Criteria | Threshold |
|----------|-----------|
| Toolcalls | ≤ 2 |
| Parallelism | Not required |
| Duration | ≤ 15 minutes |
| Scope | Single file or simple query |

### Escalate to Orchestrator (escalate)

| Criteria | Threshold |
|----------|-----------|
| Toolcalls | > 2 |
| Parallelism | Required |
| Duration | > 30 minutes |
| Scope | Multi-file, research, or complex |

## Escalation Path

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Session                             │
│                         ↓                                   │
│                   [Assess Task]                             │
│                         ↓                                   │
│              ┌──────────────────────┐                       │
│              │ Toolcalls > 2 ?      │────Yes────┐          │
│              └──────────────────────┘            │          │
│                      No ↓                        │          │
│              ┌──────────────────────┐            │          │
│              │ Requires Parallel?   │────Yes─────┤          │
│              └──────────────────────┘            │          │
│                      No ↓                        │          │
│              ┌──────────────────────┐            │          │
│              │ Duration > 30 min?   │────Yes─────┤          │
│              └──────────────────────┘            │          │
│                      No ↓                        ↓          │
│                   [main]              [oe-orchestrator]     │
│                   (local)            (native subagent)      │
└─────────────────────────────────────────────────────────────┘
```

## Usage

```python
from openclaw_enhance.skills_catalog import SkillRouter, TaskAssessment

router = SkillRouter()

# Simple task - stays local
assessment = TaskAssessment(
    description="Fix typo in README",
    estimated_toolcalls=1,
    requires_parallel=False,
    complexity_score=1,
)
decision = router.route_task(assessment)
# decision.action = "route"
# decision.target = "main"

# Complex task - escalates
assessment = TaskAssessment(
    description="Refactor auth module across 5 files",
    estimated_toolcalls=8,
    requires_parallel=False,
    complexity_score=4,
)
decision = router.route_task(assessment)
# decision.action = "escalate"
# decision.target = "oe-orchestrator"
```

## Decision Contract

Returns `RoutingDecision`:
- `action`: `"route"` | `"escalate"`
- `target`: `"main"` | `"oe-orchestrator"`
- `reason`: Human-readable explanation
- `estimated_duration`: timedelta estimate

## Important Notes

- **NEVER** route directly to workers from main
- Always escalate to `oe-orchestrator` first
- Orchestrator handles worker delegation
- Native subagent path is used for escalation
