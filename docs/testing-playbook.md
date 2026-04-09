# OpenCode Real-Environment Validation Contract

This document defines the mandatory validation process for all changes to `openclaw-enhance`. No feature can be merged without a successful real-environment test report.

## v2 Note

**openclaw-enhance v2 采用纯 Skill 架构**：
- **无工作区 (Workspaces)**：v1 的 agent 工作区已归档
- **无 Agent 注册**：不再使用 `oe-orchestrator`、`oe-searcher` 等托管 Agent
- **纯 Skill 路由**：所有路由逻辑通过 Skills 实现

## 1. Feature-Class Matrix

Validation requirements are determined by the feature class of the change.

| Feature Class | Description | Mandatory Validation |
| :--- | :--- | :--- |
| `install-lifecycle` | Changes to install/uninstall logic, path management, or config patching. | Full Lifecycle Bundle |
| `cli-surface` | Changes to `openclaw-enhance` CLI commands or output formatting. | CLI Surface Bundle |
| `skill-routing` | Changes to skills, routing logic, or sessions_spawn behavior. | Skill Routing Bundle |
| `runtime-watchdog` | Changes to hooks, runtime monitoring, or timeout detection. | Runtime Integration Bundle |
| `session-isolation` | Changes to session ownership, isolation, or sanitization. | Session Isolation Bundle |
| `docs-test-only` | Changes only to documentation or unit/integration tests. | Docs Check Only (Exempt) |

## 2. Validation Bundles

### 2.1 Full Lifecycle Bundle (`install-lifecycle`)
Target: Default `~/.openclaw`

1. **Cleanup**: `python -m openclaw_enhance.cli uninstall`
    - *Pass*: `~/.openclaw/openclaw-enhance` is removed or empty.
2. **Install**: `python -m openclaw_enhance.cli install`
    - *Pass*: Exit code 0, "Installation successful" in output.
3. **Monitor Services (macOS)**:
   - `launchctl print gui/$UID/ai.openclaw.enhance.monitor`
   - `launchctl print gui/$UID/ai.openclaw.session-cleanup`
4. **Verify Status**: `python -m openclaw_enhance.cli status`
    - *Pass*: `installed: true` in output.
5. **Doctor Check**: `python -m openclaw_enhance.cli doctor`
    - *Pass*: Exit code 0.
6. **Final Cleanup**: `python -m openclaw_enhance.cli uninstall`
    - *Pass*: Environment restored to original state.

### 2.2 CLI Surface Bundle (`cli-surface`)
1. **Status**: `python -m openclaw_enhance.cli status`
   - *Pass*: Shows installation path and status.
2. **Status JSON**: `python -m openclaw_enhance.cli status --json`
   - *Pass*: Valid JSON output containing `install_path`.
3. **Doctor**: `python -m openclaw_enhance.cli doctor`
   - *Pass*: Exit code 0, "Doctor checks passed".
4. **Render Skill**: `python -m openclaw_enhance.cli render-skill oe-tag-router`
   - *Pass*: Output contains skill definition.
5. **Render Hook**: `python -m openclaw_enhance.cli render-hook oe-subagent-spawn-enrich`
   - *Pass*: Output contains hook logic.
6. **Cleanup Sessions Dry Run**: `python -m openclaw_enhance.cli cleanup-sessions --dry-run --json`
   - *Pass*: Valid JSON output.
7. **Docs Check**: `python -m openclaw_enhance.cli docs-check`
   - *Pass*: Exit code 0, "Docs check passed".
8. **Validator Self-Surface**: `python -m openclaw_enhance.cli validate-feature --feature-class docs-test-only --report-slug self-surface-smoke`
   - *Pass*: Exit code 0, produces a report with `Conclusion: EXEMPT`.

### 2.3 Skill Routing Bundle (`skill-routing`)

#### Skill Discovery
1. **Skills Available**: `ls ~/.openclaw/openclaw-enhance/skills/`
   - *Pass*: Contains oe-tag-router, oe-spawn-search, oe-spawn-coder, oe-spawn-ops, etc.

#### Routing Functionality
2. **Tag Router Test**: `python -m openclaw_enhance.cli render-skill oe-tag-router`
   - *Pass*: Output contains routing logic and sessions_spawn guidance.

#### Spawn Skills
3. **Spawn Search**: `python -m openclaw_enhance.cli render-skill oe-spawn-search`
   - *Pass*: Output contains spawn skill definition.
4. **Spawn Coder**: `python -m openclaw_enhance.cli render-skill oe-spawn-coder`
   - *Pass*: Output contains spawn skill definition.

### 2.4 Runtime Integration Bundle (`runtime-watchdog`)
1. **Hook Verification**: `cat ~/.openclaw/openclaw.json | jq '.hooks.internal'`
   - *Pass*: `hooks.internal.entries.oe-subagent-spawn-enrich.enabled` is `true` and `hooks.internal.load.extraDirs` includes the managed hook directory.
2. **Hook Discovery**: `openclaw hooks list`
   - *Pass*: `oe-subagent-spawn-enrich` is listed as ready.
3. **Watchdog Trigger**: (Specific trigger command or scenario)
   - *Pass*: Watchdog identifies timeout or state change as expected.

### 2.5 Session Isolation Bundle (`session-isolation`)

1. **Ownership Binding Test**: `python -m openclaw_enhance.validation.live_probes session-isolation --openclaw-home "$OPENCLAW_HOME" --test ownership-binding`
   - *Pass*: Probe verifies that `(channel_type, channel_conversation_id)` is correctly bound to a `session_id` in `runtime-state.json`.
2. **Fail-Closed Test**: `python -m openclaw_enhance.validation.live_probes session-isolation --openclaw-home "$OPENCLAW_HOME" --test fail-closed`
   - *Pass*: Probe verifies that ambiguous or non-string session keys are rejected.
3. **Restart Epoch Test**: `python -m openclaw_enhance.cli governance restart-resume && python -m openclaw_enhance.validation.live_probes session-isolation --openclaw-home "$OPENCLAW_HOME" --test restart-epoch`
   - *Pass*: Probe verifies that `restart_epoch` is incremented and old session bindings are marked as stale.
4. **Sanitization Test**: `python -m openclaw_enhance.validation.live_probes session-isolation --openclaw-home "$OPENCLAW_HOME" --test sanitization`
   - *Pass*: Probe verifies that internal markers like `[Pasted ~]` are stripped from enhance-controlled output.

### 2.6 Docs Check Only (`docs-test-only`)
- **Exemption Policy**: Real-environment testing is NOT required if changes are strictly limited to `.md` files or `tests/` (excluding `tests/e2e/`).
- **Mandatory Command**: `python -m openclaw_enhance.cli docs-check`
  - *Pass*: Exit code 0.

## 3. Phase Order

1. **Pre-flight**: Run unit and integration tests (`pytest`).
2. **Environment Prep**: Ensure `~/.openclaw` exists and is backed up if necessary.
3. **Execution**: Run the mandatory validation bundle(s) for the change.
4. **Reporting**: Document results in a new report file.
5. **Cleanup**: Run `uninstall` to leave the environment clean.

## 4. Report Location & Format

Reports must be saved to: `docs/reports/YYYY-MM-DD-<slug>-<feature-class>.md`

**Template**:
```markdown
# Validation Report: [Feature Name]

- **Date**: YYYY-MM-DD
- **Feature Class**: [class]
- **Environment**: [e.g., macOS, default ~/.openclaw]

## Execution Log
[Paste command outputs here]

## Results
- [ ] Step 1: [Pass/Fail]
- [ ] Step 2: [Pass/Fail]

## Findings
[Any issues or observations]
```

## 5. Cleanup Guardrails

- Always target the default `~/.openclaw` unless explicitly overridden.
- The `uninstall` command is the primary cleanup mechanism.
- Manual removal of `~/.openclaw/openclaw-enhance` is permitted if `uninstall` fails.
- Never modify `~/.openclaw/openclaw.json` manually; use the CLI.

## 6. Current Branch Shipped Set

| Feature Capability | Canonical Slug | Feature Class | Method Contract | Observable Proof |
| :--- | :--- | :--- | :--- | :--- |
| Core Installation | `backfill-core-install` | `install-lifecycle` | `python -m openclaw_enhance.cli install` | `status` shows `installed: true`; files exist in `~/.openclaw/openclaw-enhance` |
| Monitor Auto-Start (macOS) | `backfill-monitor-auto-start` | `install-lifecycle` | `python -m openclaw_enhance.cli install` + `launchctl print gui/$UID/ai.openclaw.enhance.monitor` | LaunchAgent is loaded |
| CLI Surface Area | `backfill-cli-surface` | `cli-surface` | `status`, `status --json`, `doctor`, `cleanup-sessions --dry-run --json`, `render-*`, `docs-check` | Valid JSON; doctor passes |
| Skill Routing | `backfill-skill-routing` | `skill-routing` | `ls ~/.openclaw/openclaw-enhance/skills/` + `render-skill oe-tag-router` | Skills present; routing logic visible |
| Watchdog Hooks | `backfill-watchdog-reminder` | `runtime-watchdog` | `cat ~/.openclaw/openclaw.json` + `openclaw hooks list` | Hook enabled |
| Session Isolation | `backfill-session-isolation` | `session-isolation` | `python -m openclaw_enhance.validation.live_probes session-isolation` | Ownership, fail-closed, restart-epoch, sanitization verified |

## Version

Testing Playbook Version: 2.0.0
Last Updated: 2026-04-09
