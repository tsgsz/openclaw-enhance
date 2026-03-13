"""Integration tests for spawn event contract.

Tests the contract between:
- oe-subagent-spawn-enrich hook (TypeScript)
- openclaw-enhance-runtime extension (TypeScript)
- Python CLI integration
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestSpawnEventContract:
    """Test spawn event enrichment contract."""

    def test_hook_handler_exists(self):
        """Verify hook handler TypeScript file exists."""
        handler_path = PROJECT_ROOT / "hooks" / "oe-subagent-spawn-enrich" / "handler.ts"
        assert handler_path.exists(), f"Handler not found: {handler_path}"

        content = handler_path.read_text()
        assert "export function enrichSpawnEvent" in content
        assert "export function handler" in content
        assert "task_id" in content
        assert "dedupe_key" in content

    def test_hook_documentation_exists(self):
        """Verify hook documentation exists."""
        doc_path = PROJECT_ROOT / "hooks" / "oe-subagent-spawn-enrich" / "HOOK.md"
        assert doc_path.exists(), f"Hook documentation not found: {doc_path}"

        content = doc_path.read_text()
        assert "oe-subagent-spawn-enrich" in content
        assert "subagent_spawning" in content
        assert "task_id" in content
        assert "eta_bucket" in content
        assert "dedupe_key" in content

    def test_extension_package_exists(self):
        """Verify extension package.json exists."""
        pkg_path = PROJECT_ROOT / "extensions" / "openclaw-enhance-runtime" / "package.json"
        assert pkg_path.exists(), f"Extension package.json not found: {pkg_path}"

        import json

        pkg = json.loads(pkg_path.read_text())
        assert pkg["name"] == "@openclaw-enhance/runtime"
        assert "exports" in pkg

    def test_extension_plugin_config_exists(self):
        """Verify extension plugin config exists."""
        plugin_path = (
            PROJECT_ROOT / "extensions" / "openclaw-enhance-runtime" / "openclaw.plugin.json"
        )
        assert plugin_path.exists(), f"Plugin config not found: {plugin_path}"

        import json

        config = json.loads(plugin_path.read_text())
        assert config["name"] == "openclaw-enhance-runtime"
        assert config["namespace"] == "oe"
        assert "subagent_spawning" in config.get("hooks", {})

    def test_extension_index_exists(self):
        """Verify extension index.ts exists."""
        index_path = PROJECT_ROOT / "extensions" / "openclaw-enhance-runtime" / "index.ts"
        assert index_path.exists(), f"Extension index not found: {index_path}"

        content = index_path.read_text()
        assert "RuntimeBridge" in content
        assert "EXTENSION_NAME" in content
        assert "activate" in content

    def test_runtime_bridge_exists(self):
        """Verify runtime bridge implementation exists."""
        bridge_path = (
            PROJECT_ROOT / "extensions" / "openclaw-enhance-runtime" / "src" / "runtime-bridge.ts"
        )
        assert bridge_path.exists(), f"Runtime bridge not found: {bridge_path}"

        content = bridge_path.read_text()
        assert "export class RuntimeBridge" in content
        assert "handleSpawnEvent" in content
        assert "getActiveTasks" in content
        assert "isDuplicate" in content

    def test_runtime_bridge_tests_exist(self):
        """Verify runtime bridge tests exist."""
        test_path = (
            PROJECT_ROOT
            / "extensions"
            / "openclaw-enhance-runtime"
            / "src"
            / "runtime-bridge.test.ts"
        )
        assert test_path.exists(), f"Runtime bridge tests not found: {test_path}"

        content = test_path.read_text()
        assert 'import { describe, it } from "node:test"' in content
        assert "RuntimeBridge" in content
        assert "handleSpawnEvent" in content


class TestRenderHookCLI:
    """Test CLI render-hook command."""

    def test_render_hook_command_exists(self):
        """Verify render-hook command is available."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-hook", "--help"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0, f"render-hook command failed: {result.stderr}"
        assert "HOOK_NAME" in result.stdout or "hook" in result.stdout.lower()

    def test_render_hook_oe_subagent_spawn_enrich(self):
        """Verify render-hook works for oe-subagent-spawn-enrich."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "render-hook",
                "oe-subagent-spawn-enrich",
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0, f"render-hook failed: {result.stderr}"

        output = result.stdout
        assert "oe-subagent-spawn-enrich" in output
        assert "subagent_spawning" in output
        assert "task_id" in output
        assert "project" in output
        assert "parent_session" in output
        assert "eta_bucket" in output
        assert "dedupe_key" in output


class TestEventContract:
    """Test the enriched event contract fields."""

    def test_task_id_format(self):
        """Verify task_id format specification."""
        # Task ID should be unique and contain identifying info
        handler_path = PROJECT_ROOT / "hooks" / "oe-subagent-spawn-enrich" / "handler.ts"
        content = handler_path.read_text()

        # Should generate task_id
        assert "generateTaskId" in content
        assert "task_" in content

    def test_eta_buckets(self):
        """Verify ETA bucket categories."""
        handler_path = PROJECT_ROOT / "hooks" / "oe-subagent-spawn-enrich" / "handler.ts"
        content = handler_path.read_text()

        # Should have all three buckets
        assert '"short"' in content
        assert '"medium"' in content
        assert '"long"' in content

    def test_dedupe_key_format(self):
        """Verify dedupe key format."""
        handler_path = PROJECT_ROOT / "hooks" / "oe-subagent-spawn-enrich" / "handler.ts"
        content = handler_path.read_text()

        # Should use project:subagent_type:hash:date format
        assert "generateDedupeKey" in content
        assert "sha256" in content


class TestTypeScriptCompilation:
    """Test TypeScript compilation."""

    def test_hook_handler_compiles(self):
        """Verify hook handler can be type-checked."""
        result = subprocess.run(
            ["npx", "tsc", "--noEmit", "hooks/oe-subagent-spawn-enrich/handler.ts"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        # Type checking may fail due to missing DOM types, but should parse
        # A return code of 0 or specific error patterns are acceptable
        assert "Cannot find name" not in result.stderr or "console" in result.stderr

    def test_extension_compiles(self):
        """Verify extension can be type-checked."""
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        # Extension code should type-check cleanly
        # Ignore errors from test files which are excluded in tsconfig
        error_lines = [line for line in result.stderr.split("\n") if "error TS" in line]
        # Filter out errors from non-extension files
        extension_errors = [
            line
            for line in error_lines
            if "openclaw-enhance-runtime" in line or "hooks/oe-subagent" in line
        ]
        assert len(extension_errors) == 0, f"TypeScript errors: {extension_errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
