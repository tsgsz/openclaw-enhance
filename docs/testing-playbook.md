# OpenCode Real-Environment Validation Contract

This document defines the mandatory validation process for all changes to `openclaw-enhance`. No feature can be merged without a successful real-environment test report.

## 1. Feature-Class Matrix

Validation requirements are determined by the feature class of the change.

| Feature Class | Description | Mandatory Validation |
| :--- | :--- | :--- |
| `install-lifecycle` | Changes to install/uninstall logic, path management, or config patching. | Full Lifecycle Bundle |
| `cli-surface` | Changes to `openclaw-enhance` CLI commands or output formatting. | CLI Surface Bundle |
| `workspace-routing` | Changes to `AGENTS.md`, `TOOLS.md`, or agent registration. | Routing & Agent Bundle |
| `runtime-watchdog` | Changes to hooks, runtime monitoring, or watchdog logic. | Runtime Integration Bundle |
| `docs-test-only` | Changes only to documentation or unit/integration tests. | Docs Check Only (Exempt) |

## 2. Validation Bundles

### 2.1 Full Lifecycle Bundle (`install-lifecycle`)
Target: Default `~/.openclaw`

1. **Cleanup**: `python -m openclaw_enhance.cli uninstall`
    - *Pass*: `~/.openclaw/openclaw-enhance` is removed or empty.
2. **Install**: `python -m openclaw_enhance.cli install`
    - *Pass*: Exit code 0, "Installation successful" in output.
3. **Monitor Service (macOS)**: `launchctl print gui/$UID/ai.openclaw.enhance.monitor`
    - *Pass*: LaunchAgent is loaded and points at `python -m openclaw_enhance.monitor_runtime` with `RunAtLoad` and a 60-second interval.
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
4. **Render Workspace**: `python -m openclaw_enhance.cli render-workspace oe-orchestrator`
   - *Pass*: Output contains "oe-orchestrator" and workspace content.
5. **Render Skill**: `python -m openclaw_enhance.cli render-skill oe-toolcall-router`
   - *Pass*: Output contains skill definition.
6. **Render Hook**: `python -m openclaw_enhance.cli render-hook oe-subagent-spawn-enrich`
   - *Pass*: Output contains hook logic.
7. **Cleanup Sessions Dry Run**: `python -m openclaw_enhance.cli cleanup-sessions --dry-run --json`
   - *Pass*: Valid JSON output containing `safe_to_remove`, `skipped_active`, `skipped_uncertain`, `removed`, and `dry_run`.
8. **Docs Check**: `python -m openclaw_enhance.cli docs-check`
   - *Pass*: Exit code 0, "Docs check passed".
9. **Validator Self-Surface**: `python -m openclaw_enhance.cli validate-feature --feature-class docs-test-only --report-slug self-surface-smoke`
   - *Pass*: Exit code 0, produces a report with `Conclusion: EXEMPT`.

### 2.3 Routing & Agent Bundle (`workspace-routing`)

#### Direct Orchestrator Proof (`backfill-routing-yield`)
1. **Agent List**: `openclaw agents list`
   - *Pass*: Output includes `oe-orchestrator`, `oe-searcher`, `oe-syshelper`, `oe-script_coder`, `oe-watchdog`, `oe-tool-recovery`.
2. **Routing Surface Test**: `openclaw agent --agent oe-orchestrator -m "帮我规划一个复杂任务" --json`
   - *Pass*: Live agent output returns a real session id, exposes `sessions_yield` in the orchestrator tool surface, and `openclaw sessions --agent oe-orchestrator --json` provides a transcript path for that runtime session.

#### Recovery Runtime Surface (`backfill-recovery-worker`)
3. **Recovery Specialist Test**: `openclaw agent --agent oe-tool-recovery -m "A tool call failed because the requested tool name was websearch. Respond with only the corrected method name to use instead." --json`
   - *Pass*: `oe-tool-recovery` is registered, live recovery session returns a session id and transcript path, and the runtime recovery identity is initialized.

#### Main-to-Orchestrator Escalation Proof (`backfill-main-escalation`)
4. **Main Session Escalation**: `python -m openclaw_enhance.validation.live_probes main-escalation --openclaw-home "$OPENCLAW_HOME" --message "搜索 2025 年整个东南亚 iGaming 行业现状，给出 2026 年判断，并先设计一个 20 页左右的 PPT 大纲（包含内容、数据和讲稿），保证数据真实可追溯。"`
   - *Pass*: Heavy main-session request triggers `oe-orchestrator` spawn, main session transcript contains `sessions_spawn` tool call for `oe-orchestrator`, probe emits `PROBE_MAIN_ESCALATION_OK` marker with both main and orchestrator session evidence.
   - *Note*: This proof is currently **PROVISIONAL** and depends on Task 8 runtime repair for a full PASS.

### 2.4 Runtime Integration Bundle (`runtime-watchdog`)
1. **Hook Verification**: `cat ~/.openclaw/openclaw.json | jq '.hooks.internal'`
   - *Pass*: `hooks.internal.entries.oe-subagent-spawn-enrich.enabled` is `true` and `hooks.internal.load.extraDirs` includes the managed hook directory.
2. **Hook Discovery**: `openclaw hooks list`
   - *Pass*: `oe-subagent-spawn-enrich` is listed as ready.
3. **Watchdog Trigger**: (Specific trigger command or scenario)
   - *Pass*: Watchdog identifies timeout or state change as expected.

### 2.5 Docs Check Only (`docs-test-only`)
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

## 6. Current branch shipped set (Canonical Current-Branch Backfill)

This section tracks the canonical backfill slugs for features already shipped in the current branch. Use these slugs with `validate-feature --report-slug <slug>` to generate standardized backfill reports.

| Feature Capability | Canonical Slug | Feature Class | Method Contract | Observable Proof |
| :--- | :--- | :--- | :--- | :--- |
| Core Installation | `backfill-core-install` | `install-lifecycle` | `python -m openclaw_enhance.cli install` | `status` shows `installed: true`; files exist in `~/.openclaw/openclaw-enhance` |
| Monitor Auto-Start (macOS) | `backfill-monitor-auto-start` | `install-lifecycle` | `python -m openclaw_enhance.cli install` + `launchctl print gui/$UID/ai.openclaw.enhance.monitor` | LaunchAgent is loaded and points at `python -m openclaw_enhance.monitor_runtime` |
| Dev Mode (Symlinks) | `backfill-dev-install` | `install-lifecycle` | `python -m openclaw_enhance.cli install --dev` | `ls -la ~/.openclaw/openclaw-enhance/workspaces/` shows symlinks (starts with `l`) |
| CLI Surface Area | `backfill-cli-surface` | `cli-surface` | `status`, `status --json`, `doctor`, `cleanup-sessions --dry-run --json`, `render-*`, `docs-check`, `validate-feature` | Valid JSON; doctor passes; cleanup dry-run reports buckets; rendered content matches; docs-check passes; validator self-surface ok |
| Orchestrator Runtime Surface | `backfill-routing-yield` | `workspace-routing` | `openclaw agent --agent oe-orchestrator -m "帮我规划一个复杂任务" --json` | Live agent output exposes `sessions_yield`; session metadata exposes transcript path; runtime orchestrator identity is initialized |
| Recovery Runtime Surface | `backfill-recovery-worker` | `workspace-routing` | `openclaw agents list` + `openclaw agent --agent oe-tool-recovery -m "..." --json` | `oe-tool-recovery` is registered; live recovery session returns a session id and transcript path; runtime recovery identity is initialized |
| Main-to-Orchestrator Escalation | `backfill-main-escalation` | `workspace-routing` | `python -m openclaw_enhance.validation.live_probes main-escalation` | **PROVISIONAL**: Main session transcript contains `sessions_spawn` for `oe-orchestrator`; both session IDs are captured. |
| Watchdog Hooks | `backfill-watchdog-reminder` | `runtime-watchdog` | `cat ~/.openclaw/openclaw.json` + `openclaw hooks list` | `hooks.internal.entries.oe-subagent-spawn-enrich.enabled` is true and the hook is discoverable |

### 6.1 Method Contracts & Expectations

#### `backfill-core-install`
- **Command**: `python -m openclaw_enhance.cli uninstall && python -m openclaw_enhance.cli install`
- **Expectation**: Exit code 0. "Installation successful" in stdout.
- **Report**: Must include `doctor` output showing all checks passed.

#### `backfill-dev-install`
- **Command**: `python -m openclaw_enhance.cli install --dev`
- **Expectation**: Exit code 0.
- **Proof**: `ls -la ~/.openclaw/openclaw-enhance/workspaces/oe-orchestrator` shows it points back to `src/openclaw_enhance/workspaces/oe-orchestrator`.

#### `backfill-cli-surface`
- **Command**: `python -m openclaw_enhance.cli status && python -m openclaw_enhance.cli status --json`
- **Expectation**: Valid JSON. `installed` is `true`.
- **Command**: `python -m openclaw_enhance.cli doctor`
- **Expectation**: Exit code 0. "Doctor checks passed".
- **Command**: `python -m openclaw_enhance.cli cleanup-sessions --dry-run --json`
- **Expectation**: Exit code 0. Valid JSON output with cleanup classification buckets and no mutation in dry-run mode.
- **Command**: `python -m openclaw_enhance.cli render-workspace oe-orchestrator`
- **Expectation**: Output contains "Workspace: oe-orchestrator".
- **Command**: `python -m openclaw_enhance.cli render-skill oe-toolcall-router`
- **Expectation**: Output contains "Toolcall Router" and "sessions_spawn".
- **Command**: `python -m openclaw_enhance.cli docs-check`
- **Expectation**: Exit code 0. "Docs check passed".
- **Command**: `python -m openclaw_enhance.cli validate-feature --feature-class docs-test-only --report-slug self-surface-smoke`
- **Expectation**: Exit code 0. Produces a report with `Conclusion: EXEMPT`.

#### `backfill-routing-yield`
- **Command**: `openclaw agent --agent oe-orchestrator -m "帮我规划一个复杂任务" --json`
- **Expectation**: Exit code 0. Live output returns a real session id and the orchestrator tool surface includes `sessions_yield`.
- **Proof**: `openclaw sessions --agent oe-orchestrator --json` provides a `transcriptPath` for the live session and the runtime workspace identity is initialized.

#### `backfill-recovery-worker`
- **Command**: `openclaw agents list`
- **Expectation**: `oe-tool-recovery` is listed.
- **Command**: `openclaw agent --agent oe-tool-recovery -m "A tool call failed because the requested tool name was websearch. Respond with only the corrected method name to use instead." --json`
- **Expectation**: Exit code 0. Live output returns a real session id for the recovery workspace.
- **Proof**: `openclaw sessions --agent oe-tool-recovery --json` provides a `transcriptPath` for the live session and the runtime recovery workspace identity is initialized.

#### `backfill-recovery-worker`
- **Command**: `openclaw agents list`
- **Expectation**: `oe-tool-recovery` is listed.
- **Command**: `openclaw agent --agent oe-tool-recovery -m "A tool call failed because the requested tool name was websearch. Respond with only the corrected method name to use instead." --json`
- **Expectation**: Exit code 0. Live output returns a real session id for the recovery workspace.
- **Proof**: `openclaw sessions --agent oe-tool-recovery --json` provides a `transcriptPath` for the live session and the runtime recovery workspace identity is initialized.

#### `backfill-main-escalation`
- **Command**: `python -m openclaw_enhance.validation.live_probes main-escalation --openclaw-home "$OPENCLAW_HOME" --message "..."`
- **Expectation**: **PROVISIONAL**. Probe identifies main session ID and orchestrator session ID.
- **Proof**: `PROBE_MAIN_ESCALATION_OK` marker in output. Note: Full transcript evidence depends on Task 8 repair.

#### `backfill-watchdog-reminder`
- **Command**: `python -m openclaw_enhance.validation.live_probes watchdog-reminder --openclaw-home "$OPENCLAW_HOME" --config-path "$OPENCLAW_CONFIG_PATH" --session-id strict-watchdog-probe`
- **Expectation**: Verifies supported `hooks.internal` config (or workspace contract fallback) and live reminder delivery.
- **Proof**: JSON output with `marker: PROBE_WATCHDOG_REMINDER_OK`, `proof: config_hook_plus_live_reminder` or `workspace_contract_plus_live_reminder`, and session_id evidence.
