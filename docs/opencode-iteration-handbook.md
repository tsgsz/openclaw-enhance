# OpenCode Iteration Handbook

> **Purpose**: Durable project memory for future OpenCode sessions. Records current architecture state, permanent progress rules, and required reading paths.
> 
> **When to update**: After architecture changes, new workflow constraints, completed milestones, or new permanent doc locations. Do NOT update for small code-only changes.

## Current Design Status

### Implemented Architecture (Milestone: session-yield-orchestrator-loop)

The repository uses a **bounded, semi-visible orchestration loop** with native `sessions_yield` synchronization and **automated tool-failure recovery**:

**Core Model**: `oe-orchestrator` runs a multi-round loop (Assess → Plan → Dispatch → Yield → Collect → Evaluate) instead of one-shot execution.

**Key Components**:
- **Bounded Loop**: Orchestrator owns loop state (`round_index`, `max_rounds`, `pending_dispatches`). Default `max_rounds=3`, hard cap `5`.
- **Tool-Failure Recovery**: Specialized `oe-tool-recovery` worker diagnoses tool failures and suggests corrections.
- **Recovery-Assisted Retry**: Max one recovery-assisted retry per failed step.
- **Native Synchronization**: `sessions_yield` is the turn-ending primitive for the orchestrator to wait for auto-announced worker results (including recovery results).
- **Semi-Visible Checkpoints**: Only `started`, `meaningful_progress`, `blocked`, and terminal states are reported to the main session.
- **Worker Boundaries**: Workers remain single-round executors; they do NOT use `sessions_yield` or own loop state.
- **Guardrails**: Explicit duplicate-dispatch guards (dedupe keys) and blocker escalation rules.
- **No Polling**: Querying session history or polling for results is strictly forbidden; results arrive via native announce on the next turn.

**Routing Thresholds**:
- Toolcalls: ≤ 2 stays in main, > 2 escalates to orchestrator
- Duration: ≤ 15 min short, 15-30 min medium, > 30 min long
- Parallelism: Required → orchestrator

**Execution Flow**:
```
User Request
    ↓
Main Session + Skills (η estimator, router, timeout-sync)
    ↓ (TOOLCALL > 2 or complex)
sessions_spawn → oe-orchestrator
    ↓
[ Orchestrator Loop (max 5 rounds) ]
    ↓ 1. Plan & Dispatch (sessions_spawn)
    ↓ 2. Yield turn (sessions_yield)
    ↓ 3. Collect results (auto-announce)
    ↓ 4. Evaluate & Checkpoint (semi-visible)
    ↓ (Repeat or Terminate)
    ↓
Results → Orchestrator synthesis → Return to main
```

**Worker Discovery and Routing** (AGENTS.md frontmatter):

Worker routing is now **catalog-driven** from YAML frontmatter in each worker's `AGENTS.md`:
- `oe-searcher`: Research capabilities — cheap model, read-only, web search tools
- `oe-syshelper`: Introspection capabilities — cheap model, strictly read-only (no recovery)
- `oe-tool-recovery`: Recovery capabilities — reasoning model, leaf-node, read-only
- `oe-script_coder`: Code generation capabilities — standard model, repo write, requires tests
- `oe-watchdog`: Monitoring capabilities — narrow authority, runtime state only

**Source of Truth**:
- **Routing metadata**: Worker `AGENTS.md` frontmatter (capabilities, constraints, cost model)
- **Exact tool definitions**: Worker `TOOLS.md` (parameter schemas, examples)
- **Dispatch policy**: `oe-worker-dispatch` skill (least-privilege ranking, hard filters)

The Orchestrator discovers workers by parsing frontmatter at runtime, not from hardcoded lists.

### What This Means for Future Work

**When adding features:**
- Router decisions must stay in skill contracts (`skills/*/SKILL.md`)
- Execution must use native `sessions_spawn` / announce — no custom dispatch runtime
- Worker capabilities must respect workspace `AGENTS.md` boundaries
- Installer changes must maintain symmetric uninstall
- **Mandatory Validation**: Every feature must pass the real-environment validation loop (`validate-feature`) before completion.

**When modifying skills:**
- Update `SKILL.md` file directly — this is the source of truth
- Run `python -m openclaw_enhance.cli render-skill {name}` to verify
- Skills are synced to workspace on install — consider sync implications
- **Validation**: Skill changes require `docs-check` and may require routing validation if behavior changes.

## Source of Truth Map

| Topic | Canonical Doc | What It Contains |
|-------|--------------|------------------|
| **Project intent** | `README.md` | Original goals, multi-task solution, non-invasive constraints (Chinese) |
| **System architecture** | `docs/architecture.md` | Component diagrams, control flow, namespace design |
| **Runtime behavior** | `docs/operations.md` | Orchestrator workflow, routing logic, timeout monitoring |
| **Installation** | `docs/install.md` | Install/uninstall flow, main-skill sync behavior |
| **Troubleshooting** | `docs/troubleshooting.md` | Diagnostics, recovery procedures |
| **Routing boundaries** | `docs/adr/0002-native-subagent-announce.md` | `sessions_spawn` as only transport, skill-vs-runtime separation |
| **Namespace design** | `docs/adr/0001-managed-namespace.md` | Isolation strategy, `oe-` prefix conventions |
| **Watchdog authority** | `docs/adr/0003-watchdog-authority.md` | Narrow authority boundaries, prohibited operations |
| **This handbook** | `docs/opencode-iteration-handbook.md` | Current design state, permanent progress (this file) |
| **Agent entrypoint** | `AGENTS.md` | Required reading order, hard boundaries |
| **Worker roles** | `workspaces/{name}/AGENTS.md` | Per-workspace capabilities and constraints |

## Required Reading Paths

### For Planning a New Feature

1. Read this handbook — Current Design Status (above)
2. Read `docs/architecture.md` — Understand component interactions
3. Read `docs/adr/0002-native-subagent-announce.md` — Transport boundaries
4. Read relevant workspace `AGENTS.md` — If involving workers
5. Read `docs/operations.md` — If changing runtime behavior

### For Implementing Code

1. Read `AGENTS.md` — Hard boundaries and checklist
2. Read this handbook — Current state and invariants
3. Read workspace `AGENTS.md` — If touching worker code
4. Run `python -m openclaw_enhance.cli docs-check` — Validate before committing

### For Workspace-Specific Work

1. Read `workspaces/{name}/AGENTS.md` — Capability boundaries
2. Read `workspaces/{name}/TOOLS.md` — Available tools
3. Read this handbook — How workers fit into overall architecture
4. Respect: Searcher/syshelper read-only or limited, script_coder requires tests, watchdog narrow authority

### For Understanding Permanent Progress

1. Read **Permanent Progress Record** (below)
2. Read **Session State vs Permanent Memory** (below)
3. Check latest milestone in this handbook
4. Consult `.sisyphus/plans/*.md` only for execution detail — not for architectural truth

## Known Invariants / No-Go Areas

### Architecture Invariants (Do Not Violate)

1. **Native execution only**: `sessions_spawn` / announce is the ONLY subagent mechanism
   - Never create wrapper functions like dispatch helper methods over native primitives
   - Skills teach when/why to spawn, not how

2. **File-backed skills**: `skills/*/SKILL.md` is source of truth
   - Never duplicate skill content in Python strings
   - Use `render_skill_contract()` to read at runtime

3. **Symmetric lifecycle**: Install and uninstall must mirror each other
   - Every installed component must have removal logic
   - Manifest tracks enhancement-owned components

4. **Non-invasive to OpenClaw core**:
   - No edits to OpenClaw source
   - No runtime modifications to main's AGENTS.md/TOOLS.md
   - CLI-first preference for all operations

### Worker Role Boundaries (Do Not Cross)

- **oe-searcher**: Read-only file access, sandbox for temp files, NO agent spawning
- **oe-syshelper**: Strictly read-only, NO file modifications, NO agent spawning, NO recovery
- **oe-tool-recovery**: Leaf-node recovery specialist, read-only, NO file modifications, NO agent spawning
- **oe-script_coder**: Full file access, can spawn searcher only for research, requires tests
- **oe-watchdog**: Runtime state only, NO project file modifications, NO git, NO tests, reports to orchestrator

### Documentation Invariants

- `AGENTS.md` stays short and operational
- This handbook stays focused on state/navigation, not deep technical docs
- Existing `docs/*.md` remain canonical for their topics
- `.sisyphus/*` is session state, not permanent memory

## Permanent Progress Record

### Completed Milestones

**session-yield-orchestrator-loop** — COMPLETE
- Date: 2026-03-13
- Scope: Redesigned orchestrator as a bounded multi-round loop using `sessions_yield`.
- Deliverables:
  - Round-based orchestrator workflow in `oe-orchestrator/AGENTS.md`.
  - Iterative dispatch contract with `sessions_yield` in `oe-worker-dispatch/SKILL.md`.
  - Semi-visible checkpoint policy (milestones only).
  - Bounded loop controls (max_rounds, dedupe, blocker escalation).
  - Native transport docs updated for `sessions_yield` semantics.
- Success criteria: Integration tests pass, no polling in contracts, docs aligned.

**tool-failure-recovery-worker** — COMPLETE
- Date: 2026-03-14
- Scope: Added specialized recovery worker for tool-call failures.
- Deliverables:
  - `oe-tool-recovery` worker with reasoning-capable model.
  - Recovery flow in orchestrator (detect → dispatch → yield → retry).
  - Max one recovery-assisted retry per failed step.
  - Clear boundary between `oe-syshelper` (read-only) and `oe-tool-recovery` (recovery).
- Success criteria: Recovery flow documented, worker boundaries enforced, docs-check passes.

**router-skill-first-alignment** — COMPLETE
- Date: 2026-03-13
- Scope: Refactored routing from Python API to skill-first model
- Deliverables:
  - File-backed skill loading from `skills/*/SKILL.md`
  - Removal of Python router runtime (router classes and assessment types)
  - Main-skill sync during install to active workspace
  - Symmetric uninstall with manifest tracking
  - `docs-check` validation for `sessions_spawn` and banned terms
  - Documentation alignment across all docs
- Success criteria: 77 tests passing, no router API in source, all docs reference native execution

**repo-wide-real-env-backfill** — COMPLETE
- Date: 2026-03-14
- Scope: Executed canonical backfill scenarios to establish a baseline of real-environment validation reports.
- Deliverables:
  - Six canonical PASS reports in `docs/reports/`:
    - `backfill-core-install` (install-lifecycle)
    - `backfill-dev-install` (install-lifecycle)
    - `backfill-cli-surface` (cli-surface)
    - `backfill-routing-yield` (workspace-routing)
    - `backfill-recovery-worker` (workspace-routing)
    - `backfill-watchdog-reminder` (runtime-watchdog)
  - Report inventory recorded in durable state.
  - Validation of all core enhancement primitives in a clean environment.
- Success criteria: All six canonical slugs conclude PASS, `docs-check` passes.

**real-environment-testing-loop** — COMPLETE
- Date: 2026-03-14
- Scope: Implemented mandatory real-environment validation loop for all features.
- Deliverables:
  - `validate-feature` CLI command for automated bundle execution.
  - Feature-class matrix in `docs/testing-playbook.md`.
  - Mandatory report generation in `docs/reports/`.
  - Post-development checklist integration in `AGENTS.md`.
- Success criteria: CLI command functional, all docs aligned on mandatory gate, reports generated.

### Current Durable Status

The repository is in **stable maintenance mode** for the bounded-loop orchestration architecture:
- Core orchestration: Bounded multi-round loop + `sessions_yield`.
- Core routing: skill contracts + native `sessions_spawn`.
- Installer: syncs main skills, symmetric uninstall.
- Validation: `docs-check` enforces alignment.
- Workers: 5 specialized agents with strict boundaries.
- No planned breaking changes to architecture.

### Where to Record Future Progress

**Record in this handbook:**
- Completed milestones that change future work
- Architecture changes (routing, transport, worker model)
- New workflow constraints or validation rules
- New permanent documentation locations

**Do NOT record here:**
- Session-level execution state (use `.sisyphus/*`)
- Small code-only bugfixes
- Test additions with no architecture impact
- Documentation typo fixes

## Session State vs Permanent Memory

### What `.sisyphus/*` Contains (Session-Only)

- **`.sisyphus/plans/*.md`** — Active and completed execution plans with task breakdowns
- **`.sisyphus/boulder.json`** — Pointer to current active plan and session tracking
- **`.sisyphus/evidence/*.txt`** — Task execution artifacts and QA scenario outputs

**These are execution artifacts.** They record HOW work was done in a session. They may be consulted for detail but are **NOT** canonical architectural truth.

### What This Handbook Contains (Permanent)

- Current design status at milestone level
- Source-of-truth map for the repo
- Invariants and no-go areas
- Progress record of completed milestones
- Update protocol (this section)

**This is durable project memory.** It survives sessions and tells future agents where the project stands.

## Update Protocol

### When You MUST Update This Handbook

Update after completing work that changes:
- [ ] **Architecture**: Routing model, transport mechanism, worker topology
- [ ] **Workflow**: New constraints on how agents must operate
- [ ] **Milestones**: Completed milestones that unlock/change future work
- [ ] **Documentation**: New permanent doc locations or source-of-truth changes

### When You MUST NOT Update This Handbook

Do NOT update for:
- [ ] Code-only bugfixes with no architecture impact
- [ ] Adding tests to existing functionality
- [ ] Documentation typo fixes
- [ ] Refactoring with no behavioral change
- [ ] Session execution updates (those go to `.sisyphus/*`)

### How to Update

1. Edit `docs/opencode-iteration-handbook.md` directly
2. Update relevant section (Current Design Status, Progress Record, etc.)
3. Run `python -m openclaw_enhance.cli docs-check` to validate
4. Commit with message: `docs(handbook): update [what changed]`
5. Ensure `AGENTS.md` still correctly links to handbook sections

## Quick Reference

**Validation:**
```bash
python -m openclaw_enhance.cli docs-check
pytest tests/unit/test_docs_examples.py -q
```

**Skill rendering:**
```bash
python -m openclaw_enhance.cli render-skill oe-toolcall-router
python -m openclaw_enhance.cli render-workspace oe-orchestrator
```

**Install/Uninstall:**
```bash
python -m openclaw_enhance.cli install --dry-run
python -m openclaw_enhance.cli status
python -m openclaw_enhance.cli uninstall
```

---

**Version**: 1.3.1  
**Last Updated**: 2026-03-15  
**Milestone**: real-environment-testing-loop COMPLETE
