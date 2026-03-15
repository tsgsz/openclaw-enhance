"""Unit tests for worker workspace templates."""

from pathlib import Path

from openclaw_enhance.workspaces import (
    get_workspace_metadata,
    get_workspace_skills,
    list_workspaces,
    render_workspace,
    workspace_exists,
)


class TestWorkerWorkspaceStructure:
    """Test that worker workspaces have correct structure."""

    WORKER_WORKSPACES = [
        "oe-searcher",
        "oe-syshelper",
        "oe-script_coder",
        "oe-watchdog",
        "oe-tool-recovery",
    ]

    def test_all_worker_workspaces_exist(self):
        """All worker workspaces should exist."""
        available = list_workspaces()

        for workspace in self.WORKER_WORKSPACES:
            assert workspace in available, f"Workspace {workspace} not found"

    def test_worker_workspaces_have_agents_md(self):
        """Each worker should have AGENTS.md."""
        for workspace in self.WORKER_WORKSPACES:
            metadata = get_workspace_metadata(workspace)
            assert metadata["has_agents"] is True, f"{workspace} missing AGENTS.md"

    def test_worker_workspaces_have_tools_md(self):
        """Each worker should have TOOLS.md."""
        for workspace in self.WORKER_WORKSPACES:
            metadata = get_workspace_metadata(workspace)
            assert metadata["has_tools"] is True, f"{workspace} missing TOOLS.md"

    def test_worker_workspaces_exist_in_filesystem(self):
        """Each worker should exist as directory."""
        for workspace in self.WORKER_WORKSPACES:
            assert workspace_exists(workspace), f"{workspace} directory not found"


class TestSearcherWorkspace:
    """Test oe-searcher workspace specifics."""

    def test_searcher_has_web_search_skill(self):
        """Searcher should have web search skill."""
        skills = get_workspace_skills("oe-searcher")
        assert "oe-web-search" in skills

    def test_searcher_metadata(self):
        """Searcher metadata should be correct."""
        metadata = get_workspace_metadata("oe-searcher")
        assert metadata["name"] == "oe-searcher"
        assert "oe-web-search" in metadata["skills"]


class TestSyshelperWorkspace:
    """Test oe-syshelper workspace specifics."""

    def test_syshelper_has_session_inspect_skill(self):
        """Syshelper should have session inspect skill."""
        skills = get_workspace_skills("oe-syshelper")
        assert "oe-session-inspect" in skills

    def test_syshelper_metadata(self):
        """Syshelper metadata should be correct."""
        metadata = get_workspace_metadata("oe-syshelper")
        assert metadata["name"] == "oe-syshelper"
        assert "oe-session-inspect" in metadata["skills"]


class TestScriptCoderWorkspace:
    """Test oe-script_coder workspace specifics."""

    def test_script_coder_has_script_test_skill(self):
        """Script coder should have script test skill."""
        skills = get_workspace_skills("oe-script_coder")
        assert "oe-script-test" in skills

    def test_script_coder_metadata(self):
        """Script coder metadata should be correct."""
        metadata = get_workspace_metadata("oe-script_coder")
        assert metadata["name"] == "oe-script_coder"
        assert "oe-script-test" in metadata["skills"]


class TestWatchdogWorkspace:
    """Test oe-watchdog workspace specifics."""

    def test_watchdog_has_timeout_alarm_skill(self):
        """Watchdog should have timeout alarm skill."""
        skills = get_workspace_skills("oe-watchdog")
        assert "oe-timeout-alarm" in skills

    def test_watchdog_has_session_status_skill(self):
        """Watchdog should have session status skill."""
        skills = get_workspace_skills("oe-watchdog")
        assert "oe-session-status" in skills

    def test_watchdog_has_both_skills(self):
        """Watchdog should have exactly 2 skills."""
        skills = get_workspace_skills("oe-watchdog")
        assert len(skills) == 2
        assert "oe-timeout-alarm" in skills
        assert "oe-session-status" in skills

    def test_watchdog_metadata(self):
        """Watchdog metadata should be correct."""
        metadata = get_workspace_metadata("oe-watchdog")
        assert metadata["name"] == "oe-watchdog"
        assert "oe-timeout-alarm" in metadata["skills"]
        assert "oe-session-status" in metadata["skills"]


class TestToolRecoveryWorkspace:
    """Test oe-tool-recovery workspace specifics."""

    def test_tool_recovery_has_recovery_skill(self):
        """Tool recovery should have tool recovery skill."""
        skills = get_workspace_skills("oe-tool-recovery")
        assert "oe-tool-recovery" in skills

    def test_tool_recovery_metadata(self):
        """Tool recovery metadata should be correct."""
        metadata = get_workspace_metadata("oe-tool-recovery")
        assert metadata["name"] == "oe-tool-recovery"
        assert "oe-tool-recovery" in metadata["skills"]

    def test_tool_recovery_has_exactly_one_skill(self):
        """Tool recovery should have exactly 1 skill."""
        skills = get_workspace_skills("oe-tool-recovery")
        assert len(skills) == 1
        assert "oe-tool-recovery" in skills


class TestWorkspaceRendering:
    """Test workspace rendering functionality."""

    def test_render_searcher_includes_web_search_skill(self):
        """Rendered searcher should include web search skill."""
        rendered = render_workspace("oe-searcher")
        assert "oe-web-search" in rendered
        assert "Web Search" in rendered or "web search" in rendered.lower()

    def test_render_syshelper_includes_session_inspect_skill(self):
        """Rendered syshelper should include session inspect skill."""
        rendered = render_workspace("oe-syshelper")
        assert "oe-session-inspect" in rendered
        assert "Session Inspect" in rendered or "session" in rendered.lower()

    def test_render_script_coder_includes_script_test_skill(self):
        """Rendered script coder should include script test skill."""
        rendered = render_workspace("oe-script_coder")
        assert "oe-script-test" in rendered
        assert "Script Test" in rendered or "test" in rendered.lower()

    def test_render_watchdog_includes_both_skills(self):
        """Rendered watchdog should include both skills."""
        rendered = render_workspace("oe-watchdog")
        assert "oe-timeout-alarm" in rendered
        assert "oe-session-status" in rendered
        assert "Timeout Alarm" in rendered or "timeout" in rendered.lower()
        assert "Session Status" in rendered or "status" in rendered.lower()

    def test_render_watchdog_shows_only_watchdog_specific_content(self):
        """Watchdog render should show only watchdog-specific context."""
        rendered = render_workspace("oe-watchdog")

        # Should contain watchdog-specific content
        assert "Watchdog" in rendered or "watchdog" in rendered.lower()
        assert "monitoring" in rendered.lower() or "timeout" in rendered.lower()

        # Should contain its skills
        assert "oe-timeout-alarm" in rendered
        assert "oe-session-status" in rendered

        # Header should be present
        assert "# Workspace: oe-watchdog" in rendered

    def test_render_tool_recovery_includes_recovery_skill(self):
        """Rendered tool recovery should include recovery skill."""
        rendered = render_workspace("oe-tool-recovery")
        assert "oe-tool-recovery" in rendered
        assert "Recovery" in rendered or "recovery" in rendered.lower()

    def test_render_tool_recovery_shows_only_recovery_specific_content(self):
        """Tool recovery render should show only recovery-specific context."""
        rendered = render_workspace("oe-tool-recovery")

        # Should contain recovery-specific content
        assert "Tool Recovery" in rendered or "tool-recovery" in rendered.lower()
        assert "recovered_method" in rendered or "failure" in rendered.lower()

        # Should contain its skill
        assert "oe-tool-recovery" in rendered

        # Header should be present
        assert "# Workspace: oe-tool-recovery" in rendered


class TestWorkspacePathResolution:
    """Test workspace path resolution."""

    def test_worker_workspace_paths_are_directories(self):
        """Worker workspace paths should be directories."""
        for workspace in TestWorkerWorkspaceStructure.WORKER_WORKSPACES:
            metadata = get_workspace_metadata(workspace)
            path = Path(metadata["path"])
            assert path.exists()
            assert path.is_dir()

    def test_worker_workspace_paths_contain_agents_md(self):
        """Worker workspace paths should contain AGENTS.md."""
        for workspace in TestWorkerWorkspaceStructure.WORKER_WORKSPACES:
            metadata = get_workspace_metadata(workspace)
            path = Path(metadata["path"])
            assert (path / "AGENTS.md").exists()

    def test_worker_workspace_paths_contain_tools_md(self):
        """Worker workspace paths should contain TOOLS.md."""
        for workspace in TestWorkerWorkspaceStructure.WORKER_WORKSPACES:
            metadata = get_workspace_metadata(workspace)
            path = Path(metadata["path"])
            assert (path / "TOOLS.md").exists()


class TestWorkspaceMetadataWithFrontmatter:
    """Test workspace metadata includes parsed frontmatter."""

    def test_metadata_includes_manifest_key(self):
        """Metadata should include manifest key for workspaces with frontmatter."""
        metadata = get_workspace_metadata("oe-searcher")
        assert "manifest" in metadata

    def test_manifest_has_required_fields(self):
        """Manifest should have agent_id, workspace, routing, is_valid, errors."""
        metadata = get_workspace_metadata("oe-searcher")
        manifest = metadata["manifest"]
        assert "agent_id" in manifest
        assert "workspace" in manifest
        assert "routing" in manifest
        assert "is_valid" in manifest
        assert "errors" in manifest

    def test_metadata_preserves_existing_keys(self):
        """Metadata should preserve existing keys like name, path, skills."""
        metadata = get_workspace_metadata("oe-searcher")
        assert metadata["name"] == "oe-searcher"
        assert "path" in metadata
        assert "skills" in metadata
        assert metadata["has_agents"] is True
        assert metadata["has_tools"] is True
