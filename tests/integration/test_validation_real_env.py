"""Integration tests for validate-feature command with isolated fixtures.

Tests the validate-feature CLI command with mocked subprocess calls to verify:
- Report creation and file structure
- Command ordering within feature class bundles
- Exemption handling (docs-test-only)
- Cleanup verification (before/after state)
- Failure classification (environment vs product)
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from openclaw_enhance.cli import cli
from openclaw_enhance.validation.types import FeatureClass, ValidationConclusion


@pytest.fixture
def mock_openclaw_home(tmp_path: Path) -> Path:
    """Create a mock OpenClaw home directory with harness readiness."""
    openclaw_home = tmp_path / ".openclaw"
    openclaw_home.mkdir(parents=True)

    version_file = openclaw_home / "VERSION"
    version_file.write_text("2026.3.1\n")

    config_file = openclaw_home / "config.json"
    config_file.write_text(json.dumps({"test": True}) + "\n")

    return openclaw_home


@pytest.fixture
def reports_dir(tmp_path: Path) -> Path:
    """Create a reports directory."""
    reports = tmp_path / "reports"
    reports.mkdir()
    return reports


class TestValidateFeatureReportCreation:
    """Tests for report creation and file structure."""

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_report_file_created(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """Validate-feature should create a report file."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "cli-surface",
                "--report-slug",
                "test-run",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        assert result.exit_code == 0

        # Check report file exists
        report_files = list(reports_dir.glob("*-test-run-cli-surface.md"))
        assert len(report_files) == 1

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_report_contains_baseline(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """Report should contain baseline state information."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "cli-surface",
                "--report-slug",
                "baseline-test",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        report_files = list(reports_dir.glob("*-baseline-test-cli-surface.md"))
        assert len(report_files) == 1

        content = report_files[0].read_text()
        assert "Baseline" in content or "baseline" in content


class TestValidateFeatureCommandOrdering:
    """Tests for command ordering within feature class bundles."""

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_install_lifecycle_command_order(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """Install lifecycle should execute commands in correct order."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "install-lifecycle",
                "--report-slug",
                "order-test",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        # Verify commands were called in order
        calls = [call[0][0] for call in mock_run.call_args_list]

        # Should have uninstall, install, status, doctor, uninstall
        assert len(calls) >= 5
        assert "uninstall" in calls[0]
        assert "install" in calls[1]
        assert "status" in calls[2]
        assert "doctor" in calls[3]
        assert "uninstall" in calls[4]

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_cli_surface_command_order(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """CLI surface should execute render commands in order."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "cli-surface",
                "--report-slug",
                "baseline-test",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        calls = [call[0][0] for call in mock_run.call_args_list]

        # Should have status --json, render-workspace, render-skill, render-hook
        assert len(calls) >= 4
        assert "status --json" in calls[0]
        assert "render-workspace" in calls[1]
        assert "render-skill" in calls[2]
        assert "render-hook" in calls[3]


class TestValidateFeatureExemptions:
    """Tests for exemption handling (docs-test-only)."""

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_docs_test_only_exempt(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """Docs-test-only feature class should be exempt with docs-check evidence."""
        mock_run.return_value = MagicMock(returncode=0, stdout="docs-check ok", stderr="")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "docs-test-only",
                "--report-slug",
                "exempt-test",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        assert result.exit_code == 0

        report_files = list(reports_dir.glob("*-exempt-test-docs-test-only.md"))
        assert len(report_files) == 1

        content = report_files[0].read_text()
        assert "EXEMPT" in content or "exempt" in content
        assert "docs-check" in content

    def test_docs_test_only_executes_docs_check(
        self,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """Docs-test-only should execute docs-check for evidence."""
        with patch("openclaw_enhance.validation.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

            runner = CliRunner()
            runner.invoke(
                cli,
                [
                    "validate-feature",
                    "--feature-class",
                    "docs-test-only",
                    "--report-slug",
                    "docs-check-exec",
                    "--openclaw-home",
                    str(mock_openclaw_home),
                    "--reports-dir",
                    str(reports_dir),
                ],
            )

            mock_run.assert_called_once()
            assert "docs-check" in mock_run.call_args[0][0]


class TestValidateFeatureFailureClassification:
    """Tests for failure classification (environment vs product)."""

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_environment_failure_exit_127(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """Exit code 127 should be classified as environment failure."""
        mock_run.return_value = MagicMock(returncode=127, stdout="", stderr="command not found")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "cli-surface",
                "--report-slug",
                "env-fail",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        # CLI exits 1 on validation failure, but report should be created
        assert result.exit_code == 1

        report_files = list(reports_dir.glob("*-env-fail-cli-surface.md"))
        assert len(report_files) == 1

        content = report_files[0].read_text()
        assert "ENVIRONMENT_FAILURE" in content or "environment_failure" in content

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_product_failure_nonzero_exit(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """Non-zero exit (not 127) should be classified as product failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "cli-surface",
                "--report-slug",
                "prod-fail",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        assert result.exit_code == 1

        report_files = list(reports_dir.glob("*-prod-fail-cli-surface.md"))
        assert len(report_files) == 1

        content = report_files[0].read_text()
        assert "PRODUCT_FAILURE" in content or "product_failure" in content

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_pass_all_commands_succeed(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """All commands succeeding should result in PASS."""
        mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "cli-surface",
                "--report-slug",
                "pass-test",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        assert result.exit_code == 0

        report_files = list(reports_dir.glob("*-pass-test-cli-surface.md"))
        assert len(report_files) == 1

        content = report_files[0].read_text()
        assert "PASS" in content or "pass" in content


class TestValidateFeatureCleanupVerification:
    """Tests for cleanup verification (before/after state)."""

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_baseline_captured_before_execution(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """Baseline state should be captured before command execution."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "cli-surface",
                "--report-slug",
                "baseline-capture",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        report_files = list(reports_dir.glob("*-baseline-capture-cli-surface.md"))
        content = report_files[0].read_text()

        assert "environment" in content.lower() or "baseline" in content.lower()
