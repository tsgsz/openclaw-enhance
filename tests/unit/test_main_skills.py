"""Unit tests for main session skill routing logic."""

from datetime import timedelta
from pathlib import Path

import pytest

from openclaw_enhance.skills_catalog import (
    SKILLS_REGISTRY,
    RoutingDecision,
    SkillMetadata,
    SkillRouter,
    TaskAssessment,
    estimate_task_duration,
    list_skill_contract_names,
    render_skill_contract,
    should_escalate_to_orchestrator,
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


class TestRoutingDecision:
    """Test RoutingDecision dataclass."""

    def test_routing_decision_creation(self):
        """Test creating RoutingDecision."""
        decision = RoutingDecision(
            action="escalate",
            target="oe-orchestrator",
            reason="High toolcall count",
            estimated_duration=timedelta(minutes=30),
        )
        assert decision.action == "escalate"
        assert decision.target == "oe-orchestrator"
        assert decision.reason == "High toolcall count"
        assert decision.estimated_duration == timedelta(minutes=30)

    def test_routing_decision_route_local(self):
        """Test creating a local routing decision."""
        decision = RoutingDecision(
            action="route",
            target="main",
            reason="Simple task",
            estimated_duration=timedelta(minutes=5),
        )
        assert decision.action == "route"
        assert decision.target == "main"


class TestTaskAssessment:
    """Test TaskAssessment dataclass."""

    def test_task_assessment_creation(self):
        """Test creating TaskAssessment."""
        assessment = TaskAssessment(
            description="Refactor code",
            estimated_toolcalls=3,
            requires_parallel=False,
            complexity_score=2,
        )
        assert assessment.description == "Refactor code"
        assert assessment.estimated_toolcalls == 3
        assert assessment.requires_parallel is False
        assert assessment.complexity_score == 2


class TestEstimateTaskDuration:
    """Test task duration estimation."""

    @pytest.mark.parametrize(
        "description,toolcalls,parallel,expected_minutes",
        [
            ("Fix typo", 1, False, 2),
            ("Add simple function", 2, False, 5),
            ("Refactor module", 5, False, 15),
            ("Complex refactor with tests", 8, True, 45),
            ("Multi-file architecture change", 10, True, 60),
            ("Large codebase migration", 20, True, 120),
        ],
    )
    def test_estimate_duration_scenarios(self, description, toolcalls, parallel, expected_minutes):
        """Test various task duration estimation scenarios."""
        assessment = TaskAssessment(
            description=description,
            estimated_toolcalls=toolcalls,
            requires_parallel=parallel,
            complexity_score=toolcalls // 2,
        )
        duration = estimate_task_duration(assessment)
        assert duration == timedelta(minutes=expected_minutes)

    def test_estimate_duration_minimum(self):
        """Test that minimum duration is 1 minute."""
        assessment = TaskAssessment(
            description="Trivial fix",
            estimated_toolcalls=0,
            requires_parallel=False,
            complexity_score=0,
        )
        duration = estimate_task_duration(assessment)
        assert duration >= timedelta(minutes=1)


class TestShouldEscalateToOrchestrator:
    """Test escalation decision logic."""

    def test_escalate_high_toolcall_count(self):
        """Tasks with >2 toolcalls should escalate."""
        assessment = TaskAssessment(
            description="Complex task",
            estimated_toolcalls=5,
            requires_parallel=False,
            complexity_score=3,
        )
        assert should_escalate_to_orchestrator(assessment) is True

    def test_no_escalate_low_toolcall_count(self):
        """Tasks with <=2 toolcalls stay local."""
        assessment = TaskAssessment(
            description="Simple task",
            estimated_toolcalls=2,
            requires_parallel=False,
            complexity_score=1,
        )
        assert should_escalate_to_orchestrator(assessment) is False

    def test_escalate_parallel_required(self):
        """Tasks requiring parallelism should escalate."""
        assessment = TaskAssessment(
            description="Parallel refactor",
            estimated_toolcalls=2,
            requires_parallel=True,
            complexity_score=2,
        )
        assert should_escalate_to_orchestrator(assessment) is True

    def test_escalate_long_duration(self):
        """Long-running tasks should escalate."""
        assessment = TaskAssessment(
            description="Long task",
            estimated_toolcalls=3,
            requires_parallel=False,
            complexity_score=3,
            estimated_duration_override=timedelta(minutes=45),
        )
        assert should_escalate_to_orchestrator(assessment) is True

    def test_no_escalate_simple_task(self):
        """Simple single-toolcall task stays local."""
        assessment = TaskAssessment(
            description="Quick edit",
            estimated_toolcalls=1,
            requires_parallel=False,
            complexity_score=1,
        )
        assert should_escalate_to_orchestrator(assessment) is False


class TestSkillRouter:
    """Test SkillRouter class."""

    def test_router_initialization(self):
        """Test router can be initialized."""
        router = SkillRouter()
        assert router is not None

    def test_route_task_simple(self):
        """Test routing simple task stays local."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Fix typo",
            estimated_toolcalls=1,
            requires_parallel=False,
            complexity_score=1,
        )
        decision = router.route_task(assessment)
        assert decision.action == "route"
        assert decision.target == "main"

    def test_route_task_escalate(self):
        """Test routing complex task escalates to orchestrator."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Complex refactor",
            estimated_toolcalls=5,
            requires_parallel=False,
            complexity_score=4,
        )
        decision = router.route_task(assessment)
        assert decision.action == "escalate"
        assert decision.target == "oe-orchestrator"
        assert "toolcall" in decision.reason.lower() or "orchestrator" in decision.reason.lower()

    def test_route_task_parallel(self):
        """Test routing parallel task escalates."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Parallel work",
            estimated_toolcalls=2,
            requires_parallel=True,
            complexity_score=2,
        )
        decision = router.route_task(assessment)
        assert decision.action == "escalate"
        assert decision.target == "oe-orchestrator"

    def test_route_task_with_timeout(self):
        """Test routing includes timeout info for long tasks."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Very long task",
            estimated_toolcalls=10,
            requires_parallel=True,
            complexity_score=5,
        )
        decision = router.route_task(assessment)
        assert decision.estimated_duration is not None
        assert decision.estimated_duration >= timedelta(minutes=30)


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
        assert router_skill.routing_heuristics["escalation_threshold"] == 2


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


class TestIntegrationWithRuntime:
    """Test integration with runtime schema."""

    def test_router_uses_runtime_schema_types(self):
        """Router should work with runtime schema types."""
        from openclaw_enhance.runtime.schema import RuntimeState

        router = SkillRouter()
        runtime_state = RuntimeState()
        assert runtime_state.schema_version == 1

        # Router should be able to work with runtime state
        assessment = TaskAssessment(
            description="Test with runtime",
            estimated_toolcalls=1,
            requires_parallel=False,
            complexity_score=1,
        )
        decision = router.route_task(assessment)
        assert decision is not None
