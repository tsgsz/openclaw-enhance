#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from openclaw_enhance.paths import resolve_openclaw_config_path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    home = Path(tmpdir) / ".openclaw"
    home.mkdir()

    # Test 1: openclaw.json exists - should prefer it
    openclaw_json = home / "openclaw.json"
    config_json = home / "config.json"
    openclaw_json.write_text("{}")
    config_json.write_text("{}")

    result = resolve_openclaw_config_path(home)
    if result.name == "openclaw.json":
        print("openclaw-json-preferred")
    else:
        print(f"FAIL: got {result.name}")
        sys.exit(1)

    # Test 2: only config.json exists - should fall back
    openclaw_json.unlink()
    result = resolve_openclaw_config_path(home)
    if result.name == "config.json":
        print("config-json-fallback")
    else:
        print(f"FAIL: got {result.name}")
        sys.exit(1)
