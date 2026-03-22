# Fix Main → Orchestrator → OpenCode/ACP Routing Chain

## TL;DR

> **Quick Summary**: 修复从 main 到 oe-orchestrator 再到 opencode/ACP 的完整路由链路。当前 oe-runtime hook 崩溃导致 tool gate 失效，main 绕过 orch 直接干活。
> 
> **Deliverables**:
> - oe-runtime extension null guard 修复 + fail-closed 行为
> - 部署验证流程（每次改动后自动验证 live 环境）
> - main → orch 路由链路端到端可用
> - orch → opencode 分发 skill 实现（ACP 集成）
> - 开发工作流（issue → worktree → PR → CI → merge）可被 orch 调度
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 → Task 3 → Task 5 → Task 7 → Task 9 → F1-F4

---

## Context

### Original Request
用户通过飞书要求 OpenClaw："在公司有个openclaw-enhance 你让opencode去改，要先提issue，再开worktree，再pr，再merge，用sss-reverse的Claudeopus模型"。结果 main 直接自己处理了 bug，完全没有走 main → orch → opencode 路径。

### Interview Summary
**Key Discussions**:
- 根因调查确认 oe-runtime hook 在飞书对话期间持续崩溃（TypeError: undefined.startsWith）
- Tool gate 崩溃后 fail-open，main 可以直接使用所有工具
- ACP 在 README 里定义为"opencode 用于开发，无需新建专门的Agents，但要在 Orchestrator 的分发skill体现出来"
- 之前的修复（null guard）从未成功部署到 ~/.openclaw/

**Research Findings**:
- oe-runtime 是唯一的硬性执行门控，但有 null guard bug
- oe-main-routing-gate hook 是 advisory only，不阻塞
- oe-worker-dispatch skill 没有 opencode/ACP 分支
- ACPX plugin 在 gateway 日志中注册但 opencode-acp.log 为空（0 bytes）
- sessions_spawn 参数名不一致：代码用 agentId，hook 检查 agent

### Metis Review
**Identified Gaps** (addressed):
- before_tool_call 事件是否真的在当前 OpenClaw 版本中触发 → 添加验证任务
- opencode 具体指什么（CLI? ACP server? 原生 agent?）→ 需要用户确认，但默认按 ACPX plugin 处理
- 部署验证缺失 → 每个 fix 必须包含 install + live verify
- fail-closed 定义 → hook 崩溃时 block 主 session 的 forbidden tools
- oe-orchestrator 从未在生产环境被真正调用过 → 需要端到端验证

---

## Work Objectives

### Core Objective
修复 main → oe-orchestrator → opencode/ACP 完整路由链路，使用户通过飞书发起的开发任务能按照 issue → worktree → PR → CI → merge 流程执行。

### Concrete Deliverables
- 修复后的 `extensions/openclaw-enhance-runtime/index.ts`（null guard + fail-closed + 正确参数名）
- 更新后的 `oe-worker-dispatch` skill（含 opencode/ACP 分支）
- 部署验证集成测试
- 端到端路由验证

### Definition of Done
- [ ] `openclaw plugins list` 显示 oe-runtime 已加载
- [ ] main session 中 edit/write/exec 被 oe-runtime 拦截
- [ ] 被拦截后 main 使用 sessions_spawn 路由到 oe-orchestrator
- [ ] oe-orchestrator 收到任务后能触发 opencode/ACP 分发
- [ ] 全部单元测试通过
- [ ] 部署到 ~/.openclaw/ 后 live 验证通过

### Must Have
- oe-runtime null guard 修复
- fail-closed 行为（hook 崩溃 → block forbidden tools）
- 正确的 sessions_spawn 参数处理（agentId vs agent）
- 部署后 live 验证步骤
- orch → opencode 分发 skill 分支

### Must NOT Have (Guardrails)
- 不修改 OpenClaw 源代码
- 不把 oe-main-routing-gate 改成 blocking（它是故意设计为 advisory 的分层防御）
- 不在 P0-P2 验证通过前实现 P3-P4（严格 stop-gate）
- 不假设 opencode/ACP 已可用 — 必须先验证
- 不创建 oe-acp workspace（README 明确说不需要专门 Agent）

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: YES (Tests-after)
- **Framework**: bun test (TypeScript) + pytest (Python)

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **TypeScript**: Use Bash (bun test) — Run tests, assert pass
- **Integration**: Use Bash (openclaw CLI) — Run commands, check output
- **Deployment**: Use Bash (openclaw plugins list, grep logs) — Verify live state

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — verify + fix oe-runtime):
├── Task 1: Verify before_tool_call event fires in OpenClaw [deep]
├── Task 2: Fix oe-runtime null guard + fail-closed + agentId param [deep]
├── Task 3: Add unit tests for oe-runtime fixes [quick]
└── Task 4: Verify ACPX plugin state and opencode availability [quick]

Wave 2 (Deploy + verify main→orch chain — after Wave 1):
├── Task 5: Deploy oe-runtime fix + live verification (depends: 2, 3) [unspecified-high]
├── Task 6: End-to-end test: main→orch spawn (depends: 5) [deep]
└── Task 7: Add opencode/ACP dispatch branch to oe-worker-dispatch (depends: 4) [unspecified-high]

Wave 3 (Integration + E2E — after Wave 2):
├── Task 8: Deploy dispatch skill + test orch→opencode chain (depends: 6, 7) [deep]
├── Task 9: Full chain integration test: Feishu-like scenario (depends: 8) [deep]
└── Task 10: Update handbook + docs with routing chain status (depends: 9) [writing]

Wave FINAL (After ALL tasks — 4 parallel reviews, then user okay):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay
```

Critical Path: Task 1 → Task 2 → Task 5 → Task 6 → Task 8 → Task 9 → F1-F4 → user okay
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 4 (Wave 1)

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 | — | 2, 5 |
| 2 | — | 3, 5 |
| 3 | 2 | 5 |
| 4 | — | 7 |
| 5 | 2, 3 | 6 |
| 6 | 5 | 8 |
| 7 | 4 | 8 |
| 8 | 6, 7 | 9 |
| 9 | 8 | 10 |
| 10 | 9 | F1-F4 |

### Agent Dispatch Summary

- **Wave 1**: **4** — T1 → `deep`, T2 → `deep`, T3 → `quick`, T4 → `quick`
- **Wave 2**: **3** — T5 → `unspecified-high`, T6 → `deep`, T7 → `unspecified-high`
- **Wave 3**: **3** — T8 → `deep`, T9 → `deep`, T10 → `writing`
- **FINAL**: **4** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.

- [x] 1. Verify before_tool_call event fires in OpenClaw

  **What to do**:
  - 在 `extensions/openclaw-enhance-runtime/index.ts` 的 `before_tool_call` handler 入口添加一行 `api.logger.info("OE_RUNTIME_GATE_FIRED")` 日志
  - 执行 `python -m openclaw_enhance.cli install` 部署
  - 通过 `openclaw agent --agent main` 发一条需要 tool call 的消息
  - 在 `~/.openclaw/logs/gateway.log` 或 `gateway.err.log` 中 grep `OE_RUNTIME_GATE_FIRED`
  - 如果事件不触发，则 oe-runtime 整个方案需要重新评估

  **Must NOT do**:
  - 不修改 OpenClaw 源码
  - 不修改除 index.ts 以外的文件

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要理解 OpenClaw plugin 事件模型并精准验证
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Tasks 2, 5
  - **Blocked By**: None

  **References**:
  - `extensions/openclaw-enhance-runtime/index.ts:1-60` — 当前 before_tool_call handler 注册逻辑
  - `extensions/openclaw-enhance-runtime/openclaw.plugin.json` — 插件清单
  - `~/.openclaw/logs/gateway.err.log` — 当前已有的 `before_tool_call handler from oe-runtime failed` 错误（证明事件确实触发了，只是 handler 崩了）
  - **WHY**: gateway.err.log 已有崩溃日志说明事件确实在触发，这个任务主要是做正面确认并记录证据

  **Acceptance Criteria**:
  - [ ] 日志中出现 `OE_RUNTIME_GATE_FIRED` 字样
  - [ ] 或确认 gateway.err.log 中已有的 oe-runtime crash 日志已经证明事件在触发

  **QA Scenarios**:
  ```
  Scenario: 验证 before_tool_call 事件触发
    Tool: Bash
    Preconditions: OpenClaw gateway 运行中
    Steps:
      1. grep "before_tool_call handler from oe-runtime" ~/.openclaw/logs/gateway.err.log | tail -5
      2. 确认错误日志时间在最近（2026-03-22）
    Expected Result: 存在 oe-runtime handler 崩溃日志，证明事件确实被触发
    Failure Indicators: 无任何 oe-runtime 相关日志
    Evidence: .sisyphus/evidence/task-1-before-tool-call-verify.txt
  ```

  **Commit**: NO (验证任务，不产生代码变更)

- [ ] 2. Fix oe-runtime null guard + fail-closed + agentId param

  **What to do**:
  - 修复 `extensions/openclaw-enhance-runtime/index.ts` 中的 `isMainSession` 函数：
    ```typescript
    const isMainSession = (sessionKey: string | undefined): boolean =>
      typeof sessionKey === "string" && sessionKey.startsWith("agent:main:");
    ```
  - 用 try/catch 包裹整个 `before_tool_call` handler，**fail-closed**：catch 时对 main session 返回 `{block: true}`
  - 修复 sessions_spawn 参数名检查：从 `event.params.agent` 改为 `event.params.agentId`（参考 gateway.err.log 中的诊断）
  - 确保 blockReason 消息中推荐 `sessions_spawn({ agentId: "oe-orchestrator", ... })`

  **Must NOT do**:
  - 不修改 OpenClaw 源码
  - 不改变 hook 的 advisory 设计（oe-main-routing-gate 保持 advisory）
  - 不添加新功能，只修 bug

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要精准理解 plugin 事件上下文结构和 fail-closed 语义
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: 先写 failing test 再修 bug

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Tasks 3, 5
  - **Blocked By**: None

  **References**:
  - `extensions/openclaw-enhance-runtime/index.ts:1-60` — 当前有 bug 的代码（isMainSession 没有 null guard，没有 try/catch，参数名错误）
  - `hooks/oe-main-routing-gate/handler.ts:1-10` — 正确的 null guard 实现参考：`typeof sessionKey === "string" && sessionKey.startsWith("agent:main:")`
  - `~/.openclaw/logs/gateway.err.log` 10:43 时间段 — 崩溃现场：`TypeError: Cannot read properties of undefined (reading 'startsWith')`
  - `ses_2f1dca44dffeYOhGKqWGoA8Byf` 中的诊断 — sessions_spawn 参数名是 `agentId` 不是 `agent`
  - **WHY**: 这是整个链路断裂的直接技术根因

  **Acceptance Criteria**:
  - [ ] `isMainSession(undefined)` 返回 `false` 而不是 crash
  - [ ] handler 崩溃时返回 `{block: true}` 而不是 fail-open
  - [ ] sessions_spawn 拦截检查 `event.params.agentId` 而非 `event.params.agent`
  - [ ] `bun test extensions/openclaw-enhance-runtime/` 全部通过

  **QA Scenarios**:
  ```
  Scenario: null sessionKey 不崩溃
    Tool: Bash (bun test)
    Preconditions: 代码已修改
    Steps:
      1. bun test extensions/openclaw-enhance-runtime/ --filter "undefined sessionKey"
    Expected Result: 测试通过，isMainSession(undefined) 返回 false
    Evidence: .sisyphus/evidence/task-2-null-guard.txt

  Scenario: handler 崩溃时 fail-closed
    Tool: Bash (bun test)
    Preconditions: 代码已修改
    Steps:
      1. bun test extensions/openclaw-enhance-runtime/ --filter "fail-closed"
    Expected Result: 当 handler 内部抛异常时，对 main session 返回 block=true
    Evidence: .sisyphus/evidence/task-2-fail-closed.txt

  Scenario: agentId 参数正确检查
    Tool: Bash (bun test)
    Preconditions: 代码已修改
    Steps:
      1. bun test extensions/openclaw-enhance-runtime/ --filter "agentId"
    Expected Result: sessions_spawn 拦截使用 params.agentId
    Evidence: .sisyphus/evidence/task-2-agentid-param.txt
  ```

  **Commit**: YES
  - Message: `fix(runtime): add null guard, fail-closed and correct agentId param to oe-runtime`
  - Files: `extensions/openclaw-enhance-runtime/index.ts`
  - Pre-commit: `bun test extensions/openclaw-enhance-runtime/`

- [ ] 3. Add unit tests for oe-runtime fixes

  **What to do**:
  - 在 `extensions/openclaw-enhance-runtime/src/runtime-bridge.test.ts`（已有测试文件）中添加：
    - `isMainSession` 测试：undefined, null, empty string, valid "agent:main:main", 非 main session
    - fail-closed 测试：模拟 handler 内部异常，验证返回 block=true
    - sessions_spawn 参数测试：验证拦截检查 agentId 而非 agent
    - blockReason 消息测试：验证包含 `sessions_spawn` 和 `oe-orchestrator` 建议

  **Must NOT do**:
  - 不测试 oe-main-routing-gate（那个 hook 是好的）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 纯测试编写，逻辑简单
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES (but depends on Task 2 for code)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 5
  - **Blocked By**: Task 2

  **References**:
  - `extensions/openclaw-enhance-runtime/src/runtime-bridge.test.ts` — 已有测试文件（注意在 src/ 子目录下），按此模式添加
  - `extensions/openclaw-enhance-runtime/index.ts` — 被测代码
  - **WHY**: 确保 fix 不回退

  **Acceptance Criteria**:
  - [ ] 新增至少 5 个测试用例
  - [ ] `bun test extensions/openclaw-enhance-runtime/` 全部通过
  - [ ] 覆盖：null guard, fail-closed, agentId param, blockReason

  **QA Scenarios**:
  ```
  Scenario: 全部测试通过
    Tool: Bash
    Steps:
      1. bun test extensions/openclaw-enhance-runtime/
    Expected Result: 所有测试通过，0 failures
    Evidence: .sisyphus/evidence/task-3-test-results.txt
  ```

  **Commit**: YES
  - Message: `test(runtime): add unit tests for oe-runtime tool gate`
  - Files: `extensions/openclaw-enhance-runtime/src/runtime-bridge.test.ts`
  - Pre-commit: `bun test extensions/openclaw-enhance-runtime/`

- [x] 4. Verify ACPX plugin state and opencode availability

  **What to do**:
  - 确认 ACPX 插件在 openclaw.json 中已启用（`acp.enabled: true`, `acp.backend: "acpx"`, `acp.defaultAgent: "opencode"`）
  - 确认 opencode 配置存在于 `~/.config/opencode/opencode.json`
  - 读取 `acp-router` skill（位于 acpx 扩展内）了解 sessions_spawn 如何带 `runtime: "acp"` 路由到 opencode
  - 验证 `~/.acpx/sessions/` 中是否有历史 session 数据（证明 ACP 曾经工作过）
  - 记录 ACP dispatch 的正确调用方式：`sessions_spawn({ agentId: "opencode", runtime: "acp", ... })`

  **Must NOT do**:
  - 不修改任何配置
  - 不启动 opencode 进程

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 纯读取验证
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Task 7
  - **Blocked By**: None

  **References**:
  - `~/.openclaw/openclaw.json` — ACP 配置段：`acp.enabled`, `acp.backend`, `acp.defaultAgent`, `acp.allowedAgents`
  - `~/.config/opencode/opencode.json` — opencode 模型和 provider 配置
  - `~/.nvm/versions/node/v25.8.0/lib/node_modules/openclaw/extensions/acpx/skills/acp-router/SKILL.md` — ACP 路由 skill
  - `~/.acpx/sessions/` — 历史 ACP session 文件（证明曾经工作）
  - **WHY**: 在实现 orch→opencode 分发前，必须确认 ACP 基础设施可用

  **Acceptance Criteria**:
  - [ ] 确认 `acp.enabled: true` 在 openclaw.json
  - [ ] 确认 opencode.json 配置存在且有效
  - [ ] 记录 ACP dispatch 正确调用语法到证据文件
  - [ ] 确认 ~/.acpx/sessions/ 有历史数据

  **QA Scenarios**:
  ```
  Scenario: ACPX 配置验证
    Tool: Bash
    Steps:
      1. cat ~/.openclaw/openclaw.json | python3 -c "import json,sys; c=json.load(sys.stdin); print(c.get('acp',{}))"
      2. ls ~/.acpx/sessions/ | head -5
      3. cat ~/.config/opencode/opencode.json | python3 -c "import json,sys; c=json.load(sys.stdin); print('provider:', list(c.get('providers',{}).keys()))"
    Expected Result: acp.enabled=true, sessions 存在, opencode 配置有效
    Evidence: .sisyphus/evidence/task-4-acpx-verify.txt
  ```

  **Commit**: NO (验证任务)

- [ ] 5. Deploy oe-runtime fix + live verification

  **What to do**:
  - 执行 `python -m openclaw_enhance.cli install` 部署修复后的 oe-runtime
  - 验证 `openclaw plugins list` 输出中包含 oe-runtime
  - 重启 gateway：`openclaw gateway restart`
  - 通过 main session 触发一个 forbidden tool call（如 edit），验证被 block
  - 检查 gateway.err.log 不再有 `TypeError: Cannot read properties of undefined` 错误
  - 同时更新 oe-subagent-spawn-enrich hook 到最新版本（repo 版 301 行 vs 已安装 181 行）

  **Must NOT do**:
  - 不修改 OpenClaw 源码
  - 不改变 openclaw.json 配置

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要执行部署命令并验证 live 环境
  - **Skills**: [`verification-before-completion`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 2 start)
  - **Blocks**: Task 6
  - **Blocked By**: Tasks 2, 3

  **References**:
  - `src/openclaw_enhance/cli.py` — install 命令实现
  - `~/.openclaw/openclaw-enhance/install-manifest.json` — 部署清单，确认 extension:oe-runtime 以 symlink 方式安装
  - `~/.openclaw/logs/gateway.err.log` — 验证崩溃不再出现
  - **WHY**: 之前的修复从未成功部署，这次必须有 live 验证

  **Acceptance Criteria**:
  - [ ] `python -m openclaw_enhance.cli install` 成功
  - [ ] gateway 重启后无 oe-runtime crash
  - [ ] main session 中 forbidden tool 被 block
  - [ ] oe-subagent-spawn-enrich hook 更新到最新版本

  **QA Scenarios**:
  ```
  Scenario: 部署成功且 hook 不崩溃
    Tool: Bash
    Steps:
      1. python -m openclaw_enhance.cli install
      2. openclaw gateway restart
      3. sleep 5
      4. grep "oe-runtime failed" ~/.openclaw/logs/gateway.err.log | tail -3
      5. 检查最新错误时间是否在部署之前（非之后）
    Expected Result: 部署成功，重启后无新 oe-runtime 崩溃
    Evidence: .sisyphus/evidence/task-5-deploy-verify.txt

  Scenario: forbidden tool 被 block
    Tool: Bash
    Steps:
      1. 通过 openclaw agent 发送一条需要 edit 的消息
      2. 检查 gateway.log 中是否出现 BLOCKED 或 blockReason
    Expected Result: tool call 被拦截，日志中有 block 记录
    Evidence: .sisyphus/evidence/task-5-tool-block.txt
  ```

  **Commit**: NO (部署任务)

- [ ] 6. End-to-end test: main → orch spawn

  **What to do**:
  - 通过 main session 发送一条复杂开发请求（如："修复 openclaw-enhance 项目中的 XX bug"）
  - 验证 main 尝试使用 forbidden tool 时被 block
  - 验证 main 读到 blockReason 后调用 `sessions_spawn({ agentId: "oe-orchestrator", ... })`
  - 验证 oe-orchestrator session 被创建（检查 gateway.log 中的 spawn 记录）
  - 如果 main 仍然不路由：分析是因为 LLM 忽略了 blockReason，还是其他原因

  **Must NOT do**:
  - 不修改代码（这是纯验证任务）
  - 不改变模型配置

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要分析 LLM 行为和 session 交互
  - **Skills**: [`systematic-debugging`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 2)
  - **Blocks**: Task 8
  - **Blocked By**: Task 5

  **References**:
  - `~/.openclaw/logs/gateway.log` — spawn 事件记录
  - `~/.openclaw/logs/gateway.err.log` — block 事件和错误
  - `hooks/oe-subagent-spawn-enrich/handler.ts` — spawn enrichment 逻辑
  - `extensions/openclaw-enhance-runtime/index.ts` — block 消息内容
  - **WHY**: 验证修复后 main 是否真的会路由到 orch

  **Acceptance Criteria**:
  - [ ] gateway.log 中出现 `sessions_spawn` 到 `oe-orchestrator` 的记录
  - [ ] 或发现 LLM 不遵守 blockReason 的具体行为（需要记录并分析）

  **QA Scenarios**:
  ```
  Scenario: main 路由到 orch
    Tool: Bash
    Steps:
      1. openclaw agent --agent main -m "修复 openclaw-enhance 项目中 oe-runtime hook 的 sessionKey 类型问题"
      2. sleep 30
      3. grep "oe-orchestrator" ~/.openclaw/logs/gateway.log | tail -5
    Expected Result: 出现 oe-orchestrator spawn 记录
    Failure Indicators: main 自己处理了请求，无 spawn 记录
    Evidence: .sisyphus/evidence/task-6-e2e-main-orch.txt

  Scenario: block 后 LLM 不遵守（负面场景）
    Tool: Bash
    Steps:
      1. 检查 gateway.err.log 中 BLOCKED 之后 main 的行为
      2. 如果 main 继续使用 forbidden tool，记录具体行为
    Expected Result: 记录 LLM 的实际响应模式
    Evidence: .sisyphus/evidence/task-6-llm-compliance.txt
  ```

  **Commit**: NO (验证任务)

- [ ] 7. Add opencode/ACP dispatch branch to oe-worker-dispatch skill

  **What to do**:
  - 修改 `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`
  - 添加 ACP/opencode 分发分支：
    - 当任务类型为"代码开发/bug修复/功能实现"且用户明确要求使用 opencode 时
    - 使用 `sessions_spawn({ agentId: "opencode", runtime: "acp", task: "...", ... })`
    - 包含开发工作流指令：先提 issue → 创建 worktree → 开发测试 → PR → CI → merge
  - 添加任务类型判断逻辑：
    - 如果用户说"用 opencode 改"/"让 opencode 去做" → ACP dispatch
    - 如果是普通搜索/诊断/脚本 → 继续走现有 worker dispatch
  - 参考 `acp-router` skill 的 sessions_spawn 语法

  **Must NOT do**:
  - 不创建 oe-acp workspace
  - 不修改 acp-router skill（那是 OpenClaw 内置的）
  - 不自动判定所有开发任务都走 opencode — 只在用户明确要求时

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要理解 skill 设计模式和 ACP 协议
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 2, parallel with Task 5/6)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 8
  - **Blocked By**: Task 4

  **References**:
  - `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md` — 当前 dispatch skill（只有 oe-* workers）
  - `~/.nvm/versions/node/v25.8.0/lib/node_modules/openclaw/extensions/acpx/skills/acp-router/SKILL.md` — ACP 路由 skill，包含 `runtime: "acp"` 语法
  - `~/.openclaw/openclaw.json` acp 配置段 — `defaultAgent: "opencode"`, `allowedAgents`
  - `README.md:45` — "acp：opencode 用于开发，无需新建专门的Agents，但是要在 Orchestrator 的分发skill体现出来"
  - **WHY**: 这是补全链路第三层（orch→opencode）的核心任务

  **Acceptance Criteria**:
  - [ ] SKILL.md 中有 ACP/opencode 分发分支
  - [ ] 分支包含正确的 `sessions_spawn` 语法（`runtime: "acp"`, `agentId: "opencode"`）
  - [ ] 包含开发工作流指令（issue → worktree → PR → CI → merge）
  - [ ] 只在用户明确要求时触发，不自动接管所有开发任务

  **QA Scenarios**:
  ```
  Scenario: skill 语法验证
    Tool: Bash
    Steps:
      1. grep -c "runtime.*acp" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md
      2. grep -c "agentId.*opencode" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md
      3. grep -c "issue.*worktree.*PR" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md
    Expected Result: 每个 grep 返回 ≥1
    Evidence: .sisyphus/evidence/task-7-dispatch-skill.txt
  ```

  **Commit**: YES
  - Message: `feat(dispatch): add opencode/ACP dispatch branch to oe-worker-dispatch`
  - Files: `workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md`

- [ ] 8. Deploy dispatch skill + test orch → opencode chain

  **What to do**:
  - 执行 `python -m openclaw_enhance.cli install` 部署更新后的 dispatch skill
  - 手动 spawn oe-orchestrator 并给它一个 "用 opencode 修复 XX bug" 的任务
  - 验证 orch 读取 dispatch skill 后选择 ACP 路径
  - 验证 `sessions_spawn` 调用中包含 `runtime: "acp"` 和 `agentId: "opencode"`
  - 检查 opencode ACP session 是否被创建

  **Must NOT do**:
  - 不跳过部署直接测试 repo 代码

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要理解多层 session 交互
  - **Skills**: [`systematic-debugging`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3 start)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 6, 7

  **References**:
  - Task 5 证据文件 — 部署流程参考
  - Task 6 证据文件 — main→orch 验证结果
  - `~/.openclaw/logs/gateway.log` — ACP spawn 记录
  - `~/.acpx/sessions/` — 新 ACP session 文件
  - **WHY**: 验证链路第三层（orch→opencode）

  **Acceptance Criteria**:
  - [ ] orch dispatch skill 部署成功
  - [ ] orch 对 "用 opencode 修 bug" 的任务选择 ACP 路径
  - [ ] gateway.log 或 acpx session 中出现 opencode spawn 记录

  **QA Scenarios**:
  ```
  Scenario: orch 分发到 opencode
    Tool: Bash
    Steps:
      1. python -m openclaw_enhance.cli install
      2. openclaw agent --agent oe-orchestrator -m "用 opencode 修复 openclaw-enhance 项目中的 ruff lint 错误，要先提issue再开worktree"
      3. sleep 60
      4. ls -lt ~/.acpx/sessions/ | head -3
      5. grep "opencode\|acp" ~/.openclaw/logs/gateway.log | tail -10
    Expected Result: 新 ACP session 被创建，或 gateway.log 中有 opencode spawn 记录
    Failure Indicators: orch 自己处理任务或分发给 oe-script_coder
    Evidence: .sisyphus/evidence/task-8-orch-opencode.txt
  ```

  **Commit**: NO (部署+验证任务)

- [ ] 9. Full chain integration test: Feishu-like scenario

  **What to do**:
  - 模拟完整 Feishu 场景：通过 main session 发送类似用户原始请求的消息
  - 验证完整链路：main → (被 block) → sessions_spawn → oe-orchestrator → dispatch skill → ACP/opencode
  - 记录每一层的日志和 session 数据
  - 如果任何环节失败，记录具体失败点和原因

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`verification-before-completion`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 10
  - **Blocked By**: Task 8

  **References**:
  - 飞书原始消息："在公司有个openclaw-enhance 你让opencode去改，要先提issue，再开worktree，再pr，再merge"
  - Tasks 5-8 的所有证据文件

  **Acceptance Criteria**:
  - [ ] 完整链路至少走到 orch dispatch 阶段
  - [ ] 记录完整的 session 追踪日志

  **QA Scenarios**:
  ```
  Scenario: 完整链路测试
    Tool: Bash
    Steps:
      1. openclaw agent --agent main -m "在公司有个openclaw-enhance 你让opencode去改session清理的bug，要先提issue再开worktree再pr再merge"
      2. sleep 120
      3. grep -E "spawn|orchestrator|opencode|acp|BLOCKED" ~/.openclaw/logs/gateway.log | tail -20
    Expected Result: 日志显示 main→block→spawn orch→dispatch opencode 完整链路
    Evidence: .sisyphus/evidence/task-9-full-chain.txt
  ```

  **Commit**: NO

- [ ] 10. Update handbook + docs with routing chain status

  **What to do**:
  - 更新 `docs/opencode-iteration-handbook.md`：记录 routing-chain-fix milestone
  - 记录已修复的问题：null guard, fail-closed, agentId param, dispatch skill
  - 记录当前链路状态和已知限制
  - 更新 PLAYBOOK.md（如果路由行为变化影响系统能力清单）

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: F1-F4
  - **Blocked By**: Task 9

  **Acceptance Criteria**:
  - [ ] handbook 更新包含 routing chain 修复记录
  - [ ] `python -m openclaw_enhance.cli docs-check` 通过

  **Commit**: YES
  - Message: `docs(handbook): record routing-chain-fix milestone`
  - Files: `docs/opencode-iteration-handbook.md`, `PLAYBOOK.md`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search codebase for forbidden patterns. Check evidence files exist. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

  **QA Scenarios**:
  ```
  Scenario: Must Have 验证
    Tool: Bash
    Steps:
      1. grep -l "typeof sessionKey" extensions/openclaw-enhance-runtime/index.ts — 确认 null guard 存在
      2. grep -l "try" extensions/openclaw-enhance-runtime/index.ts — 确认 try/catch 存在
      3. grep -l "agentId" extensions/openclaw-enhance-runtime/index.ts — 确认正确参数名
      4. grep -l "runtime.*acp" workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md — 确认 ACP 分支
      5. ls .sisyphus/evidence/task-*  — 确认证据文件存在
    Expected Result: 所有 grep 匹配成功，证据文件存在
    Evidence: .sisyphus/evidence/final-qa/f1-compliance.txt

  Scenario: Must NOT Have 验证
    Tool: Bash + Grep
    Steps:
      1. 搜索仓库中是否有 OpenClaw 源码修改（不应有）
      2. 确认 workspaces/ 下不存在 oe-acp 目录
      3. 确认 oe-main-routing-gate 仍为 advisory（不含 block: true）
    Expected Result: 所有禁止项均不存在
    Evidence: .sisyphus/evidence/final-qa/f1-must-not-have.txt
  ```

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `tsc --noEmit` + linter + `bun test`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod. Check AI slop.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | VERDICT`

  **QA Scenarios**:
  ```
  Scenario: TypeScript 编译和测试
    Tool: Bash
    Steps:
      1. cd extensions/openclaw-enhance-runtime && npx tsc --noEmit
      2. bun test extensions/openclaw-enhance-runtime/
      3. python -m pytest tests/ -k "runtime or routing" --tb=short
    Expected Result: 编译无错误，所有测试通过
    Evidence: .sisyphus/evidence/final-qa/f2-quality.txt

  Scenario: 代码质量检查
    Tool: Bash + Grep
    Steps:
      1. grep -rn "as any\|@ts-ignore\|console.log" extensions/openclaw-enhance-runtime/index.ts
      2. grep -rn "catch.*{}" extensions/openclaw-enhance-runtime/index.ts（空 catch）
    Expected Result: 无 as any / @ts-ignore / console.log / 空 catch
    Evidence: .sisyphus/evidence/final-qa/f2-lint.txt
  ```

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task. Test cross-task integration. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

  **QA Scenarios**:
  ```
  Scenario: 全部 task QA 场景回归
    Tool: Bash
    Steps:
      1. 依次执行 Task 1-9 中所有 QA scenario 的具体命令
      2. 对每个 scenario 记录 PASS/FAIL
      3. 测试跨 task 集成：install → restart → tool block → spawn orch → dispatch opencode
    Expected Result: 所有 scenario 通过或记录已知限制
    Evidence: .sisyphus/evidence/final-qa/f3-regression.txt

  Scenario: 跨 task 集成测试
    Tool: Bash
    Steps:
      1. python -m openclaw_enhance.cli install
      2. openclaw gateway restart
      3. sleep 10
      4. openclaw agent --agent main -m "修复 openclaw-enhance 的 ruff lint 问题，用 opencode 来改"
      5. sleep 60
      6. grep -E "BLOCKED|oe-orchestrator|opencode|acp" ~/.openclaw/logs/gateway.log | tail -20
    Expected Result: 日志显示完整路由链路
    Evidence: .sisyphus/evidence/final-qa/f3-integration.txt
  ```

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance.
  Output: `Tasks [N/N compliant] | VERDICT`

  **QA Scenarios**:
  ```
  Scenario: 逐 task 对照检查
    Tool: Bash + Read
    Steps:
      1. git diff main --stat — 列出所有变更文件
      2. 对每个变更文件，读取对应 task 的 "What to do" 和 "Must NOT do"
      3. 确认变更与 spec 一致，无 scope creep
    Expected Result: 每个变更文件都能追溯到具体 task spec
    Evidence: .sisyphus/evidence/final-qa/f4-fidelity.txt
  ```

---

## Commit Strategy

- **Commit 1**: `fix(runtime): add null guard and fail-closed to oe-runtime before_tool_call` — index.ts
- **Commit 2**: `test(runtime): add unit tests for oe-runtime tool gate` — runtime-bridge.test.ts
- **Commit 3**: `fix(runtime): correct sessions_spawn param name (agentId not agent)` — index.ts
- **Commit 4**: `feat(dispatch): add opencode/ACP dispatch branch to oe-worker-dispatch` — SKILL.md
- **Commit 5**: `test(integration): add deployment verification and E2E routing tests` — test files
- **Commit 6**: `docs(handbook): record routing-chain-fix milestone` — opencode-iteration-handbook.md

---

## Success Criteria

### Verification Commands
```bash
bun test extensions/openclaw-enhance-runtime/  # Expected: all pass
python -m pytest tests/ -k "runtime or routing"  # Expected: all pass
python -m openclaw_enhance.cli install  # Expected: success
openclaw plugins list  # Expected: shows oe-runtime
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] oe-runtime deployed and functioning
- [ ] main session tools blocked when appropriate
- [ ] main→orch routing verified in live
- [ ] orch→opencode dispatch skill in place
