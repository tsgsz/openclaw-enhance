"""Shared test fixtures for openclaw-enhance tests.

This module provides common fixtures used across unit, integration,
and E2E tests for the openclaw-enhance project.
"""

import json
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def tmp_path_with_home(tmp_path: Path) -> Path:
    """Create a temporary path structure with a home directory."""
    home = tmp_path / "home"
    home.mkdir()
    return home


@pytest.fixture
def mock_openclaw_home(tmp_path: Path) -> Path:
    """Create a mock OpenClaw home directory structure.

    Returns:
        Path to the mock OpenClaw home directory.
    """
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)

    # Create VERSION file for support matrix check
    version_file = openclaw_home / "VERSION"
    version_file.write_text("2026.3.1\n")

    # Create openclaw.json (canonical config)
    config_file = openclaw_home / "openclaw.json"
    config_file.write_text(json.dumps({"test": True}) + "\n")

    return openclaw_home


@pytest.fixture
def mock_openclaw_home_with_agents(tmp_path: Path) -> Path:
    """Create a mock OpenClaw home with AGENTS.md."""
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)

    # Create VERSION file
    version_file = openclaw_home / "VERSION"
    version_file.write_text("2026.3.1\n")

    # Create openclaw.json (canonical config)
    config_file = openclaw_home / "openclaw.json"
    config_file.write_text(json.dumps({"test": True}) + "\n")

    # Create AGENTS.md
    agents_file = openclaw_home / "AGENTS.md"
    agents_file.write_text("# Test Agents\n\nTest content\n")

    return openclaw_home


@pytest.fixture
def isolated_user_home(tmp_path: Path) -> Path:
    """Create an isolated user home directory for testing.

    Returns:
        Path to the isolated user home directory.
    """
    return tmp_path / "user_home"


@pytest.fixture
def clean_managed_root(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a clean managed root directory.

    Yields:
        Path to the managed root directory.
    """
    from openclaw_enhance.install import uninstall
    from openclaw_enhance.paths import managed_root

    user_home = tmp_path / "test_user"
    target_root = managed_root(user_home)

    # Ensure clean state
    if target_root.exists():
        uninstall(user_home=user_home)

    yield target_root

    # Cleanup
    if target_root.exists():
        uninstall(user_home=user_home)


@pytest.fixture
def sample_manifest_data() -> dict:
    """Return sample manifest data for testing.

    Returns:
        Dictionary with sample manifest data.
    """
    from datetime import datetime

    from openclaw_enhance.constants import VERSION

    return {
        "version": VERSION,
        "install_time": datetime.now().isoformat(),
        "components": [
            {"name": "test-component-1", "version": VERSION, "path": "test1"},
            {"name": "test-component-2", "version": VERSION, "path": "test2"},
        ],
    }


@pytest.fixture
def sample_task_assessment() -> dict:
    """Return sample task assessment data.

    Returns:
        Dictionary with sample task assessment parameters.
    """
    return {
        "description": "Test task",
        "estimated_toolcalls": 3,
        "requires_parallel": False,
        "complexity_score": 2,
    }


@pytest.fixture
def sample_spawn_event() -> dict:
    """Return sample spawn event data.

    Returns:
        Dictionary with sample spawn event.
    """
    return {
        "event": "subagent_spawning",
        "timestamp": "2024-01-15T10:00:00Z",
        "payload": {
            "subagent_type": "oe-orchestrator",
            "task_description": "Test task",
            "task_id": "task_test_001",
            "project": "test-project",
            "parent_session": "sess_test_001",
            "eta_bucket": "medium",
            "dedupe_key": "test:oe:test:20240115",
        },
        "context": {"session_id": "sess_test_001"},
    }


@pytest.fixture
def runtime_bridge():
    """Provide a RuntimeBridge instance if available.

    Returns:
        RuntimeBridge instance or None if not available.
    """
    try:
        from extensions.openclaw_enhance_runtime.src.runtime_bridge import (
            RuntimeBridge,
        )

        return RuntimeBridge()
    except ImportError:
        return None


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner.

    Returns:
        CliRunner instance.
    """
    from click.testing import CliRunner

    return CliRunner()


@pytest.fixture
def mock_config_file(tmp_path: Path) -> Path:
    """Create a mock OpenClaw config file.

    Returns:
        Path to the mock config file.
    """
    config = {
        "agents": {
            "main": {
                "model": {"primary": "minimax/MiniMax-M2.1", "fallbacks": []},
                "skills": ["oe-eta-estimator", "oe-toolcall-router"],
            }
        }
    }

    config_file = tmp_path / "openclaw.json"
    config_file.write_text(json.dumps(config, indent=2))
    return config_file


@pytest.fixture
def mock_agents_md(tmp_path: Path) -> Path:
    """Create a mock AGENTS.md file.

    Returns:
        Path to the mock AGENTS.md file.
    """
    content = """# Agents

## main

The main agent for handling user requests.

### Tools

- Read
- Write
- Bash

### Skills

- oe-eta-estimator
- oe-toolcall-router
"""

    agents_file = tmp_path / "AGENTS.md"
    agents_file.write_text(content)
    return agents_file


@pytest.fixture
def mock_tools_md(tmp_path: Path) -> Path:
    """Create a mock TOOLS.md file.

    Returns:
        Path to the mock TOOLS.md file.
    """
    content = """# Tools

## Read

Read a file from the filesystem.

## Write

Write content to a file.

## Bash

Execute a bash command.
"""

    tools_file = tmp_path / "TOOLS.md"
    tools_file.write_text(content)
    return tools_file


@pytest.fixture
def sample_skill_md(tmp_path: Path) -> Path:
    """Create a sample SKILL.md file.

    Returns:
        Path to the sample SKILL.md file.
    """
    content = """---
name: test-skill
version: 1.0.0
description: A test skill
---

# Test Skill

This is a test skill for testing purposes.

## Usage

Use this skill for testing.
"""

    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(content)
    return skill_file


@pytest.fixture
def corrupted_manifest(tmp_path: Path) -> Path:
    """Create a corrupted manifest file.

    Returns:
        Path to the corrupted manifest file.
    """
    manifest_file = tmp_path / "install-manifest.json"
    manifest_file.write_text("not valid json {{{")
    return manifest_file


@pytest.fixture
def empty_manifest(tmp_path: Path) -> Path:
    """Create an empty manifest file.

    Returns:
        Path to the empty manifest file.
    """
    manifest_file = tmp_path / "install-manifest.json"
    manifest_file.write_text("")
    return manifest_file
