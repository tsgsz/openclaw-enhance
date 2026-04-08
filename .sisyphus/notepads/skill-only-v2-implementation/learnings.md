# Learnings: skill-only-v2-implementation

## manifest.py creation

### Pattern: JSON manifest at user home directory
- Location: `~/.openclaw/openclaw-enhance/manifest.json`
- Default to empty dict `{}` if file doesn't exist (no error)
- Use `Path.home()` for home directory resolution

### Schema implemented
```python
{
    "version": "2.0.0",
    "skills": {name: {"name", "location", "version"}},
    "hooks": {name: {"name", "enabled"}},
    "extension": {name: {"name", "enabled"}}
}
```

### Functions created
- `load_manifest()` - returns `{}` if file missing
- `save_manifest(data)` - creates parent dir if needed
- `add_skill(name, location, version)` - adds to manifest
- `remove_skill(name)` - removes from manifest
- `get_installed()` - returns summary dict

## T2: CLI --target flag implementation

### New CLI options added
- `--target main|global` on install command
- `--skill <name>` on install command (requires --target)
- `--target main|global` on uninstall command

### Target locations
- `main`: `~/.openclaw/workspace/main/skills/`
- `global`: `~/.openclaw/openclaw-enhance/skills/`

### Behavior
- `install --target main`: Installs all skills to main workspace skills dir
- `install --target global`: Installs all skills to global skills dir
- `install --skill <name> --target <loc>`: Installs specific skill
- `uninstall --target <loc>`: Removes skills from that location
- `status`: Shows manifest contents with locations

### Implementation details
- Skills copied from `openclaw-enhance/skills/` to target location
- Manifest updated via `add_skill()` / `remove_skill()` from manifest.py
- Original hook/extension install behavior unchanged when no --target
