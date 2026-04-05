# Session Isolation Restart Guardrails

## TL;DR

> Add openclaw-enhance-only guardrails that fail closed when post-restart session ownership is ambiguous, prevent channel-agnostic fallback from collapsing Feishu and Telegram into the same OpenClaw session context, and sanitize leaked internal markers on enhance-controlled outward paths.
>
> **Deliverables**:
> - Channel-aware ownership metadata in enhance runtime state
> - Restart epoch / stale-binding safety checks
> - Safer spawn/runtime guardrails that reject ambiguous reuse instead of silently falling back
> - Deterministic sanitizer for leaked internal markers in enhance-controlled output paths
> - TDD coverage for restart collision blocking, same-channel resume, stale legacy state, and sanitization
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: T1 → T4 → T8 → T12 → F1-F4

---

## Context

### Original Request
用户反馈：重启 OpenClaw 后，飞书和 Telegram 仍会同时修改同一个 session；同时最新 session 中出现了不应该泄漏给用户的内部文本，例如 `[Pasted ~1 lines]`、`<|tool_calls_section_begin|>` 等。要求先查根因，再给出如何修改的工作计划。

### Interview Summary
**Key Discussions**:
- 用户明确要求把“跨渠道串 session”与“内部文本泄漏”当成一个整体问题处理。
- 修复范围被锁定为 **openclaw-enhance / hook / config / governance guardrails only**，不修改 OpenClaw core。
- 测试策略选择为 **TDD**。

**Research Findings**:
- `openclaw-enhance` 当前没有 `{channel, external_conversation} -> openclaw_session` 级别的 ownership map，也没有重启后 rebind/reconcile 逻辑。
- `hooks/oe-subagent-spawn-enrich/handler.ts` 存在 `context.parent_session ?? context.session_id` 注入和 `active_project/default` fallback，可能放大跨渠道上下文塌缩风险。
- `extensions/openclaw-enhance-runtime/index.ts` 的 `isMainSession()` 识别范围扩大到了 `main` 和对象归一化 key，存在把不同来源会话归并到同一逻辑 main 的风险。
- `src/openclaw_enhance/governance/restart.py` 只检查 `openclaw sessions --json` 是否为空，不做 ownership rehydrate。
- `src/openclaw_enhance/runtime/schema.py` / `project_state.py` 只有 `active_project` 和 `project_occupancy`，没有 channel 维度状态。
- 当前测试覆盖 project occupancy、spawn/runtime contract，但没有 restart-driven multi-channel collision 或 leaked marker sanitization 测试。

### Metis Review
**Identified Gaps** (addressed):
- 缺少对“什么算 collision”的明确定义 → 本计划定义为：不同 `(channel_type, channel_conversation_id)` 试图复用同一 enhance-managed session lineage / binding 时视为 collision。
- 缺少 fail-open vs fail-closed 策略 → 本计划明确采用 **fail-closed**：身份缺失、过期、歧义时拒绝复用。
- 缺少输出过滤边界 → 本计划仅覆盖 enhance-controlled outward paths 的 deterministic sanitizer，不假设可拦截 core 全部输出。
- 缺少 legacy/backward-compat 策略 → 本计划要求 pre-guard state 进入“stale/needs rebind”路径而不是继续隐式复用。

---

## Work Objectives

### Core Objective
在不修改 OpenClaw core 的前提下，为 openclaw-enhance 增加一层“会话归属与重启安全护栏”：当跨渠道身份不匹配、状态过期、或绑定信息缺失时，系统必须拒绝危险复用；同时对 enhance 可控输出路径做内部标记净化，避免明显的 tool-call / pasted sentinel 文本外泄。

### Concrete Deliverables
- 扩展 runtime state schema，支持 channel-aware ownership metadata 与 restart epoch。
- 新增/调整 governance/runtime helpers，用于写入、读取、校验 session ownership binding。
- 收紧 spawn-enrich 和 runtime gate 的 fallback 逻辑，禁止缺少 channel identity 时隐式复用。
- 新增 sanitizer 模块与 enhance-controlled 输出接入点。
- 新增 Python + TypeScript 自动化测试，以及真实环境验证方案。
- 相关文档 / PLAYBOOK 更新。

### Definition of Done
- [ ] 针对“重启后 Feishu/TG 共享 session”有自动化失败测试，且修复后通过。
- [ ] 同渠道合法 resume 仍可通过自动化测试和真实环境 QA。
- [ ] 增强层可控输出路径不再包含已知内部标记 token。
- [ ] `pytest tests/unit -q --tb=short`、`pytest tests/integration -q --tb=short`、`npm test`、`npm run typecheck` 通过。
- [ ] `python -m openclaw_enhance.cli docs-check` 通过。

### Must Have
- 对 ownership ambiguity 采用 fail-closed。
- ownership key 至少包含 `channel_type` + `channel_conversation_id`。
- restart 后旧绑定必须经历显式验证，不能静默复用。
- sanitizer 只做 deterministic token stripping，不做泛化内容理解。
- 所有任务均包含 agent-executed QA scenarios。

### Must NOT Have (Guardrails)
- 不修改 OpenClaw core bridge/rendering/session internals。
- 不把问题扩展成整个架构重写或 generalized content filtering system。
- 不允许在 channel identity 缺失时退回到 `active_project/default` 并继续正常流转。
- 不允许 acceptance criteria 依赖“用户手动看看”。

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: TDD
- **Framework**: pytest + Node.js built-in test runner + existing TypeScript typecheck
- **If TDD**: Each implementation task starts with a failing test, then minimal implementation, then verification.

### QA Policy
Every task below includes agent-executed QA scenarios and evidence capture.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Python state/governance**: Bash (`pytest`) + captured output
- **TypeScript hook/extension**: Bash (`npm test`, `npx tsc --noEmit`) + captured output
- **CLI/runtime integration**: Bash (`python -m openclaw_enhance.cli ...`) + captured JSON/text output
- **Real-environment validation**: Bash + generated report under `docs/reports/`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation + test scaffolding):
├── Task 1: Define ownership contract + runtime schema tests [quick]
├── Task 2: Add sanitizer token-spec tests [quick]
├── Task 3: Add spawn-enrich regression tests for ambiguous fallback [unspecified-high]
├── Task 4: Add runtime-gate session identity tests [unspecified-high]
└── Task 5: Map docs/PLAYBOOK touchpoints for new guardrails [writing]

Wave 2 (Core guardrails, depends on Wave 1):
├── Task 6: Implement runtime ownership state helpers (depends: 1) [unspecified-high]
├── Task 7: Implement sanitizer module + unit coverage (depends: 2) [quick]
├── Task 8: Tighten spawn-enrich ownership/fallback behavior (depends: 3, 6) [deep]
├── Task 9: Tighten runtime main-session normalization / fail-closed behavior (depends: 4, 6) [deep]
└── Task 10: Update docs/PLAYBOOK for new runtime guardrails (depends: 5, 6, 7, 8, 9) [writing]

Wave 3 (Restart safety + cleanup integration):
├── Task 11: Add restart epoch + stale-binding checks in governance/runtime (depends: 6) [unspecified-high]
├── Task 12: Integrate sanitizer into enhance-controlled outward paths (depends: 7, 9) [deep]
├── Task 13: Make cleanup/legacy-state classification ownership-aware (depends: 6, 11) [unspecified-high]
└── Task 14: Add integration tests for restart collision blocking + same-channel resume (depends: 8, 9, 11, 13) [deep]

Wave 4 (Validation + final doc alignment):
├── Task 15: Add real-environment validation entry/report coverage (depends: 10, 12, 14) [unspecified-high]
├── Task 16: Run docs-check / CI-equivalent verification updates (depends: 10, 14, 15) [quick]
└── Task 17: Commit preparation and evidence collation (depends: 15, 16) [quick]

Wave FINAL:
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
```

### Dependency Matrix
- **1**: - → 6, 1
- **2**: - → 7, 1
- **3**: - → 8, 1
- **4**: - → 9, 1
- **5**: - → 10, 1
- **6**: 1 → 8, 9, 10, 11, 13, 2
- **7**: 2 → 10, 12, 2
- **8**: 3, 6 → 14, 2
- **9**: 4, 6 → 10, 12, 14, 2
- **10**: 5, 6, 7, 8, 9 → 15, 16, 2
- **11**: 6 → 13, 14, 3
- **12**: 7, 9 → 15, 3
- **13**: 6, 11 → 14, 3
- **14**: 8, 9, 11, 13 → 15, 16, 3
- **15**: 10, 12, 14 → 17, 16, 4
- **16**: 10, 14, 15 → 17, 4
- **17**: 15, 16 → F1-F4, 4

### Agent Dispatch Summary
- **1**: **5** - T1 `quick`, T2 `quick`, T3 `unspecified-high`, T4 `unspecified-high`, T5 `writing`
- **2**: **5** - T6 `unspecified-high`, T7 `quick`, T8 `deep`, T9 `deep`, T10 `writing`
- **3**: **4** - T11 `unspecified-high`, T12 `deep`, T13 `unspecified-high`, T14 `deep`
- **4**: **3** - T15 `unspecified-high`, T16 `quick`, T17 `quick`
- **FINAL**: **4** - F1 `oracle`, F2 `unspecified-high`, F3 `unspecified-high`, F4 `deep`

---

## TODOs

- [x] 1. Define ownership contract + runtime schema tests

  **What to do**:
  - Add failing Python tests for runtime state schema evolution covering new ownership metadata fields and restart epoch defaults.
  - Define expected backward-compatible behavior when old runtime-state files lack channel ownership data.
  - Specify the ownership contract shape that enhance layer will persist, including `channel_type`, `channel_conversation_id`, `bound_session_id`, `binding_epoch`, and binding status.

  **Must NOT do**:
  - Do not invent a generalized user/account identity model beyond what restart collision prevention requires.
  - Do not break legacy runtime-state loading.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: focused Python test/schema changes in a small number of files.
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: required because this task defines the failing tests first.
  - **Skills Evaluated but Omitted**:
    - `systematic-debugging`: investigation is already complete; this task is test/spec codification.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5)
  - **Blocks**: 6
  - **Blocked By**: None

  **References**:
  - `src/openclaw_enhance/runtime/schema.py:7-28` - Current runtime state model; extend this rather than creating a second state file.
  - `src/openclaw_enhance/runtime/project_state.py:11-55` - Shows backward-compatible load/save behavior and atomic persistence pattern.
  - `tests/integration/test_runtime_project_state.py:22-88` - Existing test style for backward compatibility and occupancy locking.

  **Acceptance Criteria**:
  - [ ] New tests assert missing ownership fields load safely with defaults.
  - [ ] New tests assert ownership contract fields exist in validated runtime state.
  - [ ] `pytest tests/integration/test_runtime_project_state.py -q --tb=short` fails before implementation and passes after implementation.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Legacy runtime state upgrades safely
    Tool: Bash (pytest)
    Preconditions: Failing test added for loading old runtime-state payload without ownership metadata
    Steps:
      1. Run `pytest tests/integration/test_runtime_project_state.py -q --tb=short`
      2. Capture the failing assertion for missing/defaulted ownership fields
      3. After implementation, rerun the same command
    Expected Result: Initial FAIL, then PASS with tests asserting default-safe load path
    Failure Indicators: Legacy JSON crashes validation or silently produces malformed ownership state
    Evidence: .sisyphus/evidence/task-1-legacy-runtime-schema.txt

  Scenario: Ownership contract fields persisted deterministically
    Tool: Bash (pytest)
    Preconditions: Test writes runtime state using temp home fixture
    Steps:
      1. Run targeted test for schema persistence
      2. Assert stored state contains expected keys: `channel_type`, `channel_conversation_id`, `binding_epoch`
    Expected Result: PASS with exact field assertions
    Failure Indicators: Fields absent, renamed unexpectedly, or non-deterministic values appear
    Evidence: .sisyphus/evidence/task-1-ownership-contract.txt
  ```

  **Commit**: NO

- [x] 2. Add sanitizer token-spec tests

  **What to do**:
  - Add failing tests for a deterministic sanitizer that strips known internal markers from enhance-controlled outward text.
  - Cover at least these markers: `[Pasted ~N lines]`, `<|tool_calls_section_begin|>`, `<|tool_call_begin|>`, `<|tool_call_end|>`, `<|tool_calls_section_end|>`.
  - Include a non-regression case ensuring ordinary user text is preserved.

  **Must NOT do**:
  - Do not build semantic moderation or rewrite unrelated user content.
  - Do not assume the sanitizer can intercept every core-rendered path.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: isolated test-first utility spec work.
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: task is explicitly test-first.
  - **Skills Evaluated but Omitted**:
    - `writing-skills`: not relevant; no skill authoring involved.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4, 5)
  - **Blocks**: 7
  - **Blocked By**: None

  **References**:
  - Latest OpenClaw session transcript evidence from `ses_2aeba3679ffetOREvSvdNCCjUd` - Demonstrates real leaked markers to normalize against.
  - `tests/integration/test_spawn_event_contract.py:184-216` - Existing TypeScript verification pattern in repo.
  - `extensions/openclaw-enhance-runtime/index.ts:73-110` - Candidate extension boundary where sanitized outward messages may need to be enforced or supported.

  **Acceptance Criteria**:
  - [ ] Tests fail before sanitizer implementation.
  - [ ] Tests verify leaked markers are removed while normal prose remains intact.
  - [ ] `npm test` covers the sanitizer spec once implemented.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Known internal markers are stripped
    Tool: Bash (npm test)
    Preconditions: New TypeScript/Node tests added for sanitizer function
    Steps:
      1. Run `npm test`
      2. Confirm sanitizer test cases include literal marker tokens from the reported leak
      3. After implementation, rerun and verify pass
    Expected Result: Tests transition from FAIL to PASS and assert stripped output contains none of the marker literals
    Failure Indicators: Any leaked marker still appears in sanitized output
    Evidence: .sisyphus/evidence/task-2-sanitizer-strip.txt

  Scenario: Legitimate user prose is preserved
    Tool: Bash (npm test)
    Preconditions: Test includes regular sentence with angle brackets / brackets that should remain
    Steps:
      1. Run sanitizer preservation test
      2. Assert non-token text remains unchanged except deterministic whitespace normalization if specified
    Expected Result: PASS preserving benign content
    Failure Indicators: Over-sanitization deletes legitimate user text
    Evidence: .sisyphus/evidence/task-2-sanitizer-preserve.txt
  ```

  **Commit**: NO

- [x] 3. Add spawn-enrich regression tests for ambiguous fallback

  **What to do**:
  - Add failing tests around `enrichSpawnEvent()` covering ambiguous parent session and project fallback after restart.
  - Define a red path where missing channel ownership metadata must block or mark the payload unsafe rather than silently using `active_project/default` and `context.session_id`.
  - Cover dedupe behavior so different channels cannot produce indistinguishable keys when ownership metadata is present.

  **Must NOT do**:
  - Do not keep existing fallback behavior untested.
  - Do not treat channel identity as optional in the new guarded path.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: this touches subtle hook contract behavior and regression boundaries.
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: ensures regression is locked before behavior changes.
  - **Skills Evaluated but Omitted**:
    - `systematic-debugging`: already completed; now encoding the repro into tests.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4, 5)
  - **Blocks**: 8
  - **Blocked By**: None

  **References**:
  - `hooks/oe-subagent-spawn-enrich/handler.ts:120-191` - Current `resolveProjectContext()` fallback chain that must be constrained.
  - `hooks/oe-subagent-spawn-enrich/handler.ts:272-315` - Current `parent_session` injection and dedupe generation flow.
  - `tests/integration/test_spawn_event_contract.py:19-183` - Existing spawn contract tests to extend instead of inventing a separate style.

  **Acceptance Criteria**:
  - [ ] Tests encode failure for missing/ambiguous ownership metadata after restart.
  - [ ] Tests encode channel-aware dedupe/ownership expectations.
  - [ ] Hook tests fail before implementation and pass after.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Ambiguous restart context is rejected instead of silently falling back
    Tool: Bash (npm test)
    Preconditions: New tests simulate spawn input without valid ownership metadata after restart
    Steps:
      1. Run `npm test`
      2. Confirm failing assertion expects refusal / unsafe marker rather than `project=default` + reused parent_session
      3. After implementation, rerun tests
    Expected Result: PASS with explicit guarded behavior
    Failure Indicators: Test output still shows default fallback accepted as valid
    Evidence: .sisyphus/evidence/task-3-ambiguous-fallback.txt

  Scenario: Cross-channel dedupe keys remain distinct
    Tool: Bash (npm test)
    Preconditions: Test uses same task description with two distinct channel ownership identities
    Steps:
      1. Run dedupe-specific test
      2. Assert generated keys differ when channel ownership differs
    Expected Result: PASS with deterministic non-colliding keys
    Failure Indicators: Keys are identical across channels for same task payload
    Evidence: .sisyphus/evidence/task-3-dedupe-channel.txt
  ```

  **Commit**: NO

- [x] 4. Add runtime-gate session identity tests

  **What to do**:
  - Add failing tests around `normalizeSessionKey()` / `isMainSession()` and any new ownership-aware runtime checks.
  - Define expected behavior for ambiguous object keys, missing session identity, and cross-channel-derived main detection.
  - Ensure fail-closed blocking behavior is test-covered when main-session classification cannot be established safely.

  **Must NOT do**:
  - Do not preserve broad “accept any shape with `id`/`key`” semantics without tests.
  - Do not let undefined/ambiguous keys pass through as trusted main.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: touches runtime safety semantics and possible regressions.
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: required to lock fail-closed semantics.
  - **Skills Evaluated but Omitted**:
    - `verification-before-completion`: applies later for final checks, not initial task design.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 5)
  - **Blocks**: 9
  - **Blocked By**: None

  **References**:
  - `extensions/openclaw-enhance-runtime/index.ts:18-33` - Current session key normalization and main detection logic.
  - `extensions/openclaw-enhance-runtime/index.ts:72-110` - Fail-closed `before_tool_call` behavior that should become ownership-aware.
  - `extensions/openclaw-enhance-runtime/src/runtime-bridge.test.ts` - Existing TypeScript test location referenced by integration tests.

  **Acceptance Criteria**:
  - [ ] Tests cover ambiguous object-shaped session keys.
  - [ ] Tests verify cross-channel/unknown identity cases fail closed.
  - [ ] `npm test` shows new runtime gate coverage passing after implementation.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Ambiguous session key objects fail closed
    Tool: Bash (npm test)
    Preconditions: New tests feed object session keys missing canonical ownership fields
    Steps:
      1. Run `npm test`
      2. Observe failing assertion before implementation
      3. Re-run after implementation and verify blocked path
    Expected Result: PASS with explicit block path for ambiguous identity
    Failure Indicators: Ambiguous object key is still recognized as valid main session
    Evidence: .sisyphus/evidence/task-4-ambiguous-main-key.txt

  Scenario: Legitimate main session still recognized
    Tool: Bash (npm test)
    Preconditions: Tests include `main` and `agent:main:*` canonical forms
    Steps:
      1. Run targeted runtime gate test
      2. Assert canonical main keys still pass intended checks
    Expected Result: PASS preserving valid routing behavior
    Failure Indicators: Canonical main sessions are blocked unexpectedly
    Evidence: .sisyphus/evidence/task-4-main-compat.txt
  ```

  **Commit**: NO

- [x] 5. Map docs/PLAYBOOK touchpoints for new guardrails

  **What to do**:
  - Identify which permanent docs must be updated when session ownership guardrails and sanitization are introduced.
  - Add failing doc/task checklist coverage if repo has contract-style doc tests or at minimum define exact sections to update in the plan.
  - Ensure PLAYBOOK remains authoritative for hook/runtime/CLI behavior changes.

  **Must NOT do**:
  - Do not defer documentation impact until after code lands.
  - Do not create new permanent docs unless existing canonical docs are insufficient.

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: documentation mapping and canonical-source alignment.
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `writing-skills`: not editing agent skills; documentation only.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4)
  - **Blocks**: 10
  - **Blocked By**: None

  **References**:
  - `PLAYBOOK.md` - Must reflect any hook/extension/runtime behavior changes.
  - `docs/operations.md` - Runtime behavior and restart flow source of truth.
  - `docs/architecture.md` - Guardrail/control-flow changes must remain aligned.
  - `AGENTS.md` + `docs/opencode-iteration-handbook.md` - Project invariants and durable memory expectations.

  **Acceptance Criteria**:
  - [ ] Exact doc files and sections to update are enumerated.
  - [ ] Plan explicitly includes PLAYBOOK synchronization.
  - [ ] No undocumented runtime behavior change remains in scope.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Documentation touchpoints are fully enumerated
    Tool: Bash (python/grep as needed via docs-check later)
    Preconditions: Plan references all impacted docs
    Steps:
      1. Review the identified canonical docs in the plan
      2. Confirm each runtime/hook change has a matching doc target
    Expected Result: Clear 1:1 mapping from behavior change to doc file
    Failure Indicators: A runtime/hook change lacks a documented destination
    Evidence: .sisyphus/evidence/task-5-doc-touchpoints.txt

  Scenario: PLAYBOOK remains in sync requirement is explicit
    Tool: Bash
    Preconditions: Plan includes PLAYBOOK update task dependency
    Steps:
      1. Verify task text names PLAYBOOK explicitly
      2. Capture plan section showing synchronization requirement
    Expected Result: PASS with explicit PLAYBOOK mention
    Failure Indicators: PLAYBOOK omitted from scope
    Evidence: .sisyphus/evidence/task-5-playbook-sync.txt
  ```

  **Commit**: NO

- [x] 6. Implement runtime ownership state helpers

  **What to do**:
  - Extend runtime schema and state helpers to persist channel-aware ownership bindings and restart epoch metadata.
  - Add helper APIs for creating, reading, validating, and invalidating bindings.
  - Keep migration/backward compatibility intact for existing runtime-state files.

  **Must NOT do**:
  - Do not create a second competing runtime-state store.
  - Do not silently discard malformed legacy state without marking it stale/unsafe.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: moderate-risk Python state model changes with compatibility requirements.
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: implement against Task 1 failing tests.
  - **Skills Evaluated but Omitted**:
    - `systematic-debugging`: root-cause work already complete.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7, 10)
  - **Blocks**: 8, 9, 10, 11, 13
  - **Blocked By**: 1

  **References**:
  - `src/openclaw_enhance/runtime/schema.py:7-28` - Current runtime state model to extend.
  - `src/openclaw_enhance/runtime/project_state.py:11-90` - Load/save and helper API patterns to follow.
  - `tests/integration/test_runtime_project_state.py:22-88` - Existing compatibility and occupancy test style.

  **Acceptance Criteria**:
  - [ ] Runtime state supports ownership bindings and restart epoch without breaking legacy loads.
  - [ ] Helper APIs allow deterministic validation/invalidation of bindings.
  - [ ] Targeted pytest file passes.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Ownership helpers persist and reload binding state
    Tool: Bash (pytest)
    Preconditions: Implementation complete against Task 1 tests
    Steps:
      1. Run `pytest tests/integration/test_runtime_project_state.py -q --tb=short`
      2. Confirm helper APIs store and reload ownership metadata via temp runtime state file
    Expected Result: PASS with binding data preserved across reload
    Failure Indicators: Reloaded state loses binding metadata or changes semantics
    Evidence: .sisyphus/evidence/task-6-runtime-binding.txt

  Scenario: Malformed legacy binding fails safely
    Tool: Bash (pytest)
    Preconditions: Test fixture writes partial/invalid ownership metadata
    Steps:
      1. Run targeted malformed-state test
      2. Assert helper marks state stale/unsafe instead of trusting it
    Expected Result: PASS with fail-safe path
    Failure Indicators: Invalid binding treated as authoritative
    Evidence: .sisyphus/evidence/task-6-malformed-binding.txt
  ```

  **Commit**: NO

- [x] 7. Implement sanitizer module + unit coverage

  **What to do**:
  - Implement a deterministic sanitizer utility for enhance-controlled outward text.
  - Strip only the known internal markers and normalize surrounding whitespace conservatively.
  - Make the utility easy to call from runtime/hook integration points.

  **Must NOT do**:
  - Do not hide arbitrary stack traces or unrelated content unless explicitly token-matched.
  - Do not make sanitizer behavior probabilistic.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: narrow utility implementation with direct test coverage.
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: implement only enough to satisfy Task 2 tests.
  - **Skills Evaluated but Omitted**:
    - `ai-slop-remover`: not appropriate during initial implementation.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 10)
  - **Blocks**: 10, 12
  - **Blocked By**: 2

  **References**:
  - Leaked marker examples from latest OpenClaw session transcript - use literal reported tokens.
  - `extensions/openclaw-enhance-runtime/index.ts` - likely integration boundary for calling sanitizer.
  - TypeScript test location referenced in `tests/integration/test_spawn_event_contract.py:94-109`.

  **Acceptance Criteria**:
  - [ ] Sanitizer removes known markers and preserves benign text.
  - [ ] Unit tests added in existing TS test suite pass.
  - [ ] Sanitizer API is deterministic and reusable.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Sanitizer removes all known marker classes
    Tool: Bash (npm test)
    Preconditions: Sanitizer utility implemented
    Steps:
      1. Run `npm test`
      2. Confirm tests cover pasted sentinel and tool-call section markers
    Expected Result: PASS with sanitized output free of marker tokens
    Failure Indicators: Any known token remains
    Evidence: .sisyphus/evidence/task-7-sanitizer-unit.txt

  Scenario: Sanitizer preserves normal text structure
    Tool: Bash (npm test)
    Preconditions: Preservation test exists
    Steps:
      1. Run targeted sanitizer preservation test
      2. Assert regular prose remains legible and not over-trimmed
    Expected Result: PASS with minimal output mutation
    Failure Indicators: Benign text removed or excessively mangled
    Evidence: .sisyphus/evidence/task-7-sanitizer-safe.txt
  ```

  **Commit**: NO

- [x] 8. Tighten spawn-enrich ownership/fallback behavior

  **What to do**:
  - Modify spawn enrichment so ownership metadata participates in parent-session selection and dedupe generation.
  - Reject or explicitly mark unsafe any restart-time request lacking validated ownership binding.
  - Remove channel-agnostic fallback paths that can collapse distinct channels into one session lineage.

  **Must NOT do**:
  - Do not silently continue with `context.parent_session ?? context.session_id` when ownership validation fails.
  - Do not keep dedupe keys channel-blind once ownership metadata exists.

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: central regression-risk hook logic with subtle routing consequences.
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: constrained by Task 3 failing tests.
  - **Skills Evaluated but Omitted**:
    - `systematic-debugging`: behavior decision already made; implementation should follow tests.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential within Wave 2
  - **Blocks**: 10, 14
  - **Blocked By**: 3, 6

  **References**:
  - `hooks/oe-subagent-spawn-enrich/handler.ts:120-191` - `resolveProjectContext()` fallback chain.
  - `hooks/oe-subagent-spawn-enrich/handler.ts:272-315` - current parent session injection and dedupe generation logic.
  - `tests/integration/test_spawn_event_contract.py:151-183` - existing task_id / dedupe contract checks to update.

  **Acceptance Criteria**:
  - [ ] Ambiguous restart requests fail closed.
  - [ ] Channel-aware ownership influences dedupe and parent session behavior.
  - [ ] Existing spawn contract tests updated and passing.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Cross-channel restart reuse is blocked
    Tool: Bash (npm test)
    Preconditions: Hook behavior implemented against failing tests
    Steps:
      1. Run `npm test`
      2. Confirm cross-channel same-task restart case now returns blocked/unsafe result
    Expected Result: PASS with explicit refusal path
    Failure Indicators: Hook still emits valid enriched payload for unsafe cross-channel reuse
    Evidence: .sisyphus/evidence/task-8-cross-channel-block.txt

  Scenario: Same-channel valid resume still enriches correctly
    Tool: Bash (npm test)
    Preconditions: Test includes matching ownership metadata
    Steps:
      1. Run same-channel resume test
      2. Assert parent_session and dedupe are deterministically produced
    Expected Result: PASS preserving valid same-channel flow
    Failure Indicators: Legitimate same-channel resume now breaks
    Evidence: .sisyphus/evidence/task-8-same-channel-resume.txt
  ```

  **Commit**: NO

- [x] 9. Tighten runtime main-session normalization / fail-closed behavior

  **What to do**:
  - Narrow or supplement `normalizeSessionKey()` / `isMainSession()` so ambiguous keys cannot be trusted without ownership context.
  - Ensure runtime gate blocks unsafe paths when main-session detection is uncertain during restart/rebind windows.
  - Keep canonical main routing behavior intact.

  **Must NOT do**:
  - Do not over-correct by breaking legitimate `main` or `agent:main:*` flows.
  - Do not rely on unchecked object `id/key` fields alone.

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: extension safety logic with high blast radius if wrong.
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: guided by Task 4 failing tests.
  - **Skills Evaluated but Omitted**:
    - `verification-before-completion`: final verification step, not core implementation.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential within Wave 2
  - **Blocks**: 10, 12, 14
  - **Blocked By**: 4, 6

  **References**:
  - `extensions/openclaw-enhance-runtime/index.ts:18-33` - existing normalization helpers.
  - `extensions/openclaw-enhance-runtime/index.ts:73-110` - fail-closed block logic to preserve.
  - `tests/integration/test_spawn_event_contract.py:71-109` - runtime extension contract existence and tests.

  **Acceptance Criteria**:
  - [ ] Ambiguous session keys are not trusted as valid main.
  - [ ] Canonical main flows still work.
  - [ ] Runtime tests pass under `npm test` and typecheck remains clean.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Ambiguous session identity blocks main-only tool path
    Tool: Bash (npm test)
    Preconditions: Runtime gate updated and tested
    Steps:
      1. Run `npm test`
      2. Verify ambiguous key path leads to block/fail-safe in tests
    Expected Result: PASS with block assertion
    Failure Indicators: Unsafe identity accepted as main
    Evidence: .sisyphus/evidence/task-9-runtime-failclosed.txt

  Scenario: Canonical main keys preserve existing gate semantics
    Tool: Bash (npm test)
    Preconditions: Tests include `main` and `agent:main:*`
    Steps:
      1. Run canonical key tests
      2. Assert expected tool blocking rules still apply only where intended
    Expected Result: PASS without regression in valid main behavior
    Failure Indicators: Valid main routing path breaks or becomes over-permissive
    Evidence: .sisyphus/evidence/task-9-runtime-main-compat.txt
  ```

  **Commit**: NO

- [x] 10. Update docs/PLAYBOOK for new runtime guardrails

  **What to do**:
  - Update canonical docs and PLAYBOOK to describe ownership bindings, restart epoch behavior, fail-closed collision handling, and sanitizer boundaries.
  - Keep docs aligned with actual guardrail limits: enhance-controlled only, not full core interception.
  - Ensure docs-check expectations remain satisfied.

  **Must NOT do**:
  - Do not describe capabilities the implementation does not provide.
  - Do not omit PLAYBOOK if hook/extension/runtime behavior changed.

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: documentation alignment work.
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `writing-skills`: not editing skills.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7)
  - **Blocks**: 15, 16
  - **Blocked By**: 5, 6, 7, 8, 9

  **References**:
  - `PLAYBOOK.md` - system capability authority that must reflect runtime/hook changes.
  - `docs/operations.md` - restart/runtime guardrail behavior.
  - `docs/architecture.md` - ownership and sanitization boundaries.
  - `docs/opencode-iteration-handbook.md` - if permanent architecture state changes warrant mention.

  **Acceptance Criteria**:
  - [ ] All changed behaviors have canonical doc destinations.
  - [ ] PLAYBOOK updated if capabilities/behavior changed.
  - [ ] `python -m openclaw_enhance.cli docs-check` passes later in verification.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Canonical docs mention new ownership guardrails accurately
    Tool: Bash (docs-check later)
    Preconditions: Documentation updated
    Steps:
      1. Run `python -m openclaw_enhance.cli docs-check`
      2. Inspect output for pass/fail
    Expected Result: PASS with docs aligned to behavior
    Failure Indicators: docs-check fails or docs overclaim capabilities
    Evidence: .sisyphus/evidence/task-10-docs-check.txt

  Scenario: PLAYBOOK includes guardrail changes
    Tool: Bash
    Preconditions: PLAYBOOK updated
    Steps:
      1. Read PLAYBOOK sections covering Hook / Extension / Tool Gate / CLI behavior
      2. Capture evidence of ownership/sanitization guardrail description
    Expected Result: PASS with explicit updated capability listing
    Failure Indicators: PLAYBOOK omits runtime guardrail changes
    Evidence: .sisyphus/evidence/task-10-playbook.txt
  ```

  **Commit**: NO

- [x] 11. Add restart epoch + stale-binding checks in governance/runtime

  **What to do**:
  - Introduce a restart epoch / generation marker that changes on safe/immediate restart paths under enhance control.
  - Require existing ownership bindings to match the current epoch or be revalidated before reuse.
  - Update governance helpers so restart decisions and follow-up state reflect “resume requires rebind/validation”.

  **Must NOT do**:
  - Do not pretend to validate core channel reconnection internals.
  - Do not auto-trust pre-restart bindings.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Python governance + state coupling, moderate risk.
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: should extend Task 1/6 tests with restart lifecycle assertions.
  - **Skills Evaluated but Omitted**:
    - `systematic-debugging`: already complete.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 12, 13)
  - **Blocks**: 13, 14
  - **Blocked By**: 6

  **References**:
  - `src/openclaw_enhance/governance/restart.py:19-54` - current restart evaluation and restart/resume behavior.
  - `src/openclaw_enhance/runtime/project_state.py:25-55` - atomic persistence helper pattern.
  - `tests/integration/test_runtime_project_state.py` - nearby Python integration test style to extend.

  **Acceptance Criteria**:
  - [ ] Restart path records/bumps epoch metadata.
  - [ ] Stale bindings are rejected until revalidated.
  - [ ] Tests cover safe restart and immediate restart resume semantics.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Restart invalidates stale bindings
    Tool: Bash (pytest)
    Preconditions: Restart epoch tests added
    Steps:
      1. Run targeted restart/state pytest file(s)
      2. Assert binding valid before epoch change, stale after epoch change
    Expected Result: PASS with stale binding rejection
    Failure Indicators: Pre-restart binding remains silently valid after epoch bump
    Evidence: .sisyphus/evidence/task-11-restart-epoch.txt

  Scenario: Same-channel explicit revalidation restores access
    Tool: Bash (pytest)
    Preconditions: Tests include epoch bump then explicit rebind/validation path
    Steps:
      1. Run targeted revalidation test
      2. Assert same-channel resume succeeds only after revalidation
    Expected Result: PASS with explicit controlled recovery
    Failure Indicators: Resume still works without revalidation or fails even after valid rebind
    Evidence: .sisyphus/evidence/task-11-revalidate.txt
  ```

  **Commit**: NO

- [x] 12. Integrate sanitizer into enhance-controlled outward paths

  **What to do**:
  - Identify the enhance-controlled egress points that can sanitize outward text before it leaves enhance-controlled flow.
  - Wire the sanitizer from Task 7 into those paths.
  - Add integration tests proving known leaked markers are removed at those boundaries.

  **Must NOT do**:
  - Do not claim full protection for core-only output paths enhance cannot intercept.
  - Do not sanitize unrelated logs intended for internal debugging if not user-facing.

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: requires careful boundary identification and integration without overclaiming scope.
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: integration must satisfy prewritten tests.
  - **Skills Evaluated but Omitted**:
    - `playwright`: no browser interaction needed for this task.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 13)
  - **Blocks**: 15
  - **Blocked By**: 7, 9

  **References**:
  - `extensions/openclaw-enhance-runtime/index.ts:47-110` - extension registration and interception surface.
  - Relevant hook/extension files discovered during implementation - use actual egress points under enhance control.
  - Latest session transcript leak strings - exact literals to sanitize.

  **Acceptance Criteria**:
  - [ ] At least one enhance-controlled outward path sanitizes known markers.
  - [ ] Integration tests prove marker stripping at wired boundaries.
  - [ ] Documentation accurately states the coverage limit.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Sanitized output path strips leaked markers before outward delivery
    Tool: Bash (npm test / pytest depending on implementation surface)
    Preconditions: Sanitizer wired into enhance-controlled egress point
    Steps:
      1. Run relevant integration tests
      2. Assert emitted outward text no longer includes known token markers
    Expected Result: PASS with stripped outward payload
    Failure Indicators: Egress payload still contains `[Pasted ~` or tool-call markers
    Evidence: .sisyphus/evidence/task-12-egress-sanitize.txt

  Scenario: Non-user-facing diagnostic paths remain intact where intended
    Tool: Bash (test suite)
    Preconditions: Test distinguishes outward message path from internal diagnostic path if applicable
    Steps:
      1. Run targeted tests
      2. Assert only outward path is sanitized
    Expected Result: PASS with no accidental loss of internal-only diagnostics
    Failure Indicators: Integration over-sanitizes internal diagnostics or misses outward path
    Evidence: .sisyphus/evidence/task-12-boundary.txt
  ```

  **Commit**: NO

- [x] 13. Make cleanup/legacy-state classification ownership-aware

  **What to do**:
  - Update cleanup and legacy state handling so stale session artifacts are evaluated with ownership/restart metadata, not only filename suffix or raw activity checks.
  - Ensure legacy pre-guard sessions default to uncertain/stale instead of being implicitly reused in cross-channel contexts.
  - Add tests for stale artifact classification after restart windows.

  **Must NOT do**:
  - Do not aggressively auto-delete active but ownership-uncertain sessions.
  - Do not rely solely on `.deleted/.reset` suffixes once ownership metadata exists.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: cleanup logic can be destructive if mishandled.
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: essential for safe cleanup behavior.
  - **Skills Evaluated but Omitted**:
    - `verification-before-completion`: final-stage, not implementation-stage.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 12)
  - **Blocks**: 14
  - **Blocked By**: 6, 11

  **References**:
  - `src/openclaw_enhance/cleanup.py:84-220` - current candidate discovery and classification rules.
  - `src/openclaw_enhance/runtime/schema.py` / `project_state.py` - ownership metadata source to consult.
  - Existing cleanup-related tests if present; otherwise create focused new ones in nearby Python test area.

  **Acceptance Criteria**:
  - [ ] Ownership metadata influences stale/uncertain classification.
  - [ ] Legacy sessions without ownership metadata are not treated as safe to reuse.
  - [ ] Tests cover restart-window stale artifact scenarios.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Legacy artifact without ownership metadata is classified uncertain/stale
    Tool: Bash (pytest)
    Preconditions: New cleanup tests write legacy session artifacts
    Steps:
      1. Run targeted cleanup/state tests
      2. Assert legacy artifacts are not auto-reused as safe active state
    Expected Result: PASS with uncertain/stale classification
    Failure Indicators: Legacy artifact treated as safe authoritative session
    Evidence: .sisyphus/evidence/task-13-legacy-artifact.txt

  Scenario: Valid ownership-marked session avoids false cleanup
    Tool: Bash (pytest)
    Preconditions: Test fixture includes active valid ownership metadata
    Steps:
      1. Run cleanup classification test
      2. Assert valid owned session remains protected
    Expected Result: PASS avoiding destructive cleanup
    Failure Indicators: Active valid session marked removable
    Evidence: .sisyphus/evidence/task-13-protected-session.txt
  ```

  **Commit**: NO

- [x] 14. Add integration tests for restart collision blocking + same-channel resume

  **What to do**:
  - Create integration tests that model two channels with distinct ownership identities interacting with the same session lineage across restart.
  - Cover both happy path (same-channel revalidated resume) and negative path (cross-channel collision blocked).
  - Include a race-like scenario or sequential near-race simulation where restart occurs between claims.

  **Must NOT do**:
  - Do not stop at unit tests; this task must validate multi-component interaction.
  - Do not skip the negative/error scenario.

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: this is the key integration proof for the reported bug.
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: encode the exact bug before implementation is considered done.
  - **Skills Evaluated but Omitted**:
    - `playwright`: not a browser/UI task.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential within Wave 3
  - **Blocks**: 15, 16
  - **Blocked By**: 8, 9, 11, 13

  **References**:
  - `tests/integration/test_runtime_project_state.py` - Python integration style and temp-home fixture pattern.
  - `tests/integration/test_spawn_event_contract.py` - contract-oriented integration style bridging Python and TS expectations.
  - Latest session transcript symptoms - use them to shape exact collision + leakage regression cases.

  **Acceptance Criteria**:
  - [ ] Cross-channel same-session reuse after restart is rejected in integration tests.
  - [ ] Same-channel validated resume succeeds.
  - [ ] Ambiguous/missing ownership metadata is blocked.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Feishu/TG ownership collision after restart is blocked
    Tool: Bash (pytest)
    Preconditions: New integration tests model two distinct channel ownership identities
    Steps:
      1. Run `pytest tests/integration -q --tb=short`
      2. Confirm collision test initially failed during TDD and now passes
      3. Assert blocked result includes deterministic reason/code if implemented
    Expected Result: PASS with explicit cross-channel block
    Failure Indicators: Cross-channel actor still reuses same session lineage
    Evidence: .sisyphus/evidence/task-14-collision-block.txt

  Scenario: Same-channel restart resume succeeds after revalidation
    Tool: Bash (pytest)
    Preconditions: Integration test includes restart epoch bump + explicit rebind
    Steps:
      1. Run targeted same-channel resume integration test
      2. Assert resume succeeds only after valid revalidation path
    Expected Result: PASS preserving intended resume flow
    Failure Indicators: Resume denied despite valid rebind, or allowed without rebind
    Evidence: .sisyphus/evidence/task-14-same-channel.txt
  ```

  **Commit**: NO

- [x] 15. Add real-environment validation entry/report coverage

  **What to do**:
  - Extend the repo’s real-environment validation workflow so this feature class gets a concrete validation procedure/report.
  - Capture both primary regressions: collision blocking and leaked marker sanitization on enhance-controlled paths.
  - Save the validation report under `docs/reports/` with a clear slug.

  **Must NOT do**:
  - Do not rely solely on unit/integration tests as merge gate.
  - Do not produce a validation report that omits either collision or sanitization behavior.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: combines CLI, environment validation, and reporting.
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: only if validation path later proves UI/browser-based; otherwise not necessary.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 16)
  - **Blocks**: 17
  - **Blocked By**: 10, 12, 14

  **References**:
  - `AGENTS.md` post-development checklist - real-environment validation is mandatory.
  - `docs/testing-playbook.md` - feature-class matrix and validation procedure source of truth.
  - Existing `docs/reports/` examples - report structure to mirror.

  **Acceptance Criteria**:
  - [ ] Validation flow includes collision-block and sanitization checks.
  - [ ] Report saved to `docs/reports/`.
  - [ ] Validation command(s) and expected output documented in report/plan.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Real environment validation report proves collision block
    Tool: Bash
    Preconditions: Validation command for this feature class is defined
    Steps:
      1. Run `python -m openclaw_enhance.cli validate-feature --feature-class <class> --report-slug <slug>`
      2. Confirm generated report includes blocked cross-channel reuse evidence
    Expected Result: PASS with report written under `docs/reports/`
    Failure Indicators: Report missing or collision scenario absent
    Evidence: .sisyphus/evidence/task-15-validation-report.txt

  Scenario: Real environment validation captures sanitized outward output
    Tool: Bash
    Preconditions: Validation procedure includes leaking marker sample through enhance-controlled path
    Steps:
      1. Run validation or sub-step command
      2. Assert report/evidence shows sanitized outward text without known markers
    Expected Result: PASS with marker-free outward evidence
    Failure Indicators: Report still contains leaked markers in expected-sanitized path
    Evidence: .sisyphus/evidence/task-15-sanitized-report.txt
  ```

  **Commit**: NO

- [x] 16. Run docs-check / CI-equivalent verification updates

  **What to do**:
  - Run the full relevant verification stack and fix any plan-related omissions discovered during execution.
  - Minimum stack: Python unit + integration, TypeScript tests, typecheck, docs-check.
  - Record exact commands and expected results in evidence.

  **Must NOT do**:
  - Do not claim success without command output.
  - Do not skip failing commands; either fix or mark blocked.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: verification command execution and issue triage.
  - **Skills**: [`verification-before-completion`]
    - `verification-before-completion`: ensures evidence-backed completion claims.
  - **Skills Evaluated but Omitted**:
    - `test-driven-development`: this is post-implementation verification, not red/green design.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 15)
  - **Blocks**: 17
  - **Blocked By**: 10, 14, 15

  **References**:
  - `.github/workflows/ci.yml:14-129` - CI-equivalent verification commands.
  - `AGENTS.md` post-development checklist - docs-check and validation requirements.

  **Acceptance Criteria**:
  - [ ] `pytest tests/unit -q --tb=short` passes.
  - [ ] `pytest tests/integration -q --tb=short` passes.
  - [ ] `npm test` and `npm run typecheck` pass.
  - [ ] `python -m openclaw_enhance.cli docs-check` passes.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: CI-equivalent local verification passes
    Tool: Bash
    Preconditions: All implementation tasks complete
    Steps:
      1. Run `pytest tests/unit -q --tb=short`
      2. Run `pytest tests/integration -q --tb=short`
      3. Run `npm test`
      4. Run `npm run typecheck`
      5. Run `python -m openclaw_enhance.cli docs-check`
    Expected Result: All commands exit 0
    Failure Indicators: Any command fails or is skipped
    Evidence: .sisyphus/evidence/task-16-verification.txt

  Scenario: Regression-specific tests remain green in isolation
    Tool: Bash
    Preconditions: Targeted restart collision and sanitizer tests exist
    Steps:
      1. Run only the new targeted tests
      2. Confirm they pass independently for fast regression detection
    Expected Result: PASS for targeted files/cases
    Failure Indicators: Regression tests only pass when hidden by full suite order effects
    Evidence: .sisyphus/evidence/task-16-targeted-regressions.txt
  ```

  **Commit**: NO

- [ ] 17. Commit preparation and evidence collation

  **What to do**:
  - Group changed files into coherent commit(s) following repo style after all verification passes.
  - Ensure evidence files and validation report exist and are referenced.
  - Prepare concise why-focused commit message(s).

  **Must NOT do**:
  - Do not commit before verification is green.
  - Do not include secrets or irrelevant artifacts.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: commit prep and artifact collation once work is complete.
  - **Skills**: [`git-master`, `verification-before-completion`]
    - `git-master`: choose correct git hygiene and commit style.
    - `verification-before-completion`: ensures commit only happens after evidence-backed success.
  - **Skills Evaluated but Omitted**:
    - `finishing-a-development-branch`: useful later if integrating branch, but not required for this task itself.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: F1-F4
  - **Blocked By**: 15, 16

  **References**:
  - Recent git history style in repo.
  - Evidence files produced in `.sisyphus/evidence/`.
  - Validation report in `docs/reports/`.

  **Acceptance Criteria**:
  - [ ] Evidence files exist for all key regression scenarios.
  - [ ] Commit message draft explains why the guardrails were added.
  - [ ] No commit is created before green verification.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Evidence inventory is complete before commit
    Tool: Bash
    Preconditions: All verification complete
    Steps:
      1. Enumerate expected evidence paths from completed tasks
      2. Confirm files exist
    Expected Result: PASS with complete evidence inventory
    Failure Indicators: Missing evidence for key collision/sanitization scenarios
    Evidence: .sisyphus/evidence/task-17-evidence-inventory.txt

  Scenario: Commit draft matches verified scope only
    Tool: Bash (git status/log) or direct review
    Preconditions: Verification green and candidate files staged conceptually
    Steps:
      1. Compare changed files against plan scope
      2. Draft commit message describing guardrails, restart safety, and sanitization
    Expected Result: PASS with no unaccounted scope creep
    Failure Indicators: Commit draft includes unrelated files or omits core verified changes
    Evidence: .sisyphus/evidence/task-17-commit-draft.txt
  ```

  **Commit**: YES
  - Message: `fix(runtime): fail closed on ambiguous restart session reuse`
  - Files: runtime schema/helpers, hook/extension guardrails, tests, docs, validation report
  - Pre-commit: verification stack from Task 16

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> All four final tasks are **agent-executed**. No human/manual-only verification is allowed.
> Dispatch them only after Tasks 1-17 are complete and evidence files exist.

- [ ] F1. Plan Compliance Audit

  **What to do**:
  - Audit the implemented diff against this plan’s Must Have / Must NOT Have / task list.
  - Verify every required guardrail has corresponding code + evidence.
  - Explicitly reject any fail-open behavior, undocumented fallback preservation, or missing evidence.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: structured end-to-end audit of implementation against a detailed plan.
  - **Skills**: []
  - **Escalation Reviewer**: `oracle` may be used as a second-pass reviewer if the executor wants an architectural cross-check, but the executable task itself is assigned with the standard category dispatch model.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Final Wave (with F2, F3, F4)
  - **Blocks**: completion sign-off
  - **Blocked By**: 17

  **Acceptance Criteria**:
  - [ ] Audit output includes `Must Have [N/N]`, `Must NOT Have [N/N]`, `Tasks [N/N]`, and `VERDICT`.
  - [ ] Every rejection references a concrete missing artifact, file, or evidence path.
  - [ ] No plan requirement is left unclassified.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Plan requirements are all mapped to implementation evidence
    Tool: Bash
    Preconditions: Tasks 1-17 complete and evidence files exist
    Steps:
      1. Read `.sisyphus/plans/session-isolation-restart-guardrails.md`
      2. Compare each Must Have / Must NOT Have / task acceptance criterion against the implementation diff and evidence inventory
      3. Produce a structured audit summary file
    Expected Result: Summary reports full coverage or concrete deficiencies with exact references
    Failure Indicators: Missing evidence, unreviewed tasks, or unverifiable requirements
    Evidence: .sisyphus/evidence/final-qa/f1-plan-compliance.txt

  Scenario: Forbidden scope violations are explicitly searched and reported
    Tool: Bash
    Preconditions: Implementation diff available
    Steps:
      1. Search changed paths for OpenClaw core directories or unrelated architecture additions
      2. Confirm no fail-open fallback remains where plan required fail-closed behavior
    Expected Result: PASS with `Contamination CLEAN` or explicit violation report
    Failure Indicators: OpenClaw core touched, generalized filtering introduced, or fail-open path remains
    Evidence: .sisyphus/evidence/final-qa/f1-scope-audit.txt
  ```

- [ ] F2. Code Quality Review

  **What to do**:
  - Run verification commands again and review changed files for unchecked fallbacks, over-broad sanitization, dead code, commented-out experiments, naming drift, and AI-slop patterns.
  - Confirm both Python and TypeScript sides remain maintainable and minimal.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: mixed code review + verification execution.
  - **Skills**: [`verification-before-completion`]
    - `verification-before-completion`: requires evidence-backed success claims.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Final Wave (with F1, F3, F4)
  - **Blocks**: completion sign-off
  - **Blocked By**: 17

  **Acceptance Criteria**:
  - [ ] Review output includes `Build`, `Lint/Typecheck`, `Tests`, and `VERDICT`.
  - [ ] Any code-quality issue points to exact file/path and concrete concern.
  - [ ] Review verifies sanitizer remains deterministic and bounded.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Full verification stack remains green during code review
    Tool: Bash
    Preconditions: Tasks 15-17 completed
    Steps:
      1. Run `pytest tests/unit -q --tb=short`
      2. Run `pytest tests/integration -q --tb=short`
      3. Run `npm test`
      4. Run `npm run typecheck`
      5. Run `python -m openclaw_enhance.cli docs-check`
    Expected Result: All commands exit 0 and are included in review summary
    Failure Indicators: Any command fails, is skipped, or output is missing from summary
    Evidence: .sisyphus/evidence/final-qa/f2-verification-stack.txt

  Scenario: Changed files are reviewed for bounded, maintainable implementation
    Tool: Bash
    Preconditions: Diff available
    Steps:
      1. Inspect changed Python and TypeScript files in the diff
      2. Check for dead code, commented-out experiments, broad regex/content stripping, and unguarded fallback logic
    Expected Result: PASS with concise review summary or explicit issues list
    Failure Indicators: Review finds unchecked fallback, over-broad sanitizer, or unrelated refactor creep
    Evidence: .sisyphus/evidence/final-qa/f2-code-quality.txt
  ```

- [ ] F3. Agent-Executed Final QA Sweep

  **What to do**:
  - Re-run the highest-risk regression scenarios from Tasks 8, 11, 12, 13, and 14 as a final automated QA sweep.
  - Focus on the real bug shape: cross-channel collision block, same-channel revalidation, legacy-state safety, and sanitized outward output.
  - Save consolidated final QA evidence under `.sisyphus/evidence/final-qa/`.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: final scenario execution across multiple verification surfaces.
  - **Skills**: [`verification-before-completion`]
    - `verification-before-completion`: ensures outputs are observed before approval.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Final Wave (with F1, F2, F4)
  - **Blocks**: completion sign-off
  - **Blocked By**: 17

  **Acceptance Criteria**:
  - [ ] Final QA summary includes `Scenarios [N/N pass]`, `Integration [N/N]`, `Edge Cases [N tested]`, and `VERDICT`.
  - [ ] All high-risk regression scenarios are re-executed, not just referenced.
  - [ ] Evidence paths are created under `.sisyphus/evidence/final-qa/`.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Cross-channel collision remains blocked after full implementation
    Tool: Bash
    Preconditions: Final implementation complete; targeted tests and/or validation commands available
    Steps:
      1. Re-run the targeted collision-block integration test(s)
      2. Re-run any matching real-environment validation sub-step if available
      3. Capture outputs in final QA summary
    Expected Result: PASS with deterministic cross-channel block result
    Failure Indicators: Collision path succeeds, becomes flaky, or lacks explicit block evidence
    Evidence: .sisyphus/evidence/final-qa/f3-collision-block.txt

  Scenario: Same-channel resume and outward sanitization both remain green
    Tool: Bash
    Preconditions: Targeted same-channel and sanitizer tests available
    Steps:
      1. Re-run same-channel revalidation/resume tests
      2. Re-run sanitizer integration test on enhance-controlled outward path
      3. Record both outcomes in final QA summary
    Expected Result: PASS for both resume and sanitization paths
    Failure Indicators: Valid resume fails, or leaked markers reappear in sanitized output
    Evidence: .sisyphus/evidence/final-qa/f3-resume-and-sanitize.txt
  ```

- [ ] F4. Scope Fidelity Check

  **What to do**:
  - Compare the actual diff to planned scope and ensure the implementation stayed inside enhance-layer boundaries.
  - Confirm no OpenClaw core paths were modified and no generalized new subsystem was introduced.
  - Flag any unaccounted files or optional work that slipped in.

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: requires reasoning about planned-vs-actual scope fidelity.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Final Wave (with F1, F2, F3)
  - **Blocks**: completion sign-off
  - **Blocked By**: 17

  **Acceptance Criteria**:
  - [ ] Output includes `Tasks [N/N compliant]`, `Contamination [CLEAN/N issues]`, `Unaccounted [CLEAN/N files]`, and `VERDICT`.
  - [ ] Every changed file is either planned or explicitly called out.
  - [ ] No core path modification is present.

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Every changed file maps to planned scope
    Tool: Bash
    Preconditions: Diff/stat available
    Steps:
      1. Enumerate changed files from the branch diff
      2. Compare each file to tasks in this plan
      3. Record whether each file is planned or unaccounted
    Expected Result: PASS with all files accounted for or clearly flagged
    Failure Indicators: Unplanned files appear without explanation
    Evidence: .sisyphus/evidence/final-qa/f4-file-mapping.txt

  Scenario: No OpenClaw core or generalized subsystem changes leaked into implementation
    Tool: Bash
    Preconditions: Diff available
    Steps:
      1. Inspect changed paths for core runtime/bridge locations outside this repo’s allowed scope
      2. Review architecture changes for generalized filtering/session redesign beyond plan intent
    Expected Result: PASS with `Contamination CLEAN`
    Failure Indicators: Core edits or over-broad subsystem work detected
    Evidence: .sisyphus/evidence/final-qa/f4-contamination-check.txt
  ```

---

## Commit Strategy

- Prefer 1-2 commits max:
  - `fix(runtime): enforce channel-aware restart ownership guards`
  - `test/docs: cover restart collision guardrails and sanitization`

---

## Success Criteria

### Verification Commands
```bash
pytest tests/unit -q --tb=short
pytest tests/integration -q --tb=short
npm test
npm run typecheck
python -m openclaw_enhance.cli docs-check
python -m openclaw_enhance.cli validate-feature --feature-class <class> --report-slug <slug>
```

### Final Checklist
- [ ] All Must Have items implemented
- [ ] All Must NOT Have items absent
- [ ] Cross-channel reuse after restart fails closed
- [ ] Same-channel validated resume works
- [ ] Known internal markers are stripped on enhance-controlled outward paths
- [ ] Tests, typecheck, docs-check, and real-environment validation all pass
