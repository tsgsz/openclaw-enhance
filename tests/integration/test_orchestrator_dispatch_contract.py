"""Integration tests for orchestrator dispatch contract and subagent workflows."""

import subprocess
import sys
from pathlib import Path

import pytest


class TestDispatchContractEndToEnd:
    """End-to-end tests for dispatch contract."""

    def test_render_workspace_cli_success(self):
        """CLI should successfully render oe-orchestrator workspace."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "oe-orchestrator"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert result.stdout, "Output should not be empty"

    def test_render_workspace_includes_all_components(self):
        """Rendered workspace should include all components."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "oe-orchestrator"],
            capture_output=True,
            text=True,
        )
        output = result.stdout

        # Should include AGENTS section
        assert "Orchestrator" in output or "AGENTS" in output

        # Should include TOOLS section
        assert "Tools" in output or "TOOLS" in output

        # Should include all skills
        assert "oe-project-registry" in output
        assert "oe-worker-dispatch" in output
        assert "oe-agentos-practice" in output
        assert "oe-git-context" in output

    def test_render_workspace_invalid_name_fails(self):
        """Rendering invalid workspace should fail."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "invalid-workspace"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "Should fail for invalid workspace"
        assert "not found" in result.stderr.lower() or "unknown" in result.stderr.lower()


class TestSkillContractIntegration:
    """Integration tests for skill contract rendering."""

    def test_all_workspace_skills_have_valid_files(self):
        """All workspace skills should have valid SKILL.md files."""
        from openclaw_enhance.workspaces import get_workspace_skills

        skills = get_workspace_skills("oe-orchestrator")

        for skill_name in skills:
            skill_path = Path(f"workspaces/oe-orchestrator/skills/{skill_name}/SKILL.md")
            assert skill_path.exists(), f"Skill file for {skill_name} not found"

            content = skill_path.read_text()
            assert skill_name in content

    def test_skill_contracts_have_valid_frontmatter(self):
        """All skill contracts should have valid YAML frontmatter."""
        from openclaw_enhance.workspaces import get_workspace_skills

        skills = get_workspace_skills("oe-orchestrator")

        for skill_name in skills:
            skill_path = Path(f"workspaces/oe-orchestrator/skills/{skill_name}/SKILL.md")
            contract = skill_path.read_text()

            # Check frontmatter
            assert contract.startswith("---"), f"{skill_name} missing frontmatter"
            assert "name:" in contract, f"{skill_name} missing name"
            assert "version:" in contract, f"{skill_name} missing version"
            assert "description:" in contract, f"{skill_name} missing description"


class TestWorkspaceDiscoveryIntegration:
    """Integration tests for workspace discovery."""

    def test_workspace_directory_structure_complete(self):
        """Workspace directory should have complete structure."""
        workspace_path = Path("workspaces/oe-orchestrator")

        assert (workspace_path / "AGENTS.md").exists()
        assert (workspace_path / "TOOLS.md").exists()
        assert (workspace_path / "skills").exists()

        # Check skills directory structure
        skills_dir = workspace_path / "skills"
        expected_skills = [
            "oe-project-registry",
            "oe-worker-dispatch",
            "oe-agentos-practice",
            "oe-git-context",
        ]

        for skill in expected_skills:
            skill_dir = skills_dir / skill
            assert skill_dir.exists(), f"Skill directory {skill} missing"
            assert (skill_dir / "SKILL.md").exists(), f"SKILL.md for {skill} missing"

    def test_agents_md_references_all_skills(self):
        """AGENTS.md should reference all available skills."""
        agents_content = Path("workspaces/oe-orchestrator/AGENTS.md").read_text()

        skills = [
            "oe-project-registry",
            "oe-worker-dispatch",
            "oe-agentos-practice",
            "oe-git-context",
        ]

        for skill in skills:
            assert skill in agents_content, f"AGENTS.md should reference {skill}"

    def test_tools_md_covers_agent_management(self):
        """TOOLS.md should cover agent management tools."""
        tools_content = Path("workspaces/oe-orchestrator/TOOLS.md").read_text()

        # Should mention call_omo_agent
        assert "call_omo_agent" in tools_content

        # Should mention background tasks
        assert "background" in tools_content.lower()


class TestDispatchWorkflowIntegration:
    """Integration tests for dispatch workflows."""

    def test_worker_dispatch_skill_defines_agents(self):
        """Worker dispatch skill should define agent types."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md")
        content = skill_path.read_text()

        # Should define agent types
        assert "searcher" in content
        assert "syshelper" in content
        assert "script_coder" in content
        assert "watchdog" in content

    def test_worker_dispatch_skill_defines_patterns(self):
        """Worker dispatch skill should define dispatch patterns."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md")
        content = skill_path.read_text()

        # Should define patterns
        assert "Sequential" in content or "sequential" in content
        assert "Parallel" in content or "parallel" in content
        assert "synthesize" in content.lower()

    def test_project_registry_skill_defines_project_types(self):
        """Project registry skill should define project types."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-project-registry/SKILL.md")
        content = skill_path.read_text()

        # Should mention common project indicators
        assert "pyproject.toml" in content or "python" in content.lower()
        assert "package.json" in content or "nodejs" in content.lower()

    def test_agentos_practice_skill_defines_patterns(self):
        """AgentOS practice skill should define coding patterns."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-agentos-practice/SKILL.md")
        content = skill_path.read_text()

        # Should define patterns
        assert "Skill-Based Development" in content or "skill" in content.lower()
        assert "File-Based Planning" in content or "planning" in content.lower()

    def test_git_context_skill_defines_readonly_operations(self):
        """Git context skill should only define read-only operations."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-git-context/SKILL.md")
        content = skill_path.read_text()

        # Should mention safety/read-only
        assert "read-only" in content.lower() or "safety" in content.lower()

        # Should mention common git commands for context
        assert "git log" in content or "history" in content.lower()


class TestSubagentContractIntegration:
    """Integration tests for subagent contracts."""

    def test_searcher_agent_defined(self):
        """Searcher agent should be defined in worker dispatch."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md")
        content = skill_path.read_text()

        # Find searcher section
        assert "searcher" in content
        # Should mention cheap model
        assert "cheap" in content.lower() or "research" in content.lower()

    def test_syshelper_agent_defined(self):
        """Syshelper agent should be defined in worker dispatch."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md")
        content = skill_path.read_text()

        assert "syshelper" in content
        assert "system" in content.lower() or "grep" in content.lower()

    def test_script_coder_agent_defined(self):
        """Script coder agent should be defined in worker dispatch."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md")
        content = skill_path.read_text()

        assert "script_coder" in content
        assert "codex" in content.lower() or "code" in content.lower()

    def test_watchdog_agent_defined(self):
        """Watchdog agent should be defined in worker dispatch."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md")
        content = skill_path.read_text()

        assert "watchdog" in content
        assert "monitor" in content.lower() or "timeout" in content.lower()


class TestResultSynthesisIntegration:
    """Integration tests for result synthesis workflows."""

    def test_worker_dispatch_defines_synthesis(self):
        """Worker dispatch should define result synthesis."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md")
        content = skill_path.read_text()

        # Should have synthesis section
        assert "Synthesis" in content or "synthesize" in content.lower()

        # Should mention strategies
        assert "strategy" in content.lower() or "concatenation" in content.lower()

    def test_synthesis_template_defined(self):
        """Synthesis template should be defined."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md")
        content = skill_path.read_text()

        # Should have template/example
        assert "Summary" in content or "Results" in content or "Artifacts" in content


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    def test_worker_dispatch_defines_error_handling(self):
        """Worker dispatch should define error handling."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md")
        content = skill_path.read_text()

        assert "Error Handling" in content or "error" in content.lower()

    def test_worker_dispatch_defines_recovery_strategies(self):
        """Worker dispatch should define recovery strategies."""
        skill_path = Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md")
        content = skill_path.read_text()

        assert "Recovery" in content or "retry" in content.lower() or "fallback" in content.lower()


class TestOrchestratorEndToEndWorkflow:
    """End-to-end tests simulating orchestrator workflows."""

    def test_complete_render_pipeline(self):
        """Complete pipeline from CLI to rendered output."""
        # Step 1: Verify workspace exists
        assert Path("workspaces/oe-orchestrator").exists()

        # Step 2: Render via CLI
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "oe-orchestrator"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Step 3: Verify output contains all sections
        output = result.stdout
        assert "Orchestrator" in output
        assert "Tools" in output or "TOOLS" in output
        assert "Skills" in output or "oe-project-registry" in output

    def test_workspace_components_integrated(self):
        """All workspace components should be integrated."""
        # AGENTS should reference skills
        agents = Path("workspaces/oe-orchestrator/AGENTS.md").read_text()
        assert "oe-project-registry" in agents

        # TOOLS should reference agents
        tools = Path("workspaces/oe-orchestrator/TOOLS.md").read_text()
        assert "call_omo_agent" in tools

        # Skills should reference each other where appropriate
        dispatch = Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md").read_text()
        assert "searcher" in dispatch


class TestCliIntegration:
    """Integration tests for CLI commands."""

    def test_cli_help_includes_render_workspace(self):
        """CLI help should mention render-workspace command."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "render-workspace" in result.stdout

    def test_render_workspace_help_shows_workspace_argument(self):
        """render-workspace help should show workspace argument."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Should mention workspace name or similar
        assert "WORKSPACE" in result.stdout or "workspace" in result.stdout.lower()
