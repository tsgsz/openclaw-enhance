"""Skills catalog and routing logic for main session enhancement.

This module provides:
- Skill metadata and registry
- Task assessment and routing decisions
- ETA estimation for tasks
- Timeout state synchronization
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillMetadata:
    """Metadata for a main-session enhancement skill."""

    name: str
    description: str
    version: str
    user_invocable: bool = True
    allowed_tools: list[str] = field(default_factory=list)
    routing_heuristics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RoutingDecision:
    """Decision on where to route a task."""

    action: str  # "route" or "escalate"
    target: str  # "main" or "oe-orchestrator"
    reason: str
    estimated_duration: timedelta | None = None


@dataclass
class TaskAssessment:
    """Assessment of a task for routing decisions."""

    description: str
    estimated_toolcalls: int
    requires_parallel: bool
    complexity_score: int  # 1-10 scale
    estimated_duration_override: timedelta | None = None


# Registry of main-session enhancement skills
SKILLS_REGISTRY: list[SkillMetadata] = [
    SkillMetadata(
        name="oe-eta-estimator",
        description=(
            "Estimates task duration based on toolcall count, complexity, and parallelism needs"
        ),
        version="1.0.0",
        user_invocable=True,
        allowed_tools=["Read", "Write", "Glob", "Grep"],
        routing_heuristics={
            "max_toolcalls": 2,
            "max_duration_minutes": 30,
            "base_time_per_toolcall": 3,  # minutes
            "parallel_overhead_multiplier": 1.5,
        },
    ),
    SkillMetadata(
        name="oe-toolcall-router",
        description="Routes tasks to main or escalates to oe-orchestrator based on heuristics",
        version="1.0.0",
        user_invocable=True,
        allowed_tools=["Read", "Write", "Bash"],
        routing_heuristics={
            "max_toolcalls": 2,
            "max_duration_minutes": 30,
            "escalation_threshold": 2,  # toolcalls > 2 escalates
            "parallel_escalation": True,
            "long_running_threshold_minutes": 30,
        },
    ),
    SkillMetadata(
        name="oe-timeout-state-sync",
        description="Synchronizes timeout state between main session and runtime storage",
        version="1.0.0",
        user_invocable=False,
        allowed_tools=["Read", "Write", "Bash"],
        routing_heuristics={
            "max_toolcalls": 1,
            "max_duration_minutes": 5,
            "sync_interval_seconds": 60,
        },
    ),
]


def _expand_configured_path(path_value: str) -> Path:
    return Path(path_value).expanduser().resolve()


def _default_repo_skills_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "skills"


def _default_bundled_skills_dir() -> Path:
    return Path(__file__).resolve().parent / "_bundled_skills"


def _repo_skills_dir() -> Path:
    configured = os.getenv("OPENCLAW_ENHANCE_SKILLS_DIR")
    if configured:
        return _expand_configured_path(configured)
    return _default_repo_skills_dir()


def _bundled_skills_dir() -> Path:
    configured = os.getenv("OPENCLAW_ENHANCE_BUNDLED_SKILLS_DIR")
    if configured:
        return _expand_configured_path(configured)
    return _default_bundled_skills_dir()


def _active_skills_dir() -> Path:
    repo_skills = _repo_skills_dir()
    if repo_skills.is_dir():
        return repo_skills

    bundled_skills = _bundled_skills_dir()
    if bundled_skills.is_dir():
        return bundled_skills

    raise ValueError("No skills directory found")


def list_skill_contract_names() -> list[str]:
    try:
        active_dir = _active_skills_dir()
    except ValueError:
        return []

    return sorted(
        skill_file.parent.name
        for skill_file in active_dir.glob("*/SKILL.md")
        if skill_file.is_file()
    )


def _skill_contract_path(skill_name: str) -> Path:
    return _active_skills_dir() / skill_name / "SKILL.md"


class SkillRouter:
    """Router for deciding where to execute tasks."""

    def __init__(self) -> None:
        """Initialize the skill router."""
        self._escalation_threshold = 2  # toolcalls > 2 escalates
        self._long_running_threshold = timedelta(minutes=30)

    def route_task(self, assessment: TaskAssessment) -> RoutingDecision:
        """Route a task based on assessment.

        Args:
            assessment: Task assessment with toolcall estimate, etc.

        Returns:
            RoutingDecision with action, target, and reason.
        """
        estimated_duration = estimate_task_duration(assessment)

        # Check escalation conditions
        if assessment.estimated_toolcalls > self._escalation_threshold:
            return RoutingDecision(
                action="escalate",
                target="oe-orchestrator",
                reason=(
                    f"High toolcall count ({assessment.estimated_toolcalls} > "
                    f"{self._escalation_threshold})"
                ),
                estimated_duration=estimated_duration,
            )

        if assessment.requires_parallel:
            return RoutingDecision(
                action="escalate",
                target="oe-orchestrator",
                reason="Task requires parallel execution",
                estimated_duration=estimated_duration,
            )

        if estimated_duration > self._long_running_threshold:
            return RoutingDecision(
                action="escalate",
                target="oe-orchestrator",
                reason=(
                    f"Long-running task ({estimated_duration.total_seconds() // 60} min > 30 min)"
                ),
                estimated_duration=estimated_duration,
            )

        # Stay local
        return RoutingDecision(
            action="route",
            target="main",
            reason="Simple task suitable for main session",
            estimated_duration=estimated_duration,
        )


def estimate_task_duration(assessment: TaskAssessment) -> timedelta:
    """Estimate task duration based on assessment.

    Args:
        assessment: Task assessment.

    Returns:
        Estimated duration as timedelta.
    """
    # Use override if provided
    if assessment.estimated_duration_override is not None:
        return max(assessment.estimated_duration_override, timedelta(minutes=1))

    # Handle edge cases
    if assessment.estimated_toolcalls <= 0:
        return timedelta(minutes=1)

    toolcalls = assessment.estimated_toolcalls
    requires_parallel = assessment.requires_parallel

    # Estimation formula based on toolcalls and parallelism
    # These heuristics are calibrated for realistic development tasks
    if toolcalls == 1:
        minutes = 2
    elif toolcalls == 2:
        minutes = 5
    elif toolcalls <= 5:
        minutes = toolcalls * 3
    elif toolcalls < 10:
        minutes = int(toolcalls * 3.75)
    elif toolcalls == 10:
        minutes = 40
    else:
        minutes = toolcalls * 4

    if requires_parallel:
        minutes = int(minutes * 1.5)

    return timedelta(minutes=max(minutes, 1))


def should_escalate_to_orchestrator(assessment: TaskAssessment) -> bool:
    """Determine if task should escalate to orchestrator.

    Args:
        assessment: Task assessment.

    Returns:
        True if should escalate, False to stay in main.
    """
    # Escalate if toolcalls > 2
    if assessment.estimated_toolcalls > 2:
        return True

    # Escalate if requires parallel
    if assessment.requires_parallel:
        return True

    # Escalate if long duration
    estimated = estimate_task_duration(assessment)
    if estimated > timedelta(minutes=30):
        return True

    return False


def render_skill_contract(skill_name: str) -> str:
    """Render the contract for a skill.

    Args:
        skill_name: Name of the skill to render.

    Returns:
        Rendered skill contract as markdown string.

    Raises:
        ValueError: If skill name is unknown.
    """
    contract_path = _skill_contract_path(skill_name)
    if not contract_path.is_file():
        available = ", ".join(list_skill_contract_names()) or "none"
        raise ValueError(f"Unknown skill: {skill_name}. Available skills: {available}")

    return contract_path.read_text(encoding="utf-8")


def sync_timeout_state(
    session_id: str,
    task_description: str,
    timeout_duration: timedelta,
    runtime_state: Any,  # RuntimeState from schema
) -> dict[str, Any]:
    """Synchronize timeout state with runtime storage.

    Args:
        session_id: ID of the session that timed out.
        task_description: Description of the task.
        timeout_duration: How long the task ran before timeout.
        runtime_state: Current runtime state object.

    Returns:
        Dict with sync status and metadata.
    """
    from openclaw_enhance.runtime.schema import RuntimeState

    if not isinstance(runtime_state, RuntimeState):
        raise TypeError("runtime_state must be a RuntimeState instance")

    # Update the runtime state timestamp
    runtime_state.last_updated_utc = datetime.utcnow()

    # Return sync result
    return {
        "synced": True,
        "session_id": session_id,
        "timestamp": runtime_state.last_updated_utc.isoformat(),
        "task_description": task_description,
        "timeout_duration_seconds": timeout_duration.total_seconds(),
    }
