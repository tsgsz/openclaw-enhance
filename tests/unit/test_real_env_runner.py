"""Unit tests for validation runner and reporting."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from openclaw_enhance.validation.reporting import generate_markdown_report, write_report
from openclaw_enhance.validation.runner import (
    build_report_path,
    execute_command,
    run_scenario,
)
from openclaw_enhance.validation.types import (
    BaselineState,
    CommandResult,
    FeatureClass,
    ValidationConclusion,
    ValidationReport,
)


class TestExecuteCommand:
    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_execute_command_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output",
            stderr="",
        )

        result = execute_command("echo test", Path("/tmp"))

        assert result.exit_code == 0
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.command == "echo test"
        assert result.duration_seconds >= 0

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_execute_command_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error",
        )

        result = execute_command("false", Path("/tmp"))

        assert result.exit_code == 1
        assert result.stderr == "error"
        assert not result.is_success

    @patch("openclaw_enhance.validation.runner.pinned_openclaw_runtime_model")
    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_execute_command_skips_outer_model_pin_for_live_probes(self, mock_run, mock_pin):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ok",
            stderr="",
        )

        result = execute_command(
            "python -m openclaw_enhance.validation.live_probes watchdog-reminder",
            Path("/tmp/.openclaw"),
        )

        assert result.exit_code == 0
        mock_pin.assert_not_called()


class TestRunScenario:
    @patch("openclaw_enhance.validation.runner.execute_command")
    @patch("openclaw_enhance.validation.runner._capture_baseline")
    @patch("openclaw_enhance.validation.guardrails.capture_baseline_state")
    @patch("openclaw_enhance.validation.runner.verify_ownership")
    def test_run_scenario_all_pass(self, mock_verify, mock_guardrail, mock_baseline, mock_execute):
        mock_baseline.return_value = BaselineState(
            openclaw_home=Path("/tmp/.openclaw"),
            is_installed=False,
        )
        from openclaw_enhance.validation.guardrails import BaselineState as GuardrailState

        mock_guardrail.return_value = GuardrailState(
            openclaw_home=Path("/tmp/.openclaw"),
            is_installed=False,
            owned_by_checkout=True,
            config_state={},
            managed_root_state={},
        )
        mock_execute.return_value = CommandResult(
            command="test",
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_seconds=0.1,
        )

        report = run_scenario(
            FeatureClass.CLI_SURFACE,
            "test-slug",
            Path("/tmp/.openclaw"),
            Path("/tmp/reports"),
        )

        assert report.conclusion == ValidationConclusion.PASS
        assert report.feature_class == FeatureClass.CLI_SURFACE
        assert len(report.results) > 0

    @patch("openclaw_enhance.validation.runner.execute_command")
    @patch("openclaw_enhance.validation.runner._capture_baseline")
    @patch("openclaw_enhance.validation.guardrails.capture_baseline_state")
    @patch("openclaw_enhance.validation.runner.verify_ownership")
    def test_run_scenario_product_failure(
        self, mock_verify, mock_guardrail, mock_baseline, mock_execute
    ):
        mock_baseline.return_value = BaselineState(
            openclaw_home=Path("/tmp/.openclaw"),
            is_installed=False,
        )
        from openclaw_enhance.validation.guardrails import BaselineState as GuardrailState

        mock_guardrail.return_value = GuardrailState(
            openclaw_home=Path("/tmp/.openclaw"),
            is_installed=False,
            owned_by_checkout=True,
            config_state={},
            managed_root_state={},
        )
        mock_execute.return_value = CommandResult(
            command="test",
            exit_code=1,
            stdout="",
            stderr="error",
            duration_seconds=0.1,
        )

        report = run_scenario(
            FeatureClass.CLI_SURFACE,
            "test-slug",
            Path("/tmp/.openclaw"),
            Path("/tmp/reports"),
        )

        assert report.conclusion == ValidationConclusion.PRODUCT_FAILURE

    @patch("openclaw_enhance.validation.runner.execute_command")
    @patch("openclaw_enhance.validation.runner._capture_baseline")
    @patch("openclaw_enhance.validation.guardrails.capture_baseline_state")
    @patch("openclaw_enhance.validation.runner.verify_ownership")
    def test_run_scenario_environment_failure(
        self, mock_verify, mock_guardrail, mock_baseline, mock_execute
    ):
        mock_baseline.return_value = BaselineState(
            openclaw_home=Path("/tmp/.openclaw"),
            is_installed=False,
        )
        from openclaw_enhance.validation.guardrails import BaselineState as GuardrailState

        mock_guardrail.return_value = GuardrailState(
            openclaw_home=Path("/tmp/.openclaw"),
            is_installed=False,
            owned_by_checkout=True,
            config_state={},
            managed_root_state={},
        )
        mock_execute.return_value = CommandResult(
            command="test",
            exit_code=127,
            stdout="",
            stderr="command not found",
            duration_seconds=0.1,
        )

        report = run_scenario(
            FeatureClass.CLI_SURFACE,
            "test-slug",
            Path("/tmp/.openclaw"),
            Path("/tmp/reports"),
        )

        assert report.conclusion == ValidationConclusion.ENVIRONMENT_FAILURE

    @patch("openclaw_enhance.validation.runner.execute_command")
    def test_run_scenario_exempt(self, mock_execute):
        mock_execute.return_value = CommandResult(
            command="python -m openclaw_enhance.cli docs-check",
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_seconds=0.1,
        )

        report = run_scenario(
            FeatureClass.DOCS_TEST_ONLY,
            "test-slug",
            Path("/tmp/.openclaw"),
            Path("/tmp/reports"),
        )

        assert report.conclusion == ValidationConclusion.EXEMPT
        assert len(report.results) == 1
        assert "docs-check" in report.results[0].command

    @patch("openclaw_enhance.validation.runner.execute_command")
    @patch("openclaw_enhance.validation.runner._capture_baseline")
    @patch("openclaw_enhance.validation.guardrails.capture_baseline_state")
    @patch("openclaw_enhance.validation.runner.verify_ownership")
    def test_run_scenario_cleanup_verification_install_lifecycle(
        self, mock_verify, mock_guardrail, mock_baseline, mock_execute
    ):
        mock_baseline.return_value = BaselineState(
            openclaw_home=Path("/tmp/.openclaw"),
            is_installed=False,
        )
        from openclaw_enhance.validation.guardrails import BaselineState as GuardrailState

        initial_state = GuardrailState(
            openclaw_home=Path("/tmp/.openclaw"),
            is_installed=False,
            owned_by_checkout=True,
            config_state={},
            managed_root_state={},
        )
        final_state = GuardrailState(
            openclaw_home=Path("/tmp/.openclaw"),
            is_installed=False,
            owned_by_checkout=True,
            config_state={},
            managed_root_state={},
        )
        mock_guardrail.side_effect = [initial_state, final_state]
        mock_execute.return_value = CommandResult(
            command="test",
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_seconds=0.1,
        )

        report = run_scenario(
            FeatureClass.INSTALL_LIFECYCLE,
            "test-slug",
            Path("/tmp/.openclaw"),
            Path("/tmp/reports"),
        )

        assert report.conclusion == ValidationConclusion.PASS
        assert mock_guardrail.call_count == 2


class TestBuildReportPath:
    def test_build_report_path_format(self):
        path = build_report_path(
            Path("/tmp/reports"),
            "test-slug",
            FeatureClass.CLI_SURFACE,
        )

        assert path.parent == Path("/tmp/reports")
        assert "test-slug" in path.name
        assert "cli-surface" in path.name
        assert path.suffix == ".md"


class TestGenerateMarkdownReport:
    def test_generate_markdown_report_basic(self):
        report = ValidationReport(
            feature_name="test-feature",
            feature_class=FeatureClass.CLI_SURFACE,
            conclusion=ValidationConclusion.PASS,
            environment="macOS /tmp/.openclaw",
            baseline=BaselineState(
                openclaw_home=Path("/tmp/.openclaw"),
                is_installed=False,
            ),
        )

        markdown = generate_markdown_report(report)

        assert "# Validation Report: test-feature" in markdown
        assert "cli-surface" in markdown
        assert "PASS" in markdown

    def test_generate_markdown_report_with_results(self):
        report = ValidationReport(
            feature_name="test-feature",
            feature_class=FeatureClass.CLI_SURFACE,
            conclusion=ValidationConclusion.PASS,
            environment="macOS /tmp/.openclaw",
            baseline=BaselineState(
                openclaw_home=Path("/tmp/.openclaw"),
                is_installed=False,
            ),
            results=[
                CommandResult(
                    command="echo test",
                    exit_code=0,
                    stdout="test",
                    stderr="",
                    duration_seconds=0.1,
                )
            ],
        )

        markdown = generate_markdown_report(report)

        assert "echo test" in markdown
        assert "✓ PASS" in markdown
        assert "Exit Code: 0" in markdown


class TestWriteReport:
    def test_write_report(self, tmp_path):
        report = ValidationReport(
            feature_name="test-feature",
            feature_class=FeatureClass.CLI_SURFACE,
            conclusion=ValidationConclusion.PASS,
            environment="macOS /tmp/.openclaw",
            baseline=BaselineState(
                openclaw_home=Path("/tmp/.openclaw"),
                is_installed=False,
            ),
        )

        output_path = tmp_path / "reports" / "test.md"
        write_report(report, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "test-feature" in content
