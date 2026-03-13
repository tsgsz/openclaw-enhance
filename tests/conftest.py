"""Pytest configuration and shared fixtures for openclaw-enhance tests.

This conftest.py makes all fixtures from tests.fixtures available globally.
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Add tests directory to path for fixtures
fixtures_path = Path(__file__).parent
if str(fixtures_path) not in sys.path:
    sys.path.insert(0, str(fixtures_path))

# Import all fixtures from fixtures module
from fixtures import *  # noqa: F401, F403
