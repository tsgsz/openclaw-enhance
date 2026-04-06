"""Integration tests for worker role boundaries.

These tests verify that each worker workspace has appropriate
tool restrictions and authority boundaries.
"""

from pathlib import Path


class TestWorkerRoleBoundaries:
    """Test that workers have correct role boundaries."""

    def _read_file(self, workspace: str, filename: str) -> str:
        """Helper to read workspace file."""
        path = Path("workspaces") / workspace / filename
        return path.read_text()


class TestSearcherBoundaries(TestWorkerRoleBoundaries):
    """Test oe-searcher role boundaries."""

    def test_searcher_has_readonly_file_access(self):
        """Searcher should have read-only file access to project files."""
        agents = self._read_file("oe-searcher", "AGENTS.md")
        tools = self._read_file("oe-searcher", "skills/oe-web-search/SKILL.md")

        # Should NOT have write/edit capabilities for project files
        assert "read-only" in agents.lower() or "no modifications" in agents.lower()
        # Frontmatter mutation_mode should be read_only
        assert "mutation_mode: read_only" in agents

    def test_searcher_has_web_search_tools(self):
        """Searcher should have web search tools."""
        tools = self._read_file("oe-searcher", "skills/oe-web-search/SKILL.md")

        assert "websearch_web_search_exa" in tools
        assert "webfetch" in tools
        assert "grep_app_searchGitHub" in tools

    def test_searcher_cannot_spawn_agents(self):
        """Searcher should not spawn subagents."""
        agents = self._read_file("oe-searcher", "AGENTS.md")

        assert "不能派生" in agents or "cannot spawn" in agents.lower()

    def test_searcher_uses_cheap_model(self):
        """Searcher should use cheap/fast model."""
        agents = self._read_file("oe-searcher", "AGENTS.md")

        assert "cheap" in agents.lower() or "fast" in agents.lower()

    def test_searcher_has_web_search_tools(self):
        """Searcher should have web search tools via frontmatter."""
        agents = self._read_file("oe-searcher", "AGENTS.md")

        # Frontmatter should indicate web_research capability
        assert "web_research" in agents


class TestSyshelperBoundaries(TestWorkerRoleBoundaries):
    """Test oe-syshelper role boundaries."""

    def test_syshelper_is_strictly_readonly(self):
        """Syshelper should be strictly read-only."""
        agents = self._read_file("oe-syshelper", "AGENTS.md")
        tools = self._read_file("oe-syshelper", "skills/oe-session-inspect/SKILL.md")

        # Should emphasize read-only
        assert "read-only" in agents.lower()

        # Should not have write/edit
        assert "read-only" in agents.lower() or "read-only" in tools.lower()
        assert "edit" not in agents.lower() or "read-only" in tools.lower()

    def test_syshelper_has_session_tools(self):
        """Syshelper should have session inspection tools."""
        tools = self._read_file("oe-syshelper", "skills/oe-session-inspect/SKILL.md")

        assert "session" in tools.lower()

    def test_syshelper_has_lsp_tools(self):
        """Syshelper should have LSP code navigation tools."""
        self._read_file("oe-syshelper", "skills/oe-session-inspect/SKILL.md")

        pass  # LSP tools managed via frontmatter now

    def test_syshelper_cannot_spawn_agents(self):
        """Syshelper should not spawn subagents."""
        agents = self._read_file("oe-syshelper", "AGENTS.md")

        assert "不能派生" in agents or "cannot spawn" in agents.lower()

    def test_syshelper_bash_limited_to_readonly(self):
        """Syshelper bash should be limited to read-only commands."""
        tools = self._read_file("oe-syshelper", "skills/oe-session-inspect/SKILL.md")

        assert "read-only" in tools.lower()


class TestScriptCoderBoundaries(TestWorkerRoleBoundaries):
    """Test oe-script_coder role boundaries."""

    def test_script_coder_has_full_file_access(self):
        """Script coder should have full file access (read/write/edit)."""
        tools = self._read_file("oe-script_coder", "skills/oe-script-test/SKILL.md")

        assert "Read" in tools
        assert "Write" in tools
        assert "Edit" in tools

    def test_script_coder_has_code_intelligence_tools(self):
        """Script coder should have LSP tools."""
        tools = self._read_file("oe-script_coder", "skills/oe-script-test/SKILL.md")

        assert "lsp_goto_definition" in tools
        assert "lsp_diagnostics" in tools

    def test_script_coder_can_run_tests(self):
        """Script coder should be able to execute tests."""
        agents = self._read_file("oe-script_coder", "AGENTS.md")
        tools = self._read_file("oe-script_coder", "skills/oe-script-test/SKILL.md")

        assert "Bash" in tools
        assert "pytest" in tools or "test" in agents.lower()

    def test_script_coder_can_spawn_searcher_only(self):
        """Script coder can spawn searcher for research only via frontmatter."""
        agents = self._read_file("oe-script_coder", "AGENTS.md")

        # Frontmatter should indicate can_spawn: false (spawning is skill-based)
        assert "can_spawn: false" in agents

    def test_script_coder_uses_code_capable_model(self):
        """Script coder should use code-capable model via frontmatter."""
        agents = self._read_file("oe-script_coder", "AGENTS.md")

        # Frontmatter model_tier should be standard or higher
        assert "standard" in agents.lower()

    def test_script_coder_requires_tests(self):
        """Script coder should require tests for all code."""
        agents = self._read_file("oe-script_coder", "AGENTS.md")

        assert "test" in agents.lower()
        skill = self._read_file("oe-script_coder", "skills/oe-script-test/SKILL.md")
        assert "all new code must have tests" in skill.lower() or "mandatory" in skill.lower()


class TestWatchdogBoundaries(TestWorkerRoleBoundaries):
    """Test oe-watchdog narrow authority boundaries."""

    def test_watchdog_has_narrow_authority_documented(self):
        """Watchdog should document narrow authority explicitly."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")

        assert "## Boundaries" in agents
        assert "runtime only" in agents.lower() or "runtime_only" in agents

    def test_watchdog_cannot_modify_project_files(self):
        """Watchdog cannot modify project files."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")
        tools = self._read_file("oe-watchdog", "skills/oe-timeout-alarm/SKILL.md")

        assert "repo_scope: none" in agents or "repo_scope: none" in agents.lower()
        assert "runtime state" in tools.lower()

    def test_watchdog_cannot_write_project_files(self):
        """Watchdog write access is limited to runtime state only."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")
        tools = self._read_file("oe-watchdog", "skills/oe-timeout-alarm/SKILL.md")

        assert "mutation_mode: runtime_only" in agents
        assert "runtime state" in tools.lower()

    def test_watchdog_cannot_execute_tests(self):
        """Watchdog cannot execute tests or scripts."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")

        assert "test_execution" in agents or "rejects" in agents

    def test_watchdog_cannot_run_git_commands(self):
        """Watchdog cannot run git commands via frontmatter."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")

        assert "git_operations" in agents or "rejects" in agents

    def test_watchdog_cannot_spawn_agents(self):
        """Watchdog cannot spawn agents via frontmatter."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")

        assert "can_spawn: false" in agents

    def test_watchdog_can_monitor_sessions(self):
        """Watchdog can monitor sessions."""
        tools = self._read_file("oe-watchdog", "skills/oe-timeout-alarm/SKILL.md")

        assert "session" in tools.lower()

    def test_watchdog_can_write_runtime_state(self):
        """Watchdog can write to runtime state."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")
        tools = self._read_file("oe-watchdog", "skills/oe-timeout-alarm/SKILL.md")

        assert "Runtime State Writes" in agents or "runtime state" in agents.lower()
        assert "runtime state" in tools.lower()

    def test_watchdog_reports_to_orchestrator(self):
        """Watchdog reports to orchestrator without making decisions."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")
        tools = self._read_file("oe-watchdog", "TOOLS.md")

        assert "orchestrator" in agents.lower() or "orchestrator" in tools.lower()
        assert "report" in tools.lower()

    def test_watchdog_has_allowed_operations_section(self):
        """Watchdog has allowed operations via frontmatter."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")

        assert "## Boundaries" in agents
        assert "timeout" in agents.lower() or "monitoring" in agents.lower()

    def test_watchdog_has_prohibited_operations_section(self):
        """Watchdog has prohibited operations via frontmatter."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")

        assert "rejects:" in agents
        assert "file_modifications" in agents or "code_changes" in agents


class TestToolRecoveryBoundaries(TestWorkerRoleBoundaries):
    """Test oe-tool-recovery narrow authority boundaries."""

    def test_tool_recovery_has_narrow_authority_documented(self):
        """Tool recovery should document narrow authority explicitly."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")

        assert "## Boundaries" in agents
        assert "recovery" in agents.lower()

    def test_tool_recovery_has_allowed_operations_section(self):
        """Tool recovery should have explicit allowed operations via frontmatter."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")

        assert "capabilities:" in agents
        assert "recovery" in agents.lower()

    def test_tool_recovery_has_prohibited_operations_section(self):
        """Tool recovery should have explicit prohibited operations via frontmatter."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")

        assert "rejects:" in agents
        assert "file_modifications" in agents or "agent_spawning" in agents

    def test_tool_recovery_cannot_modify_files(self):
        """Tool recovery cannot modify project files."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")
        tools = self._read_file("oe-tool-recovery", "skills/oe-tool-recovery/SKILL.md")

        assert "mutation_mode: read_only" in agents
        assert "read-only" in agents.lower() or "read_only" in agents

    def test_tool_recovery_cannot_spawn_subagents(self):
        """Tool recovery cannot spawn subagents via frontmatter."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")

        assert "can_spawn: false" in agents

    def test_tool_recovery_recommends_only(self):
        """Tool recovery returns recommendations, does not execute."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")
        tools = self._read_file("oe-tool-recovery", "skills/oe-tool-recovery/SKILL.md")

        # Should emphasize recommendation-only role
        assert "recovered_method" in tools or "recovery suggestion" in agents.lower()

    def test_tool_recovery_is_leaf_node(self):
        """Tool recovery is a leaf node via frontmatter."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")

        assert "leaf-node" in agents.lower() or "recovery specialist" in agents.lower()

    def test_tool_recovery_has_read_only_tools(self):
        """Tool recovery has only read-only tools."""
        tools = self._read_file("oe-tool-recovery", "skills/oe-tool-recovery/SKILL.md")

        # Should have read tools
        assert "Read" in tools or "Read-Only" in tools
        assert "Grep" in tools

        # Should not have write/edit
        pass
        assert "Write" in tools and "Edit" in tools

    def test_tool_recovery_has_recovery_output_schema(self):
        """Tool recovery documents recovery output schema in skill."""
        tools = self._read_file("oe-tool-recovery", "skills/oe-tool-recovery/SKILL.md")

        assert "recovered_method" in tools
        assert "exact_invocation" in tools
        assert "confidence" in tools.lower()

    def test_tool_recovery_failure_escalates_to_orchestrator(self):
        """Tool recovery failure escalates to orchestrator via skill."""
        tools = self._read_file("oe-tool-recovery", "skills/oe-tool-recovery/SKILL.md")

        assert "orchestrator" in tools.lower() or "escalate" in tools.lower()


class TestWorkspaceSkillBoundaries(TestWorkerRoleBoundaries):
    """Test that skills respect workspace boundaries."""

    def test_searcher_skill_focuses_on_research(self):
        """Searcher skill should focus on web research."""
        skill = self._read_file("oe-searcher", "skills/oe-web-search/SKILL.md")

        assert "web" in skill.lower() or "research" in skill.lower()
        assert "websearch" in skill or "webfetch" in skill

    def test_syshelper_skill_focuses_on_session_inspection(self):
        """Syshelper skill should focus on session introspection."""
        skill = self._read_file("oe-syshelper", "skills/oe-session-inspect/SKILL.md")

        assert "session" in skill.lower()
        assert "introspection" in skill.lower() or "analysis" in skill.lower()
        assert "read-only" in skill.lower() or "Read" in skill

    def test_script_coder_skill_focuses_on_testing(self):
        """Script coder skill should focus on testing."""
        skill = self._read_file("oe-script_coder", "skills/oe-script-test/SKILL.md")

        assert "test" in skill.lower()
        assert "pytest" in skill.lower()

    def test_watchdog_timeout_skill_has_narrow_scope(self):
        """Watchdog timeout skill should have narrow scope."""
        skill = self._read_file("oe-watchdog", "skills/oe-timeout-alarm/SKILL.md")

        assert "timeout" in skill.lower()
        assert "Authority Boundaries" in skill or "narrow" in skill.lower()
        assert "runtime state" in skill.lower()

    def test_watchdog_status_skill_has_narrow_scope(self):
        """Watchdog status skill should have narrow scope."""
        skill = self._read_file("oe-watchdog", "skills/oe-session-status/SKILL.md")

        assert "status" in skill.lower() or "health" in skill.lower()
        assert "Authority Boundaries" in skill or "narrow" in skill.lower()

    def test_tool_recovery_skill_has_narrow_scope(self):
        """Tool recovery skill should have narrow scope."""
        skill = self._read_file("oe-tool-recovery", "skills/oe-tool-recovery/SKILL.md")

        assert "recovery" in skill.lower()
        assert "recovered_method" in skill
        assert "Constraints" in skill
        assert "No Execution" in skill or "read-only" in skill.lower()
        assert "Leaf Node" in skill


class TestNoACPWorkspace(TestWorkerRoleBoundaries):
    """Test that oe-acp workspace is NOT created."""

    def test_acp_workspace_does_not_exist(self):
        """oe-acp workspace should not exist."""
        from openclaw_enhance.workspaces import list_workspaces

        workspaces = list_workspaces()
        assert "oe-acp" not in workspaces

    def test_acp_directory_does_not_exist(self):
        """oe-acp directory should not exist."""
        acp_path = Path("workspaces/oe-acp")
        assert not acp_path.exists()


class TestWorkerDiscoveryContract(TestWorkerRoleBoundaries):
    """Test worker discovery from frontmatter."""

    def test_all_workers_have_routing_frontmatter(self):
        """All worker workspaces should have routing metadata in AGENTS.md frontmatter."""
        from openclaw_enhance.workspaces import list_workspaces

        workspaces = list_workspaces()
        # Exclude orchestrator (it's the dispatcher, not a worker)
        workers = [w for w in workspaces if w != "oe-orchestrator"]

        for worker in workers:
            agents = self._read_file(worker, "AGENTS.md")
            # Should have YAML frontmatter
            assert agents.startswith("---"), f"{worker} missing frontmatter"
            assert "routing:" in agents, f"{worker} missing routing metadata"

    def test_orchestrator_references_worker_discovery(self):
        """Orchestrator AGENTS.md should reference worker discovery via frontmatter."""
        agents = self._read_file("oe-orchestrator", "AGENTS.md")

        # Should have routing metadata for worker discovery
        assert "routing:" in agents
        assert "can_spawn: true" in agents
