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
3. **Verify Status**: `python -m openclaw_enhance.cli status`
   - *Pass*: `installed: true` in output.
4. **Doctor Check**: `python -m openclaw_enhance.cli doctor`
   - *Pass*: Exit code 0.
5. **Final Cleanup**: `python -m openclaw_enhance.cli uninstall`
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
7. **Docs Check**: `python -m openclaw_enhance.cli docs-check`
   - *Pass*: Exit code 0, "Docs check passed".
8. **Validator Self-Surface**: `python -m openclaw_enhance.cli validate-feature --feature-class docs-test-only --report-slug self-surface-smoke`
   - *Pass*: Exit code 0, produces a report with `Conclusion: EXEMPT`.

### 2.3 Routing & Agent Bundle (`workspace-routing`)
1. **Agent List**: `openclaw agent list`
   - *Strict Proof*: Output includes `oe-orchestrator`, `oe-searcher`, `oe-syshelper`, `oe-script_coder`, `oe-watchdog`, `oe-tool-recovery`.
2. **Routing Test**: `openclaw chat --message "帮我规划一个复杂任务"`
   - *Strict Proof*: `openclaw session info <id>` shows `sessions_spawn` to `oe-orchestrator` and subsequent `sessions_yield`.

### 2.4 Runtime Integration Bundle (`runtime-watchdog`)
1. **Hook Verification**: `cat ~/.openclaw/openclaw.json | grep "openclawEnhance"`
   - *Strict Proof*: Hooks are correctly registered in `openclaw.json` under the `hooks` key.
2. **Watchdog Trigger**: `python -m openclaw_enhance.cli status --json`
   - *Strict Proof*: Output contains `timeouts` object, even if empty.

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

## 6. Canonical Current-Branch Backfill

This section tracks the canonical backfill slugs for features already shipped in the current branch. Use these slugs with `validate-feature --report-slug <slug>` to generate standardized backfill reports.

| Feature Capability | Canonical Slug | Feature Class | Method Contract | Strict Observable Proof |
| :--- | :--- | :--- | :--- | :--- |
| Core Installation | `backfill-core-install` | `install-lifecycle` | `python -m openclaw_enhance.cli install` | `status` shows `installed: true`; `openclaw.json` contains `openclawEnhance` |
| Dev Mode (Symlinks) | `backfill-dev-install` | `install-lifecycle` | `python -m openclaw_enhance.cli install --dev` | `ls -la ~/.openclaw/openclaw-enhance/workspaces/` shows symlinks (starts with `l`) |
| CLI Surface Area | `backfill-cli-surface` | `cli-surface` | `status`, `doctor`, `render-*`, `docs-check` | Exit code 0 for all; `status --json` returns valid schema |
| Orchestrator Yield | `backfill-routing-yield` | `workspace-routing` | `openclaw chat --message "..."` | `openclaw session info` shows `sessions_yield` in history |
| Recovery Worker | `backfill-recovery-worker` | `workspace-routing` | `openclaw agent list` | `oe-tool-recovery` present; `render-workspace` shows recovery logic |
| Watchdog Hooks | `backfill-watchdog-reminder` | `runtime-watchdog` | `cat ~/.openclaw/openclaw.json` | `openclawEnhance` hooks present in `hooks` section |

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
- **Command**: `python -m openclaw_enhance.cli render-workspace oe-orchestrator`
- **Expectation**: Output contains "Workspace: oe-orchestrator".
- **Command**: `python -m openclaw_enhance.cli render-skill oe-toolcall-router`
- **Expectation**: Output contains "Toolcall Router" and "sessions_spawn".
- **Command**: `python -m openclaw_enhance.cli docs-check`
- **Expectation**: Exit code 0. "Docs check passed".
- **Command**: `python -m openclaw_enhance.cli validate-feature --feature-class docs-test-only --report-slug self-surface-smoke`
- **Expectation**: Exit code 0. Produces a report with `Conclusion: EXEMPT`.

#### `backfill-routing-yield`
- **Command**: `openclaw chat --message "帮我规划一个复杂任务"`
- **Expectation**: Orchestrator spawns subagents and uses `sessions_yield` to wait for results.
- **Proof**: `openclaw session info <id>` shows `sessions_yield` calls in history.

#### `backfill-recovery-worker`
- **Command**: `openclaw agent list`
- **Expectation**: `oe-tool-recovery` is listed.
- **Proof**: `openclaw agent info oe-tool-recovery` shows "Recovery capabilities".

#### `backfill-watchdog-reminder`
- **Command**: `python -m openclaw_enhance.cli status`
- **Expectation**: Shows hook registration status.
- **Proof**: `grep "openclawEnhance" ~/.openclaw/openclaw.json` returns matches.
