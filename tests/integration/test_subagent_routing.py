"""Integration tests for subagent routing logic.

Tests the SkillRouter and related routing decisions that determine
whether tasks should stay in main or escalate to the orchestrator.
"""

from datetime import timedelta

import pytest

from openclaw_enhance.skills_catalog import (
    SKILL_CONTRACTS,
    SkillRouter,
    TaskAssessment,
    estimate_task_duration,
    render_skill_contract,
    should_escalate_to_orchestrator,
)


class TestSkillRouterRoutingDecisions:
    """Tests for SkillRouter routing decisions."""

    def test_simple_task_routes_to_main(self):
        """Simple tasks (1 toolcall) should stay in main."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Fix typo in README",
            estimated_toolcalls=1,
            requires_parallel=False,
            complexity_score=1,
        )

        decision = router.route_task(assessment)

        assert decision.action == "route"
        assert decision.target == "main"
        assert "Simple task" in decision.reason

    def test_two_toolcalls_routes_to_main(self):
        """Tasks with 2 toolcalls should stay in main."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Update function and add test",
            estimated_toolcalls=2,
            requires_parallel=False,
            complexity_score=2,
        )

        decision = router.route_task(assessment)

        assert decision.action == "route"
        assert decision.target == "main"

    def test_three_toolcalls_escalates(self):
        """Tasks with 3 toolcalls should escalate to orchestrator."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Refactor auth module with tests",
            estimated_toolcalls=3,
            requires_parallel=False,
            complexity_score=3,
        )

        decision = router.route_task(assessment)

        assert decision.action == "escalate"
        assert decision.target == "oe-orchestrator"
        assert "toolcall" in decision.reason.lower()

    def test_high_toolcall_count_escalates(self):
        """Tasks with many toolcalls should escalate."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Large refactoring with multiple files",
            estimated_toolcalls=10,
            requires_parallel=False,
            complexity_score=5,
        )

        decision = router.route_task(assessment)

        assert decision.action == "escalate"
        assert decision.target == "oe-orchestrator"

    def test_parallel_requirement_escalates(self):
        """Tasks requiring parallel execution should escalate."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Multi-file refactor requiring parallel agents",
            estimated_toolcalls=2,
            requires_parallel=True,
            complexity_score=3,
        )

        decision = router.route_task(assessment)

        assert decision.action == "escalate"
        assert decision.target == "oe-orchestrator"
        assert "parallel" in decision.reason.lower()

    def test_long_duration_escalates(self):
        """Long-running tasks should escalate."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Research task with long duration",
            estimated_toolcalls=2,
            requires_parallel=False,
            complexity_score=2,
            estimated_duration_override=timedelta(minutes=45),
        )

        decision = router.route_task(assessment)

        assert decision.action == "escalate"
        assert decision.target == "oe-orchestrator"
        assert "long" in decision.reason.lower()

    def test_duration_at_threshold_routes_to_main(self):
        """Tasks at exactly 30 minutes should escalate (threshold is >30)."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Task at boundary",
            estimated_toolcalls=2,
            requires_parallel=False,
            complexity_score=2,
            estimated_duration_override=timedelta(minutes=30),
        )

        # 30 minutes is NOT > 30, so should route to main
        decision = router.route_task(assessment)

        # Actually, the condition is estimated_duration > threshold
        # So 30 minutes should route to main
        assert decision.action == "route"
        assert decision.target == "main"

    def test_duration_over_threshold_escalates(self):
        """Tasks just over 30 minutes should escalate."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Task just over boundary",
            estimated_toolcalls=2,
            requires_parallel=False,
            complexity_score=2,
            estimated_duration_override=timedelta(minutes=31),
        )

        decision = router.route_task(assessment)

        assert decision.action == "escalate"
        assert decision.target == "oe-orchestrator"


class TestTaskDurationEstimation:
    """Tests for task duration estimation."""

    def test_single_toolcall_duration(self):
        """Single toolcall should estimate 2 minutes."""
        assessment = TaskAssessment(
            description="Quick fix",
            estimated_toolcalls=1,
            requires_parallel=False,
            complexity_score=1,
        )

        duration = estimate_task_duration(assessment)

        assert duration == timedelta(minutes=2)

    def test_two_toolcalls_duration(self):
        """Two toolcalls should estimate 5 minutes."""
        assessment = TaskAssessment(
            description="Small change",
            estimated_toolcalls=2,
            requires_parallel=False,
            complexity_score=1,
        )

        duration = estimate_task_duration(assessment)

        assert duration == timedelta(minutes=5)

    def test_five_toolcalls_duration(self):
        """Five toolcalls should estimate 15 minutes."""
        assessment = TaskAssessment(
            description="Medium task",
            estimated_toolcalls=5,
            requires_parallel=False,
            complexity_score=1,
        )

        duration = estimate_task_duration(assessment)

        assert duration == timedelta(minutes=15)

    def test_ten_toolcalls_duration(self):
        """Ten toolcalls should estimate 40 minutes."""
        assessment = TaskAssessment(
            description="Large task",
            estimated_toolcalls=10,
            requires_parallel=False,
            complexity_score=1,
        )

        duration = estimate_task_duration(assessment)

        assert duration == timedelta(minutes=40)

    def test_parallel_multiplier_applied(self):
        """Parallel tasks get 1.5x multiplier."""
        assessment = TaskAssessment(
            description="Parallel task",
            estimated_toolcalls=2,
            requires_parallel=True,
            complexity_score=1,
        )

        # Base: 5 minutes * 1.5 = 7.5 -> int = 7 or 8
        duration = estimate_task_duration(assessment)

        # 5 * 1.5 = 7.5 -> int(7.5) = 7
        assert duration == timedelta(minutes=7)

    def test_zero_toolcalls_minimum_duration(self):
        """Zero toolcalls should return minimum 1 minute."""
        assessment = TaskAssessment(
            description="No toolcalls",
            estimated_toolcalls=0,
            requires_parallel=False,
            complexity_score=1,
        )

        duration = estimate_task_duration(assessment)

        assert duration == timedelta(minutes=1)

    def test_negative_toolcalls_minimum_duration(self):
        """Negative toolcalls should return minimum 1 minute."""
        assessment = TaskAssessment(
            description="Negative toolcalls",
            estimated_toolcalls=-5,
            requires_parallel=False,
            complexity_score=1,
        )

        duration = estimate_task_duration(assessment)

        assert duration == timedelta(minutes=1)

    def test_duration_override_used(self):
        """Duration override should be used when provided."""
        assessment = TaskAssessment(
            description="With override",
            estimated_toolcalls=5,
            requires_parallel=False,
            complexity_score=1,
            estimated_duration_override=timedelta(minutes=100),
        )

        duration = estimate_task_duration(assessment)

        assert duration == timedelta(minutes=100)

    def test_duration_override_minimum_enforced(self):
        """Duration override should respect minimum of 1 minute."""
        assessment = TaskAssessment(
            description="With small override",
            estimated_toolcalls=5,
            requires_parallel=False,
            complexity_score=1,
            estimated_duration_override=timedelta(seconds=30),
        )

        duration = estimate_task_duration(assessment)

        assert duration == timedelta(minutes=1)


class TestShouldEscalateToOrchestrator:
    """Tests for the should_escalate_to_orchestrator function."""

    def test_returns_false_for_simple_task(self):
        """Simple task should not escalate."""
        assessment = TaskAssessment(
            description="Simple fix",
            estimated_toolcalls=1,
            requires_parallel=False,
            complexity_score=1,
        )

        result = should_escalate_to_orchestrator(assessment)

        assert result is False

    def test_returns_true_for_high_toolcalls(self):
        """High toolcall count should escalate."""
        assessment = TaskAssessment(
            description="Complex task",
            estimated_toolcalls=5,
            requires_parallel=False,
            complexity_score=1,
        )

        result = should_escalate_to_orchestrator(assessment)

        assert result is True

    def test_returns_true_for_parallel(self):
        """Parallel requirement should escalate."""
        assessment = TaskAssessment(
            description="Parallel task",
            estimated_toolcalls=1,
            requires_parallel=True,
            complexity_score=1,
        )

        result = should_escalate_to_orchestrator(assessment)

        assert result is True

    def test_returns_true_for_long_duration(self):
        """Long duration should escalate."""
        assessment = TaskAssessment(
            description="Long task",
            estimated_toolcalls=1,
            requires_parallel=False,
            complexity_score=1,
            estimated_duration_override=timedelta(minutes=45),
        )

        result = should_escalate_to_orchestrator(assessment)

        assert result is True

    def test_returns_false_at_exactly_three_toolcalls(self):
        """Exactly 3 toolcalls should escalate (>2 threshold)."""
        assessment = TaskAssessment(
            description="At threshold",
            estimated_toolcalls=3,
            requires_parallel=False,
            complexity_score=1,
        )

        result = should_escalate_to_orchestrator(assessment)

        assert result is True


class TestSkillContracts:
    """Tests for skill contract rendering."""

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

        for skill_name, contract in SKILL_CONTRACTS.items():
            for field in required_fields:
                assert field in contract, f"{skill_name} missing {field}"


class TestRoutingEdgeCases:
    """Tests for routing edge cases and boundary conditions."""

    def test_large_toolcall_count(self):
        """Very large toolcall counts should still work."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Massive refactoring",
            estimated_toolcalls=100,
            requires_parallel=False,
            complexity_score=10,
        )

        decision = router.route_task(assessment)

        assert decision.action == "escalate"
        assert decision.target == "oe-orchestrator"

    def test_complexity_score_does_not_affect_routing(self):
        """Complexity score should not directly affect routing decision."""
        router = SkillRouter()

        low_complexity = TaskAssessment(
            description="Simple but many toolcalls",
            estimated_toolcalls=5,
            requires_parallel=False,
            complexity_score=1,
        )

        high_complexity = TaskAssessment(
            description="Complex but few toolcalls",
            estimated_toolcalls=1,
            requires_parallel=False,
            complexity_score=10,
        )

        low_decision = router.route_task(low_complexity)
        high_decision = router.route_task(high_complexity)

        # Low complexity but many toolcalls should escalate
        assert low_decision.action == "escalate"
        # High complexity but few toolcalls should route to main
        assert high_decision.action == "route"

    def test_parallel_with_few_toolcalls_escalates(self):
        """Parallel requirement escalates even with few toolcalls."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Parallel with 1 toolcall",
            estimated_toolcalls=1,
            requires_parallel=True,
            complexity_score=1,
        )

        decision = router.route_task(assessment)

        assert decision.action == "escalate"

    def test_duration_included_in_decision(self):
        """Estimated duration should be included in routing decision."""
        router = SkillRouter()
        assessment = TaskAssessment(
            description="Task with duration",
            estimated_toolcalls=2,
            requires_parallel=False,
            complexity_score=1,
        )

        decision = router.route_task(assessment)

        assert decision.estimated_duration is not None
        assert isinstance(decision.estimated_duration, timedelta)


class TestSkillRouterConfiguration:
    """Tests for SkillRouter configuration and initialization."""

    def test_default_initialization(self):
        """SkillRouter should initialize with default values."""
        router = SkillRouter()

        # Should be able to route tasks
        assessment = TaskAssessment(
            description="Test",
            estimated_toolcalls=1,
            requires_parallel=False,
            complexity_score=1,
        )
        decision = router.route_task(assessment)

        assert decision is not None

    def test_multiple_routing_calls(self):
        """Router should handle multiple routing calls."""
        router = SkillRouter()

        decisions = []
        for toolcalls in range(1, 6):
            assessment = TaskAssessment(
                description=f"Task with {toolcalls} toolcalls",
                estimated_toolcalls=toolcalls,
                requires_parallel=False,
                complexity_score=1,
            )
            decision = router.route_task(assessment)
            decisions.append(decision)

        # First 2 should route to main
        assert decisions[0].target == "main"
        assert decisions[1].target == "main"
        # Rest should escalate
        assert decisions[2].target == "oe-orchestrator"
        assert decisions[3].target == "oe-orchestrator"
        assert decisions[4].target == "oe-orchestrator"
