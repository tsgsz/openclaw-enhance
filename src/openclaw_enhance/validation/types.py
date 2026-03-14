"""Validation types and enums for real-environment testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TYPE_CHECKING


class FeatureClass(Enum):
    """Classification of features for validation targeting."""

    INSTALL_LIFECYCLE = "install-lifecycle"
    CLI_SURFACE = "cli-surface"
    WORKSPACE_ROUTING = "workspace-routing"
    RUNTIME_WATCHDOG = "runtime-watchdog"
    DOCS_TEST_ONLY = "docs-test-only"


class ValidationConclusion(Enum):
    """Final result of a validation run."""

    PASS = "pass"
    PRODUCT_FAILURE = "product_failure"
    ENVIRONMENT_FAILURE = "environment_failure"
    EXEMPT = "exempt"


class ValidationPhase(Enum):
    """Phases of the validation lifecycle."""

    PREFLIGHT = "preflight"
    BASELINE = "baseline"
    EXECUTION = "execution"
    CLEANUP = "cleanup"
    REPORT = "report"


@dataclass
class CommandResult:
    """Result of a single command execution."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_success(self) -> bool:
        """Check if the command was successful."""
        return self.exit_code == 0


@dataclass
class BaselineState:
    """Captured state of the environment before validation."""

    openclaw_home: Path
    is_installed: bool
    version: str | None = None
    config_exists: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ValidationReport:
    """Complete report of a validation run."""

    feature_name: str
    feature_class: FeatureClass
    conclusion: ValidationConclusion
    environment: str
    baseline: BaselineState
    results: list[CommandResult] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def get_report_path(self, reports_dir: Path, slug: str) -> Path:
        """Generate the standard report path: YYYY-MM-DD-<slug>-<feature-class>.md"""
        date_str = self.timestamp.strftime("%Y-%m-%d")
        filename = f"{date_str}-{slug}-{self.feature_class.value}.md"
        return reports_dir / filename


def get_bundle_commands(feature_class: FeatureClass, slug: str = "") -> list[str]:
    """Get the mandatory command bundle for a feature class.

    Args:
        feature_class: The feature class to get commands for.
        slug: Optional slug to determine variant (e.g., 'backfill-dev-install' for dev mode).

    Returns:
        List of commands to execute for validation.
    """
    if feature_class == FeatureClass.INSTALL_LIFECYCLE:
        if "dev" in slug:
            return [
                "python -m openclaw_enhance.cli uninstall",
                "python -m openclaw_enhance.cli install --dev",
                "python -m openclaw_enhance.cli status",
                "python -m openclaw_enhance.cli doctor",
                "python -m openclaw_enhance.cli uninstall",
            ]
        else:
            return [
                "python -m openclaw_enhance.cli uninstall",
                "python -m openclaw_enhance.cli install",
                "python -m openclaw_enhance.cli status",
                "python -m openclaw_enhance.cli doctor",
                "python -m openclaw_enhance.cli uninstall",
            ]

    if feature_class == FeatureClass.WORKSPACE_ROUTING:
        project_root = Path(__file__).parent.parent.parent.parent
        return [
            "python -m openclaw_enhance.cli render-workspace oe-orchestrator",
            f"cd {project_root} && pytest tests/integration/test_orchestrator_dispatch_contract.py::TestBoundedLoopContract -q --tb=no",
        ]

    bundles = {
        FeatureClass.CLI_SURFACE: [
            "python -m openclaw_enhance.cli status",
            "python -m openclaw_enhance.cli status --json",
            "python -m openclaw_enhance.cli doctor",
            "python -m openclaw_enhance.cli render-workspace oe-orchestrator",
            "python -m openclaw_enhance.cli render-skill oe-toolcall-router",
            "python -m openclaw_enhance.cli render-hook oe-subagent-spawn-enrich",
            "python -m openclaw_enhance.cli docs-check",
            (
                "python -m openclaw_enhance.cli validate-feature "
                "--feature-class docs-test-only --report-slug self-surface-smoke"
            ),
        ],
        FeatureClass.RUNTIME_WATCHDOG: [
            'cat ~/.openclaw/config.json | grep "openclawEnhance"',
        ],
        FeatureClass.DOCS_TEST_ONLY: [
            "python -m openclaw_enhance.cli docs-check",
        ],
    }
    return bundles.get(feature_class, [])
