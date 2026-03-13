"""Integration tests for main session skill synchronization."""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from openclaw_enhance.skills_catalog import (
    SkillRouter,
    TaskAssessment,
    RoutingDecision,
    render_skill_contract,
    sync_timeout_state,
    SKILLS_REGISTRY,
)
from openclaw_enhance.runtime.schema import RuntimeState
from openclaw_enhance.paths import managed_root


class TestSkillRoutingIntegration:
    """Integration tests for skill routing end-to-end flow."""

    def test_simple_task_routing_flow(self):
        """End-to-end test: simple task stays in main."""
        router = SkillRouter()

        # User asks for a simple file edit
        assessment = TaskAssessment(
            description="Fix typo in README",
            estimated_toolcalls=1,
            requires_parallel=False,
            complexity_score=1,
        )

        decision = router.route_task(assessment)

        assert decision.action == "route"
        assert decision.target == "main"
        assert decision.estimated_duration <= timedelta(minutes=5)

    def test_complex_task_escalation_flow(self):
        """End-to-end test: complex task escalates to orchestrator."""
        router = SkillRouter()

        # User asks for multi-file refactor with tests
        assessment = TaskAssessment(
            description="Refactor auth module and add comprehensive tests",
            estimated_toolcalls=8,
            requires_parallel=False,
            complexity_score=4,
        )

        decision = router.route_task(assessment)

        assert decision.action == "escalate"
        assert decision.target == "oe-orchestrator"
        assert decision.estimated_duration >= timedelta(minutes=30)

    def test_parallel_task_escalation_flow(self):
        """End-to-end test: parallel work escalates to orchestrator."""
        router = SkillRouter()

        # Task that can benefit from parallel agents
        assessment = TaskAssessment(
            description="Update all API endpoints to v2 in parallel",
            estimated_toolcalls=6,
            requires_parallel=True,
            complexity_score=3,
        )

        decision = router.route_task(assessment)

        assert decision.action == "escalate"
        assert decision.target == "oe-orchestrator"
        # Reason should mention why it escalated (toolcalls or parallel)
        assert "toolcall" in decision.reason.lower() or "parallel" in decision.reason.lower()


class TestSkillContractRenderingIntegration:
    """Integration tests for skill contract rendering."""

    def test_all_skills_render_successfully(self):
        """All registered skills should render without errors."""
        for skill in SKILLS_REGISTRY:
            contract = render_skill_contract(skill.name)
            assert contract is not None
            assert len(contract) > 0
            assert "---" in contract  # Has YAML frontmatter
            assert skill.name in contract

    def test_rendered_contracts_are_valid_markdown(self):
        """Rendered contracts should be valid markdown."""
        for skill in SKILLS_REGISTRY:
            contract = render_skill_contract(skill.name)
            # Basic markdown validation
            assert contract.startswith("---")  # YAML frontmatter
            assert "#" in contract or skill.description in contract  # Has content


class TestTimeoutStateSyncIntegration:
    """Integration tests for timeout state synchronization."""

    def test_sync_timeout_state_updates_runtime(self, tmp_path):
        """Timeout sync should update runtime state."""
        with patch("openclaw_enhance.paths.managed_root", return_value=tmp_path):
            runtime_state = RuntimeState()

            # Simulate a timeout event
            result = sync_timeout_state(
                session_id="test-session-123",
                task_description="Long running task",
                timeout_duration=timedelta(minutes=30),
                runtime_state=runtime_state,
            )

            assert result is not None
            assert result.get("synced") is True
            assert result.get("session_id") == "test-session-123"

    def test_sync_timeout_state_creates_backup(self, tmp_path):
        """Timeout sync should create state backup."""
        with patch("openclaw_enhance.paths.managed_root", return_value=tmp_path):
            runtime_state = RuntimeState()

            sync_timeout_state(
                session_id="test-session-456",
                task_description="Another task",
                timeout_duration=timedelta(minutes=15),
                runtime_state=runtime_state,
            )

            # Should update last_updated timestamp
            assert runtime_state.last_updated_utc is not None


class TestMainSessionWorkflowIntegration:
    """Integration tests simulating main session workflows."""

    def test_main_session_simple_query(self):
        """Simulate main session handling simple query."""
        router = SkillRouter()

        # Simple question that needs 1-2 tool calls
        assessment = TaskAssessment(
            description="What files are in the src directory?",
            estimated_toolcalls=1,
            requires_parallel=False,
            complexity_score=1,
        )

        decision = router.route_task(assessment)

        # Simple query stays in main
        assert decision.action == "route"
        assert decision.target == "main"

    def test_main_session_code_change(self):
        """Simulate main session handling code change request."""
        router = SkillRouter()

        # Code change requiring multiple files
        assessment = TaskAssessment(
            description="Add error handling to all API routes",
            estimated_toolcalls=5,
            requires_parallel=False,
            complexity_score=3,
        )

        decision = router.route_task(assessment)

        # Multi-file changes escalate to orchestrator
        assert decision.action == "escalate"
        assert decision.target == "oe-orchestrator"

    def test_main_session_research_task(self):
        """Simulate main session handling research task."""
        router = SkillRouter()

        # Research with multiple searches
        assessment = TaskAssessment(
            description="Research best practices for async Python patterns",
            estimated_toolcalls=4,
            requires_parallel=False,
            complexity_score=3,
        )

        decision = router.route_task(assessment)

        # Research tasks with many searches escalate
        assert decision.action == "escalate"


class TestOrchestratorEscalationIntegration:
    """Integration tests for orchestrator escalation paths."""

    def test_escalation_includes_eta(self):
        """Escalation should always include ETA estimation."""
        router = SkillRouter()

        assessment = TaskAssessment(
            description="Implement new feature",
            estimated_toolcalls=7,
            requires_parallel=False,
            complexity_score=4,
        )

        decision = router.route_task(assessment)

        assert decision.action == "escalate"
        assert decision.estimated_duration is not None
        assert isinstance(decision.estimated_duration, timedelta)

    def test_escalation_includes_reason(self):
        """Escalation should include clear reason."""
        router = SkillRouter()

        assessment = TaskAssessment(
            description="Complex task",
            estimated_toolcalls=5,
            requires_parallel=True,
            complexity_score=3,
        )

        decision = router.route_task(assessment)

        assert decision.action == "escalate"
        assert decision.reason is not None
        assert len(decision.reason) > 0

    def test_escalation_target_is_orchestrator(self):
        """Escalation target should always be oe-orchestrator."""
        router = SkillRouter()

        escalated_cases = [
            TaskAssessment("High toolcalls", 5, False, 3),
            TaskAssessment("Parallel", 2, True, 2),
            TaskAssessment("Long duration", 3, False, 3, timedelta(minutes=60)),
        ]

        for assessment in escalated_cases:
            decision = router.route_task(assessment)
            assert decision.target == "oe-orchestrator"


class TestSkillHeuristicsIntegration:
    """Integration tests for skill routing heuristics."""

    def test_toolcall_threshold_at_boundary(self):
        """Test routing at exactly the toolcall threshold."""
        router = SkillRouter()

        # At threshold (2 toolcalls) - stays local
        at_threshold = TaskAssessment(
            description="At threshold",
            estimated_toolcalls=2,
            requires_parallel=False,
            complexity_score=2,
        )
        decision = router.route_task(at_threshold)
        assert decision.action == "route"

        # Just above threshold - escalates
        above_threshold = TaskAssessment(
            description="Above threshold",
            estimated_toolcalls=3,
            requires_parallel=False,
            complexity_score=2,
        )
        decision = router.route_task(above_threshold)
        assert decision.action == "escalate"

    def test_parallel_overrides_toolcall_count(self):
        """Parallel requirement can escalate even with low toolcalls."""
        router = SkillRouter()

        assessment = TaskAssessment(
            description="Parallel with few toolcalls",
            estimated_toolcalls=1,
            requires_parallel=True,
            complexity_score=2,
        )

        decision = router.route_task(assessment)
        assert decision.action == "escalate"

    def test_duration_overrides_toolcall_count(self):
        """Long duration can escalate even with low toolcalls."""
        router = SkillRouter()

        assessment = TaskAssessment(
            description="Long but few toolcalls",
            estimated_toolcalls=2,
            requires_parallel=False,
            complexity_score=2,
            estimated_duration_override=timedelta(minutes=60),
        )

        decision = router.route_task(assessment)
        assert decision.action == "escalate"


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    def test_invalid_skill_name_raises(self):
        """Requesting unknown skill should raise clear error."""
        with pytest.raises(ValueError, match="Unknown skill"):
            render_skill_contract("nonexistent-skill-xyz")

    def test_router_handles_edge_cases(self):
        """Router should handle edge case assessments."""
        router = SkillRouter()

        # Very high toolcalls
        edge_cases = [
            TaskAssessment("", 0, False, 0),  # Empty
            TaskAssessment("Huge", 100, True, 10),  # Very large
            TaskAssessment("Negative", -1, False, -1),  # Negative (should handle gracefully)
        ]

        for assessment in edge_cases:
            # Should not raise
            decision = router.route_task(assessment)
            assert decision is not None
            assert decision.action in ["route", "escalate"]
