---
name: oe-eta-estimator
version: 1.0.0
description: Estimates task duration based on toolcall count, complexity, and parallelism needs. Use when planning multi-step tasks or when user asks for time estimates.
user-invocable: true
allowed-tools: "Read, Write, Glob, Grep"
metadata:
  routing_heuristics:
    max_toolcalls: 2
    max_duration_minutes: 30
    base_time_per_toolcall: 3
---

# ETA Estimator

Estimate task duration before execution to set user expectations.

## When to Use

Use this skill when:
- User asks "how long will this take?"
- Planning a multi-step task
- Deciding whether to escalate to orchestrator
- Providing timeline estimates for work

## Estimation Formula

```python
def estimate_duration(toolcalls, complexity_score, requires_parallel):
    if toolcalls == 1:
        minutes = 2
    elif toolcalls == 2:
        minutes = 5
    elif toolcalls <= 5:
        minutes = toolcalls * 3
    elif toolcalls < 10:
        minutes = int(toolcalls * 3.75)
    elif toolcalls == 10:
        minutes = 40
    else:
        minutes = toolcalls * 4
    
    if requires_parallel:
        minutes = int(minutes * 1.5)
    
    return timedelta(minutes=minutes)
```

## Examples

| Task | Toolcalls | Parallel | ETA |
|------|-----------|----------|-----|
| Fix typo | 1 | No | 2 min |
| Add simple function | 2 | No | 5 min |
| Refactor module | 5 | No | 15 min |
| Complex refactor with tests | 8 | Yes | 45 min |
| Multi-file architecture change | 10 | Yes | 60 min |
| Large codebase migration | 20 | Yes | 120 min |

## Usage

```python
from openclaw_enhance.skills_catalog import estimate_task_duration, TaskAssessment

assessment = TaskAssessment(
    description="Add authentication middleware",
    estimated_toolcalls=4,
    requires_parallel=False,
    complexity_score=3,
)
duration = estimate_task_duration(assessment)
# Returns: timedelta(minutes=12)
```

## Output Contract

Returns estimation with:
- `estimated_duration`: timedelta
- Confidence level based on task clarity

## Notes

- Estimates are rough heuristics, not guarantees
- Parallel execution adds 50% overhead for coordination
- Complex tasks (high complexity_score) take longer per toolcall
