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

    def test_has_frontmatter_manifest(self, agents_content):
        """Should define routing metadata in YAML frontmatter."""
        assert agents_content.startswith("---")
        assert "agent_id: oe-orchestrator" in agents_content
        assert "workspace: oe-orchestrator" in agents_content
        assert "routing:" in agents_content

    def test_has_minimal_body_structure(self, agents_content):
        """AGENTS.md body should only contain frontmatter and a short Role sentence."""
        lines = agents_content.strip().split("\n")
        # First line should be ---
        assert lines[0] == "---"
        # After frontmatter (---), should have title and one sentence
        body_start = agents_content.index("---\n", 4) + len("---\n")
        body = agents_content[body_start:].strip()
        body_lines = [l for l in body.split("\n") if l.strip()]
        # Title line
        assert body_lines[0] == "# oe-orchestrator"
        # Role sentence (should be short, one line)
        assert len(body_lines) == 2
        assert "Dispatcher" in body_lines[1]
        assert len(body_lines[1]) < 100

    def test_removes_redundant_sections(self, agents_content):
        """Redundant sections should be removed per simplification principle."""
        assert "## Session Startup" not in agents_content
        assert "## Skills" not in agents_content
        assert "## Boundaries" not in agents_content
        assert "## Workflow" not in agents_content
        assert "## Version" not in agents_content
        assert "Bounded Round-Based Orchestration Loop" not in agents_content
        assert "## Output Format" not in agents_content


class TestToolsMdContent:
    """Tests for TOOLS.md content."""

    @pytest.fixture
    def tools_content(self):
        """Load TOOLS.md content."""
        return Path("workspaces/oe-orchestrator/TOOLS.md").read_text()

    def test_uses_local_notes_template(self, tools_content):
        """TOOLS.md should align with local-notes semantics."""
        assert "# TOOLS.md - Local Notes" in tools_content
        assert "Skills define how tools work" in tools_content

    def test_keeps_only_workspace_specific_notes(self, tools_content):
        """TOOLS.md should keep local paths/notes instead of generic manuals."""
        assert ".sisyphus/plans/" in tools_content
        assert "project-registry.json" in tools_content
        assert "workspaces/*/AGENTS.md" in tools_content

    def test_removes_tool_policy_duplication(self, tools_content):
        """Detailed tool usage guides should not remain in TOOLS.md."""
        assert "## Core Tools" not in tools_content
        assert "## Agent Management Tools" not in tools_content
        assert "## Tool Selection Guide" not in tools_content
        assert "## Output Formats" not in tools_content


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
        assert "# oe-orchestrator" in output

    def test_render_includes_tools_md(self):
        """Rendering should include TOOLS.md content."""
        from openclaw_enhance.workspaces import render_workspace

        output = render_workspace("oe-orchestrator")
        assert "# TOOLS.md - Local Notes" in output

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

    def test_agents_md_keeps_checkpoint_details_out_of_bootstrap(self, agents_content):
        """Checkpoint details should move to the dispatch skill, not AGENTS.md."""
        assert "meaningful_progress" not in agents_content
        assert "Main does NOT see:" not in agents_content
        assert "sessions_yield" not in agents_content

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
