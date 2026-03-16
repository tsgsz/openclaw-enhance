"""Unit tests for real-environment validation types."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from openclaw_enhance.validation.types import (
    BaselineState,
    CommandResult,
    FeatureClass,
    ValidationConclusion,
    ValidationReport,
    get_bundle_commands,
)


def test_feature_class_enum():
    """Test FeatureClass enum values."""
    assert FeatureClass.INSTALL_LIFECYCLE.value == "install-lifecycle"
    assert FeatureClass.CLI_SURFACE.value == "cli-surface"
    assert FeatureClass.WORKSPACE_ROUTING.value == "workspace-routing"
    assert FeatureClass.RUNTIME_WATCHDOG.value == "runtime-watchdog"
    assert FeatureClass.DOCS_TEST_ONLY.value == "docs-test-only"


def test_validation_conclusion_enum():
    """Test ValidationConclusion enum values."""
    assert ValidationConclusion.PASS.value == "pass"
    assert ValidationConclusion.PRODUCT_FAILURE.value == "product_failure"
    assert ValidationConclusion.ENVIRONMENT_FAILURE.value == "environment_failure"
    assert ValidationConclusion.EXEMPT.value == "exempt"


def test_command_result_success():
    """Test CommandResult success check."""
    result = CommandResult(
        command="ls",
        exit_code=0,
        stdout="file.txt",
        stderr="",
        duration_seconds=0.1,
    )
    assert result.is_success is True


def test_command_result_failure():
    """Test CommandResult failure check."""
    result = CommandResult(
        command="ls non_existent",
        exit_code=1,
        stdout="",
        stderr="error",
        duration_seconds=0.1,
    )
    assert result.is_success is False


def test_report_path_generation():
    """Test ValidationReport path generation."""
    baseline = BaselineState(
        openclaw_home=Path("/tmp/.openclaw"),
        is_installed=True,
    )
    report = ValidationReport(
        feature_name="Test Feature",
        feature_class=FeatureClass.CLI_SURFACE,
        conclusion=ValidationConclusion.PASS,
        environment="macOS",
        baseline=baseline,
        timestamp=datetime(2026, 3, 14, 12, 0, 0),
    )

    reports_dir = Path("docs/reports")
    path = report.get_report_path(reports_dir, "test-feature")

    assert path == Path("docs/reports/2026-03-14-test-feature-cli-surface.md")


def test_get_bundle_commands():
    """Test get_bundle_commands for various feature classes."""
    with patch("openclaw_enhance.validation.types.sys.platform", "darwin"):
        install_cmds = get_bundle_commands(FeatureClass.INSTALL_LIFECYCLE)
    assert len(install_cmds) == 6
    assert "install" in install_cmds[1]
    assert install_cmds[2] == "launchctl print gui/$(id -u)/ai.openclaw.enhance.monitor"

    docs_cmds = get_bundle_commands(FeatureClass.DOCS_TEST_ONLY)
    assert len(docs_cmds) == 1
    assert "docs-check" in docs_cmds[0]

    cli_cmds = get_bundle_commands(FeatureClass.CLI_SURFACE)
    assert len(cli_cmds) == 8
    assert "status --json" in cli_cmds[1]
