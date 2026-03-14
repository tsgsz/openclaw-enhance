"""Tests for agent catalog and manifest parsing."""

import pytest

from openclaw_enhance.agent_catalog import AgentManifest, parse_agent_manifest


def test_parse_valid_manifest():
    """Test parsing a valid agent manifest."""
    content = """---
agent_id: oe-searcher
workspace: oe-searcher
routing:
  capabilities: [research, documentation]
  model_tier: cheap
  tools_allowed: [websearch, webfetch, Read]
---

# Searcher Agent

Research and documentation lookup agent.
"""
    manifest = parse_agent_manifest(content)

    assert manifest.agent_id == "oe-searcher"
    assert manifest.workspace == "oe-searcher"
    assert manifest.is_valid is True
    assert manifest.errors == []


def test_parse_missing_agent_id():
    """Test parsing manifest with missing agent_id."""
    content = """---
workspace: oe-searcher
routing:
  capabilities: [research]
---

# Agent
"""
    manifest = parse_agent_manifest(content)

    assert manifest.is_valid is False
    assert "agent_id" in manifest.errors[0]


def test_parse_missing_workspace():
    """Test parsing manifest with missing workspace."""
    content = """---
agent_id: oe-searcher
routing:
  capabilities: [research]
---

# Agent
"""
    manifest = parse_agent_manifest(content)

    assert manifest.is_valid is False
    assert "workspace" in manifest.errors[0]


def test_parse_missing_routing():
    """Test parsing manifest with missing routing section."""
    content = """---
agent_id: oe-searcher
workspace: oe-searcher
---

# Agent
"""
    manifest = parse_agent_manifest(content)

    assert manifest.is_valid is False
    assert "routing" in manifest.errors[0]


def test_parse_malformed_yaml():
    """Test parsing manifest with malformed YAML."""
    content = """---
agent_id: oe-searcher
workspace: oe-searcher
routing:
  capabilities: [research
---

# Agent
"""
    manifest = parse_agent_manifest(content)

    assert manifest.is_valid is False
    assert len(manifest.errors) > 0


def test_parse_no_frontmatter():
    """Test parsing content without frontmatter."""
    content = """# Agent

Just markdown content.
"""
    manifest = parse_agent_manifest(content)

    assert manifest.is_valid is False
    assert "frontmatter" in manifest.errors[0].lower()


def test_parse_invalid_capabilities_enum():
    """Test parsing manifest with invalid capability value."""
    content = """---
agent_id: oe-searcher
workspace: oe-searcher
routing:
  capabilities: [invalid_capability]
  model_tier: cheap
---

# Agent
"""
    manifest = parse_agent_manifest(content)

    assert manifest.is_valid is False
    assert "capabilities" in manifest.errors[0].lower()


def test_parse_invalid_model_tier_enum():
    """Test parsing manifest with invalid model_tier value."""
    content = """---
agent_id: oe-searcher
workspace: oe-searcher
routing:
  capabilities: [research]
  model_tier: invalid_tier
---

# Agent
"""
    manifest = parse_agent_manifest(content)

    assert manifest.is_valid is False
    assert "model_tier" in manifest.errors[0].lower()
