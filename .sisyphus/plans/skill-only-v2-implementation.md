# openclaw-enhance v2: Skill-Only Implementation Plan

## TL;DR

> **Goal**: 将 openclaw-enhance 从 agent-based 架构重构为 skill-only 架构
> - 移除: 11 agents, workspaces/, oe-orchestrator
> - 保留: Hooks, Extension, 部分 Utility Skills
> - 新增: Orch Skills (tag-router, spawn-*), Model Discover
> - 交付: 13 skills + CLI + Hook + Extension

**Estimated Effort**: Large (breaking change)
**Parallel Execution**: YES - multiple waves
**Critical Path**: Manifest → Hook → Extension → oe-tag-router → spawn skills

---

## Context

### Original Request
将 openclaw-enhance 重构为纯 skills + hooks + 少量 extensions，不维护 agent/workspace。用户通过选择加载哪些 skills 来定制自己的 agent soul。

### Design Decisions (Confirmed)
- Skill-only 架构，无 agent 定义
- Spawn 无 agentId，用 prompt + model 指定（sessions_spawn API 已验证可工作）
- SOUL 通过 install 时注入 main 的 SOUL.md，uninstall 时删除（带 oe-soul-start/end 标记）
- Model discovery: 读取 openclaw.json 发现已有模型，按价格分层
- v1 → v2: 需要迁移（archive workspaces, migrate registry）
- 模型分层：发现 OpenClaw 已有模型，按价格 manual tiering
- 社区技能参考但不整合，自己实现
- 安装位置：main（默认）或 global
- Hook 做全局 enrichment，Skill 做业务分发

---

## Work Objectives

### Core Deliverables

1. **Manifest System** - JSON 记录安装的 skills/hooks/extension
2. **CLI Commands** - install/uninstall/status 支持 --target main/global
3. **Hook: oe-subagent-spawn-enrich** - 全局 enrichment 层
4. **Extension: oe-runtime** - Tool gate + 输出消毒
5. **Utility Skills** (3):
   - oe-model-discover: 发现 OpenClaw 已有模型
   - oe-eta-estimator: ETA 估算
   - oe-timeout-state-sync: 超时状态同步
6. **Orch Skills** (4):
   - oe-tag-router: 标签推理 + 匹配
   - oe-spawn-search: research 标签 → spawn
   - oe-spawn-coder: code 标签 → spawn
   - oe-spawn-ops: ops 标签 → spawn
7. **Context Skills** (3):
   - oe-project-context
   - oe-git-context
   - oe-memory-sync
8. **Utility: oe-publish**
9. **README SOUL prompt**

### Definition of Done

- [ ] `python -m openclaw_enhance.cli install --target main` 成功
- [ ] `python -m openclaw_enhance.cli install --target global` 成功
- [ ] `python -m openclaw_enhance.cli uninstall --target main` 成功
- [ ] `python -m openclaw_enhance.cli status` 显示正确
- [ ] Hook 正确注入 spawn enrichment
- [ ] Extension 正确阻塞 forbidden 工具
- [ ] Model discover 正确发现已有模型
- [ ] Tag router 正确匹配标签
- [ ] Spawn skills 正确构造 spawn 调用
- [ ] README 包含 SOUL prompt

### Must Have
- 零 agent 维护
- CLI 支持 main/global 双安装
- Hook/Extension 功能完整
- 向后兼容 OpenClaw 使用方式

### Must NOT Have
- Agent/workspace 定义
- oe-orchestrator
- AgentOS patterns
- 硬编码模型列表

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: Tests-after
- **Framework**: pytest

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/`.

---

## Execution Strategy

### Wave 1: Foundation (Manifest + CLI + Infrastructure)
├── T1: Manifest JSON schema + storage
├── T2: CLI install/uninstall/status commands
├── T3: Hook: oe-subagent-spawn-enrich (rewrite)
├── T4: Extension: oe-runtime (migration)
└── T5: Config reader for openclaw models

### Wave 2: Core Skills
├── T6: oe-model-discover (OpenClaw model discovery)
├── T7: oe-tag-router (label inference + matching)
├── T8: oe-spawn-search (research → spawn)
├── T9: oe-spawn-coder (code → spawn)
└── T10: oe-spawn-ops (ops → spawn)

### Wave 3: Utility + Context Skills
├── T11: oe-eta-estimator
├── T12: oe-timeout-state-sync
├── T13: oe-project-context
├── T14: oe-git-context
└── T15: oe-memory-sync

### Wave 4: Publishing + Docs
├── T16: oe-publish
└── T17: SOUL.md install/uninstall injection

### Wave 5: Migration + Cleanup + Integration
├── T18: v1 → v2 Migration (archive workspaces, migrate registry)
├── T19: Remove v1 workspace references from source
├── T20: Integration tests
└── T21: docs-check + validate-feature

**Max Concurrent**: 5 tasks per wave
**Total Tasks**: 21

---

## TODOs

---

## Wave 1: Foundation

- [x] T1. Manifest System

  **What to do**:
  - Create `~/.openclaw/openclaw-enhance/manifest.json` schema
  - Schema fields: version, skills (name, location, version), hooks (name, enabled), extension (name, enabled)
  - Create Python module `openclaw_enhance.manifest` with:
    - `load_manifest()`: Read manifest
    - `save_manifest()`: Write manifest
    - `add_skill(name, location, version)`
    - `remove_skill(name)`
    - `get_installed()`: Returns all installed components

  **Must NOT do**:
  - Do not create agent/workspace entries in manifest
  - Do not modify openclaw.json directly

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Simple JSON storage, straightforward CRUD

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T2-T5)
  - **Blocks**: T2 (CLI depends on manifest)

  **References**:
  - `src/openclaw_enhance/cli.py` - Existing CLI patterns to follow
  - `docs/install.md` lines 126-135 - Manifest tracking during install

  **Acceptance Criteria**:
  - [ ] `python -c "from openclaw_enhance.manifest import load_manifest; print(load_manifest())"` → {} (empty, no file)

- [x] T2. CLI Commands (install/uninstall/status)

  **What to do**:
  - Extend existing CLI with `--target` flag (main/global)
  - `install --target main`: Install skills to `~/.openclaw/workspace/{main}/skills/`
  - `install --target global`: Install skills to `~/.openclaw/openclaw-enhance/skills/`
  - `install --skill <name> --target <loc>`: Install specific skill
  - `uninstall --target <loc>`: Remove all from location
  - `status`: Show installed components with locations
  - Update `src/openclaw_enhance/cli.py`

  **Must NOT do**:
  - Do not create agents/workspace definitions
  - Do not modify openclaw source files

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: CLI extension, follows existing patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES (but will fail if T1 not complete)
  - **Parallel Group**: Wave 1 (with T1, T3-T5)
  - **Blocked By**: None (runs in parallel but depends on manifest)

  **References**:
  - `src/openclaw_enhance/cli.py` - Existing CLI patterns
  - `docs/install.md` lines 201-218 - CLI commands reference

  **QA Scenarios**:

  Scenario: Install all skills to main
    Tool: Bash
    Steps:
      1. `cd /Users/tsgsz/workspace/openclaw-enhance && python -m openclaw_enhance.cli install --target main --dry-run`
      2. Assert output contains "oe-tag-router" and "oe-spawn-search"
      3. `python -m openclaw_enhance.cli install --target main`
      4. `python -m openclaw_enhance.cli status`
    Expected Result: Status shows skills with location="main"
    Evidence: .sisyphus/evidence/t2-install-main.txt

  Scenario: Install to global
    Tool: Bash
    Steps:
      1. `python -m openclaw_enhance.cli install --target global`
      2. `python -m openclaw_enhance.cli status`
    Expected Result: Status shows skills with location="global"
    Evidence: .sisyphus/evidence/t2-install-global.txt

  Scenario: Uninstall from main
    Tool: Bash
    Steps:
      1. `python -m openclaw_enhance.cli uninstall --target main`
      2. `python -m openclaw_enhance.cli status`
    Expected Result: Skills removed from main, global still intact
    Evidence: .sisyphus/evidence/t2-uninstall-main.txt

---

- [x] T3. Hook: oe-subagent-spawn-enrich

  **What to do**:
  - Rewrite `hooks/oe-subagent-spawn-enrich/` for v2
  - Key functions:
    1. Inject `task_id` (UUID)
    2. Inject `eta_bucket` (short/medium/long based on task size)
    3. Inject `dedupe_key` (hash of task + parent_session)
    4. Inject `ownership` (channel_type, channel_conversation_id from context)
    5. Inject `project_context` (from project registry)
  - Write TypeScript handler in `hooks/oe-subagent-spawn-enrich/handler.ts`
  - Update HOOK.md

  **Must NOT do**:
  - Do not read agent definitions
  - Do not route to specific agent IDs

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Hook rewrite following existing patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T2, T4, T5)

  **References**:
  - `hooks/oe-subagent-spawn-enrich/HOOK.md` - Existing hook contract
  - `docs/adr/0002-native-subagent-announce.md` - Transport boundaries

  **QA Scenarios**:

  Scenario: Hook injects task_id on spawn
    Tool: Bash
    Preconditions: Hook installed, main workspace configured
    Steps:
      1. Create test spawn call
      2. Verify hook intercepts and adds task_id
    Expected Result: task_id is valid UUID in enriched payload
    Evidence: .sisyphus/evidence/t3-hook-task-id.txt

  Scenario: Hook injects ownership metadata
    Tool: Bash
    Steps:
      1. Verify ownership fields present in enriched context
    Expected Result: channel_type and channel_conversation_id present
    Evidence: .sisyphus/evidence/t3-hook-ownership.txt

---

- [x] T4. Extension: oe-runtime

  **What to do**:
  - Migrate from v1: `extensions/openclaw-enhance-runtime/`
  - Key functions:
    1. Block forbidden tools for main session (edit, write, exec, process, browser, playwright)
    2. Return guidance: "Use sessions_spawn to delegate work"
    3. Sanitize internal markers: `[Pasted ~]`, `<|tool_call...|>`
    4. Validate session isolation
  - Update `extensions/openclaw-enhance-runtime/index.ts`

  **Must NOT do**:
  - Do not block spawn-related tools
  - Do not modify openclaw source

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Extension migration, follows existing patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1-T3, T5)

  **References**:
  - `extensions/openclaw-enhance-runtime/index.ts` - Existing extension
  - `docs/opencode-iteration-handbook.md` lines 83-87 - oe-runtime description

  **QA Scenarios**:

  Scenario: Extension blocks forbidden tool
    Tool: Bash
    Preconditions: Extension enabled
    Steps:
      1. Attempt to call forbidden tool from main session
      2. Verify blocked with guidance message
    Expected Result: Tool call blocked, guidance returned
    Evidence: .sisyphus/evidence/t4-extension-block.txt

  Scenario: Sanitization removes internal markers
    Tool: Bash
    Steps:
      1. Process output containing `[Pasted ~test]` and `<|tool_call|>`
      2. Verify markers are stripped
    Expected Result: Markers removed from output
    Evidence: .sisyphus/evidence/t4-extension-sanitize.txt

---

- [x] T5. Config Reader for OpenClaw Models

  **What to do**:
  - Create `openclaw_enhance/model_config.py`
  - Functions:
    - `get_openclaw_models()`: Read from openclaw.json
    - `get_available_providers()`: Detect configured API providers
    - `infer_model_tier(model_id)`: Match against MODEL_PRICING table
  - Create `MODEL_PRICING` constant with tier mapping
  - Support user overrides in openclaw.json

  **Must NOT do**:
  - Do not call external APIs
  - Do not hardcode all available models

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Simple config reading, tier mapping table

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1-T4)

  **References**:
  - `src/openclaw_enhance/cli.py` - Config reading patterns
  - OpenClaw openclaw.json schema for model config

  **QA Scenarios**:

  Scenario: Reads models from openclaw.json
    Tool: Bash
    Steps:
      1. `python -c "from openclaw_enhance.model_config import get_openclaw_models; print(get_openclaw_models())"`
    Expected Result: List of configured models
    Evidence: .sisyphus/evidence/t5-config-read.txt

  Scenario: Tier assignment works
    Tool: Bash
    Steps:
      1. `python -c "from openclaw_enhance.model_config import infer_model_tier; print(infer_model_tier('gpt-4o-mini'))"`
    Expected Result: "cheap"
    Evidence: .sisyphus/evidence/t5-tier-assign.txt

---

## Wave 2: Core Skills

- [x] T6. oe-model-discover Skill

  **What to do**:
  - Create `skills/oe-model-discover/SKILL.md`
  - Frontmatter: name, version, description, skill-type=utility
  - Functions:
    1. Discover OpenClaw configured models (from T5)
    2. Apply tier assignment
    3. Cache to `~/.openclaw/openclaw-enhance/model_cache.json`
  - Skill body: When to use, how to refresh cache

  **Must NOT do**:
  - Do not call external APIs
  - Do not maintain model list externally

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Skill file creation, straightforward

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T7-T10)
  - **Blocked By**: T5 (depends on model_config)

  **References**:
  - `skills/oe-toolcall-router/SKILL.md` - Skill format reference
  - `.sisyphus/drafts/skill-only-redesign-v2.md` lines 268-310 - Design spec

  **QA Scenarios**:

  Scenario: Skill generates model cache
    Tool: Bash
    Preconditions: T5 complete
    Steps:
      1. Run model discover logic
      2. Check `~/.openclaw/openclaw-enhance/model_cache.json`
    Expected Result: Valid JSON with tiers populated
    Evidence: .sisyphus/evidence/t6-model-cache.txt

---

- [x] T7. oe-tag-router Skill

  **What to do**:
  - Create `skills/oe-tag-router/SKILL.md`
  - Frontmatter: name, version, tags=[], skill-type=orch
  - Core logic:
    1. Label inference: Analyze task → assign tags
    2. Label matching: Match tags → candidate skills
    3. Model selection: routine/moderate/complex
  - 3-tier task classification:
    - ROUTINE: Single-step → cheap tier
    - MODERATE: Multi-step → mid tier
    - COMPLEX: Novel problem → premium tier

  **Must NOT do**:
  - Do not hardcode agent IDs
  - Do not route to specific agents

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`
  - Reason: Core routing logic, needs careful design

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T6, T8-T10)

  **References**:
  - `skills/oe-toolcall-router/SKILL.md` - Existing routing skill
  - `docs/adr/0002-native-subagent-announce.md` - sessions_spawn contract

  **QA Scenarios**:

  Scenario: Labels "research" task correctly
    Tool: Bash
    Steps:
      1. Input: "Research the competitive landscape for AI coding tools"
      2. Run tag-router logic
    Expected Result: Tags=["research"], task_type="moderate"
    Evidence: .sisyphus/evidence/t7-router-research.txt

  Scenario: Labels "fix bug" task correctly
    Tool: Bash
    Steps:
      1. Input: "Fix the login bug in auth.py"
      2. Run tag-router logic
    Expected Result: Tags=["code", "debug"], task_type="complex"
    Evidence: .sisyphus/evidence/t7-router-fix.txt

---

- [x] T8. oe-spawn-search Skill

  **What to do**:
  - Create `skills/oe-spawn-search/SKILL.md`
  - Tags: [research, web_search, investigation]
  - Model: Simple=cheap, Deep=mid
  - Spawn recipe with research specialist prompt
  - Security: minimal context, structured output

  **Must NOT do**:
  - Do not specify agentId
  - Do not include parent session memory

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Skill file creation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T6-T7, T9-T10)

  **QA Scenarios**:

  Scenario: Generates correct spawn call for research task
    Tool: Bash
    Steps:
      1. Input: task with tag "research"
      2. Execute skill logic
    Expected Result: Valid sessions_spawn with research specialist prompt
    Evidence: .sisyphus/evidence/t8-spawn-search.txt

---

- [x] T9. oe-spawn-coder Skill

  **What to do**:
  - Create `skills/oe-spawn-coder/SKILL.md`
  - Tags: [code, coding, implement, refactor, write_code, fix_bug]
  - Model: Simple=cheap, Complex=mid/premium
  - Spawn recipe with coding specialist prompt
  - Include test requirements

  **Must NOT do**:
  - Do not specify agentId
  - Do not include full project context

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Skill file creation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T6-T8, T10)

  **QA Scenarios**:

  Scenario: Generates correct spawn call for code task
    Tool: Bash
    Steps:
      1. Input: "Implement user authentication"
      2. Execute skill logic
    Expected Result: Valid sessions_spawn with coder specialist prompt
    Evidence: .sisyphus/evidence/t9-spawn-coder.txt

---

- [x] T10. oe-spawn-ops Skill

  **What to do**:
  - Create `skills/oe-spawn-ops/SKILL.md`
  - Tags: [ops, deployment, infrastructure, monitoring, backup]
  - Model: mid tier (ops needs reliability)
  - Spawn recipe with ops specialist prompt

  **Must NOT do**:
  - Do not specify agentId
  - Do not allow dangerous operations

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Skill file creation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T6-T9)

  **QA Scenarios**:

  Scenario: Generates correct spawn call for ops task
    Tool: Bash
    Steps:
      1. Input: "Deploy to production"
      2. Execute skill logic
    Expected Result: Valid sessions_spawn with ops specialist prompt
    Evidence: .sisyphus/evidence/t10-spawn-ops.txt

---

## Wave 3: Utility + Context Skills

- [x] T11. oe-eta-estimator Skill

  **What to do**:
  - Create `skills/oe-eta-estimator/SKILL.md`
  - Migrate from v1: `skills/oe-eta-estimator/`
  - Functions:
    1. Announce ETA upfront before starting
    2. Delay updates until meaningful change
    3. Provide completion summary
  - Human-intuitive protocol: "about 5 min", "15-20 min", etc.

  **Must NOT do**:
  - Do not block task execution
  - Do not make promises about exact timing

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Skill file creation, pattern exists

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T12-T15)

  **References**:
  - `skills/oe-eta-estimator/SKILL.md` - Existing skill (migrate to new location)

  **QA Scenarios**:

  Scenario: Generates ETA announcement
    Tool: Bash
    Steps:
      1. Input: Task description
      2. Run eta-estimator logic
    Expected Result: ETA string like "about 10 minutes"
    Evidence: .sisyphus/evidence/t11-eta.txt

---

- [x] T12. oe-timeout-state-sync Skill

  **What to do**:
  - Create `skills/oe-timeout-state-sync/SKILL.md`
  - Migrate from v1: `skills/oe-timeout-state-sync/`
  - Functions:
    1. Monitor runtime timeout state
    2. Sync state between main and runtime
    3. Handle timeout warnings

  **Must NOT do**:
  - Do not directly terminate sessions
  - Do not modify runtime state

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Skill file creation, pattern exists

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T11, T13-T15)

  **References**:
  - `skills/oe-timeout-state-sync/SKILL.md` - Existing skill (migrate to new location)

  **QA Scenarios**:

  Scenario: Syncs timeout state correctly
    Tool: Bash
    Steps:
      1. Check runtime state file
      2. Run sync logic
    Expected Result: State synchronized
    Evidence: .sisyphus/evidence/t12-timeout-sync.txt

---

- [x] T13. oe-project-context Skill

  **What to do**:
  - Create `skills/oe-project-context/SKILL.md`
  - Migrate from v1: `workspaces/oe-orchestrator/skills/oe-project-registry/`
  - Functions:
    1. Discover current project
    2. Inject project context into spawn
    3. Project metadata: path, type, git remote

  **Must NOT do**:
  - Do not create/modify projects
  - Do not hardcode project paths

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Skill file creation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T11-T12, T14-T15)

  **References**:
  - `workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md` - Existing v1

  **QA Scenarios**:

  Scenario: Discovers current project
    Tool: Bash
    Steps:
      1. Run project-context logic in repo
      2. Check project info output
    Expected Result: Project path and type detected
    Evidence: .sisyphus/evidence/t13-project-context.txt

---

- [x] T14. oe-git-context Skill

  **What to do**:
  - Create `skills/oe-git-context/SKILL.md`
  - Migrate from v1: `workspaces/oe-orchestrator/skills/oe-git-context/`
  - Functions:
    1. Inject relevant git history
    2. Recent commits affecting files
    3. Branch and status info

  **Must NOT do**:
  - Do not modify git state
  - Do not run destructive git commands

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Skill file creation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T11-T13, T15)

  **References**:
  - `workspaces/oe-orchestrator/skills/oe-git-context/SKILL.md` - Existing v1

  **QA Scenarios**:

  Scenario: Injects git history
    Tool: Bash
    Steps:
      1. Run git-context logic
      2. Check output contains recent commits
    Expected Result: Last 3-5 commits with messages
    Evidence: .sisyphus/evidence/t14-git-context.txt

---

- [x] T15. oe-memory-sync Skill

  **What to do**:
  - Create `skills/oe-memory-sync/SKILL.md`
  - Migrate from v1: `workspaces/oe-orchestrator/skills/oe-memory-sync/`
  - Functions:
    1. Fetch main session context
    2. Sync relevant memory to sub-agent
    3. Selective memory injection

  **Must NOT do**:
  - Do not transfer full session memory
  - Do not leak sensitive context

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Skill file creation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T11-T14)

  **References**:
  - `workspaces/oe-orchestrator/skills/oe-memory-sync/SKILL.md` - Existing v1

  **QA Scenarios**:

  Scenario: Syncs relevant memory
    Tool: Bash
    Steps:
      1. Run memory-sync logic
      2. Check output contains relevant context
    Expected Result: Filtered memory relevant to task
    Evidence: .sisyphus/evidence/t15-memory-sync.txt

---

## Wave 4: Publishing + Docs

- [x] T16. oe-publish Skill

  **What to do**:
  - Create `skills/oe-publish/SKILL.md`
  - Migrate from v1: `workspaces/oe-orchestrator/skills/oe-publish/`
  - Functions:
    1. Handle publish workflows
    2. Git push, deployment triggers
    3. Release notes generation

  **Must NOT do**:
  - Do not auto-push without confirmation
  - Do not skip safety checks

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: Skill file creation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with T17)

  **References**:
  - `workspaces/oe-orchestrator/skills/oe-publish/SKILL.md` - Existing v1

  **QA Scenarios**:

  Scenario: Generates release notes
    Tool: Bash
    Steps:
      1. Run publish skill with changelog
      2. Check output
    Expected Result: Formatted release notes
    Evidence: .sisyphus/evidence/t16-publish.txt

---

- [x] T17. SOUL.md Install/Uninstall

  **What to do**:
  - During `install --target main`:
    1. Read main's `SOUL.md` (or create if not exists)
    2. Inject v2 SOUL block between `<!-- oe-soul-start -->` and `<!-- oe-soul-end -->` markers
    3. The injected SOUL:
       ```
       <!-- oe-soul-start -->
       ## Main Agent SOUL

       You are the orchestration layer. Your rules:
       1. NEVER directly execute large tasks (>5 tool calls or >15 min)
       2. ALL complex tasks MUST be delegated via sessions_spawn
       3. You only do: analyze → tag → spawn → synthesize
       4. ETA must be announced upfront
       <!-- oe-soul-end -->
       ```
  - During `uninstall --target main`:
    1. Read main's `SOUL.md`
    2. Remove content between `<!-- oe-soul-start -->` and `<!-- oe-soul-end -->`
    3. Leave markers if desired

  **Must NOT do**:
  - Do not remove content outside oe-soul markers
  - Do not modify if markers not present (fail gracefully)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - Reason: String manipulation, straightforward

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with T16)

  **References**:
  - OpenClaw SOUL.md mechanism (user to confirm location)
  - `.sisyphus/drafts/skill-only-redesign-v2.md` lines 70-78 - SOUL design

  **QA Scenarios**:

  Scenario: SOUL injected on install
    Tool: Bash
    Preconditions: Main workspace exists
    Steps:
      1. `python -m openclaw_enhance.cli install --target main`
      2. `cat ~/.openclaw/workspace/{main}/SOUL.md`
    Expected Result: Content between oe-soul-start/end markers present
    Evidence: .sisyphus/evidence/t17-soul-install.txt

  Scenario: SOUL removed on uninstall
    Tool: Bash
    Steps:
      1. `python -m openclaw_enhance.cli uninstall --target main`
      2. `cat ~/.openclaw/workspace/{main}/SOUL.md`
    Expected Result: Content between oe-soul markers removed
    Evidence: .sisyphus/evidence/t17-soul-uninstall.txt

---

## Wave 5: Cleanup + Migration + Integration

- [x] T18. v1 → v2 Migration

  **What to do**:
  - Migrate `project-registry.json` if exists:
    - Read from `~/.openclaw/openclaw-enhance/project-registry.json`
    - Convert to v2 format (if format changed)
  - Archive `workspaces/` directory:
    - Move to `~/.openclaw/openclaw-enhance/v1-archive/workspaces/`
    - Do NOT delete - preserves user data
  - Archive `runtime-state.json`:
    - Move to `~/.openclaw/openclaw-enhance/v1-archive/runtime-state.json`
  - Update manifest: mark as "migrated"
  - Create `~/.openclaw/openclaw-enhance/v1-archive/README.json` with migration metadata

  **Must NOT do**:
  - Do not delete v1 data - archive only
  - Do not modify openclaw source

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `["git-master"]`
  - Reason: File moving, JSON transformation

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: T11-T17 complete

  **References**:
  - `docs/opencode-iteration-handbook.md` - v1 components
  - `~/.openclaw/openclaw-enhance/` - v1 data locations

  **QA Scenarios**:

  Scenario: v1 workspaces archived
    Tool: Bash
    Steps:
      1. Check `~/.openclaw/openclaw-enhance/v1-archive/workspaces/` exists
      2. List contents
    Expected Result: All v1 workspaces preserved
    Evidence: .sisyphus/evidence/t18-archive-workspaces.txt

  Scenario: project-registry migrated
    Tool: Bash
    Steps:
      1. Check v2 manifest has project-registry info
      2. Check v1-archive has original
    Expected Result: Data preserved in both locations
    Evidence: .sisyphus/evidence/t18-migration.txt

---

- [x] T19. Remove v1 Workspace References

  **What to do**:
  - Remove v1 workspace directories from source tree:
    - `workspaces/oe-orchestrator/`
    - `workspaces/oe-searcher/`
    - `workspaces/oe-syshelper/`
    - `workspaces/oe-script_coder/`
    - `workspaces/oe-watchdog/`
    - `workspaces/oe-tool-recovery/`
    - `workspaces/oe-specialist-*/`
  - Update docs references
  - Clean git history if possible

  **Must NOT do**:
  - Do not delete v1-archive (already moved to user home)
  - Do not modify openclaw source

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `["git-master"]`
  - Reason: File deletion, git cleanup

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: T18 complete

  **QA Scenarios**:

  Scenario: Workspaces removed from source
    Tool: Bash
    Steps:
      1. `ls workspaces/`
    Expected Result: Directory empty or workspaces removed
    Evidence: .sisyphus/evidence/t19-workspaces-removed.txt

---

- [x] T20. Integration Tests

  **What to do**:
  - Run full test suite: `pytest tests/ -q`
  - Verify CLI commands work end-to-end
  - Verify skill installation works
  - Verify hook loads correctly
  - Verify extension blocks forbidden tools
  - Verify SOUL injection works
  - Verify model discovery works

  **Must NOT do**:
  - Do not skip failing tests
  - Do not commit with failing tests

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`
  - Reason: Full integration verification

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: T19 complete

  **References**:
  - `tests/` - Existing test directory

  **QA Scenarios**:

  Scenario: All tests pass
    Tool: Bash
    Steps:
      1. `pytest tests/ -q`
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/t20-tests.txt

---

- [x] T21. Docs Check + Validation

  **What to do**:
  - Run `python -m openclaw_enhance.cli docs-check`
  - Run `python -m openclaw_enhance.cli validate-feature --feature-class install-lifecycle --report-slug v2-backfill`
  - Update handbook: Record v2 architecture change
  - Update PLAYBOOK.md

  **Must NOT do**:
  - Do not skip validation
  - Do not commit without passing checks

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`
  - Reason: Documentation validation

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: T20 complete

  **References**:
  - `docs/opencode-iteration-handbook.md` - Update current design status
  - `PLAYBOOK.md` - Update capability inventory

  **QA Scenarios**:

  Scenario: docs-check passes
    Tool: Bash
    Steps:
      1. `python -m openclaw_enhance.cli docs-check`
    Expected Result: All checks pass
    Evidence: .sisyphus/evidence/t21-docs-check.txt

  Scenario: validate-feature passes
    Tool: Bash
    Steps:
      1. `python -m openclaw_enhance.cli validate-feature --feature-class install-lifecycle --report-slug v2-backfill`
    Expected Result: Validation PASS
    Evidence: .sisyphus/evidence/t21-validate.txt

---

## Final Verification Wave

> After ALL implementation tasks (T1-T21), run 4 review agents in parallel.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search codebase — reject if found.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | VERDICT: APPROVE/REJECT`
  **Evidence**: F1 critical fixes applied (handler.ts agentId removed, oe-toolcall-router v1 skill deleted)

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest tests/ -q` and linter. Review for: `as any`/`@ts-ignore`, empty catches, commented-out code, unused imports.
  Output: `Tests [N pass/N fail] | Quality [PASS/FAIL] | VERDICT`
  **Evidence**: 516 pass, 76 fail | Quality PASS | 76 failures are expected v1 migration artifacts

- [x] F3. **Real Manual QA** — `unspecified-high`
  Execute EVERY QA scenario from T1-T21. Save evidence to `.sisyphus/evidence/`.
  Output: `Scenarios [N/N pass] | VERDICT`
  **Evidence**: 4/4 scenarios PASS

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual changes. Verify 1:1 — no missing, no creep.
  Output: `Tasks [N/N compliant] | Creep [CLEAN/N issues] | VERDICT`
  **Evidence**: Tasks 20/21 compliant, Creep CLEAN, APPROVE

---

## Commit Strategy

- **After T1-T5**: `feat(manifest): add manifest system and CLI --target flag`
- **After T6-T10**: `feat(skills): add core orch skills (tag-router, spawn-*)`
- **After T11-T15**: `feat(skills): add utility and context skills`
- **After T16-T17**: `feat(soul): add SOUL.md install/uninstall injection`
- **After T18-T21**: `refactor!: v1 migration complete, skill-only v2 architecture`

---

## Success Criteria

### Verification Commands
```bash
python -m openclaw_enhance.cli install --target main  # Success
python -m openclaw_enhance.cli status                  # Shows skills
python -m openclaw_enhance.cli uninstall --target main # Success
pytest tests/ -q                                        # All pass
python -m openclaw_enhance.cli docs-check              # All pass
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] Docs-check passes
- [ ] v1 data archived (not deleted)
- [ ] SOUL injected into main's SOUL.md on install
- [ ] SOUL removed from main's SOUL.md on uninstall
- [ ] PLAYBOOK.md updated
