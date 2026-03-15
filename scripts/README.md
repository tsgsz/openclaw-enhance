# Development Mode Testing

## Quick Test

Run the automated test script:

```bash
./scripts/test_dev_mode.sh
```

This will:
1. Clean up any existing installation
2. Install in dev mode
3. Verify symlinks are created
4. Test that changes reflect immediately
5. Uninstall and verify cleanup

## Manual Testing Steps

### 1. Install in Dev Mode

```bash
python -m openclaw_enhance.cli install --openclaw-home ~/.openclaw --dev
```

### 2. Verify Symlinks

```bash
ls -la ~/.openclaw/openclaw-enhance/workspaces/
```

You should see symlinks (indicated by `->`) pointing to your source directory.

### 3. Test Immediate Changes

```bash
# Edit a source file
vim workspaces/oe-searcher/AGENTS.md

# Verify change is immediately visible
cat ~/.openclaw/openclaw-enhance/workspaces/oe-searcher/AGENTS.md
```

### 4. Test with OpenClaw

```bash
# Render a workspace to verify OpenClaw can read it
python -m openclaw_enhance.cli render-workspace oe-searcher

# If you have OpenClaw CLI, test agent listing
openclaw agent list | grep oe-
```

### 5. Uninstall

```bash
python -m openclaw_enhance.cli uninstall --openclaw-home ~/.openclaw

# Verify source files are preserved
ls workspaces/oe-searcher/AGENTS.md
```

## Troubleshooting

### Symlinks not created

Check platform:
```bash
uname -s  # Should be Darwin (macOS) or Linux
```

### Changes not reflecting

Verify it's actually a symlink:
```bash
file ~/.openclaw/openclaw-enhance/workspaces/oe-searcher
# Should show: symbolic link to ...
```

### Permission errors

Ensure you have write access:
```bash
ls -ld ~/.openclaw/openclaw-enhance/
```
