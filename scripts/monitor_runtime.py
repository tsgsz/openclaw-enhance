#!/usr/bin/env python3
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


if __name__ == "__main__":
    runpy.run_module("openclaw_enhance.monitor_runtime", run_name="__main__")
