"""Integration tests for spawn-enrich hook project context resolution.

Tests verify that the spawn-enrich hook correctly resolves project context
from the runtime state and project registry, with graceful fallback to "default".

Test strategy (hybrid):
- 2 functional tests: verify Python-side runtime state functions that feed the hook
- 1 structural test: verify the TypeScript handler.ts contains resolution logic
"""

import json
from pathlib import Path

import pytest

from openclaw_enhance.runtime.project_state import get_active_project, set_active_project

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestSpawnProjectContext:
    """Test project context resolution for spawn enrichment."""

    def test_spawn_with_active_project(self, tmp_path: Path) -> None:
        """When active_project is set in runtime state, get_active_project returns it.

        This verifies the Python-side contract: set_active_project persists
        and get_active_project retrieves, which the TS hook reads from the
        same runtime-state.json file.
        """
        user_home = tmp_path / "home"
        user_home.mkdir()

        project_path = "/Users/dev/workspace/my-cool-project"
        set_active_project(project_path, user_home=user_home)

        result = get_active_project(user_home=user_home)
        assert result == project_path

        # Also verify the underlying JSON has the right shape
        state_file = user_home / ".openclaw" / "openclaw-enhance" / "runtime-state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["active_project"] == project_path

    def test_spawn_fallback_no_active_project(self, tmp_path: Path) -> None:
        """When no runtime state exists, get_active_project returns None.

        The hook should then fall back to "default" project. This tests
        the graceful degradation path.
        """
        user_home = tmp_path / "empty_home"
        user_home.mkdir()

        # No runtime state file exists
        result = get_active_project(user_home=user_home)
        assert result is None

    def test_hook_ts_source_has_resolution_logic(self) -> None:
        """Verify handler.ts contains project context resolution logic.

        The hook must:
        1. Read runtime-state.json for active_project
        2. Read project-registry.json for project metadata
        3. Expose a project_context field in the enriched payload
        """
        handler_path = PROJECT_ROOT / "hooks" / "oe-subagent-spawn-enrich" / "handler.ts"
        assert handler_path.exists(), f"Handler not found: {handler_path}"

        content = handler_path.read_text()

        # Must read runtime state for active_project
        assert "runtime-state.json" in content, (
            "handler.ts must read runtime-state.json for active_project"
        )
        assert "active_project" in content, "handler.ts must reference active_project field"

        # Must read project registry
        assert "project-registry.json" in content, (
            "handler.ts must read project-registry.json for project metadata"
        )

        # Must produce project_context in output
        assert "project_context" in content, (
            "handler.ts must include project_context in enriched output"
        )

        # Must have graceful fallback
        assert "default" in content, "handler.ts must fallback to 'default' when files missing"

    def test_hook_ts_project_context_shape(self) -> None:
        """Verify handler.ts defines project_context with required fields.

        The project_context must include: project_id, project_name,
        project_type, project_kind.
        """
        handler_path = PROJECT_ROOT / "hooks" / "oe-subagent-spawn-enrich" / "handler.ts"
        content = handler_path.read_text()

        required_fields = ["project_id", "project_name", "project_type", "project_kind"]
        for field in required_fields:
            assert field in content, f"handler.ts must define '{field}' in project_context"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
