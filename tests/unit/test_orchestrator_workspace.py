"""Unit tests for orchestrator workspace configuration and rendering."""

import subprocess
import sys
from pathlib import Path

import pytest


class TestOrchestratorWorkspaceStructure:
    """Tests for workspace directory structure."""

    def test_agents_md_exists(self):
        """AGENTS.md should exist in oe-orchestrator workspace."""
        agents_path = Path("workspaces/oe-orchestrator/AGENTS.md")
        assert agents_path.exists(), "AGENTS.md not found"
        assert agents_path.is_file(), "AGENTS.md is not a file"

    def test_tools_md_exists(self):
        """TOOLS.md should exist in oe-orchestrator workspace."""
        tools_path = Path("workspaces/oe-orchestrator/TOOLS.md")
        assert tools_path.exists(), "TOOLS.md not found"
        assert tools_path.is_file(), "TOOLS.md is not a file"

    def test_skills_directory_exists(self):
        """Skills directory should exist with all required skills."""
        skills_dir = Path("workspaces/oe-orchestrator/skills")
        assert skills_dir.exists(), "Skills directory not found"
        assert skills_dir.is_dir(), "Skills path is not a directory"

    def test_all_required_skills_exist(self):
        """All required skill directories should exist."""
        required_skills = [
            "oe-project-registry",
            "oe-worker-dispatch",
            "oe-agentos-practice",
            "oe-git-context",
        ]

        for skill_name in required_skills:
            skill_path = Path(f"workspaces/oe-orchestrator/skills/{skill_name}")
            assert skill_path.exists(), f"Skill {skill_name} not found"
            assert skill_path.is_dir(), f"Skill {skill_name} is not a directory"

    def test_all_skill_md_files_exist(self):
        """Each skill should have a SKILL.md file."""
        skills_dir = Path("workspaces/oe-orchestrator/skills")
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]

        for skill_dir in skill_dirs:
            skill_md = skill_dir / "SKILL.md"
            assert skill_md.exists(), f"SKILL.md not found in {skill_dir.name}"


class TestAgentsMdContent:
    """Tests for AGENTS.md content."""

    @pytest.fixture
    def agents_content(self):
        """Load AGENTS.md content."""
        return Path("workspaces/oe-orchestrator/AGENTS.md").read_text()

    def test_has_role_section(self, agents_content):
        """Should define Orchestrator role."""
        assert "# Orchestrator Agent Configuration" in agents_content
        assert "## Role" in agents_content

    def test_describes_capabilities(self, agents_content):
        """Should describe capabilities section."""
        assert "## Capabilities" in agents_content

    def test_lists_core_responsibilities(self, agents_content):
        """Should list core responsibilities."""
        responsibilities = [
            "Project Discovery",
            "Workspace Selection",
            "Task Splitting",
            "Worker Dispatch",
            "Result Synthesis",
            "Git Context Injection",
        ]
        for resp in responsibilities:
            assert resp in agents_content, f"Missing responsibility: {resp}"

    def test_describes_supported_agent_types(self, agents_content):
        """Should list supported agent types."""
        agent_types = ["searcher", "syshelper", "script_coder", "watchdog", "tool_recovery"]
        for agent in agent_types:
            assert agent in agents_content, f"Missing agent type: {agent}"

    def test_defines_loop_state_fields(self, agents_content):
        """Should define mandatory loop state fields."""
        fields = [
            "task_id",
            "round_index",
            "max_rounds",
            "pending_dispatches",
            "received_results",
            "blocked_items",
            "dedupe_keys",
            "recovery_attempts",
            "recovered_methods",
            "recovery_in_progress",
            "termination_state",
        ]
        for field in fields:
            assert field in agents_content, f"Missing state field: {field}"

    def test_documents_recovery_flow(self, agents_content):
        """Should document tool recovery flow and constraints."""
        assert "Tool Recovery Flow" in agents_content
        assert "Recovery Cap" in agents_content
        assert "No Recovery Loops" in agents_content
        assert "No Worker Handoff" in agents_content
        assert "oe-tool-recovery" in agents_content

    def test_describes_workflow(self, agents_content):
        """Should describe workflow."""
        assert "## Workflow" in agents_content
        assert "Bounded Round-Based Orchestration Loop" in agents_content

    def test_lists_available_skills(self, agents_content):
        """Should list available skills."""
        skills = [
            "oe-project-registry",
            "oe-worker-dispatch",
            "oe-agentos-practice",
            "oe-git-context",
        ]
        for skill in skills:
            assert skill in agents_content, f"Missing skill: {skill}"


class TestToolsMdContent:
    """Tests for TOOLS.md content."""

    @pytest.fixture
    def tools_content(self):
        """Load TOOLS.md content."""
        return Path("workspaces/oe-orchestrator/TOOLS.md").read_text()

    def test_has_title(self, tools_content):
        """Should have proper title."""
        assert "# Orchestrator Tools Configuration" in tools_content

    def test_describes_core_tools(self, tools_content):
        """Should describe core tools section."""
        assert "## Core Tools" in tools_content
        assert "### Read" in tools_content
        assert "### Write" in tools_content
        assert "### Bash" in tools_content

    def test_describes_agent_management_tools(self, tools_content):
        """Should describe agent management tools."""
        assert "## Agent Management Tools" in tools_content
        assert "### call_omo_agent" in tools_content
        assert "### background_output" in tools_content

    def test_has_tool_selection_guide(self, tools_content):
        """Should have tool selection guide."""
        assert "## Tool Selection Guide" in tools_content

    def test_defines_output_formats(self, tools_content):
        """Should define output formats."""
        assert "## Output Formats" in tools_content


class TestSkillMdContent:
    """Tests for SKILL.md files."""

    @pytest.mark.parametrize(
        "skill_name",
        [
            "oe-project-registry",
            "oe-worker-dispatch",
            "oe-agentos-practice",
            "oe-git-context",
        ],
    )
    def test_skill_has_frontmatter(self, skill_name):
        """Each skill should have YAML frontmatter."""
        skill_path = Path(f"workspaces/oe-orchestrator/skills/{skill_name}/SKILL.md")
        content = skill_path.read_text()

        assert content.startswith("---"), f"{skill_name} missing frontmatter start"
        assert "name:" in content, f"{skill_name} missing name field"
        assert "version:" in content, f"{skill_name} missing version field"
        assert "description:" in content, f"{skill_name} missing description field"

    @pytest.mark.parametrize(
        "skill_name",
        [
            "oe-project-registry",
            "oe-worker-dispatch",
            "oe-agentos-practice",
            "oe-git-context",
        ],
    )
    def test_skill_has_purpose_section(self, skill_name):
        """Each skill should define its purpose."""
        skill_path = Path(f"workspaces/oe-orchestrator/skills/{skill_name}/SKILL.md")
        content = skill_path.read_text()

        assert "## Purpose" in content or "# " in content, f"{skill_name} missing purpose"

    @pytest.mark.parametrize(
        "skill_name",
        [
            "oe-project-registry",
            "oe-worker-dispatch",
            "oe-agentos-practice",
            "oe-git-context",
        ],
    )
    def test_skill_has_usage_section(self, skill_name):
        """Each skill should have usage instructions."""
        skill_path = Path(f"workspaces/oe-orchestrator/skills/{skill_name}/SKILL.md")
        content = skill_path.read_text()

        assert "## Usage" in content or "## When to Use" in content, f"{skill_name} missing usage"


class TestRenderWorkspaceCommand:
    """Tests for render-workspace CLI command."""

    def test_render_workspace_command_exists(self):
        """render-workspace command should be available."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"render-workspace --help failed: {result.stderr}"

    def test_render_workspace_shows_usage(self):
        """render-workspace --help should show usage."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "--help"],
            capture_output=True,
            text=True,
        )
        assert "WORKSPACE_NAME" in result.stdout or "workspace" in result.stdout.lower()

    def test_render_workspace_valid_workspace(self):
        """render-workspace should work for valid workspace."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "oe-orchestrator"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"render-workspace failed: {result.stderr}"

    def test_render_workspace_output_includes_agents(self):
        """render-workspace output should include AGENTS.md content."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "oe-orchestrator"],
            capture_output=True,
            text=True,
        )
        assert "Orchestrator" in result.stdout or "AGENTS" in result.stdout

    def test_render_workspace_output_includes_tools(self):
        """render-workspace output should include TOOLS.md content."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "oe-orchestrator"],
            capture_output=True,
            text=True,
        )
        assert "Tools" in result.stdout or "TOOLS" in result.stdout

    def test_render_workspace_output_includes_skills(self):
        """render-workspace output should include skills."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "oe-orchestrator"],
            capture_output=True,
            text=True,
        )
        assert "oe-project-registry" in result.stdout
        assert "oe-worker-dispatch" in result.stdout

    def test_render_workspace_invalid_workspace(self):
        """render-workspace should fail gracefully for invalid workspace."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "nonexistent"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "Should fail for invalid workspace"


class TestWorkspaceRenderingLogic:
    """Tests for workspace rendering logic."""

    def test_render_includes_agents_md(self):
        """Rendering should include AGENTS.md content."""
        from openclaw_enhance.workspaces import render_workspace

        output = render_workspace("oe-orchestrator")
        assert "# Orchestrator Agent Configuration" in output

    def test_render_includes_tools_md(self):
        """Rendering should include TOOLS.md content."""
        from openclaw_enhance.workspaces import render_workspace

        output = render_workspace("oe-orchestrator")
        assert "# Orchestrator Tools Configuration" in output

    def test_render_includes_all_skills(self):
        """Rendering should include all skill definitions."""
        from openclaw_enhance.workspaces import render_workspace

        output = render_workspace("oe-orchestrator")
        assert "oe-project-registry" in output
        assert "oe-worker-dispatch" in output
        assert "oe-agentos-practice" in output
        assert "oe-git-context" in output

    def test_render_unknown_workspace_raises(self):
        """Rendering unknown workspace should raise ValueError."""
        from openclaw_enhance.workspaces import render_workspace

        with pytest.raises(ValueError, match="Unknown workspace"):
            render_workspace("nonexistent-workspace")


class TestCheckpointBehaviorDocumentation:
    """Tests for checkpoint visibility and behavior documentation."""

    @pytest.fixture
    def agents_content(self):
        """Load AGENTS.md content."""
        return Path("workspaces/oe-orchestrator/AGENTS.md").read_text()

    @pytest.fixture
    def dispatch_skill_content(self):
        """Load worker dispatch SKILL.md content."""
        return Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md").read_text()

    def test_agents_md_documents_checkpoint_semi_visible_model(self, agents_content):
        """AGENTS.md should document semi-visible checkpoint model for main."""
        assert "Semi-Visible" in agents_content or "semi-visible" in agents_content.lower()
        assert "Main sees:" in agents_content or "Main session receives" in agents_content
        assert "Main does NOT see:" in agents_content

    def test_agents_md_documents_meaningful_progress_checkpoint(self, agents_content):
        """AGENTS.md should document meaningful_progress checkpoint."""
        assert "meaningful_progress" in agents_content
        # Should describe it as optional/suppress routine
        assert (
            "optional" in agents_content.lower()
            or "suppress" in agents_content.lower()
            or "Significant" in agents_content
        )

    def test_agents_md_documents_blocked_checkpoint(self, agents_content):
        """AGENTS.md should document blocked checkpoint for escalation."""
        assert "blocked" in agents_content
        # Should describe it as requiring main decision
        assert "decision" in agents_content.lower() or "intervention" in agents_content.lower()

    def test_agents_md_documents_terminal_checkpoint(self, agents_content):
        """AGENTS.md should document terminal checkpoint states."""
        assert (
            "terminal" in agents_content
            or "exhausted" in agents_content
            or "escalated" in agents_content
        )

    def test_agents_md_no_polling_patterns(self, agents_content):
        """AGENTS.md should not document polling patterns using sessions_history."""
        assert "sessions_history" not in agents_content
        # Should emphasize yield-based waiting
        assert "sessions_yield" in agents_content

    def test_dispatch_skill_documents_checkpoint_visibility(self, dispatch_skill_content):
        """Worker dispatch skill should document checkpoint visibility to main."""
        assert "Checkpoint Visibility" in dispatch_skill_content
        assert (
            "Always report:" in dispatch_skill_content or "main" in dispatch_skill_content.lower()
        )

    def test_dispatch_skill_documents_meaningful_progress(self, dispatch_skill_content):
        """Worker dispatch skill should document meaningful_progress as conditional report."""
        assert "meaningful_progress" in dispatch_skill_content
        # Should describe as conditional
        assert (
            "Conditionally" in dispatch_skill_content
            or "optional" in dispatch_skill_content.lower()
        )

    def test_dispatch_skill_no_routine_round_boundaries(self, dispatch_skill_content):
        """Worker dispatch skill should document that routine round boundaries are hidden."""
        assert (
            "Never report:" in dispatch_skill_content or "routine" in dispatch_skill_content.lower()
        )
        assert (
            "round boundaries" in dispatch_skill_content.lower()
            or "Individual worker" in dispatch_skill_content
        )


class TestWorkspaceRegistry:
    """Tests for workspace registry functionality."""

    def test_list_workspaces_includes_orchestrator(self):
        """Workspace list should include oe-orchestrator."""
        from openclaw_enhance.workspaces import list_workspaces

        workspaces = list_workspaces()
        assert "oe-orchestrator" in workspaces

    def test_get_workspace_metadata(self):
        """Should be able to get workspace metadata."""
        from openclaw_enhance.workspaces import get_workspace_metadata

        metadata = get_workspace_metadata("oe-orchestrator")
        assert metadata["name"] == "oe-orchestrator"
        assert "path" in metadata
        assert "skills" in metadata

    def test_get_workspace_skills(self):
        """Should list all skills for workspace."""
        from openclaw_enhance.workspaces import get_workspace_skills

        skills = get_workspace_skills("oe-orchestrator")
        expected_skills = [
            "oe-project-registry",
            "oe-worker-dispatch",
            "oe-agentos-practice",
            "oe-git-context",
        ]
        for skill in expected_skills:
            assert skill in skills, f"Missing skill: {skill}"
