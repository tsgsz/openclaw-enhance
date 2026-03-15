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
        tools = self._read_file("oe-searcher", "TOOLS.md")

        # Should mention sandbox for temp files
        assert "sandbox" in agents.lower() or "Read" in tools

        # Should NOT have write/edit capabilities for project files
        assert "Cannot Write" in agents or "Cannot modify" in agents
        # Sandbox has read/write to temp files only, but no bash for project
        assert "Sandbox" in agents or "temporary" in agents.lower()

    def test_searcher_has_web_search_tools(self):
        """Searcher should have web search tools."""
        tools = self._read_file("oe-searcher", "TOOLS.md")

        assert "websearch_web_search_exa" in tools
        assert "webfetch" in tools
        assert "grep_app_searchGitHub" in tools

    def test_searcher_cannot_spawn_agents(self):
        """Searcher should not spawn subagents."""
        agents = self._read_file("oe-searcher", "AGENTS.md")

        assert "Cannot spawn subagents" in agents or "call_omo_agent" not in agents

    def test_searcher_uses_cheap_model(self):
        """Searcher should use cheap/fast model."""
        agents = self._read_file("oe-searcher", "AGENTS.md")

        assert "cheap" in agents.lower() or "fast" in agents.lower()

    def test_searcher_has_sandbox_access(self):
        """Searcher should have sandbox read/write for research."""
        agents = self._read_file("oe-searcher", "AGENTS.md")

        # Sandbox allows temp writes for research
        assert "sandbox" in agents.lower()


class TestSyshelperBoundaries(TestWorkerRoleBoundaries):
    """Test oe-syshelper role boundaries."""

    def test_syshelper_is_strictly_readonly(self):
        """Syshelper should be strictly read-only."""
        agents = self._read_file("oe-syshelper", "AGENTS.md")
        tools = self._read_file("oe-syshelper", "TOOLS.md")

        # Should emphasize read-only
        assert "Read-Only Guarantee" in agents or "strictly read-only" in agents.lower()

        # Should not have write/edit
        assert "Cannot Write" in agents or "No file modifications" in tools
        assert "Cannot Edit" in agents or "No file modifications" in tools

    def test_syshelper_has_session_tools(self):
        """Syshelper should have session inspection tools."""
        tools = self._read_file("oe-syshelper", "TOOLS.md")

        assert "session_list" in tools
        assert "session_read" in tools
        assert "session_info" in tools

    def test_syshelper_has_lsp_tools(self):
        """Syshelper should have LSP code navigation tools."""
        tools = self._read_file("oe-syshelper", "TOOLS.md")

        assert "lsp_goto_definition" in tools
        assert "lsp_find_references" in tools
        assert "lsp_symbols" in tools

    def test_syshelper_cannot_spawn_agents(self):
        """Syshelper should not spawn subagents."""
        agents = self._read_file("oe-syshelper", "AGENTS.md")

        assert "Cannot spawn subagents" in agents or "call_omo_agent" not in agents

    def test_syshelper_bash_limited_to_readonly(self):
        """Syshelper bash should be limited to read-only commands."""
        tools = self._read_file("oe-syshelper", "TOOLS.md")

        assert "Read-only commands only" in tools
        assert "Prohibited Commands" in tools or "rm" in tools or "git checkout" in tools


class TestScriptCoderBoundaries(TestWorkerRoleBoundaries):
    """Test oe-script_coder role boundaries."""

    def test_script_coder_has_full_file_access(self):
        """Script coder should have full file access (read/write/edit)."""
        tools = self._read_file("oe-script_coder", "TOOLS.md")

        assert "Read" in tools
        assert "Write" in tools
        assert "Edit" in tools

    def test_script_coder_has_code_intelligence_tools(self):
        """Script coder should have LSP tools."""
        tools = self._read_file("oe-script_coder", "TOOLS.md")

        assert "lsp_goto_definition" in tools
        assert "lsp_diagnostics" in tools

    def test_script_coder_can_run_tests(self):
        """Script coder should be able to execute tests."""
        agents = self._read_file("oe-script_coder", "AGENTS.md")
        tools = self._read_file("oe-script_coder", "TOOLS.md")

        assert "Bash" in tools
        assert "pytest" in tools or "test" in agents.lower()

    def test_script_coder_can_spawn_searcher_only(self):
        """Script coder can spawn searcher for research only."""
        agents = self._read_file("oe-script_coder", "AGENTS.md")

        # Should mention limited agent spawning
        assert "searcher" in agents.lower()
        assert "limited" in agents.lower() or "emergency" in agents.lower()

    def test_script_coder_uses_codex_model(self):
        """Script coder should use code-capable model."""
        agents = self._read_file("oe-script_coder", "AGENTS.md")

        assert "Codex" in agents or "code-capable" in agents.lower()

    def test_script_coder_requires_tests(self):
        """Script coder should require tests for all code."""
        agents = self._read_file("oe-script_coder", "AGENTS.md")

        assert "test" in agents.lower()
        assert "All new code must have tests" in agents or "mandatory" in agents.lower()


class TestWatchdogBoundaries(TestWorkerRoleBoundaries):
    """Test oe-watchdog narrow authority boundaries."""

    def test_watchdog_has_narrow_authority_documented(self):
        """Watchdog should document narrow authority explicitly."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")

        assert "Narrow Authority" in agents or "narrow authority" in agents.lower()
        assert "Authority Boundaries" in agents

    def test_watchdog_cannot_modify_project_files(self):
        """Watchdog cannot modify project files."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")
        tools = self._read_file("oe-watchdog", "TOOLS.md")

        assert "❌ File Modifications" in agents or "Cannot modify" in agents
        assert "Cannot write to project" in tools.lower() or "runtime state only" in tools.lower()

    def test_watchdog_cannot_write_project_files(self):
        """Watchdog write access is limited to runtime state only."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")
        tools = self._read_file("oe-watchdog", "TOOLS.md")

        assert "Runtime State Access Only" in agents or "runtime state only" in tools.lower()
        assert "❌ Write" in tools or "runtime state" in tools.lower()

    def test_watchdog_cannot_execute_tests(self):
        """Watchdog cannot execute tests or scripts."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")

        assert "❌ Test Execution" in agents or "Cannot run tests" in agents

    def test_watchdog_cannot_run_git_commands(self):
        """Watchdog cannot run git commands."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")

        assert "❌ Git Operations" in agents or "No git commands" in agents

    def test_watchdog_cannot_spawn_agents(self):
        """Watchdog cannot spawn agents."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")
        tools = self._read_file("oe-watchdog", "TOOLS.md")

        assert "❌ Agent Spawning" in agents or "Cannot spawn" in agents
        assert "call_omo_agent" not in tools or "Not available" in tools

    def test_watchdog_can_monitor_sessions(self):
        """Watchdog can monitor sessions."""
        tools = self._read_file("oe-watchdog", "TOOLS.md")

        assert "session_list" in tools
        assert "session_info" in tools

    def test_watchdog_can_write_runtime_state(self):
        """Watchdog can write to runtime state."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")
        tools = self._read_file("oe-watchdog", "TOOLS.md")

        assert "Runtime State Writes" in agents or "runtime state" in agents.lower()
        assert ".runtime/" in tools or "runtime state" in tools.lower()

    def test_watchdog_reports_to_orchestrator(self):
        """Watchdog reports to orchestrator without making decisions."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")

        assert "orchestrator" in agents.lower()
        assert "Does NOT make decisions" in agents or "reports" in agents.lower()

    def test_watchdog_has_allowed_operations_section(self):
        """Watchdog should have explicit allowed operations section."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")

        assert "✅ ALLOWED" in agents
        assert "Timeout Confirmation" in agents or "timeout" in agents.lower()
        assert "Reminder Delivery" in agents or "reminder" in agents.lower()

    def test_watchdog_has_prohibited_operations_section(self):
        """Watchdog should have explicit prohibited operations section."""
        agents = self._read_file("oe-watchdog", "AGENTS.md")

        assert "❌ PROHIBITED" in agents
        assert "File Modifications" in agents
        assert "Code Changes" in agents


class TestToolRecoveryBoundaries(TestWorkerRoleBoundaries):
    """Test oe-tool-recovery narrow authority boundaries."""

    def test_tool_recovery_has_narrow_authority_documented(self):
        """Tool recovery should document narrow authority explicitly."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")

        assert "Narrow Scope" in agents or "narrow authority" in agents.lower()
        assert "Authority Boundaries" in agents

    def test_tool_recovery_has_allowed_operations_section(self):
        """Tool recovery should have explicit allowed operations section."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")

        assert "✅ ALLOWED" in agents
        assert "Contract Reading" in agents or "Documentation Lookup" in agents

    def test_tool_recovery_has_prohibited_operations_section(self):
        """Tool recovery should have explicit prohibited operations section."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")

        assert "❌ PROHIBITED" in agents
        assert "File Modifications" in agents
        assert "Agent Spawning" in agents

    def test_tool_recovery_cannot_modify_files(self):
        """Tool recovery cannot modify project files."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")
        tools = self._read_file("oe-tool-recovery", "TOOLS.md")

        assert "❌ File Modifications" in agents or "Cannot write or edit" in agents
        assert "Read-Only Guarantee" in agents or "read-only" in agents.lower()
        assert "Prohibited Tools" in tools
        assert "Write/Edit" in tools or "Cannot modify" in tools

    def test_tool_recovery_cannot_spawn_subagents(self):
        """Tool recovery cannot spawn subagents."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")
        tools = self._read_file("oe-tool-recovery", "TOOLS.md")

        assert "❌ Agent Spawning" in agents or "Cannot spawn subagents" in agents
        assert "call_omo_agent" not in tools or "Prohibited" in tools
        assert "sessions_spawn" not in agents or "Cannot" in agents

    def test_tool_recovery_recommends_only(self):
        """Tool recovery returns recommendations, does not execute."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")

        # Should emphasize recommendation-only role
        assert "Advisory Role" in agents or "recommendation" in agents.lower()
        assert "Autonomous Retry" in agents or "Cannot execute" in agents
        assert "recovered_method" in agents

    def test_tool_recovery_is_leaf_node(self):
        """Tool recovery is a leaf node - cannot dispatch to other workers."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")

        assert "leaf-node" in agents.lower() or "leaf node" in agents.lower()
        assert "Worker Communication" in agents or "Cannot communicate" in agents
        assert "No Direct Contact" in agents or "does not interact" in agents.lower()

    def test_tool_recovery_has_read_only_tools(self):
        """Tool recovery has only read-only tools."""
        tools = self._read_file("oe-tool-recovery", "TOOLS.md")

        # Should have read tools
        assert "Read" in tools
        assert "Glob" in tools
        assert "Grep" in tools

        # Should not have write/edit
        assert "Prohibited Tools" in tools
        assert "Write/Edit" in tools or "Cannot modify" in tools

    def test_tool_recovery_has_recovery_output_schema(self):
        """Tool recovery documents recovery output schema."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")

        assert "Recovery Output Schema" in agents or "recovered_method" in agents
        assert "exact_invocation" in agents
        assert "confidence" in agents.lower()

    def test_tool_recovery_failure_escalates_to_orchestrator(self):
        """Tool recovery failure escalates to orchestrator."""
        agents = self._read_file("oe-tool-recovery", "AGENTS.md")

        assert "orchestrator" in agents.lower()
        assert "Advisory Role" in agents or "Passive Specialist" in agents


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
        """Orchestrator AGENTS.md should reference worker discovery mechanism."""
        agents = self._read_file("oe-orchestrator", "AGENTS.md")

        # Should reference discovery mechanism
        assert "discover" in agents.lower() or "frontmatter" in agents.lower()
        assert "AGENTS.md" in agents
