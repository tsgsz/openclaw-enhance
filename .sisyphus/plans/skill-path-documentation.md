# Skill Path Documentation Fix

## TL;DR
> **Summary**: Add explicit skill path resolution rules to orchestrator's AGENTS.md to prevent AI from constructing wrong paths
> **Deliverables**: Updated AGENTS.md with clear path documentation
> **Effort**: Quick
> **Parallel**: NO
> **Critical Path**: Single task

## Context
### Original Request
Fix the remaining task from previous session: document skill path resolution rules so orchestrator AI doesn't construct wrong paths like `~/.openclaw/openclaw-enhance/skills/oe-project-registry/SKILL.md` instead of the correct `~/.openclaw/openclaw-enhance/workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md`.

### Interview Summary
- Symlinks were created as temporary workaround
- Need permanent fix via documentation
- Orchestrator's AGENTS.md lists skills but doesn't specify where they're located
- AI tries multiple paths when uncertain about conventions

### Metis Review
N/A - trivial documentation task

## Work Objectives
### Core Objective
Add skill path resolution documentation to orchestrator's AGENTS.md

### Deliverables
- Updated `workspaces/oe-orchestrator/AGENTS.md` with skill path section

### Definition of Done
- AGENTS.md explicitly states skill path format
- Documentation warns against wrong path pattern
- File can be read successfully

### Must Have
- Clear path format with example
- Explicit warning about wrong path

### Must NOT Have
- Verbose explanations
- Changes to other files

## Verification Strategy
- Test decision: none (documentation only)
- QA policy: Read file to verify content
- Evidence: N/A

## Execution Strategy
### Parallel Execution Waves
Wave 1: Single documentation task

### Dependency Matrix
None - single task

### Agent Dispatch Summary
Wave 1: 1 task (quick category)

## TODOs

- [ ] 1. Add Skill Path Resolution Section

  **What to do**: 
  - Add new subsection under "## Skills" header in orchestrator's AGENTS.md
  - Include clear path format: `~/.openclaw/openclaw-enhance/workspaces/oe-orchestrator/skills/{skill-name}/SKILL.md`
  - Add explicit warning: "Never use `~/.openclaw/openclaw-enhance/skills/{skill-name}/` — that path does not exist"
  - Keep existing skill list intact

  **Must NOT do**: 
  - Change skill descriptions
  - Modify other sections
  - Add verbose explanations

  **Recommended Agent Profile**:
  - Category: `quick` — Simple documentation edit
  - Skills: [] — No special skills needed
  - Omitted: All — straightforward file edit

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [] | Blocked By: []

  **References**:
  - File: `workspaces/oe-orchestrator/AGENTS.md:59-67` — Skills section to update
  - Pattern: Add subsection with path format and warning before skill list

  **Acceptance Criteria**:
  - [ ] AGENTS.md contains "Skill Path Resolution" subsection
  - [ ] Path format explicitly documented with example
  - [ ] Warning about wrong path included
  - [ ] Existing skill list preserved

  **QA Scenarios**:
  ```
  Scenario: Verify documentation added
    Tool: Bash
    Steps: cat workspaces/oe-orchestrator/AGENTS.md | grep -A 5 "Skill Path Resolution"
    Expected: Section exists with path format and warning
    Evidence: N/A (documentation only)
  ```

  **Commit**: YES | Message: `docs(orchestrator): add skill path resolution rules` | Files: [workspaces/oe-orchestrator/AGENTS.md]

## Final Verification Wave
N/A - single trivial task, no verification wave needed

## Commit Strategy
Single commit after documentation update

## Success Criteria
- Orchestrator's AGENTS.md clearly documents skill path format
- Future AI sessions won't construct wrong paths
