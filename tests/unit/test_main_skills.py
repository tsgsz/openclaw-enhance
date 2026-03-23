"""Unit tests for main session skill rendering and metadata."""

from datetime import timedelta
from pathlib import Path

import pytest

from openclaw_enhance.skills_catalog import (
    SKILLS_REGISTRY,
    SkillMetadata,
    estimate_task_duration,
    list_skill_contract_names,
    render_skill_contract,
)


class TestSkillMetadata:
    """Test SkillMetadata dataclass."""

    def test_skill_metadata_creation(self):
        """Test creating SkillMetadata with all fields."""
        skill = SkillMetadata(
            name="test-skill",
            description="A test skill",
            version="1.0.0",
            user_invocable=True,
            allowed_tools=["Read", "Write"],
            routing_heuristics={"max_toolcalls": 5},
        )
        assert skill.name == "test-skill"
        assert skill.description == "A test skill"
        assert skill.version == "1.0.0"
        assert skill.user_invocable is True
        assert skill.allowed_tools == ["Read", "Write"]
        assert skill.routing_heuristics == {"max_toolcalls": 5}


class TestEstimateTaskDuration:
    """Test task duration estimation function."""

    @pytest.mark.parametrize(
        "toolcalls,parallel,expected_minutes",
        [
            (1, False, 2),
            (2, False, 5),
            (5, False, 15),
            (8, True, 45),
            (10, True, 60),
            (20, True, 120),
        ],
    )
    def test_estimate_duration_scenarios(self, toolcalls, parallel, expected_minutes):
        """Test various task duration estimation scenarios."""
        duration = estimate_task_duration(
            estimated_toolcalls=toolcalls,
            requires_parallel=parallel,
        )
        assert duration == timedelta(minutes=expected_minutes)

    def test_estimate_duration_minimum(self):
        """Test that minimum duration is 1 minute."""
        duration = estimate_task_duration(
            estimated_toolcalls=0,
            requires_parallel=False,
        )
        assert duration >= timedelta(minutes=1)

    def test_estimate_duration_with_override(self):
        """Test duration override is respected."""
        duration = estimate_task_duration(
            estimated_toolcalls=5,
            requires_parallel=False,
            estimated_duration_override=timedelta(minutes=100),
        )
        assert duration == timedelta(minutes=100)

    def test_estimate_duration_override_minimum(self):
        """Test that duration override respects minimum of 1 minute."""
        duration = estimate_task_duration(
            estimated_toolcalls=5,
            requires_parallel=False,
            estimated_duration_override=timedelta(seconds=30),
        )
        assert duration == timedelta(minutes=1)


class TestSkillRegistry:
    """Test skill registry constants."""

    def test_registry_has_all_main_skills(self):
        """Registry should contain all three main-session skills."""
        skill_names = {skill.name for skill in SKILLS_REGISTRY}
        assert "oe-eta-estimator" in skill_names
        assert "oe-toolcall-router" in skill_names
        assert "oe-timeout-state-sync" in skill_names

    def test_registry_skills_have_routing_heuristics(self):
        """All skills should have routing heuristics defined."""
        for skill in SKILLS_REGISTRY:
            assert "max_toolcalls" in skill.routing_heuristics
            assert "max_duration_minutes" in skill.routing_heuristics

    def test_toolcall_router_has_special_heuristics(self):
        """Toolcall router should have toolcall-specific heuristics."""
        router_skill = next(s for s in SKILLS_REGISTRY if s.name == "oe-toolcall-router")
        assert router_skill.routing_heuristics["escalation_threshold"] == 0


class TestRenderSkillContract:
    """Test skill contract rendering."""

    def test_render_eta_estimator_contract(self):
        """Test rendering oe-eta-estimator skill contract."""
        contract = render_skill_contract("oe-eta-estimator")
        assert contract is not None
        assert "eta" in contract.lower() or "duration" in contract.lower()
        assert "estimate" in contract.lower()

    def test_render_toolcall_router_contract(self):
        """Toolcall router contract matches SKILL.md exactly."""
        contract = render_skill_contract("oe-toolcall-router")
        expected = Path("skills/oe-toolcall-router/SKILL.md").read_text(encoding="utf-8")
        assert contract == expected

    def test_render_timeout_sync_contract(self):
        """Test rendering oe-timeout-state-sync skill contract."""
        contract = render_skill_contract("oe-timeout-state-sync")
        assert contract is not None
        assert "timeout" in contract.lower()
        assert "sync" in contract.lower() or "state" in contract.lower()

    def test_render_unknown_skill_raises(self):
        """Rendering unknown skill should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown skill"):
            render_skill_contract("nonexistent-skill")

    def test_render_unknown_skill_lists_available_names(self):
        """Unknown skill errors include available skill names."""
        with pytest.raises(ValueError, match="Available skills"):
            render_skill_contract("missing")

    def test_list_skill_contract_names(self):
        """Skill listing includes known contracts."""
        names = list_skill_contract_names()
        assert "oe-eta-estimator" in names
        assert "oe-toolcall-router" in names
        assert "oe-timeout-state-sync" in names

    def test_render_contract_has_yaml_frontmatter(self):
        """Rendered contract should have YAML frontmatter."""
        contract = render_skill_contract("oe-toolcall-router")
        assert contract.startswith("---")
        assert "name:" in contract


class TestSkillContracts:
    """Test skill contract content validation."""

    def test_eta_estimator_contract_has_required_fields(self):
        """oe-eta-estimator contract should have all required fields."""
        contract = render_skill_contract("oe-eta-estimator")
        required_fields = ["name:", "version:", "description:", "oe-eta-estimator"]
        for field in required_fields:
            assert field in contract, f"Missing field: {field}"

    def test_toolcall_router_contract_has_required_fields(self):
        """oe-toolcall-router contract should have all required fields."""
        contract = render_skill_contract("oe-toolcall-router")
        required_fields = [
            "name:",
            "version:",
            "description:",
            "oe-toolcall-router",
            "Main session",
        ]
        for field in required_fields:
            assert field in contract, f"Missing field: {field}"

    def test_toolcall_router_contract_has_issue9_heavy_research_example(self):
        contract = render_skill_contract("oe-toolcall-router")
        assert "issue #9" in contract.lower()
        assert "ppt" in contract.lower()
        assert "traceable data" in contract.lower()
        assert "sessions_spawn" in contract
        assert '"agentId": "oe-orchestrator"' in contract
        assert "no python wrappers" in contract.lower()

    def test_timeout_sync_contract_has_required_fields(self):
        """oe-timeout-state-sync contract should have all required fields."""
        contract = render_skill_contract("oe-timeout-state-sync")
        required_fields = ["name:", "version:", "description:", "oe-timeout-state-sync"]
        for field in required_fields:
            assert field in contract, f"Missing field: {field}"

    def test_all_contracts_have_yaml_frontmatter(self):
        """All skill contracts should have YAML frontmatter."""
        names = list_skill_contract_names()
        for name in names:
            contract = render_skill_contract(name)
            assert contract.startswith("---"), f"{name} missing YAML frontmatter"
            assert "name:" in contract, f"{name} missing name field"
            assert "version:" in contract, f"{name} missing version field"


class TestFileBackedSkillLoading:
    """Test file-backed skill contract loading."""

    def test_skill_contracts_loaded_from_files(self):
        """Skill contracts should be loaded from SKILL.md files."""
        names = list_skill_contract_names()
        assert len(names) >= 3
        # Verify we can load each one
        for name in names:
            contract = render_skill_contract(name)
            assert len(contract) > 0
            assert isinstance(contract, str)

    def test_skill_contracts_consistency(self):
        """Skill registry should match available file contracts."""
        registry_names = {skill.name for skill in SKILLS_REGISTRY}
        file_names = set(list_skill_contract_names())
        # All registry skills should have contracts
        for name in registry_names:
            assert name in file_names, f"Registry skill {name} missing contract file"
