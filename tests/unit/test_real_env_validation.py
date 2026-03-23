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
    assert len(cli_cmds) == 9
    assert "status --json" in cli_cmds[1]
    assert any("cleanup-sessions --dry-run --json" in cmd for cmd in cli_cmds)


def test_get_bundle_commands_workspace_routing_variants():
    orchestrator_child_spawn_cmds = get_bundle_commands(
        FeatureClass.WORKSPACE_ROUTING, "orchestrator-child-spawn"
    )
    routing_cmds = get_bundle_commands(FeatureClass.WORKSPACE_ROUTING, "backfill-routing-yield")
    recovery_cmds = get_bundle_commands(FeatureClass.WORKSPACE_ROUTING, "backfill-recovery-worker")
    main_escalation_cmds = get_bundle_commands(
        FeatureClass.WORKSPACE_ROUTING, "backfill-main-escalation"
    )

    assert orchestrator_child_spawn_cmds == [
        (
            "python -m openclaw_enhance.validation.live_probes orchestrator-spawn "
            '--openclaw-home "$OPENCLAW_HOME" --message '
            '"请让 orchestrator 通过子 agent 完成一个复杂任务，并确认存在 child spawn 证据"'
        )
    ]
    assert routing_cmds == [
        (
            "python -m openclaw_enhance.validation.live_probes routing-yield "
            '--openclaw-home "$OPENCLAW_HOME" --message '
            '"帮我规划一个复杂任务，先并行搜索两个方向，再汇总一个执行计划"'
        )
    ]
    assert recovery_cmds == [
        (
            "python -m openclaw_enhance.validation.live_probes recovery-worker "
            '--openclaw-home "$OPENCLAW_HOME" --message '
            '"请先尝试使用 websearch 工具搜索 Python async patterns；'
            '若失败，继续完成任务并报告最终采用的方法"'
        )
    ]
    assert main_escalation_cmds == [
        (
            "python -m openclaw_enhance.validation.live_probes main-escalation "
            '--openclaw-home "$OPENCLAW_HOME" --message '
            '"搜索 2025 年整个东南亚 iGaming 行业现状，给出 2026 年判断，并先设计一个 '
            '20 页左右的 PPT 大纲（包含内容、数据和讲稿），保证数据真实可追溯。"'
        )
    ]
