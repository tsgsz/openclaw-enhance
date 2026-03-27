---
name: oe-eta-estimator
version: 2.0.0
description: Announces upfront ETA and refreshes expectations when tasks are delayed. Human-intuitive expectation management — not just internal metadata.
user-invocable: true
allowed-tools: "Read, Write, Glob, Grep, Bash"
metadata:
  routing_heuristics:
    max_toolcalls: 2
    max_duration_minutes: 30
    base_time_per_toolcall: 3
---

# ETA Estimator v2 — Human-Intuitive Expectation Protocol

## Core Responsibility

**NOT just internal estimation. This skill governs HOW the main session talks to users about time.**

The main session MUST:
1. Announce a concrete ETA BEFORE starting any non-trivial task
2. Refresh expectations when the original ETA is exceeded
3. Explain delays with three-part updates (state + reason + new ETA)
4. Summarize if completed-late

## When to Use

Use this skill when:
- User asks "how long will this take?"
- Planning a multi-step task
- About to dispatch a subagent or start a long operation
- Original ETA has been exceeded
- Task has just completed — check if it was on-time or late

## The Four ETA Protocol Phases

### Phase 1: Upfront ETA Announcement (BEFORE starting)

Before `sessions_spawn` or starting any multi-step work:

```python
from openclaw_enhance.skills_catalog import estimate_task_duration, TaskAssessment
from openclaw_enhance.runtime.eta_registry import TaskETARegistry
from datetime import datetime, timedelta

assessment = TaskAssessment(
    description="Add authentication middleware",
    estimated_toolcalls=4,
    requires_parallel=False,
    complexity_score=3,
)

duration = estimate_task_duration(assessment)
minutes = int(duration.total_seconds() / 60)

next_update_minutes = min(3, minutes // 3)
completion_minutes = minutes

print(f"我来处理，预计 {next_update_minutes}-{minutes} 分钟。")
print(f"如果到时还没做完，我会回来说明现在卡在哪、还要多久。")
```

**Key: announce next_update separately from total ETA.** Humans care more about "when will I hear back" than total duration.

### Phase 2: Three-Part Delay Update (when ETA exceeded)

When the original ETA is exceeded but the task is still making progress:

```python
def format_delay_update(state_reason: str, new_remaining_minutes: int) -> str:
    return (
        f"我回来同步一下：这件事还在推进，不是卡死。\n"
        f"比我刚预估的慢，原因是：{state_reason}。\n"
        f"我重新估计还需要 {new_remaining_minutes} 分钟左右。"
    )
```

### Phase 3: Blocked Update (when genuinely stuck)

When there is a specific blocker preventing progress:

```python
def format_blocked_update(blocker_description: str, new_remaining_minutes: int | None = None) -> str:
    eta_part = f"我重新估计还需要 {new_remaining_minutes} 分钟左右。" if new_remaining_minutes else "我无法估计还需要多久。"
    return (
        f"我回来同步一下：现在不是单纯变慢，而是遇到了一个明确阻塞。\n"
        f"阻塞点在：{blocker_description}。\n"
        f"{eta_part}\n"
        f"如果你想换方案，我也可以现在切。"
    )
```

### Phase 4: Completed-Late Summary (when done but exceeded original ETA)

When the task is complete but took longer than estimated:

```python
def format_completed_late(reason: str) -> str:
    return (
        f"好了，实际比我一开始估的时间长一点。\n"
        f"主要原因是：{reason}。\n"
        f"现在我把完整结果给你。"
    )
```

## Delay Reason Taxonomy

Only use these categories when explaining delays (avoids vague explanations):

| Reason Code | Display Text |
|------------|-------------|
| `scope_larger` | 范围比预估大 |
| `subagent_slow` | 子任务返回比预期慢 |
| `retry_path` | 出现错误，正在重试/切路径 |
| `waiting_external` | 等待某个外部步骤完成 |
| `result_pending` | 结果已回到系统，但主流程尚未汇总 |
| `complexity_higher` | 实际复杂度比预估高 |

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

## Usage in Orchestrator Dispatch

When the Orchestrator dispatches workers:

```python
from openclaw_enhance.skills_catalog import estimate_task_duration, TaskAssessment
from openclaw_enhance.runtime.eta_registry import TaskETARegistry

assessment = TaskAssessment(
    description=task_description,
    estimated_toolcalls=estimated_toolcalls,
    requires_parallel=requires_parallel,
)
duration = estimate_task_duration(assessment)
minutes = int(duration.total_seconds() / 60)

registry = TaskETARegistry()
registry.register(
    task_id=task_id,
    child_session_id=child_session_id,
    parent_session=parent_session_id,
    estimated_minutes=minutes,
    first_update_minutes=min(3, minutes // 3),
)
```

## State Model

Tasks managed by this protocol transition through these states:

| State | Meaning |
|-------|---------|
| `on_track` | Within original ETA — no action needed |
| `delayed` | Exceeded ETA but still making progress — use Phase 2 update |
| `blocked` | Specific blocker — use Phase 3 update |
| `stalled` | No progress signal for extended period — suggest manual intervention |
| `completed_late` | Finished but exceeded original ETA — use Phase 4 summary |
| `completed_on_time` | Finished within original ETA — silent completion OK |

## Notes

- Estimates are rough heuristics — always acknowledge uncertainty
- `next_update_minutes` should be shorter than `completion_minutes`
- Never say "等一会儿" — always give concrete time windows
- If the user asks for technical detail, provide it; otherwise keep explanations user-facing
