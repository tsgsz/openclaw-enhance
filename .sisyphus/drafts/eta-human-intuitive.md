# Draft: Human-Intuitive ETA Behavior

## Requirements (confirmed)
- "人做事情会在做事情之前说大概要多久"
- "如果到时间没做完会跑过来说现在怎么了, 为啥没搞完, 还需要多久"
- Current system should stop saying vague "等一会儿" and instead provide concrete ETA + refresh behavior
- Subagent completion should not be misreported as timeout when work is still progressing or already finished

## Technical Decisions
- Redesign ETA as a user-facing conversation contract, not only runtime metadata
- Main session owns expectation-setting language; watchdog/orchestrator provide evidence and refresh triggers
- Timeout must be split into distinct states: on-track, extended, suspicious, stalled, completed-late
- Refresh policy: restrained/proactive only at start, delay, blocker, and completed-late checkpoints
- Delay explanation style: concise and user-facing; technical detail is available only when the user asks

## Research Findings
- `skills/oe-eta-estimator/SKILL.md`: estimation exists but is heuristic-only and not automatically surfaced to user
- `hooks/oe-subagent-spawn-enrich/handler.ts`: hook adds `eta_bucket` metadata only; no user-visible duration text
- `extensions/openclaw-enhance-runtime/src/runtime-bridge.ts`: tracks active tasks in memory; no conversational ETA refresh output
- `workspaces/oe-watchdog/skills/oe-timeout-alarm/SKILL.md`: timeout logic exists but is oriented around detection/logging, not human explanation

## Open Questions
- None blocking

## Scope Boundaries
- INCLUDE: upfront ETA wording, delay update wording, remaining-time refresh, timeout state model, late-completion handling
- EXCLUDE: unrelated routing/publishing changes, non-ETA UX improvements
