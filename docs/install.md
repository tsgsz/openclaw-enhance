# Installation Guide

This guide covers installing, verifying, and uninstalling `openclaw-enhance`.

## v2 Architecture

**openclaw-enhance v2 采用纯 Skill 架构**：
- **无工作区 (Workspaces)**：v1 的 agent 工作区已归档
- **无 Agent 注册**：不再使用 `oe-orchestrator`、`oe-searcher` 等托管 Agent
- **纯 Skill 路由**：所有路由逻辑通过 Skills 实现

## Prerequisites

- **Operating System**: macOS or Linux
- **OpenClaw**: Version 2026.3.x (specifically >= 2026.3.11, < 2026.4.0)
- **Python**: 3.10 or higher
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

# Run post-install validation
python -m openclaw_enhance.cli validate-feature --feature-class install-lifecycle --report-slug backfill-core-install
```

## Detailed Installation

### Step 1: Verify Environment

```bash
# Check Python version (must be 3.10 or higher)
python --version

# Check OpenClaw version
cat "$HOME/.openclaw/VERSION"

# Verify OpenClaw home exists
ls -la "$HOME/.openclaw"
ls -la "$HOME/.openclaw/openclaw.json"
```

### Step 2: Clone and Setup

```bash
git clone https://github.com/your-org/openclaw-enhance.git
cd openclaw-enhance
pip install -e ".[dev]"
```

### Step 3: Run Health Check (Doctor)

```bash
python -m openclaw_enhance.cli doctor --openclaw-home "$HOME/.openclaw"
```

### Step 4: Dry-Run Installation

```bash
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --dry-run
```

### Step 5: Install

```bash
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw"
```

The installer will:
1. Create managed namespace at `~/.openclaw/openclaw-enhance/`
2. Sync skills to `~/.openclaw/openclaw-enhance/skills/`
3. Copy main-session skills to active workspace
4. Sync hook assets into `~/.openclaw/openclaw-enhance/hooks/`
5. Update `openclaw.json` (`hooks.internal`)
6. Create backup of original config

### Step 6: Verify Installation

```bash
python -m openclaw_enhance.cli status
```

## Post-Installation Setup

### Runtime Monitor

On macOS, `install` provisions and starts two per-user managed LaunchAgents:

- `ai.openclaw.enhance.monitor` — runtime timeout/watchdog monitor (every 60 seconds)
- `ai.openclaw.session-cleanup` — OE-managed stale session cleanup (hourly)

For Linux, configure via systemd:

```bash
sudo cp scripts/systemd/openclaw-enhance-monitor.service /etc/systemd/system/
sudo cp scripts/systemd/openclaw-enhance-monitor.timer /etc/systemd/system/
sudo systemctl enable openclaw-enhance-monitor.timer
sudo systemctl start openclaw-enhance-monitor.timer
```

On macOS, verify the managed services:

```bash
launchctl print gui/$UID/ai.openclaw.enhance.monitor
tail -f ~/.openclaw/openclaw-enhance/logs/monitor.log
```

## Development Mode

For active development, use **development mode** (`--dev`). This creates symbolic links instead of copying files.

```bash
python -m openclaw_enhance.cli install --openclaw-home "$HOME/.openclaw" --dev
```

In development mode:
- **Skills**: Symbolic links to `skills/` in source
- **Config/hooks**: Still copied for safety

## Uninstall

```bash
python -m openclaw_enhance.cli uninstall --openclaw-home "$HOME/.openclaw"
```

**What gets removed:**
- Managed monitor LaunchAgent plist on macOS
- All `oe-*` prefixed skills
- Hook configurations
- Managed namespace (`~/.openclaw/openclaw-enhance/`)

**What is preserved:**
- Your OpenClaw configuration (except owned keys)
- User-created sessions
- Project files and repositories

### Force Uninstall

```bash
python -m openclaw_enhance.cli uninstall --openclaw-home "$HOME/.openclaw" --force
```

## Verification Checklist

After installation, verify:

- [ ] `python -m openclaw_enhance.cli doctor` passes
- [ ] `python -m openclaw_enhance.cli status` shows all components
- [ ] Skills installed in `~/.openclaw/openclaw-enhance/skills/`
- [ ] Main skills in workspace
- [ ] Hook enabled in OpenClaw config

Run the test suite:

```bash
pytest tests/unit tests/integration -q
```

## Version

Installation Guide Version: 2.0.0
Last Updated: 2026-04-09
