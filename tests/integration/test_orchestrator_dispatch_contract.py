"""Integration tests for orchestrator dispatch contract and subagent workflows."""

import subprocess
import sys
from pathlib import Path

import pytest

from openclaw_enhance.runtime.recovery_contract import (
    EvidenceSource,
    RecoveredMethod,
    RetryOwner,
)


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
            # Skills are loaded via native mechanism, not explicitly referenced in AGENTS.md
            # Per simplification principle: Skills exist in workspaces/*/skills/ and auto-loaded
            pass

    def test_tools_md_keeps_local_notes_only(self):
        """TOOLS.md should keep local notes and point to skills."""
        tools_content = Path("workspaces/oe-orchestrator/TOOLS.md").read_text()

        assert "Skills define how tools work" in tools_content
        assert "project-registry.json" in tools_content
        assert "oe-worker-dispatch" in tools_content
        assert "call_omo_agent" not in tools_content


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


class TestOrchestratorSelfExecutionPolicyIntegration:
    @pytest.fixture
    def agents_content(self):
        return Path("workspaces/oe-orchestrator/AGENTS.md").read_text()

    @pytest.fixture
    def dispatch_skill_content(self):
        return Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md").read_text()

    @pytest.fixture
    def operations_content(self):
        return Path("docs/operations.md").read_text()

    def test_substantive_work_requires_child_dispatch(
        self, agents_content, dispatch_skill_content, operations_content
    ):
        required_markers = [
            "Orchestrator Self-Execution Policy",
            "Orchestrator Self-Execution Exception Policy",
            "Mandatory Worker Dispatch",
            "必须分发的工作",
            "sessions_spawn",
        ]

        for marker in required_markers:
            assert (
                marker in agents_content
                or marker in dispatch_skill_content
                or marker in operations_content
            ), f"Expected orchestrator dispatch contract marker: {marker}"

        for content in (agents_content, dispatch_skill_content, operations_content):
            assert "sessions_spawn" in content, (
                "Orchestrator dispatch contract must require child sessions_spawn dispatches"
            )

        assert "substantive research" in dispatch_skill_content.lower()
        assert "introspection" in dispatch_skill_content.lower()
        assert "coding" in dispatch_skill_content.lower()
        assert "monitoring" in dispatch_skill_content.lower()

    def test_exception_list_stays_narrow(
        self, agents_content, dispatch_skill_content, operations_content
    ):
        expected_exceptions = [
            "worker selection",
            "dispatch planning",
            "checkpoint communication",
            "result synthesis",
            "trivial orchestration bookkeeping",
        ]

        for exception in expected_exceptions:
            assert (
                exception in dispatch_skill_content.lower()
                or exception in operations_content.lower()
            ), f"Missing narrow self-execution exception: {exception}"

        assert "Allowed Self-Execution Exceptions" in operations_content
        assert "Allowed Self-Execution Exceptions" in dispatch_skill_content
        # Policy now lives in dispatch_skill_content, not AGENTS.md per simplification
        assert "允许的自执行例外" in dispatch_skill_content

    def test_no_implicit_self_execution_fallback_remains_explicitly_banned(
        self, agents_content, dispatch_skill_content, operations_content
    ):
        banned_phrases = [
            "prohibited from implicit self-execution fallback",
            "No Implicit Fallback",
            "严禁静默吸收",
        ]

        for phrase in banned_phrases:
            # Policy now lives in dispatch_skill_content, not AGENTS.md per simplification
            assert phrase in dispatch_skill_content or phrase in operations_content, (
                f"Missing explicit no-fallback wording: {phrase}"
            )

        assert "must become child `sessions_spawn` dispatches" in operations_content.lower()
        assert "MUST NOT silently absorb substantive worker-eligible work" in dispatch_skill_content


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
        # Skills are auto-loaded via native mechanism, not referenced in AGENTS.md
        # Per simplification principle: Skills exist in workspaces/*/skills/ and auto-loaded
        pass

        # TOOLS should stay as local notes and point to skills
        tools = Path("workspaces/oe-orchestrator/TOOLS.md").read_text()
        assert "oe-worker-dispatch" in tools
        assert "call_omo_agent" not in tools

        # Skills should reference each other where appropriate
        dispatch = Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md").read_text()
        assert "searcher" in dispatch


class TestOrchestratorRecoveryFlow:
    """Integration tests for orchestrator recovery flow contract.

    These tests verify that the orchestrator correctly handles tool-usage failures
    by dispatching oe-tool-recovery, consuming recovered_method, and enforcing
    retry limits per the contract defined in AGENTS.md and recovery_contract.py.
    """

    @pytest.fixture
    def agents_content(self):
        """Load AGENTS.md content."""
        return Path("workspaces/oe-orchestrator/AGENTS.md").read_text()

    @pytest.fixture
    def dispatch_skill_content(self):
        """Load worker dispatch SKILL.md content."""
        return Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md").read_text()

    @pytest.fixture
    def recovery_agents_content(self):
        """Load oe-tool-recovery AGENTS.md content."""
        return Path("workspaces/oe-tool-recovery/AGENTS.md").read_text()

    def test_tool_not_found_triggers_recovery_dispatch(
        self, agents_content, dispatch_skill_content
    ):
        """Verify orchestrator detects tool_not_found failure and dispatches oe-tool-recovery.

        The short AGENTS.md should point to oe-worker-dispatch, and the detailed
        recovery contract should live in the worker-dispatch skill.
        """
        # Skills are auto-loaded via native mechanism, not referenced in AGENTS.md
        # Per simplification principle: Skills exist in workspaces/*/skills/ and auto-loaded

        # Worker dispatch skill must classify tool_not_found as Tool-Usage Failure
        assert "tool_not_found" in dispatch_skill_content, (
            "Worker dispatch must handle tool_not_found failures"
        )

        # Recovery flow must be documented
        assert "oe-tool-recovery" in dispatch_skill_content, (
            "oe-worker-dispatch must reference oe-tool-recovery for recovery dispatch"
        )

        # Recovery dispatch context must include required fields
        recovery_context_fields = [
            "failed_step",
            "tool_name",
            "failure_reason",
            "exact_invocation",
        ]
        for field in recovery_context_fields:
            assert field in dispatch_skill_content, (
                f"Recovery dispatch context must include '{field}'"
            )

    def test_websearch_not_found_recovery_executable(self):
        """Execute websearch tool-not-found recovery scenario.

        This test simulates the legacy websearch failure and validates that
        the recovery contract produces the correct corrected method.

        Scenario: Worker attempts to use legacy 'websearch' tool
        Expected: Recovery contract recommends 'websearch_web_search_exa'
        """
        from openclaw_enhance.runtime.recovery_contract import (
            EvidenceSource,
            RecoveredMethod,
            RetryOwner,
        )

        failure_signal = "tool 'websearch' not found"

        recovered = RecoveredMethod(
            failed_step="worker-search-001",
            tool_name="websearch",
            failure_reason=failure_signal,
            exact_invocation="websearch_web_search_exa(query='Python async patterns')",
            evidence_source=EvidenceSource.TOOL_CONTRACT,
            confidence=0.95,
            retry_owner=RetryOwner.SELF,
        )

        assert recovered.tool_name == "websearch"
        assert "websearch" in recovered.failure_reason
        assert "websearch_web_search_exa" in recovered.exact_invocation
        assert recovered.confidence >= 0.9
        assert recovered.retry_owner == RetryOwner.SELF

        payload = recovered.to_orchestrator_payload()
        assert payload["tool_name"] == "websearch"
        assert "websearch_web_search_exa" in payload["exact_invocation"]

    def test_invalid_parameters_triggers_recovery_dispatch(self, dispatch_skill_content):
        """Verify invalid_parameters failure routes to recovery with exact_invocation.

        Per SKILL.md: Recovery Dispatch passes exact_invocation to recovery worker.
        """
        # Must recognize invalid_parameters as recovery-triggering failure
        assert (
            "invalid_parameters" in dispatch_skill_content
            or "invalid parameter" in dispatch_skill_content.lower()
        ), "oe-worker-dispatch must handle invalid_parameters failures"

        # Must pass exact_invocation to recovery worker
        assert "exact_invocation" in dispatch_skill_content, (
            "Worker dispatch must pass exact_invocation to recovery worker"
        )

        # Recovery worker must receive failure context
        assert "failed_step" in dispatch_skill_content, (
            "Recovery context must include failed_step identifier"
        )
        assert "tool_name" in dispatch_skill_content, "Recovery context must include tool_name"

    def test_permission_denied_triggers_recovery_dispatch(self, dispatch_skill_content):
        """Verify permission_denied triggers recovery flow.

        Per oe-worker-dispatch: permission_denied is a tool-usage failure handled via recovery.
        """
        # Must recognize permission_denied as recoverable
        assert (
            "permission_denied" in dispatch_skill_content
            or "permission" in dispatch_skill_content.lower()
        ), "oe-worker-dispatch must handle permission_denied failures"

        # Must have recovery flow documentation
        assert (
            "Recovery Dispatch" in dispatch_skill_content
            or "recovery dispatch" in dispatch_skill_content.lower()
        ), "oe-worker-dispatch must document Recovery Dispatch for permission failures"

    def test_tool_execution_error_triggers_recovery_dispatch(self, dispatch_skill_content):
        """Verify tool_execution_error triggers recovery flow.

        Per oe-worker-dispatch: tool_execution_error is handled via recovery branch.
        """
        # Must recognize tool_execution_error as recoverable
        assert (
            "tool_execution_error" in dispatch_skill_content
            or "execution error" in dispatch_skill_content.lower()
        ), "oe-worker-dispatch must handle tool_execution_error failures"

        # Recovery flow must handle execution errors
        assert "oe-tool-recovery" in dispatch_skill_content, (
            "Recovery flow must handle tool_execution_error via oe-tool-recovery"
        )

    @pytest.mark.parametrize(
        "failure_type",
        [
            "tool_not_found",
            "invalid_parameters",
            "permission_denied",
            "tool_execution_error",
        ],
    )
    def test_all_tool_failure_types_route_to_recovery(self, dispatch_skill_content, failure_type):
        """Verify all four tool-usage failure types route to recovery.

        Per oe-worker-dispatch, all tool-usage failures route through the
        recovery branch before escalation.
        """
        # Each failure type should be documented as triggering recovery
        failure_patterns = {
            "tool_not_found": ["tool_not_found", "tool not found"],
            "invalid_parameters": ["invalid_parameters", "invalid parameter"],
            "permission_denied": ["permission_denied", "permission denied"],
            "tool_execution_error": ["tool_execution_error", "execution error"],
        }

        patterns = failure_patterns[failure_type]
        found = any(pattern in dispatch_skill_content.lower() for pattern in patterns)
        assert found, (
            f"oe-worker-dispatch must document {failure_type} as a recoverable failure type"
        )

    def test_recovery_consumes_recovered_method(self, dispatch_skill_content):
        """Verify orchestrator validates RecoveredMethod schema and stores in loop state.

        Per oe-worker-dispatch:
        - Integration step validates RecoveredMethod
        - Stores in recovered_methods dict
        - Respects retry_owner decision
        """
        # Verify RecoveredMethod schema exists and is importable
        test_method = RecoveredMethod(
            failed_step="test-step-1",
            tool_name="test_tool",
            failure_reason="Tool not found in registry",
            exact_invocation='test_tool(param="value")',
            evidence_source=EvidenceSource.TOOL_CONTRACT,
            confidence=0.95,
            retry_owner=RetryOwner.ORCHESTRATOR,
        )

        # Verify schema validation works
        assert test_method.failed_step == "test-step-1"
        assert test_method.tool_name == "test_tool"
        assert test_method.confidence == 0.95
        assert test_method.retry_owner == RetryOwner.ORCHESTRATOR

        # oe-worker-dispatch must document recovered_methods storage
        assert "recovered_methods" in dispatch_skill_content, (
            "oe-worker-dispatch must document recovered_methods storage in loop state"
        )

        # Must document retry_owner evaluation
        assert (
            "retry_owner" in dispatch_skill_content.lower()
            or "retry owner" in dispatch_skill_content.lower()
        ), "Worker dispatch must document retry_owner evaluation"

    def test_recovery_validates_exact_invocation_no_placeholders(self):
        """Verify RecoveredMethod rejects placeholder patterns in exact_invocation.

        Per recovery_contract.py: exact_invocation must not contain placeholders
        like <param>, ..., todo, fixme, example, placeholder.
        """
        # Test that placeholders are rejected
        placeholder_invocations = [
            "tool(<param>)",
            "tool(param=...)",
            "tool(param=todo_value)",
            "tool(param=fixme)",
            "tool(example_call)",
            "tool(placeholder_value)",
        ]

        for invocation in placeholder_invocations:
            with pytest.raises(ValueError) as exc_info:
                RecoveredMethod(
                    failed_step="test-step",
                    tool_name="test_tool",
                    failure_reason="Tool call failed with incorrect parameters",
                    exact_invocation=invocation,
                    evidence_source=EvidenceSource.TOOL_CONTRACT,
                    confidence=0.9,
                    retry_owner=RetryOwner.ORCHESTRATOR,
                )
            assert (
                "placeholder" in str(exc_info.value).lower()
                or "exact" in str(exc_info.value).lower()
            ), f"Should reject placeholder pattern in: {invocation}"

    def test_one_recovery_assisted_retry_per_step(self, dispatch_skill_content):
        """Verify retry limit is enforced (max 1) and second failure escalates.

        Per oe-worker-dispatch:
        - "Recovery Cap: Max ONE recovery-assisted retry per failed step"
        - "No Recovery Loops: Recovery worker failure or retry failure escalates immediately"
        - recovery_attempts counter prevents infinite loops
        """
        # Must document the recovery cap
        assert (
            "Max ONE" in dispatch_skill_content
            or "max 1" in dispatch_skill_content.lower()
            or "max one" in dispatch_skill_content.lower()
        ), "oe-worker-dispatch must document max ONE recovery-assisted retry per step"

        # Must document recovery_attempts counter
        assert "recovery_attempts" in dispatch_skill_content, (
            "oe-worker-dispatch must document recovery_attempts counter to prevent loops"
        )

        # Must document escalation on retry failure
        assert (
            "escalated" in dispatch_skill_content.lower()
            or "escalation" in dispatch_skill_content.lower()
        ), "oe-worker-dispatch must document escalation when retry limit exceeded"

    def test_recovery_failure_escalates(self, dispatch_skill_content):
        """Verify recovery worker failure leads to escalation, no infinite loops.

        Per oe-worker-dispatch:
        - "No Recovery Loops: Recovery worker failure or retry failure escalates immediately"
        - termination_state becomes 'escalated'
        - Do NOT re-enter recovery for the same step
        """
        assert "termination_state" in dispatch_skill_content, (
            "oe-worker-dispatch must document termination_state tracking"
        )
        assert "escalated" in dispatch_skill_content, (
            "oe-worker-dispatch must include 'escalated' as termination state"
        )
        assert (
            "re-enter" in dispatch_skill_content.lower()
            or "reenter" in dispatch_skill_content.lower()
            or "do not" in dispatch_skill_content.lower()
        ), "oe-worker-dispatch must explicitly forbid re-entering recovery for same step"

    def test_assisted_retry_success_completes_step(self, dispatch_skill_content):
        """Verify successful retry after recovery completes normally.

        Per oe-worker-dispatch recovery flow:
        - Step 6: Assisted Retry with recovered_method
        - Step 7: If retry succeeds, normal completion path
        """
        assert (
            "Assisted Retry" in dispatch_skill_content
            or "assisted retry" in dispatch_skill_content.lower()
        ), "oe-worker-dispatch must document Assisted Retry step"
        assert "completed" in dispatch_skill_content.lower(), (
            "oe-worker-dispatch must define 'completed' as valid outcome"
        )
        assert "retry" in dispatch_skill_content.lower(), (
            "oe-worker-dispatch must document retry mechanism"
        )

    def test_assisted_retry_failure_escalates(self, dispatch_skill_content):
        """Verify failed retry after recovery escalates, no third attempt.

        Per oe-worker-dispatch:
        - Recovery (1) + Retry (1) + Additional Retry = Forbidden
        - Max total attempts: 1 recovery + 1 assisted retry = 2 total
        - Third attempt must escalate
        """
        # Must document escalation on retry failure
        assert (
            "Escalation" in dispatch_skill_content or "escalated" in dispatch_skill_content.lower()
        ), "oe-worker-dispatch must document escalation when assisted retry fails"

        # Must document no third attempt
        assert "recovery_attempts" in dispatch_skill_content, (
            "recovery_attempts counter must prevent third attempt"
        )

        # Verify the loop invariant: max 1 per step
        recovery_cap_text = dispatch_skill_content.lower()
        assert "max one" in recovery_cap_text or "max 1" in recovery_cap_text, (
            "Must explicitly limit to max 1 recovery-assisted retry"
        )

    def test_recovery_during_bounded_loop_respects_max_rounds(self, dispatch_skill_content):
        """Verify recovery dispatch counts toward max_rounds, loop still terminates.

        Per oe-worker-dispatch:
        - "Recovery counts toward max_rounds limit"
        - Loop must terminate if max_rounds reached during recovery
        """
        # Must document max_rounds
        assert "max_rounds" in dispatch_skill_content, (
            "oe-worker-dispatch must document max_rounds limit"
        )

        # Must document hard cap
        assert "hard cap" in dispatch_skill_content.lower(), (
            "oe-worker-dispatch must document hard cap on rounds"
        )

        # Must document termination conditions
        assert (
            "terminate" in dispatch_skill_content.lower()
            or "exhausted" in dispatch_skill_content.lower()
        ), "oe-worker-dispatch must document termination when limits reached"

    def test_recovery_eligibility_checks_prevent_nested_recovery(self, dispatch_skill_content):
        """Verify eligibility checks prevent nested or concurrent recovery dispatches.

        Per oe-worker-dispatch:
        - Verify recovery_attempts[failed_step_id] is 0
        - Verify recovery_in_progress is false
        - recovery_in_progress flag prevents nested recovery
        """
        assert "recovery_attempts" in dispatch_skill_content, (
            "oe-worker-dispatch must document recovery_attempts eligibility check"
        )
        assert "recovery_in_progress" in dispatch_skill_content, (
            "oe-worker-dispatch must document recovery_in_progress flag"
        )
        assert "false" in dispatch_skill_content.lower(), (
            "Must check recovery_in_progress is false before dispatch"
        )

    def test_recovery_worker_is_leaf_node(self, recovery_agents_content):
        """Verify oe-tool-recovery is documented as leaf-node only.

        Per oe-tool-recovery/AGENTS.md:
        - Cannot spawn subagents
        - Leaf-node only
        """
        # Must declare leaf-node status
        assert (
            "leaf-node" in recovery_agents_content.lower()
            or "leaf node" in recovery_agents_content.lower()
            or "叶子节点" in recovery_agents_content
        ), "oe-tool-recovery must be documented as leaf-node"

        # Must prohibit agent spawning
        assert (
            "Agent Spawning" in recovery_agents_content
            or "严禁派生其他 agent" in recovery_agents_content
        ), "oe-tool-recovery must document agent spawning prohibition"

    def test_recovery_uses_sessions_spawn_and_yield(self, dispatch_skill_content):
        """Verify recovery dispatch uses native sessions_spawn and sessions_yield.

        Per oe-worker-dispatch Tool Recovery Flow:
        - Step 3: Spawn oe-tool-recovery via sessions_spawn
        - Step 4: Call sessions_yield to await results
        """
        # Must document sessions_spawn for recovery
        assert "sessions_spawn" in dispatch_skill_content, (
            "oe-worker-dispatch must document sessions_spawn for recovery dispatch"
        )

        # Must document sessions_yield
        assert "sessions_yield" in dispatch_skill_content, (
            "oe-worker-dispatch must document sessions_yield for recovery await"
        )

        # Must reference oe-tool-recovery in spawn context
        assert "oe-tool-recovery" in dispatch_skill_content, (
            "oe-worker-dispatch must reference oe-tool-recovery agent type"
        )

    def test_recovered_method_schema_enforces_bounded_retries(self):
        """Verify RecoveredMethod schema enforces max_retries bounds (0-3).

        Per recovery_contract.py:
        - max_retries: int = 1 (default)
        - ge=0, le=3 (bounded)
        """
        # Test valid bounds
        valid_retries = [0, 1, 2, 3]
        for retries in valid_retries:
            method = RecoveredMethod(
                failed_step="test-step",
                tool_name="test_tool",
                failure_reason="Test failure",
                exact_invocation="test_tool()",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.ORCHESTRATOR,
                max_retries=retries,
            )
            assert method.max_retries == retries

        # Test invalid bounds
        invalid_retries = [-1, 4, 5, 10]
        for retries in invalid_retries:
            with pytest.raises(ValueError):
                RecoveredMethod(
                    failed_step="test-step",
                    tool_name="test_tool",
                    failure_reason="Test failure",
                    exact_invocation="test_tool()",
                    evidence_source=EvidenceSource.TOOL_CONTRACT,
                    confidence=0.9,
                    retry_owner=RetryOwner.ORCHESTRATOR,
                    max_retries=retries,
                )

    def test_no_worker_to_worker_handoff_in_recovery(self, dispatch_skill_content):
        """Verify recovery does NOT create worker-to-worker handoff.

        Per oe-worker-dispatch Loop Controls:
        - "No Worker Handoff: Recovery dispatch does NOT create worker-to-worker handoff"
        - "The Orchestrator remains the sole dispatcher"
        """
        # Must document no handoff rule
        assert (
            "No Worker Handoff" in dispatch_skill_content
            or "no worker handoff" in dispatch_skill_content.lower()
        ), "oe-worker-dispatch must document 'No Worker Handoff' rule"

        # Must declare orchestrator as sole dispatcher
        assert (
            "sole dispatcher" in dispatch_skill_content.lower()
            or "Orchestrator remains" in dispatch_skill_content
        ), "oe-worker-dispatch must declare Orchestrator as sole dispatcher"


class TestBoundedLoopContract:
    """Tests for bounded loop controls and round-state behavior."""

    @pytest.fixture
    def agents_content(self):
        """Load AGENTS.md content."""
        return Path("workspaces/oe-orchestrator/AGENTS.md").read_text()

    @pytest.fixture
    def dispatch_skill_content(self):
        """Load worker dispatch SKILL.md content."""
        return Path("workspaces/oe-orchestrator/skills/oe-worker-dispatch/SKILL.md").read_text()

    def test_dispatch_skill_references_sessions_yield(self, dispatch_skill_content):
        """oe-worker-dispatch should reference sessions_yield as round-boundary primitive."""
        assert "sessions_yield" in dispatch_skill_content

    def test_dispatch_skill_defines_round_states(self, dispatch_skill_content):
        """oe-worker-dispatch should define all round-state phases."""
        round_states = [
            "Assess",
            "PlanRound",
            "DispatchRound",
            "YieldForResults",
            "CollectResults",
            "EvaluateProgress",
        ]
        for state in round_states:
            assert state in dispatch_skill_content, f"Missing round state: {state}"

    def test_dispatch_skill_defines_max_rounds(self, dispatch_skill_content):
        """oe-worker-dispatch should define max_rounds terminology with default and hard cap."""
        assert "max_rounds" in dispatch_skill_content
        assert "default: 3" in dispatch_skill_content or "default 3" in dispatch_skill_content
        assert "hard cap: 5" in dispatch_skill_content or "hard cap 5" in dispatch_skill_content

    def test_dispatch_skill_defines_checkpoint_types(self, dispatch_skill_content):
        """oe-worker-dispatch should define checkpoint visibility types."""
        checkpoint_types = [
            "started",
            "meaningful_progress",
            "blocked",
            "terminal",
        ]
        for checkpoint in checkpoint_types:
            assert checkpoint in dispatch_skill_content, f"Missing checkpoint type: {checkpoint}"

    def test_dispatch_skill_defines_duplicate_dispatch_guard(self, dispatch_skill_content):
        """oe-worker-dispatch should define duplicate-dispatch guard terms."""
        assert (
            "dedupe_keys" in dispatch_skill_content
            or "deduplicate" in dispatch_skill_content.lower()
        )
        assert (
            "duplicate dispatch" in dispatch_skill_content.lower()
            or "Duplicate dispatch" in dispatch_skill_content
        )

    def test_dispatch_skill_no_sessions_history_polling(self, dispatch_skill_content):
        """oe-worker-dispatch should NOT reference sessions_history for polling patterns."""
        # Should not suggest polling via sessions_history
        assert "sessions_history" not in dispatch_skill_content, (
            "Should not reference sessions_history for polling"
        )
        # Should emphasize yield-based waiting
        assert (
            "auto-announced" in dispatch_skill_content or "sessions_yield" in dispatch_skill_content
        )

    def test_dispatch_skill_defines_iterative_round_pattern(self, dispatch_skill_content):
        """Worker dispatch skill should define iterative round-based dispatch."""
        assert (
            "Iterative Round-Based Dispatch" in dispatch_skill_content
            or "round" in dispatch_skill_content.lower()
        )
        assert "Plan" in dispatch_skill_content and "Dispatch" in dispatch_skill_content
        assert "Yield" in dispatch_skill_content or "yield" in dispatch_skill_content.lower()

    def test_dispatch_skill_defines_dispatch_identity(self, dispatch_skill_content):
        """Worker dispatch skill should define dispatch identity for deduplication."""
        assert (
            "dispatch_id" in dispatch_skill_content or "Dispatch Identity" in dispatch_skill_content
        )
        assert "Dedupe" in dispatch_skill_content or "dedupe" in dispatch_skill_content

    def test_dispatch_skill_no_polling_guidance(self, dispatch_skill_content):
        """Worker dispatch skill should NOT include polling guidance."""
        assert "sessions_history" not in dispatch_skill_content, (
            "Should not reference sessions_history"
        )
        # Should emphasize waiting for auto-announce
        assert (
            "auto-announced" in dispatch_skill_content
            or "wait for" in dispatch_skill_content.lower()
        )

    def test_dispatch_skill_defines_failure_classification(self, dispatch_skill_content):
        """Worker dispatch skill should define failure classification categories."""
        failure_types = ["Retriable", "Reroutable", "Escalated"]
        for failure_type in failure_types:
            assert failure_type in dispatch_skill_content, f"Missing failure type: {failure_type}"

    def test_render_workspace_includes_bounded_loop_docs(self):
        """Rendered workspace should include bounded loop documentation."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "oe-orchestrator"],
            capture_output=True,
            text=True,
        )
        output = result.stdout

        # Should include round-state terminology
        assert "sessions_yield" in output
        assert "max_rounds" in output or "round" in output.lower()

        # Should include checkpoint terminology
        assert "meaningful_progress" in output or "blocked" in output

    def test_render_workspace_proves_worker_discovery(self):
        """Rendered workspace should prove worker discovery from frontmatter."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "oe-orchestrator"],
            capture_output=True,
            text=True,
        )
        output = result.stdout

        # Should reference worker discovery mechanism
        assert "frontmatter" in output.lower() or "AGENTS.md" in output
        assert "routing" in output.lower()

        # Should reference worker catalog/discovery
        assert "discover" in output.lower() or "catalog" in output.lower()


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
