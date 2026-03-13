"""Integration tests for skill contracts and file-backed loading.

Tests the file-backed skill contract system that replaced
the Python-first router runtime API.
"""

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


class TestSkillContractRendering:
    """Tests for skill contract rendering from files."""

    def test_render_eta_estimator_contract(self):
        """Should render oe-eta-estimator contract."""
        contract = render_skill_contract("oe-eta-estimator")

        assert "ETA Estimator" in contract
        assert "oe-eta-estimator" in contract
        assert "Estimates task duration" in contract

    def test_render_toolcall_router_contract(self):
        """Should render oe-toolcall-router contract."""
        contract = render_skill_contract("oe-toolcall-router")

        assert "Toolcall Router" in contract
        assert "oe-toolcall-router" in contract
        assert "Routes tasks" in contract

    def test_render_timeout_state_sync_contract(self):
        """Should render oe-timeout-state-sync contract."""
        contract = render_skill_contract("oe-timeout-state-sync")

        assert "Timeout State Sync" in contract
        assert "oe-timeout-state-sync" in contract

    def test_render_unknown_skill_raises(self):
        """Rendering unknown skill should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            render_skill_contract("unknown-skill")

        assert "Unknown skill" in str(exc_info.value)

    def test_all_contracts_have_required_fields(self):
        """All skill contracts should have required fields."""
        required_fields = ["name:", "version:", "description:"]

        for skill_name in list_skill_contract_names():
            contract = render_skill_contract(skill_name)
            for field in required_fields:
                assert field in contract, f"{skill_name} missing {field}"


class TestTaskDurationEstimation:
    """Tests for task duration estimation function."""

    def test_single_toolcall_duration(self):
        """Single toolcall should estimate 2 minutes."""
        duration = estimate_task_duration(
            estimated_toolcalls=1,
            requires_parallel=False,
        )

        assert duration == timedelta(minutes=2)

    def test_two_toolcalls_duration(self):
        """Two toolcalls should estimate 5 minutes."""
        duration = estimate_task_duration(
            estimated_toolcalls=2,
            requires_parallel=False,
        )

        assert duration == timedelta(minutes=5)

    def test_five_toolcalls_duration(self):
        """Five toolcalls should estimate 15 minutes."""
        duration = estimate_task_duration(
            estimated_toolcalls=5,
            requires_parallel=False,
        )

        assert duration == timedelta(minutes=15)

    def test_ten_toolcalls_duration(self):
        """Ten toolcalls should estimate 40 minutes."""
        duration = estimate_task_duration(
            estimated_toolcalls=10,
            requires_parallel=False,
        )

        assert duration == timedelta(minutes=40)

    def test_parallel_multiplier_applied(self):
        """Parallel tasks get 1.5x multiplier."""
        # Base: 2 toolcalls = 5 minutes * 1.5 = 7.5 -> int = 7
        duration = estimate_task_duration(
            estimated_toolcalls=2,
            requires_parallel=True,
        )

        assert duration == timedelta(minutes=7)

    def test_zero_toolcalls_minimum_duration(self):
        """Zero toolcalls should return minimum 1 minute."""
        duration = estimate_task_duration(
            estimated_toolcalls=0,
            requires_parallel=False,
        )

        assert duration == timedelta(minutes=1)

    def test_negative_toolcalls_minimum_duration(self):
        """Negative toolcalls should return minimum 1 minute."""
        duration = estimate_task_duration(
            estimated_toolcalls=-5,
            requires_parallel=False,
        )

        assert duration == timedelta(minutes=1)

    def test_duration_override_used(self):
        """Duration override should be used when provided."""
        duration = estimate_task_duration(
            estimated_toolcalls=5,
            requires_parallel=False,
            estimated_duration_override=timedelta(minutes=100),
        )

        assert duration == timedelta(minutes=100)

    def test_duration_override_minimum_enforced(self):
        """Duration override should respect minimum of 1 minute."""
        duration = estimate_task_duration(
            estimated_toolcalls=5,
            requires_parallel=False,
            estimated_duration_override=timedelta(seconds=30),
        )

        assert duration == timedelta(minutes=1)


class TestSkillContracts:
    """Tests for skill contract validation."""

    def test_all_skills_have_contracts(self):
        """All skills in registry should have contract files."""
        contract_names = set(list_skill_contract_names())

        for skill in SKILLS_REGISTRY:
            assert skill.name in contract_names, f"{skill.name} missing contract file"

    def test_contract_content_matches_registry(self):
        """Contract content should match registry metadata."""
        for skill in SKILLS_REGISTRY:
            contract = render_skill_contract(skill.name)
            # Contract should contain skill name
            assert skill.name in contract
            # Contract should contain description keywords
            desc_words = skill.description.lower().split()[:3]
            for word in desc_words:
                if len(word) > 3:  # Skip short words
                    assert word in contract.lower(), f"{skill.name} missing '{word}'"


class TestSkillMetadata:
    """Tests for skill metadata validation."""

    def test_skill_metadata_structure(self):
        """All skills should have proper metadata structure."""
        for skill in SKILLS_REGISTRY:
            assert isinstance(skill, SkillMetadata)
            assert skill.name
            assert skill.description
            assert skill.version
            assert isinstance(skill.user_invocable, bool)
            assert isinstance(skill.allowed_tools, list)
            assert isinstance(skill.routing_heuristics, dict)

    def test_routing_heuristics_structure(self):
        """All skills should have consistent routing heuristics."""
        for skill in SKILLS_REGISTRY:
            heuristics = skill.routing_heuristics
            assert "max_toolcalls" in heuristics
            assert "max_duration_minutes" in heuristics
            assert isinstance(heuristics["max_toolcalls"], int)
            assert isinstance(heuristics["max_duration_minutes"], int)


class TestFileBackedLoading:
    """Tests for file-backed skill contract loading."""

    def test_skills_loaded_from_correct_directory(self):
        """Skills should be loaded from skills/ directory."""
        names = list_skill_contract_names()
        assert len(names) >= 3

        # Verify each contract file exists
        for name in names:
            contract = render_skill_contract(name)
            assert len(contract) > 0

    def test_contract_files_have_yaml_frontmatter(self):
        """All contract files should have YAML frontmatter."""
        for name in list_skill_contract_names():
            contract = render_skill_contract(name)
            assert contract.startswith("---"), f"{name} missing YAML frontmatter"

    def test_contract_files_are_readable(self):
        """All contract files should be readable as text."""
        for name in list_skill_contract_names():
            contract = render_skill_contract(name)
            assert isinstance(contract, str)
            assert "name:" in contract
            assert "version:" in contract


class TestSkillRegistryIntegration:
    """Integration tests for skill registry consistency."""

    def test_registry_matches_file_system(self):
        """Registry should match files on disk."""
        registry_names = {skill.name for skill in SKILLS_REGISTRY}
        file_names = set(list_skill_contract_names())

        # All registry skills should have files
        assert registry_names.issubset(file_names)

    def test_skills_have_consistent_versions(self):
        """Skills should have consistent version formats."""
        for skill in SKILLS_REGISTRY:
            # Version should be in semver format (x.y.z)
            parts = skill.version.split(".")
            assert len(parts) == 3, f"{skill.name} has invalid version: {skill.version}"
            for part in parts:
                assert part.isdigit(), f"{skill.name} version has non-digit: {part}"

    def test_toolcall_router_has_escalation_threshold(self):
        """Toolcall router should have escalation threshold in heuristics."""
        router_skill = next(s for s in SKILLS_REGISTRY if s.name == "oe-toolcall-router")
        assert "escalation_threshold" in router_skill.routing_heuristics
        assert router_skill.routing_heuristics["escalation_threshold"] == 2

    def test_eta_estimator_has_base_time_per_toolcall(self):
        """ETA estimator should have base time per toolcall in heuristics."""
        eta_skill = next(s for s in SKILLS_REGISTRY if s.name == "oe-eta-estimator")
        assert "base_time_per_toolcall" in eta_skill.routing_heuristics

    def test_timeout_sync_has_sync_interval(self):
        """Timeout sync should have sync interval in heuristics."""
        timeout_skill = next(s for s in SKILLS_REGISTRY if s.name == "oe-timeout-state-sync")
        assert "sync_interval_seconds" in timeout_skill.routing_heuristics
