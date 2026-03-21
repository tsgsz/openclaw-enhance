# OpenCode Agent Instructions

## Mission

`openclaw-enhance` augments OpenClaw with multi-task handling and operational visibility **without modifying OpenClaw core source code**. Uses OpenClaw's native extension points: skills, hooks, extensions, and agent workspaces.

## Non-Invasive Boundaries (Hard Rules)

1. **No OpenClaw source code edits** — all capabilities via plugins, hooks, skills, agents
2. **No runtime file modifications** — never modify main's `AGENTS.md`, `TOOLS.md`, or config at runtime
3. **CLI-first operations** — prefer OpenClaw CLI over direct config edits
4. **Minimal workflow intrusion** — provide tools without changing OpenClaw's core logic

## Required Reading Order

**Before ANY design or development work:**

1. **Read this file** (`AGENTS.md`) — you're here
2. **Read the handbook** (`docs/opencode-iteration-handbook.md`) — current architecture state and permanent progress
3. **Read relevant workspace `AGENTS.md`** — for workspace-specific work (see hierarchy below)
4. **Read domain-specific docs** — architecture, operations, install as needed

**Never start coding before completing steps 1-2.**

## Source of Truth Map

| Topic | Canonical Document |
|-------|-------------------|
| Project intent | `README.md` (Chinese, original) |
| Current architecture | `docs/architecture.md` |
| Runtime behavior | `docs/operations.md` |
| Installation/uninstall | `docs/install.md` |
| Routing/transport boundaries | `docs/adr/0002-native-subagent-announce.md` |
| Watchdog authority | `docs/adr/0003-watchdog-authority.md` |
| Current design status | `docs/opencode-iteration-handbook.md` |
| Workspace-specific rules | `workspaces/{name}/AGENTS.md` |
| Worker routing metadata | AGENTS.md frontmatter in each workspace |
| Worker tool definitions | `workspaces/{name}/TOOLS.md` |
| System capability playbook | `PLAYBOOK.md` (安装时部署到 `~/.openclaw/openclaw-enhance/PLAYBOOK.md`) |
| Project registry state | `project-registry.json` (at `~/.openclaw/openclaw-enhance/project-registry.json`) |

## Session State vs Permanent Memory

**`.sisyphus/*` is session execution state ONLY** — not permanent architectural truth:
- `.sisyphus/plans/*.md` — active/completed plan tracking
- `.sisyphus/boulder.json` — current session pointer
- `.sisyphus/evidence/*` — task execution artifacts

**Permanent project memory lives in:**
- `docs/opencode-iteration-handbook.md` — durable design state and progress
- `docs/adr/*.md` — architectural decision records
- `docs/*.md` — canonical system documentation

## Workspace AGENTS.md Hierarchy

**Rule**: Workspace-specific work follows nearest `AGENTS.md`:
- `workspaces/oe-orchestrator/AGENTS.md` — full-capability planning + dispatch
- `workspaces/oe-searcher/AGENTS.md` — read-only research, web search
- `workspaces/oe-syshelper/AGENTS.md` — read-only introspection
- `workspaces/oe-tool-recovery/AGENTS.md` — tool failure recovery specialist
- `workspaces/oe-script_coder/AGENTS.md` — code development with tests
- `workspaces/oe-watchdog/AGENTS.md` — session monitoring, narrow authority

## Pre-Design Checklist

Before proposing any design change:
- [ ] Read handbook current design status section
- [ ] Read relevant ADRs for boundary constraints
- [ ] Check if change affects routing (must respect `sessions_spawn` native execution)
- [ ] Check if change affects worker boundaries (must respect workspace `AGENTS.md`)

## Pre-Development Checklist

Before implementing any code:
- [ ] Confirm design follows skill-first routing model
- [ ] Confirm design respects native `sessions_spawn` / announce execution
- [ ] Verify no runtime file modifications to main OpenClaw
- [ ] Check workspace-specific `AGENTS.md` if touching worker code
- [ ] Run `python -m openclaw_enhance.cli docs-check` to validate doc alignment

## Current Architecture Milestone

**Completed**: `real-environment-testing-loop` — Mandatory real-environment validation and report generation is the merge gate for all features.

**See handbook for full current state, orchestration loop rules, and invariants.**

## Post-Development Checklist (MANDATORY)

After completing any feature development:
- [ ] Unit tests pass
- [ ] Integration tests pass
  - [ ] **Real-environment validation loop completed**
  - [ ] Feature class identified (see `docs/testing-playbook.md`)
  - [ ] `python -m openclaw_enhance.cli validate-feature --feature-class <class> --report-slug <slug>` passes
  - [ ] Validation report saved to `docs/reports/`
- [ ] `python -m openclaw_enhance.cli docs-check` passes
- [ ] **PLAYBOOK.md 已更新**（如果本次变更影响了以下任何内容）：
  - Agent 新增/删除/职责变更
  - Hook 新增/删除/行为变更
  - Skill 新增/删除/行为变更
  - Extension 变更
  - openclaw.json 配置修改项变更
  - 安装产物（新增/删除文件或目录）
  - 工具限制（Tool Gate）规则变更
  - Watchdog/监控机制变更
  - CLI 命令新增/删除

**Critical Rule**: Features cannot be merged without a successful real-environment validation report in `docs/reports/`. Unit/integration tests verify code correctness, but only real-environment testing verifies actual functionality in the OpenClaw environment.

**Critical Rule**: `PLAYBOOK.md` 是系统能力的权威清单，安装时会部署到 `~/.openclaw/openclaw-enhance/PLAYBOOK.md` 供 AI 和人类查阅。每次 commit 前必须检查是否需要同步更新。

See `docs/testing-playbook.md` for the feature-class matrix and detailed validation procedures.
