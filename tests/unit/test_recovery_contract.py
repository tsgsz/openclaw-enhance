"""Unit tests for recovery result contract.

Tests validate:
1. Required fields are enforced
2. Forbidden ambiguity patterns are rejected:
   - Missing retry owner
   - Unbounded retry counts
   - Free-form-only output (placeholders in exact_invocation)
3. Confidence bounds
4. Alternative methods limits
"""

import pytest
from pydantic import ValidationError

from openclaw_enhance.runtime.recovery_contract import (
    CONTRACT_VERSION,
    EvidenceSource,
    RecoveredMethod,
    RecoveryResult,
    RetryOwner,
    get_contract_version,
)


class TestRecoveredMethodRequiredFields:
    """Tests that all required fields must be present."""

    def test_valid_minimal_recovery(self):
        """Test creating a valid recovery with minimal required fields."""
        recovery = RecoveredMethod(
            failed_step="step-001-update-config",
            tool_name="Edit",
            failure_reason="Indentation mismatch in oldString parameter",
            exact_invocation=(
                "Edit(filePath='config.py', oldString='    db_url=\"old\"', "
                "newString='    db_url=\"new\"')"
            ),
            preconditions=["Read config.py to verify current indentation"],
            evidence_source=EvidenceSource.TOOL_CONTRACT,
            confidence=0.9,
            retry_owner=RetryOwner.SCRIPT_CODER,
        )
        assert recovery.failed_step == "step-001-update-config"
        assert recovery.tool_name == "Edit"
        assert recovery.confidence == 0.9

    def test_missing_failed_step(self):
        """Test that missing failed_step raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', ...)",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "failed_step" in str(exc_info.value)

    def test_missing_tool_name(self):
        """Test that missing tool_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', ...)",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "tool_name" in str(exc_info.value)

    def test_missing_failure_reason(self):
        """Test that missing failure_reason raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                exact_invocation="Edit(filePath='config.py', ...)",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "failure_reason" in str(exc_info.value)

    def test_missing_exact_invocation(self):
        """Test that missing exact_invocation raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "exact_invocation" in str(exc_info.value)

    def test_missing_evidence_source(self):
        """Test that missing evidence_source raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', ...)",
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "evidence_source" in str(exc_info.value)

    def test_missing_confidence(self):
        """Test that missing confidence raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', ...)",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "confidence" in str(exc_info.value)

    def test_missing_retry_owner(self):
        """Test that missing retry_owner raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', ...)",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
            )
        assert "retry_owner" in str(exc_info.value)


class TestForbiddenAmbiguity:
    """Tests for forbidden ambiguity patterns."""

    def test_placeholder_in_exact_invocation_angle_brackets(self):
        """Test that angle brackets in exact_invocation are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='<path>', oldString='<content>')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "placeholder" in str(exc_info.value).lower()

    def test_placeholder_in_exact_invocation_ellipsis(self):
        """Test that ellipsis (...) in exact_invocation are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', ...)",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "placeholder" in str(exc_info.value).lower()

    def test_placeholder_in_exact_invocation_todo(self):
        """Test that TODO in exact_invocation are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='TODO: get path')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "placeholder" in str(exc_info.value).lower()

    def test_placeholder_in_exact_invocation_fixme(self):
        """Test that FIXME in exact_invocation are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='FIXME: add path')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "placeholder" in str(exc_info.value).lower()

    def test_placeholder_in_exact_invocation_example(self):
        """Test that 'example' in exact_invocation are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='example.py')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "placeholder" in str(exc_info.value).lower()

    def test_unbounded_retry_count_zero(self):
        """Test that max_retries=0 is allowed (no retry)."""
        recovery = RecoveredMethod(
            failed_step="step-001",
            tool_name="Edit",
            failure_reason="Critical failure, no retry possible",
            exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
            evidence_source=EvidenceSource.ERROR_MESSAGE,
            confidence=0.95,
            retry_owner=RetryOwner.ORCHESTRATOR,
            max_retries=0,
        )
        assert recovery.max_retries == 0

    def test_unbounded_retry_count_above_max(self):
        """Test that max_retries > 3 is rejected (unbounded)."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
                max_retries=5,  # Above max of 3
            )
        assert "max_retries" in str(exc_info.value)

    def test_vague_failure_reason_unknown_error(self):
        """Test that vague 'unknown error' failure reason is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Unknown error occurred",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.5,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "vague" in str(exc_info.value).lower()

    def test_vague_failure_reason_something_wrong(self):
        """Test that vague 'something went wrong' failure reason is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Something went wrong",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.5,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "vague" in str(exc_info.value).lower()

    def test_vague_failure_reason_it_failed(self):
        """Test that vague 'it failed' failure reason is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="It failed",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.5,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "vague" in str(exc_info.value).lower()


class TestConfidenceBounds:
    """Tests for confidence score bounds."""

    def test_confidence_below_zero(self):
        """Test that confidence < 0.0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=-0.1,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "confidence" in str(exc_info.value)

    def test_confidence_above_one(self):
        """Test that confidence > 1.0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=1.5,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "confidence" in str(exc_info.value)

    def test_confidence_at_zero(self):
        """Test that confidence = 0.0 is allowed."""
        recovery = RecoveredMethod(
            failed_step="step-001",
            tool_name="Edit",
            failure_reason="Indentation mismatch",
            exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
            evidence_source=EvidenceSource.TOOL_CONTRACT,
            confidence=0.0,
            retry_owner=RetryOwner.ORCHESTRATOR,
        )
        assert recovery.confidence == 0.0

    def test_confidence_at_one(self):
        """Test that confidence = 1.0 is allowed."""
        recovery = RecoveredMethod(
            failed_step="step-001",
            tool_name="Edit",
            failure_reason="Indentation mismatch",
            exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
            evidence_source=EvidenceSource.SOURCE_CODE,
            confidence=1.0,
            retry_owner=RetryOwner.SCRIPT_CODER,
        )
        assert recovery.confidence == 1.0


class TestPreconditions:
    """Tests for preconditions field."""

    def test_empty_preconditions(self):
        """Test that empty preconditions list is allowed."""
        recovery = RecoveredMethod(
            failed_step="step-001",
            tool_name="Edit",
            failure_reason="Indentation mismatch",
            exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
            preconditions=[],
            evidence_source=EvidenceSource.TOOL_CONTRACT,
            confidence=0.9,
            retry_owner=RetryOwner.SCRIPT_CODER,
        )
        assert recovery.preconditions == []
        assert recovery.is_ready_for_retry() is True

    def test_preconditions_with_items(self):
        """Test that preconditions with items is allowed."""
        recovery = RecoveredMethod(
            failed_step="step-001",
            tool_name="Edit",
            failure_reason="Indentation mismatch",
            exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
            preconditions=["Read config.py", "Verify indentation"],
            evidence_source=EvidenceSource.TOOL_CONTRACT,
            confidence=0.9,
            retry_owner=RetryOwner.SCRIPT_CODER,
        )
        assert len(recovery.preconditions) == 2
        assert recovery.is_ready_for_retry() is False


class TestOptionalFields:
    """Tests for optional fields."""

    def test_fallback_tool_present(self):
        """Test that fallback_tool can be provided."""
        recovery = RecoveredMethod(
            failed_step="step-001",
            tool_name="Write",
            failure_reason="File exists and cannot be overwritten",
            exact_invocation="Write(filePath='/etc/config.txt', content='test')",
            evidence_source=EvidenceSource.ENVIRONMENT_INSPECTION,
            confidence=0.7,
            retry_owner=RetryOwner.SYSHELPER,
            fallback_tool="Edit",
        )
        assert recovery.fallback_tool == "Edit"

    def test_fallback_tool_absent(self):
        """Test that fallback_tool defaults to None."""
        recovery = RecoveredMethod(
            failed_step="step-001",
            tool_name="Edit",
            failure_reason="Indentation mismatch",
            exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
            evidence_source=EvidenceSource.TOOL_CONTRACT,
            confidence=0.9,
            retry_owner=RetryOwner.SCRIPT_CODER,
        )
        assert recovery.fallback_tool is None

    def test_required_inputs_present(self):
        """Test that required_inputs can be provided."""
        recovery = RecoveredMethod(
            failed_step="step-001",
            tool_name="Edit",
            failure_reason="Indentation mismatch",
            exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
            evidence_source=EvidenceSource.TOOL_CONTRACT,
            confidence=0.9,
            retry_owner=RetryOwner.SCRIPT_CODER,
            required_inputs=["Exact line 42 content", "Current indentation level"],
        )
        assert len(recovery.required_inputs) == 2


class TestRecoveryResult:
    """Tests for RecoveryResult container."""

    def test_valid_recovery_result(self):
        """Test creating a valid RecoveryResult."""
        method = RecoveredMethod(
            failed_step="step-001",
            tool_name="Edit",
            failure_reason="Indentation mismatch",
            exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
            evidence_source=EvidenceSource.TOOL_CONTRACT,
            confidence=0.9,
            retry_owner=RetryOwner.SCRIPT_CODER,
        )
        result = RecoveryResult(recovered_method=method)
        assert result.recovered_method == method
        assert result.requires_escalation is False

    def test_too_many_alternatives(self):
        """Test that more than 2 alternatives raises ValidationError."""
        method = RecoveredMethod(
            failed_step="step-001",
            tool_name="Edit",
            failure_reason="Indentation mismatch",
            exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
            evidence_source=EvidenceSource.TOOL_CONTRACT,
            confidence=0.9,
            retry_owner=RetryOwner.SCRIPT_CODER,
        )
        alternatives = [method, method, method]  # 3 alternatives

        with pytest.raises(ValidationError) as exc_info:
            RecoveryResult(
                recovered_method=method,
                alternative_methods=alternatives,
            )
        assert "decision paralysis" in str(exc_info.value).lower()

    def test_max_alternatives_allowed(self):
        """Test that exactly 2 alternatives is allowed."""
        method1 = RecoveredMethod(
            failed_step="step-001",
            tool_name="Edit",
            failure_reason="Indentation mismatch",
            exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
            evidence_source=EvidenceSource.TOOL_CONTRACT,
            confidence=0.9,
            retry_owner=RetryOwner.SCRIPT_CODER,
        )
        method2 = RecoveredMethod(
            failed_step="step-001-alt",
            tool_name="Write",
            failure_reason="Alternative approach",
            exact_invocation="Write(filePath='config.py', content='new')",
            evidence_source=EvidenceSource.DOCUMENTATION,
            confidence=0.7,
            retry_owner=RetryOwner.SCRIPT_CODER,
        )
        result = RecoveryResult(
            recovered_method=method1,
            alternative_methods=[method2],
        )
        assert len(result.alternative_methods) == 1


class TestContractVersion:
    """Tests for contract version."""

    def test_contract_version_constant(self):
        """Test that CONTRACT_VERSION is defined."""
        assert CONTRACT_VERSION == "1.0.0"

    def test_get_contract_version(self):
        """Test get_contract_version function."""
        assert get_contract_version() == "1.0.0"


class TestEvidenceSourceEnum:
    """Tests for EvidenceSource enum."""

    def test_all_evidence_sources(self):
        """Test that all expected evidence sources exist."""
        sources = [
            EvidenceSource.TOOL_CONTRACT,
            EvidenceSource.DOCUMENTATION,
            EvidenceSource.SOURCE_CODE,
            EvidenceSource.EXTERNAL_SEARCH,
            EvidenceSource.ENVIRONMENT_INSPECTION,
            EvidenceSource.ERROR_MESSAGE,
        ]
        assert len(sources) == 6


class TestRetryOwnerEnum:
    """Tests for RetryOwner enum."""

    def test_all_retry_owners(self):
        """Test that all expected retry owners exist."""
        owners = [
            RetryOwner.ORCHESTRATOR,
            RetryOwner.SCRIPT_CODER,
            RetryOwner.SEARCHER,
            RetryOwner.SYSHELPER,
            RetryOwner.SELF,
        ]
        assert len(owners) == 5


class TestValidation:
    """Tests for validation rules with 'validation' in names for filtering."""

    def test_validation_rejects_missing_required_fields(self):
        """Test that missing required fields are rejected by validation."""
        # Test multiple missing fields scenario
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                # missing tool_name
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "tool_name" in str(exc_info.value)

    def test_validation_rejects_invalid_retry_owner_enum(self):
        """Test that invalid enum values for retry_owner are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner="invalid_owner",  # Invalid enum value
            )
        assert "retry_owner" in str(exc_info.value)

    def test_validation_rejects_max_retries_above_bound(self):
        """Test that max_retries > 3 is rejected by bounds validation."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
                max_retries=5,  # Above bound of 3
            )
        assert "max_retries" in str(exc_info.value)

    def test_validation_rejects_confidence_outside_range(self):
        """Test that confidence outside 0-1 range is rejected."""
        # Test confidence below 0
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=-0.1,  # Below 0
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "confidence" in str(exc_info.value)

        # Test confidence above 1
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence=1.1,  # Above 1
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "confidence" in str(exc_info.value)

    def test_validation_rejects_invalid_evidence_source_enum(self):
        """Test that invalid enum values for evidence_source are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source="invalid_source",  # Invalid enum value
                confidence=0.9,
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "evidence_source" in str(exc_info.value)

    def test_validation_rejects_wrong_types(self):
        """Test that wrong types are rejected by validation."""
        # Test wrong type for confidence
        with pytest.raises(ValidationError) as exc_info:
            RecoveredMethod(
                failed_step="step-001",
                tool_name="Edit",
                failure_reason="Indentation mismatch",
                exact_invocation="Edit(filePath='config.py', oldString='x', newString='y')",
                evidence_source=EvidenceSource.TOOL_CONTRACT,
                confidence="high",  # Wrong type: string instead of number
                retry_owner=RetryOwner.SCRIPT_CODER,
            )
        assert "confidence" in str(exc_info.value)


class TestToOrchestratorPayload:
    """Tests for to_orchestrator_payload method."""

    def test_payload_conversion(self):
        """Test converting to orchestrator payload format."""
        recovery = RecoveredMethod(
            failed_step="step-001",
            tool_name="Edit",
            failure_reason="Indentation mismatch in oldString",
            exact_invocation="Edit(filePath='config.py', oldString='    x', newString='    y')",
            preconditions=["Read file first"],
            evidence_source=EvidenceSource.TOOL_CONTRACT,
            confidence=0.9,
            retry_owner=RetryOwner.SCRIPT_CODER,
            fallback_tool="Write",
            max_retries=2,
            required_inputs=["Current line content"],
        )
        payload = recovery.to_orchestrator_payload()

        assert payload["failed_step"] == "step-001"
        assert payload["tool_name"] == "Edit"
        assert payload["confidence"] == 0.9
        assert payload["retry_owner"] == "script_coder"
        assert payload["evidence_source"] == "tool_contract"
        assert payload["fallback_tool"] == "Write"
        assert payload["max_retries"] == 2
