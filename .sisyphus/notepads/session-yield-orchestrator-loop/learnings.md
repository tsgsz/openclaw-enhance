### Documentation Update: Native Primitives and Bounded Loop

- Updated ADR 0002, Architecture, and Operations docs to include `sessions_yield`.
- Defined `sessions_yield` as an orchestrator-only turn-yield synchronization primitive.
- Preserved `sessions_spawn`/announce as the sole worker execution path.
- Replaced linear orchestrator diagrams with a bounded loop view (Dispatch → Yield → Collect → Evaluate → Re-dispatch).
- Clarified that `sessions_yield` is NOT for result transport and workers do not use it.
- Ensured consistency with `workspaces/oe-orchestrator/AGENTS.md` bounded loop workflow.
# session-yield-orchestrator-loop Learnings

- Updated durable project memory in `docs/opencode-iteration-handbook.md` to reflect the new orchestration model.
- The handbook now records the `session-yield-orchestrator-loop` milestone and its durable rules (bounded loop, native synchronization, semi-visible checkpoints).
- `AGENTS.md` remains a concise entrypoint, pointing to the handbook for detailed orchestration guidance.
- Maintained `AGENTS.md` line count well under the 220-line limit (currently 80 lines).
- Verified documentation alignment using `docs-check` CLI.

## Test Contract Patterns for Bounded Loop Controls (2026-03-13)

### Test Design Approach

When adding contract tests for documentation verification:

1. **Use file content fixtures** - Load AGENTS.md and SKILL.md once per test class to avoid repeated I/O
2. **Test positive presence and negative absence** - Both verify terms exist AND verify anti-patterns don't exist
3. **Follow existing test patterns** - Use class-per-concern, parametrize for lists, descriptive test names

### Bounded Loop Contract Tests Added

#### In `test_orchestrator_dispatch_contract.py`:
- `TestBoundedLoopContract` class with 12 test methods covering:
  - `sessions_yield` reference in orchestrator docs
  - Round-state phases (Assess, PlanRound, DispatchRound, YieldForResults, CollectResults, EvaluateProgress)
  - `max_rounds` terminology with default (3) and hard cap (5)
  - Checkpoint types (`started`, `meaningful_progress`, `blocked`, `terminal`)
  - Duplicate-dispatch guard terms (`dedupe_keys`, duplicate dispatch)
  - NO `sessions_history` polling guidance
  - Dispatch identity and deduplication
  - Failure classification categories (Retriable, Reroutable, Escalated)

#### In `test_orchestrator_workspace.py`:
- `TestCheckpointBehaviorDocumentation` class with 8 test methods covering:
  - Semi-visible checkpoint model documentation
  - `meaningful_progress` checkpoint (conditional reporting)
  - `blocked` checkpoint (escalation to main)
  - `terminal` checkpoint states
  - NO polling patterns with `sessions_history`
  - Routine round boundaries hidden from main

### Key Findings

1. **AGENTS.md structure** clearly separates:
   - Round lifecycle diagram showing state transitions
   - Loop state table with explicit field documentation
   - Loop controls section with mandatory limits
   - Checkpoint visibility section with "Main sees/does NOT see" distinction

2. **SKILL.md patterns** for dispatch:
   - "Iterative Round-Based Dispatch (v2)" section replaces legacy sequential patterns
   - Explicit "Do not poll" guidance with reference to auto-announce
   - Dispatch identity with dedupe key prevents duplicate work

3. **Pre-existing test debt** identified:
   - `test_describes_workflow` expected "Standard Task Flow" but AGENTS.md uses "Bounded Round-Based Orchestration Loop"
   - Fixed to reflect current documentation

### Test Maintenance Tips

- Documentation contract tests are fragile - they break when docs change
- This is intentional - changing docs should require explicit test updates
- Keep assertions flexible (e.g., `in` checks) but specific enough to catch real drift
- Separate "presence" tests from "structure" tests for easier maintenance

## Final Drift Review Results (2026-03-13)

### Acceptance Criteria Verification

#### Criterion 1: Pytest Suite Passes
```bash
pytest tests/integration/test_orchestrator_dispatch_contract.py \
       tests/unit/test_orchestrator_workspace.py \
       tests/unit/test_docs_examples.py -q
```
**Result**: ✅ 122 passed in 1.12s

#### Criterion 2: Docs-Check Passes
```bash
python -m openclaw_enhance.cli docs-check
```
**Result**: ✅ Docs check passed

#### Criterion 3: Bounded-Loop Model Contract Verification

**Required elements - ALL PRESENT**:
- ✅ `sessions_yield` - Documented as orchestrator-only turn-boundary primitive
- ✅ `max_rounds` - Default 3, hard cap 5 documented across all docs
- ✅ `meaningful_progress` - Checkpoint type documented (semi-visible model)
- ✅ `blocked` - Checkpoint type documented for escalation to main

**Prohibited elements - ALL ABSENT**:
- ✅ Worker-level yield - Docs explicitly state workers are "single-round executors" that "do NOT use yield"
- ✅ `sessions_history` polling - Handbook explicitly forbids: "`sessions_history` polling is strictly forbidden"

### Stale Wording Review

#### "One-shot" terminology
**Finding**: Found 2 references, both appropriate:
1. `docs/opencode-iteration-handbook.md`: "multi-round loop ... instead of one-shot execution" - Correctly contrasts new vs old model
2. `workspaces/oe-orchestrator/AGENTS.md`: "replaces the previous one-shot fan-out/fan-in model" - Correct historical context

**Conclusion**: No stale wording - references are appropriate historical documentation.

### Consistency Check

| Document | Bounded Loop | sessions_yield | max_rounds | Checkpoint Visibility | Worker Single-Round |
|----------|-------------|----------------|------------|----------------------|---------------------|
| AGENTS.md | ✅ | ✅ | ✅ | ✅ | ✅ |
| SKILL.md | ✅ | ✅ | ✅ | ✅ | ✅ |
| ADR 0002 | ✅ | ✅ | N/A | N/A | ✅ |
| Architecture | ✅ | ✅ | ✅ | N/A | ✅ |
| Operations | ✅ | ✅ | N/A | N/A | N/A |
| Handbook | ✅ | ✅ | ✅ | ✅ | ✅ |

**Status**: All documents aligned on bounded-loop model.

### Key Documentation Patterns

1. **Orchestrator uses yield, workers don't**:
   - AGENTS.md: "`sessions_yield` is used ONLY by the orchestrator"
   - ADR 0002: "Workers remain single-round executors and never use yield"
   - Handbook: "Workers remain single-round executors; they do NOT use `sessions_yield`"

2. **No polling guidance**:
   - SKILL.md: "Do not poll or query session state while waiting"
   - Handbook: "`sessions_history` polling is strictly forbidden"

3. **Semi-visible checkpoints**:
   - AGENTS.md: "Main sees: started, meaningful_progress, blocked, terminal"
   - AGENTS.md: "Main does NOT see: Individual worker results, Routine round boundaries"

### Conclusion

All contracts, docs, and tests are **consistent and aligned** with the bounded-loop model. No drift detected. No fixes required.
