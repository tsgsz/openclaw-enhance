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
1. **Status**: `python -m openclaw_enhance.cli status --json`
   - *Pass*: Valid JSON output containing `install_path`.
2. **Render Workspace**: `python -m openclaw_enhance.cli render-workspace oe-orchestrator`
   - *Pass*: Output contains "oe-orchestrator" and workspace content.
3. **Render Skill**: `python -m openclaw_enhance.cli render-skill oe-toolcall-router`
   - *Pass*: Output contains skill definition.
4. **Render Hook**: `python -m openclaw_enhance.cli render-hook oe-subagent-spawn-enrich`
   - *Pass*: Output contains hook logic.

### 2.3 Routing & Agent Bundle (`workspace-routing`)
1. **Agent List**: `openclaw agent list`
   - *Pass*: Output includes `oe-orchestrator`, `oe-searcher`, `oe-syshelper`, `oe-script_coder`, `oe-watchdog`, `oe-tool-recovery`.
2. **Routing Test**: `openclaw chat --message "帮我规划一个复杂任务"`
   - *Pass*: Session logs show routing to `oe-orchestrator`.

### 2.4 Runtime Integration Bundle (`runtime-watchdog`)
1. **Hook Verification**: `cat ~/.openclaw/config.json | grep "openclawEnhance"`
   - *Pass*: Hooks are correctly registered in OpenClaw config.
2. **Watchdog Trigger**: (Specific trigger command or scenario)
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
- Never modify `~/.openclaw/config.json` manually; use the CLI.
