# Troubleshooting

This guide helps diagnose and resolve common issues with `openclaw-enhance`.

**Architecture Note**: This enhancement uses a skill-first model where markdown skills define routing behavior and native `sessions_spawn` executes. Main-session skills live in `~/.openclaw/workspace*/skills/` as SKILL.md files.

## Quick Diagnostics

Start with the built-in diagnostic command:

```bash
python -m openclaw_enhance.cli doctor --openclaw-home "$HOME/.openclaw"
```

If this passes, your installation is healthy. If it fails, read on for specific issues.

## Installation Issues

### "Unsupported OpenClaw version"

**Symptom**:
```
Error: Unsupported OpenClaw version '2026.2.1'. Supported: 2026.3.x
```

**Cause**: Your OpenClaw version is outside the supported range.

**Solution**:
1. Check your OpenClaw version:
   ```bash
   cat "$HOME/.openclaw/VERSION"
   ```
2. Upgrade OpenClaw to 2026.3.x (where x >= 11)
3. Retry installation

### "Unsupported platform"

**Symptom**:
```
Error: Unsupported platform 'win32'. Supported: darwin/linux
```

**Cause**: You're running on Windows or WSL.

**Solution**: 
- Use macOS or Linux
- Windows/WSL support is planned for a future version

### "Preflight checks failed"

**Symptom**:
```
Error: Preflight checks failed
```

**Diagnosis**:
```bash
# Get detailed error output
python -m openclaw_enhance.cli doctor --openclaw-home "$HOME/.openclaw" 2>&1
```

**Common causes**:
- OpenClaw home directory doesn't exist
- Missing VERSION file
- Insufficient permissions

### "Installation already in progress"

**Symptom**:
```
Error: Installation locked by another process (PID: 12345)
```

**Cause**: Previous install/uninstall didn't complete cleanly.

**Solution**:
```bash
# Check if process exists
ps aux | grep 12345

# If process doesn't exist, manually unlock
rm ~/.openclaw/openclaw-enhance/locks/install.lock

# Retry installation
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw"
```

### Partial Installation

**Symptom**: Some components work, others don't.

**Diagnosis**:
```bash
python -m openclaw_enhance.cli status
```

**Solution**:
Force reinstall to ensure all components are present:

```bash
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --force
```

## Worker Routing Issues

### Task Not Escalating to Orchestrator

**Symptom**: Complex tasks stay on main session instead of routing to orchestrator.

**Diagnosis**:
1. Identify your active main workspace (depends on config and OPENCLAW_PROFILE):
   ```bash
   python3 -c "
   import json
   from pathlib import Path
   home = Path.home() / '.openclaw'
   config_path = home / 'openclaw.json'
   if not config_path.exists():
       config_path = home / 'config.json'
   config = json.loads(config_path.read_text()) if config_path.exists() else {}
   
   # Resolution: agent.workspace > agents.defaults.workspace > profile fallback
   ws = config.get('agent', {}).get('workspace') or config.get('agents', {}).get('defaults', {}).get('workspace')
   if ws:
       print(Path(ws).expanduser())
   else:
       import os
       profile = os.environ.get('OPENCLAW_PROFILE', 'default')
       print(home / f'workspace-{profile}' if profile != 'default' else home / 'workspace')
   "
   ```
2. Check that `oe-toolcall-router` skill is installed in that workspace:
   ```bash
   # Use the workspace path from step 1
   ls <workspace-path>/skills/oe-toolcall-router/
   ```
3. Verify skill content is correct:
   ```bash
   cat <workspace-path>/skills/oe-toolcall-router/SKILL.md
   ```

**Solution**:
Reinstall main skills:

```bash
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --force
```

### Worker Not Found

**Symptom**:
```
Error: Unknown worker: oe-searcher
```

**Diagnosis**:
```bash
# Check if agent is registered
openclaw agents list | grep oe-
```

**Solution**:
```bash
# Reinstall to register agents
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --force
```

### Worker Returns Error

**Symptom**: Orchestrator reports worker failure.

**Diagnosis**:
Check worker workspace exists:

```bash
ls -la ~/.openclaw/workspace-openclaw-enhance-searcher/
```

**Solution**:
1. Verify workspace structure:
   ```bash
   ls ~/.openclaw/workspace-openclaw-enhance-searcher/
   # Should show: AGENTS.md, TOOLS.md, skills/
   ```

2. If missing, reinstall:
   ```bash
   python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --force
   ```

## Timeout Issues

### False Positive Timeouts

**Symptom**: Healthy sessions marked as timed out.

**Cause**: Monitor script has stale state or incorrect thresholds.

**Diagnosis**:
1. Check runtime state:
   ```bash
   cat ~/.openclaw/openclaw-enhance/state/runtime-state.json | jq '.timeouts'
   ```

2. Check monitor logs:
   ```bash
   cat ~/.openclaw/openclaw-enhance/logs/monitor.log
   ```

**Solution**:
1. Clear timeout state:
   ```bash
   # Backup first
   cp ~/.openclaw/openclaw-enhance/state/runtime-state.json \
      ~/.openclaw/openclaw-enhance/state/runtime-state.json.bak
   
   # Remove false positive
   # Edit file to remove the incorrect timeout entry
   nano ~/.openclaw/openclaw-enhance/state/runtime-state.json
   ```

2. Adjust thresholds if needed (see [Operations Guide](operations.md#configuring-timeouts))

### Timeouts Not Detected

**Symptom**: Long-running sessions not timing out.

**Diagnosis**:
1. Check monitor is running:
   ```bash
   # On macOS
   launchctl print gui/$UID/ai.openclaw.enhance.monitor

   # If using cron
   crontab -l | grep monitor_runtime
   
   # If using systemd
   systemctl status openclaw-enhance-monitor.timer
   ```

2. Check runtime state has tasks:
   ```bash
   cat ~/.openclaw/openclaw-enhance/state/runtime-state.json | jq '.tasks'
   ```

**Solution**:
1. On macOS, reinstall or restart the managed LaunchAgent:
   ```bash
   python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --force
   launchctl kickstart -k gui/$UID/ai.openclaw.enhance.monitor
   ```

2. Ensure monitor script is executable:
   ```bash
   chmod +x scripts/monitor_runtime.py
   ```

3. Test monitor manually:
   ```bash
   python scripts/monitor_runtime.py --once \
     --openclaw-home "$HOME/.openclaw" \
     --state-root "$HOME/.openclaw/openclaw-enhance"
   ```

4. Re-setup cron-based monitoring:
   ```bash
    # Add to crontab
    (crontab -l 2>/dev/null; echo "* * * * * cd /path/to/openclaw-enhance && python scripts/monitor_runtime.py --once --openclaw-home \$HOME/.openclaw --state-root \$HOME/.openclaw/openclaw-enhance >/dev/null 2>&1") | crontab -
   ```

## State Corruption

### Invalid JSON in Runtime State

**Symptom**:
```
Error: Expecting ',' delimiter: line 42 column 5 (char 1234)
```

**Cause**: Runtime state file got corrupted.

**Solution**:
1. Backup corrupted state:
   ```bash
   cp ~/.openclaw/openclaw-enhance/state/runtime-state.json \
      ~/.openclaw/openclaw-enhance/state/runtime-state.json.corrupt.$(date +%s)
   ```

2. Reset to clean state:
   ```bash
   echo '{
     "version": "1.0.0",
     "last_updated_utc": "'$(date -u +%Y-%m-%dT%H:%M:%S)'",
     "tasks": {},
     "timeouts": {},
     "projects": {}
   }' > ~/.openclaw/openclaw-enhance/state/runtime-state.json
   ```

3. Reinstall if issues persist:
   ```bash
   python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --force
   ```

### Stale Task Entries

**Symptom**: Old tasks still showing as "active" in state.

**Solution**:
```bash
# View current tasks
cat ~/.openclaw/openclaw-enhance/state/runtime-state.json | jq '.tasks'

# Edit to remove stale entries
nano ~/.openclaw/openclaw-enhance/state/runtime-state.json
```

## Performance Issues

### Slow Task Routing

**Symptom**: Noticeable delay before orchestrator responds.

**Causes**:
- Large runtime state file
- Too many active tasks
- Slow disk I/O

**Diagnosis**:
```bash
# Check state file size
ls -lh ~/.openclaw/openclaw-enhance/state/runtime-state.json

# Count active tasks
cat ~/.openclaw/openclaw-enhance/state/runtime-state.json | jq '.tasks | length'
```

**Solution**:
1. Clear completed tasks:
   ```bash
   # Edit state file, remove completed/old tasks
   nano ~/.openclaw/openclaw-enhance/state/runtime-state.json
   ```

2. Archive old state:
   ```bash
   mv ~/.openclaw/openclaw-enhance/state/runtime-state.json \
      ~/.openclaw/openclaw-enhance/state/runtime-state.json.archive.$(date +%s)
   
   # Reinstall creates fresh state
   python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --force
   ```

### High Memory Usage

**Symptom**: Monitor script or agents consuming excessive memory.

**Diagnosis**:
```bash
# Check memory usage
ps aux | grep -E "(openclaw|monitor_runtime)"

# Check state file size
ls -lh ~/.openclaw/openclaw-enhance/state/runtime-state.json
```

**Solution**:
1. Reduce state history:
   ```bash
   # Edit state to remove old entries
   nano ~/.openclaw/openclaw-enhance/state/runtime-state.json
   ```

2. Restart monitoring:
   ```bash
   # Kill existing monitor processes
   pkill -f monitor_runtime
   
   # Re-setup monitoring
   # (See Installation Guide for setup)
   ```

## Configuration Issues

### OpenClaw Config Not Updated

**Symptom**: Agents/hooks not appearing in OpenClaw.

**Diagnosis**:
```bash
# Check OpenClaw config
cat ~/.openclaw/openclaw.json | jq '.agents'
cat ~/.openclaw/openclaw.json | jq '.hooks'
```

**Solution**:
1. Check backup exists:
   ```bash
   ls ~/.openclaw/openclaw-enhance/backups/
   ```

2. Restore backup and reinstall:
   ```bash
   # Restore original config
   cp ~/.openclaw/openclaw-enhance/backups/openclaw.json.bak \
      ~/.openclaw/openclaw.json
   
   # Reinstall
   python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw"
   ```

### Permission Denied

**Symptom**:
```
Error: Permission denied: ~/.openclaw/openclaw-enhance/...
```

**Solution**:
```bash
# Fix ownership
sudo chown -R $(whoami):$(whoami) ~/.openclaw/openclaw-enhance/

# Fix permissions
chmod -R u+rw ~/.openclaw/openclaw-enhance/
```

## Hook Issues

### Hook Not Firing

**Symptom**: Subagent spawn events not being enriched.

**Diagnosis**:
1. Check hook is registered:
   ```bash
   cat ~/.openclaw/openclaw.json | jq '.hooks.internal'
   openclaw hooks list
   ```

2. Check handler file exists:
   ```bash
   ls ~/.openclaw/openclaw-enhance/hooks/oe-subagent-spawn-enrich/
   ```

**Solution**:
```bash
# Reinstall hooks
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --force

# Verify
openclaw hooks list
```

## Getting More Help

### Enable Debug Logging

Set environment variable for verbose output:

```bash
export OPENCLAW_ENHANCE_DEBUG=1
python -m openclaw_enhance.cli doctor --openclaw-home "$HOME/.openclaw"
```

### Check Logs

View installation logs:

```bash
cat ~/.openclaw/openclaw-enhance/logs/install.log
```

View monitor logs:

```bash
cat ~/.openclaw/openclaw-enhance/logs/monitor.log
```

### Collect Diagnostics

Generate a diagnostics report:

```bash
# Create diagnostics bundle
{
  echo "=== System Info ==="
  uname -a
  python --version
  
  echo "=== OpenClaw Version ==="
  cat ~/.openclaw/VERSION
  
  echo "=== Installation Status ==="
  python -m openclaw_enhance.cli status --json
  
  echo "=== Runtime State ==="
  cat ~/.openclaw/openclaw-enhance/state/runtime-state.json
  
  echo "=== Install Log ==="
  cat ~/.openclaw/openclaw-enhance/logs/install.log
} > diagnostics.txt 2>&1
```

### Report Issues

Include the diagnostics report when filing issues:

1. Run the diagnostics collection above
2. Redact any sensitive information
3. File issue at: https://github.com/your-org/openclaw-enhance/issues
4. Include:
   - OpenClaw version
   - Operating system
   - Python version
   - Error messages
   - Steps to reproduce

## Recovery Procedures

### Complete Reset

**Warning**: This removes all enhancement state but preserves OpenClaw config.

```bash
# Uninstall
python -m openclaw_enhance.cli uninstall --openclaw-home "$HOME/.openclaw"

# Remove all traces (optional)
rm -rf ~/.openclaw/openclaw-enhance/
rm -rf ~/.openclaw/workspace-openclaw-enhance-*

# Reinstall fresh
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw"
```

### Restore from Backup

If something goes wrong, restore from pre-install backup:

```bash
# Restore OpenClaw config
cp ~/.openclaw/openclaw-enhance/backups/openclaw.json.bak \
   ~/.openclaw/openclaw.json

# Uninstall enhancement
python -m openclaw_enhance.cli uninstall --openclaw-home "$HOME/.openclaw"
```

## Version

Troubleshooting Guide Version: 1.0.0
Last Updated: 2026-03-13
