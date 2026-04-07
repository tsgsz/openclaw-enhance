## Task 9: Fail-closed session key normalization

Modified `extensions/openclaw-enhance-runtime/index.ts` to tighten runtime main-session normalization:

**Changes made:**
- Removed `normalizeSessionKey()` and `asString()` helper functions - no longer needed
- Modified `isMainSession()` to strictly only accept string keys:
  - Returns `false` immediately for any non-string session key
  - Only recognizes `"main"` and `"agent:main:*"` as valid main session identifiers

**Rationale:**
- Object-shaped keys like `{ id: "main" }` are ambiguous and could come from any source
- Without canonical ownership fields (channel_type, channel_conversation_id), objects cannot be trusted
- Fail-closed principle: when in doubt, treat as non-main (safer default)

**Test results:**
- ✔ "should reject ambiguous object-shaped session keys as unsafe instead of silently falling back" - PASSES
- ✔ "should preserve canonical main session recognition for 'main' and 'agent:main:*' forms" - PASSES
- LSP diagnostics: clean (no errors)

---

## Task 11: Restart epoch + stale-binding checks

### Date: 2026-04-05

### Summary
Added Python implementation and tests for restart epoch / stale-binding safety checks in governance and runtime layers.

### Changes Made

1. **`src/openclaw_enhance/runtime/project_state.py`** — added helpers:
   - `bump_restart_epoch(user_home)` — increments `restart_epoch` by 1 and saves
   - `get_binding_status(user_home)` — returns current `ownership_contract` dict
   - `is_binding_stale(user_home)` — returns True when `binding_epoch < restart_epoch`
   - `revoke_binding(user_home)` — sets `binding_status` to "revoked"
   - `rebind_ownership(channel_type, channel_conversation_id, bound_session_id, user_home)` — binds with current `restart_epoch`

2. **`src/openclaw_enhance/governance/restart.py`** — modified:
   - `safe_restart()` now calls `bump_restart_epoch()` after successful gateway restart
   - `immediate_restart_resume()` calls `revoke_binding()` to invalidate current bindings (keeps same epoch, requires revalidation)

3. **`tests/integration/test_runtime_project_state.py`** — added tests:
   - `test_restart_epoch_bump_increments_value` — verifies epoch increments on each bump
   - `test_stale_binding_detected_when_epoch_mismatch` — verifies stale detection when binding_epoch < restart_epoch
   - `test_rebind_ownership_updates_epoch` — verifies rebind uses current restart_epoch
   - `test_same_channel_resume_after_rebind` — verifies session can rebind after restart
   - `test_revoke_binding_sets_status_to_revoked` — verifies revoke updates binding_status

### Key Patterns Learned

- **Epoch comparison**: stale = `binding_epoch < restart_epoch`; rebind syncs by writing current `restart_epoch`
- **Safe restart bumps epoch**: every successful safe restart increments epoch, making all prior bindings stale
- **Immediate restart revokes**: crash recovery keeps same epoch but marks binding revoked, forcing revalidation
- **State file persistence**: all helpers use `_load_state` / `_save_state` for atomic writes to `runtime_state.json`

### Test Results
- 11 tests pass (`pytest tests/integration/test_runtime_project_state.py -q --tb=short`)
- LSP diagnostics: clean on all changed files

---

## Task 8: Tighten spawn-enrich ownership/fallback behavior

### Date: 2026-04-05

### Summary
Modified `hooks/oe-subagent-spawn-enrich/handler.ts` to implement fail-closed ownership validation and channel-aware deduplication.

### Changes Made

1. **Extended `SpawnEnrichInput` interface** to include:
   - `restart_epoch?: number` - indicates session restart scenario
   - `ownership?: { channel_type: string; channel_conversation_id: string }` - channel identity metadata

2. **Extended `SpawnEnrichOutput` interface** to include:
   - `unsafe?: boolean` - flag for unsafe/ambiguous scenarios
   - `enriched_payload.ownership_status?: string` - detailed ownership status

3. **Added `validateOwnership()` function** that:
   - Detects restart scenarios without ownership metadata (unsafe)
   - Returns `ownership_status: "unsafe_ambiguous_restart"` for ambiguous restarts
   - Returns `ownership_status: "verified"` when ownership is present and valid
   - Returns `ownership_status: "unverified"` for fresh sessions without ownership

4. **Modified `generateDedupeKey()` function** to:
   - Accept optional `ownership` parameter
   - Include `channel_type` in dedupe key when ownership is present
   - Format with ownership: `{project}:{subagent_type}:{channel_type}:{task_hash}:{date}`
   - Format without ownership: `{project}:{subagent_type}:{task_hash}:{date}`

5. **Modified `enrichSpawnEvent()` function** to:
   - Call `validateOwnership()` at start of processing
   - Return early with `unsafe: true` and `ownership_status: "unsafe_ambiguous_restart"` when ownership validation fails
   - Pass ownership to `generateDedupeKey()` for channel-aware deduplication
   - Include `ownership_status` in enriched payload for all scenarios

### Key Patterns Learned

- **Fail-closed security**: When ownership is ambiguous (restart without ownership metadata), we explicitly mark the result as unsafe rather than silently falling back to defaults
- **Channel identity isolation**: Feishu and Telegram conversations with the same task payload now generate distinct dedupe keys, preventing cross-channel task collisions
- **Metadata propagation**: Ownership status is now propagated through the enriched payload for downstream consumers to make informed decisions

### Test Results
Both Task 3 tests now pass:
- ✓ `should reject or mark ambiguous restart ownership unsafe instead of silently falling back`
- ✓ `should keep dedupe identity distinct for channel-distinct ownership on the same task payload`

### Security Implications

This change prevents:
1. **Ambiguous session hijacking**: Restarted sessions without proper ownership metadata are flagged as unsafe
2. **Cross-channel deduplication collisions**: Tasks from different channels (feishu vs telegram) cannot accidentally dedupe against each other

## Task 10: Documentation Update

Updated canonical documentation to reflect the new session isolation and restart safety guardrails.

**Files Updated:**
- `PLAYBOOK.md`: Added "会话隔离与安全护栏" section, updated `runtime-state.json` and `oe-runtime` descriptions.
- `docs/operations.md`: Added "Session Isolation & Restart Safety" and "Output Sanitization" sections, updated JSON example.
- `docs/architecture.md`: Added "Session Ownership Model" section, updated schema and component descriptions.
- `docs/opencode-iteration-handbook.md`: Added `session-isolation-restart-guardrails` milestone and new invariants.
- `docs/testing-playbook.md`: Added `session-isolation` feature class and validation bundle.
- `AGENTS.md`: Updated current architecture milestone.

**Key Learnings:**
- Documentation must be updated in a specific order to maintain consistency.
- `docs-check` is a vital tool for ensuring that documentation changes don't break internal rules (e.g., banned terms, transport boundaries).
- The "Fail-Closed" principle should be explicitly documented as a core security invariant.

## Task 12: Integrate sanitizer into enhance-controlled outward paths

### Date: 2026-04-05

### Integration Points Identified

1. **extensions/openclaw-enhance-runtime/index.ts** - `before_tool_call` handler
   - The `blockReason` strings returned when blocking forbidden tools in main session
   - Two paths: normal blocking and fail-closed error handling
   - These are enhance-controlled output paths because the extension generates these messages

2. **hooks/oe-subagent-spawn-enrich/handler.ts** - Spawn enrichment handler
   - The `prompt` field injected into subagent spawn events
   - Both orchestrator and non-orchestrator paths
   - These are enhance-controlled because enhance modifies the prompt before it flows to subagents

### Implementation

- Imported `sanitizeEnhanceOutwardText` from runtime-bridge.ts in both files
- Applied sanitization to:
  - `blockReason` in normal forbidden tool blocking (line ~87 in index.ts)
  - `blockReason` in fail-closed error handling (line ~100 in index.ts)
  - `mutablePayload.prompt` for orchestrator agents (line ~358 in handler.ts)
  - `mutablePayload.prompt` for non-orchestrator agents (line ~362 in handler.ts)

### Testing

Added integration tests in `runtime-bridge.test.ts`:
- `should sanitize blockReason when blocking forbidden tools` - Verifies sanitizer is called on blockReason
- `should sanitize fail-closed blockReason` - Verifies sanitizer is called on error path blockReason

All 37 tests pass successfully.

### Key Constraint Respected

Only intercepted enhance-controlled paths:
- Extension-generated blockReason messages (not core OpenClaw output)
- Hook-modified prompt text (enhance-controlled enrichment)

Did NOT claim to intercept core-only output paths that enhance cannot reach.

---

## Task 13: Ownership-aware cleanup classification

### Date: 2026-04-05

### Summary
Modified cleanup classification to consider ownership binding status when determining if runtime states are stale.

### Changes Made

1. **`src/openclaw_enhance/cleanup.py`**:
   - Added `_is_binding_stale_for_classification()` helper function that checks:
     - `binding_status` in ("unbound", "revoked") → stale
     - `binding_status == "bound"` and `binding_epoch < restart_epoch` → stale
     - Otherwise → not stale
   - Modified `classify_candidate()` to accept optional `binding_status` and `restart_epoch` parameters
   - For `RUNTIME_STATE` candidates, checks if binding is stale before normal classification; if stale, marks as `SAFE_TO_REMOVE`
   - Modified `cleanup_paths()` to accept and forward `binding_status` and `restart_epoch` parameters

2. **`src/openclaw_enhance/cli.py`**:
   - Updated `cleanup_sessions()` to read `ownership_contract` and `restart_epoch` from runtime state
   - Passes these values to `cleanup_paths()`

3. **`src/openclaw_enhance/monitor_runtime.py`**:
   - Updated `run_cleanup_mode()` to pass binding status and restart epoch to `cleanup_paths()`

4. **`tests/integration/test_runtime_project_state.py`**:
   - Added `test_cleanup_classifies_stale_binding_as_needs_rebind` - verifies stale binding leads to SAFE_TO_REMOVE
   - Added `test_cleanup_classifies_active_binding_as_safe` - verifies active binding (epoch match) leads to SKIPPED_ACTIVE

### Key Patterns Learned

- **Binding staleness logic**: `unbound`/`revoked` OR `binding_epoch < restart_epoch` = stale
- **Active binding**: `binding_epoch == restart_epoch` = active, not cleaned up
- **Optional parameters**: Added `binding_status` and `restart_epoch` as optional parameters to maintain backward compatibility
- **Type safety**: Used `isinstance()` check for type narrowing when comparing `binding_epoch` (which comes as `object` from dict)

### Test Results
- 16 tests pass (13 in test_runtime_project_state.py + 3 in test_cleanup.py)
- LSP diagnostics: clean on all modified files

---

## Task 14: Integration tests for restart collision blocking + same-channel resume

### Date: 2026-04-05

### Summary
Added integration tests that model the exact Feishu/Telegram cross-channel session collision bug scenario after restart.

### Changes Made

1. **`tests/integration/test_runtime_project_state.py`** - Added Python integration tests:
   - `test_cross_channel_collision_blocked_after_restart` - Simulates Feishu initially owning a session, restart epoch bump making binding stale, both Feishu (stale binding) and Telegram (no binding) being blocked, then proper revalidation
   - `test_same_channel_resume_after_revalidation` - Verifies same-channel resume succeeds with valid ownership + matching epoch
   - `test_ambiguous_missing_ownership_blocked` - Verifies missing/stale ownership metadata results in unsafe state

2. **`extensions/openclaw-enhance-runtime/src/runtime-bridge.test.ts`** - Added TypeScript integration tests:
   - `should return unsafe: true for cross-channel ambiguous restart` - Tests both Feishu and Telegram without ownership after restart
   - `should NOT mark unsafe for valid same-channel ownership with matching epoch` - Tests verified ownership passes
   - `should mark unsafe when ownership metadata is missing` - Tests missing ownership detection
   - `should allow fresh session without ownership when no restart_epoch` - Tests fresh sessions are allowed

### Key Patterns Learned

- **Integration testing approach**: Python tests verify state machine behavior, TypeScript tests verify hook handler enrichment logic
- **Cross-channel collision model**: Different channels (feishu/telegram) with same session lineage but without ownership both get blocked after restart
- **Epoch comparison in validation**: Handler checks `restart_epoch` presence + `ownership` absence to detect ambiguous restarts
- **State reload**: In Python tests, must reload state after `bump_restart_epoch()` to get updated values

### Test Results
- Python: 16 tests pass (`pytest tests/integration/test_runtime_project_state.py -q --tb=short`)
- TypeScript: 41 tests pass (`node --test dist/extensions/openclaw-enhance-runtime/src/runtime-bridge.test.js`)
- LSP diagnostics: clean on all modified files

### Security Validation

These integration tests prove the fix for the reported bug:
1. **Before fix**: Cross-channel sessions could collide after restart without ownership validation
2. **After fix**: Both cross-channel attempts are blocked (marked `unsafe: true`) until proper revalidation
3. **Same-channel resume**: Works correctly with valid ownership + epoch match

---

## Task 15: Real-Environment Validation Report

### Date: 2026-04-05

### Summary
Created real-environment validation report for `session-isolation` feature class. The CLI `validate-feature --feature-class session-isolation` is not yet wired up (FeatureClass enum and get_bundle_commands lack session-isolation), so report was produced manually per testing-playbook fallback.

### Validation Results
- Python integration tests (test_runtime_project_state.py): **16 passed**
- Python cleanup tests (test_cleanup_sessions.py): **3 passed**
- TypeScript runtime-bridge + oe-runtime tests: **41 passed**
- docs-check: **PASS**

### 4 Test Scenarios Covered
1. **Cross-channel collision block** — PASS: `test_cross_channel_collision_blocked_after_restart` + 4 TypeScript tests verify Feishu/TG collision blocked after restart
2. **Restart epoch revalidation** — PASS: epoch bump, stale detection, revoke, rebind all verified
3. **Sanitization check** — PASS: 4 sanitizer tests verify `[Pasted ~]` stripped from enhance-controlled output
4. **Same-channel resume** — PASS: 3 Python + 1 TypeScript test verify legitimate same-channel resume works

### Key Finding
`session-isolation` FeatureClass not yet registered in `src/openclaw_enhance/validation/types.py`. live_probes also lacks a `session-isolation` subcommand. These would need to be added to fully automate the bundle.

---

## Task 16: model-config.json removal in uninstaller

### Date: 2026-04-05

### Summary
Added `model-config.json` file removal to uninstaller to restore install/uninstall symmetry for the `model:config` component.

### Changes Made

1. **`src/openclaw_enhance/install/uninstaller.py`** - Added function and call:
   - Added `_remove_model_config(target_root: Path) -> list[str]` function (lines 396-410)
     - Checks for `target_root / "model-config.json"` existence
     - Removes file if exists, returns `["model:config"]` on success
     - Returns empty list if file doesn't exist (idempotent)
   - Added call to `_remove_model_config()` in uninstall flow (lines ~569-575)
     - Called after `_remove_runtime_state()`, same non-fatal error handling

### Key Patterns Learned

- **Symmetry pattern**: Follows same pattern as `_remove_runtime_state` for idempotent removal
- **Non-fatal error handling**: Uses try/except with `failed.append()` but continues uninstall
- **Component naming**: Returns `"model:config"` to match install component name from `installer.py` line 401

### Test Results
- `TestInstallUninstallSymmetry`: **15 passed**
- LSP diagnostics: clean on uninstaller.py

