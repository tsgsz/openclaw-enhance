# Installation Guide

This guide covers installing, verifying, and uninstalling `openclaw-enhance`.

**Skill-First Model**: This enhancement uses file-backed markdown skills that define routing behavior. Main-session skills (oe-eta-estimator, oe-toolcall-router, oe-timeout-state-sync) are synced to your workspace's `skills/` directory during installation. The router skill guides decisions, while native `sessions_spawn` carries out execution.

## Prerequisites

- **Operating System**: macOS or Linux (Windows/WSL not supported in v1)
- **OpenClaw**: Version 2026.3.x (specifically >= 2026.3.11, < 2026.4.0)
- **Python**: 3.10 or higher (current environment)
- **Node.js**: 18.x or higher (for hook/extension bridge)
- **Git**: For cloning the repository

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/openclaw-enhance.git
cd openclaw-enhance

# Verify Python version (>=3.10 required)
python --version

# Install in current Python environment
pip install -e ".[dev]"

# Run preflight checks (essential)
python -m openclaw_enhance.cli doctor --openclaw-home "$HOME/.openclaw"

# Install (dry-run first to preview)
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --dry-run

# Install for real
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw"

# Verify installation
python -m openclaw_enhance.cli status

# Run post-install validation (mandatory for new environments)
python -m openclaw_enhance.cli validate-feature --feature-class install-lifecycle --report-slug backfill-core-install
```

## Detailed Installation

### Step 1: Verify Environment

Before installing the enhancement, ensure your environment meets the requirements:

```bash
# Check Python version (must be 3.10 or higher)
python --version

# Check OpenClaw version
cat "$HOME/.openclaw/VERSION"
# Expected: 2026.3.x (where x >= 11)

# Verify OpenClaw home exists
ls -la "$HOME/.openclaw"
# Verify openclaw.json exists
ls -la "$HOME/.openclaw/openclaw.json"
```

### Step 2: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/openclaw-enhance.git
cd openclaw-enhance

# Install package in current interpreter
pip install -e ".[dev]"

# Note: If you prefer isolation, you can use a venv:
# python -m venv venv && source venv/bin/activate
```

### Step 3: Run Health Check (Doctor)

The `doctor` command is the primary tool for validating your setup. It verifies your environment meets all requirements:

```bash
python -m openclaw_enhance.cli doctor --openclaw-home "$HOME/.openclaw"
```

Expected output:
```
Doctor checks passed.
```

If checks fail, the command will report specific issues:
- Unsupported OpenClaw version
- Missing OpenClaw home directory
- Unsupported platform

### Step 4: Dry-Run Installation

Preview what will be installed without making changes:

```bash
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --dry-run
```

This outputs:
- Components to be installed
- Agents to be registered
- Hooks to be enabled
- Config modifications

### Step 5: Install

Run the actual installation:

```bash
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw"
```

The installer will:
1. Create managed namespace at `~/.openclaw/openclaw-enhance/`
2. Register `oe-*` agents with OpenClaw
3. Copy main-session skills to active workspace
4. Sync hook assets into `~/.openclaw/openclaw-enhance/hooks/`
5. Update supported runtime config surfaces in `openclaw.json` (`agents.list`, `hooks.internal`)
6. Create backup of original config

**Installation order** (symmetric with uninstall):
1. Support matrix check
2. Acquire install lock
3. Create/verify namespace
4. Sync worker workspaces
5. Copy main skills
6. Sync hook assets
7. Register agents and hooks on supported OpenClaw config surfaces
8. Apply config backup/rollback guardrails

### Step 6: Verify Installation

Check that all components are installed:

```bash
python -m openclaw_enhance.cli status
```

Expected output:
```
Installation Path: /Users/you/.openclaw/openclaw-enhance
Installed: Yes
Version: 1.0.0
Install Time: 2026-03-13T10:30:00
Components (13):
  - oe-orchestrator agent
  - oe-searcher agent
  - oe-syshelper agent
  - oe-script_coder agent
  - oe-watchdog agent
  - oe-tool-recovery agent
  - oe-eta-estimator skill
  - oe-toolcall-router skill
  - oe-timeout-state-sync skill
  - managed hook assets
  - oe-subagent-spawn-enrich hook
```

## Post-Installation Setup

### Optional: Setup Runtime Monitor

For automatic timeout detection, set up the monitor script:

```bash
# Add to crontab (runs every minute)
(crontab -l 2>/dev/null; echo "* * * * * cd /path/to/openclaw-enhance && python scripts/monitor_runtime.py --once --openclaw-home \$HOME/.openclaw --state-root \$HOME/.openclaw/openclaw-enhance >/dev/null 2>&1") | crontab -
```

Or use systemd timer (Linux):

```bash
# Copy service files
sudo cp scripts/systemd/openclaw-enhance-monitor.service /etc/systemd/system/
sudo cp scripts/systemd/openclaw-enhance-monitor.timer /etc/systemd/system/

# Enable and start
sudo systemctl enable openclaw-enhance-monitor.timer
sudo systemctl start openclaw-enhance-monitor.timer
```

## Upgrade

To upgrade to a new version:

```bash
# Pull latest changes
git pull origin main

# Reinstall (idempotent)
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --force
```

The `--force` flag allows reinstalling even if already installed.

## Development Mode

For active development of openclaw-enhance itself, use **development mode** (`--dev`). This creates symbolic links instead of copying files, allowing changes to source code to take effect immediately without reinstalling.

### When to Use Development Mode

- **Active development**: You're modifying openclaw-enhance source code
- **Testing changes**: You need rapid iteration without repeated install/uninstall cycles
- **Debugging**: You want to see changes reflected immediately

### Platform Support

**Important**: Development mode is only supported on **macOS and Linux**. Windows is not supported due to symlink permission requirements.

### Installing in Development Mode

```bash
# Install with --dev flag
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --dev
```

This will:
- Create symbolic links from `~/.openclaw/openclaw-enhance/` to your source directory
- Register agents and enable hooks normally
- Track symlink status in the install manifest

### How It Works

In development mode:
- **Workspaces**: Symbolic links to `workspaces/` in source
- **Main skills**: Symbolic links to skill contracts in source
- **Config/hooks**: Still copied (not symlinked) for safety

Example of a development installation:

```
~/.openclaw/openclaw-enhance/
├── workspaces/
│   ├── oe-searcher -> /path/to/source/workspaces/oe-searcher
│   ├── oe-syshelper -> /path/to/source/workspaces/oe-syshelper
│   └── ...
├── manifest.json
└── runtime-state.json
```

### Making Changes

With development mode, changes are immediate:

```bash
# Edit source file
vim workspaces/oe-searcher/AGENTS.md

# Changes are immediately active - no reinstall needed!
python -m openclaw_enhance.cli render-workspace oe-searcher
```

### Uninstalling Development Mode

Uninstall works the same way regardless of install mode:

```bash
python -m openclaw_enhance.cli uninstall --openclaw-home "$HOME/.openclaw"
```

**Note**: Uninstall removes the symbolic links but **preserves your source files**.

### Switching Between Modes

To switch from normal to development mode (or vice versa):

```bash
# Uninstall current mode
python -m openclaw_enhance.cli uninstall --openclaw-home "$HOME/.openclaw"

# Install in new mode
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --dev
```

## Uninstall

To completely remove openclaw-enhance:

```bash
python -m openclaw_enhance.cli uninstall --openclaw-home "$HOME/.openclaw"
```

**Uninstall order** (reverse of install):
1. Remove config changes (owned keys only)
2. Disable hooks
3. Unregister agents
4. Remove main skills
5. Remove worker workspaces
6. Remove managed namespace
7. Release install lock

**What gets removed:**
- All `oe-*` prefixed agents
- All `oe-*` prefixed skills in main workspace
- Hook configurations
- Managed namespace (`~/.openclaw/openclaw-enhance/`)
- Worker workspaces (`~/.openclaw/workspace-openclaw-enhance-*`)

**What is preserved:**
- Your OpenClaw configuration (except owned keys)
- User-created agents and sessions
- Credentials and API keys
- Project files and repositories

### Force Uninstall

If normal uninstall fails:

```bash
python -m openclaw_enhance.cli uninstall --openclaw-home "$HOME/.openclaw" --force
```

**Warning**: Force uninstall may leave orphaned state. Run `doctor` afterward to check.

## Troubleshooting Installation

### "Unsupported OpenClaw version"

Your OpenClaw version is outside the supported range (2026.3.x):

```bash
# Check version
cat "$HOME/.openclaw/VERSION"

# Upgrade OpenClaw first, then retry
```

### "Unsupported platform"

Windows/WSL are not supported in v1. Use macOS or Linux.

### "Preflight checks failed"

Run with verbose output to see specific failures:

```bash
python -m openclaw_enhance.cli doctor --openclaw-home "$HOME/.openclaw" 2>&1
```

### Partial install / Rollback

If installation fails mid-way, the installer automatically rolls back:

1. Config backup is restored
2. Partially installed components are removed
3. Lock is released
4. Error details are logged

Check logs for details:

```bash
cat ~/.openclaw/openclaw-enhance/logs/install.log
```

### Lock file stuck

If a previous install/uninstall was interrupted:

```bash
# Check lock status
python -m openclaw_enhance.cli status

# If stuck, manually remove (use with caution)
rm ~/.openclaw/openclaw-enhance/locks/install.lock
```

## Verification Checklist

After installation, verify:

- [ ] `python -m openclaw_enhance.cli doctor` passes
- [ ] `python -m openclaw_enhance.cli status` shows all components
- [ ] `python -m openclaw_enhance.cli validate-feature --feature-class install-lifecycle --report-slug backfill-core-install` passes
- [ ] All 5 worker agents registered in OpenClaw
- [ ] Main skills copied to main workspace
- [ ] Hook enabled in OpenClaw config
- [ ] Managed namespace exists with correct structure
- [ ] Config backup created at `~/.openclaw/openclaw-enhance/backups/`

Run the full test suite:

```bash
pytest tests/unit tests/integration -q
```

Expected: `328 passed`

## Getting Help

- Check [Troubleshooting](troubleshooting.md) for common issues
- Review [Operations](operations.md) for day-to-day usage
- Read [Architecture](architecture.md) for system understanding
- File issues at: https://github.com/your-org/openclaw-enhance/issues

## Version

Installation Guide Version: 1.0.0
Last Updated: 2026-03-13
