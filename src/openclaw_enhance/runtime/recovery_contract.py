"""Recovery result contract for orchestrator and oe-tool-recovery.

This module defines the single source of truth for the recovery result contract
used by both the orchestrator and the oe-tool-recovery agent. The contract
ensures structured, unambiguous recovery suggestions with clear ownership and
accountability.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceSource(str, Enum):
    """Source of evidence for the recovery diagnosis."""

    TOOL_CONTRACT = "tool_contract"
    DOCUMENTATION = "documentation"
    SOURCE_CODE = "source_code"
    EXTERNAL_SEARCH = "external_search"
    ENVIRONMENT_INSPECTION = "environment_inspection"
    ERROR_MESSAGE = "error_message"


class RetryOwner(str, Enum):
    """Agent types that can own retry execution."""

    ORCHESTRATOR = "orchestrator"
    SCRIPT_CODER = "script_coder"
    SEARCHER = "searcher"
    SYSHELPER = "syshelper"
    SELF = "self"  # The agent that originally failed


class RecoveredMethod(BaseModel):
    """Structured recovery suggestion for failed tool calls.

    This contract defines the complete set of information required for an
    orchestrator to make an informed decision about retrying a failed tool
    call. It eliminates ambiguity by requiring explicit ownership, evidence
    sourcing, and bounded retry parameters.

    Required Fields:
        - failed_step: Identity of the failed step (unique identifier)
        - tool_name: Name of the tool that failed
        - failure_reason: Root cause analysis
        - exact_invocation: The corrected tool call shape (exact syntax)
        - preconditions: Steps required before retry (can be empty list)
        - evidence_source: Where the diagnosis came from
        - confidence: Score (0.0 - 1.0) for the recovery suggestion
        - retry_owner: Who should execute the retry

    Optional Fields:
        - fallback_tool: Alternative tool if original cannot work
        - max_retries: Maximum retry attempts (default: 1, max: 3)
        - required_inputs: Specific data points needed for the retry

    Forbidden Patterns (enforced by validators):
        - Missing retry_owner: Every recovery must have clear ownership
        - Unbounded retry counts: max_retries must be specified and bounded
        - Free-form-only output: exact_invocation must be present and specific
    """

    model_config = ConfigDict(extra="forbid")

    # Required Fields
    failed_step: str = Field(
        description="Unique identifier or description of the step that failed",
        min_length=1,
    )
    tool_name: str = Field(
        description="Name of the tool that failed",
        min_length=1,
    )
    failure_reason: str = Field(
        description="Root cause analysis of the failure",
        min_length=1,
    )
    exact_invocation: str = Field(
        description="The exact corrected tool call string with precise parameters",
        min_length=1,
    )
    preconditions: list[str] = Field(
        default_factory=list,
        description="Steps that must be taken before retrying (empty if none)",
    )
    evidence_source: EvidenceSource = Field(
        description="Source of evidence supporting the recovery diagnosis",
    )
    confidence: float = Field(
        description="Confidence score (0.0 - 1.0) for the recovery suggestion",
        ge=0.0,
        le=1.0,
    )
    retry_owner: RetryOwner = Field(
        description="Agent type responsible for executing the retry",
    )

    # Optional Fields
    fallback_tool: str | None = Field(
        default=None,
        description="Alternative tool name if the original cannot work",
    )
    max_retries: int = Field(
        default=1,
        description="Maximum number of retry attempts (bounded)",
        ge=0,
        le=3,
    )
    required_inputs: list[str] = Field(
        default_factory=list,
        description="Specific data points needed for the retry",
    )

    @field_validator("exact_invocation")
    @classmethod
    def validate_exact_invocation_not_placeholder(cls, v: str) -> str:
        """Ensure exact_invocation is specific, not a placeholder."""
        placeholder_patterns = [
            "<",
            ">",
            "...",
            "todo",
            "fixme",
            "example",
            "placeholder",
        ]
        lower_v = v.lower()
        for pattern in placeholder_patterns:
            if pattern in lower_v:
                raise ValueError(
                    f"exact_invocation contains placeholder pattern '{pattern}'. "
                    "Must be an exact, executable tool call."
                )
        return v

    @field_validator("failure_reason")
    @classmethod
    def validate_failure_reason_specific(cls, v: str) -> str:
        """Ensure failure reason is specific, not vague."""
        vague_patterns = [
            "unknown error",
            "something went wrong",
            "it failed",
            "error occurred",
        ]
        lower_v = v.lower()
        for pattern in vague_patterns:
            if pattern in lower_v:
                raise ValueError(
                    f"failure_reason is too vague: '{pattern}'. "
                    "Must provide specific root cause analysis."
                )
        return v

    def is_ready_for_retry(self) -> bool:
        """Check if all preconditions are satisfied for retry.

        Returns:
            True if preconditions list is empty or all marked complete.
        """
        return len(self.preconditions) == 0

    def to_orchestrator_payload(self) -> dict[str, Any]:
        """Convert to payload format for orchestrator communication.

        Returns:
            Dictionary with all contract fields.
        """
        return self.model_dump()


class RecoveryResult(BaseModel):
    """Complete recovery result from oe-tool-recovery to orchestrator.

    This is the top-level container for recovery communication, including
    the recovered method and any additional context.
    """

    model_config = ConfigDict(extra="forbid")

    recovered_method: RecoveredMethod = Field(
        description="The primary recovery suggestion",
    )
    alternative_methods: list[RecoveredMethod] = Field(
        default_factory=list,
        description="Alternative recovery options if primary fails",
    )
    diagnosis_summary: str = Field(
        default="",
        description="Human-readable summary of the diagnosis",
    )
    requires_escalation: bool = Field(
        default=False,
        description="Whether this failure requires orchestrator escalation",
    )

    @field_validator("alternative_methods")
    @classmethod
    def validate_alternatives_count(cls, v: list[RecoveredMethod]) -> list[RecoveredMethod]:
        """Limit number of alternative methods to prevent decision paralysis."""
        if len(v) > 2:
            raise ValueError(
                f"Too many alternative methods ({len(v)}). "
                "Maximum allowed is 2 to prevent decision paralysis."
            )
        return v


# Contract version for tracking compatibility
CONTRACT_VERSION = "1.0.0"


def get_contract_version() -> str:
    """Return the current recovery contract version."""
    return CONTRACT_VERSION
