"""Integration tests for validate-feature command with isolated fixtures.

Tests the validate-feature CLI command with mocked subprocess calls to verify:
- Report creation and file structure
- Command ordering within feature class bundles
- Exemption handling (docs-test-only)
- Cleanup verification (before/after state)
- Failure classification (environment vs product)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from openclaw_enhance.cli import cli


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

        with patch("openclaw_enhance.validation.types.sys.platform", "darwin"):
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

        calls = [call[0][0] for call in mock_run.call_args_list]

        assert len(calls) >= 6
        assert "uninstall" in calls[0]
        assert "install" in calls[1]
        assert "--dev" not in calls[1]
        assert calls[2] == "launchctl print gui/$(id -u)/ai.openclaw.enhance.monitor"
        assert "status" in calls[3]
        assert "doctor" in calls[4]
        assert "uninstall" in calls[5]

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_install_lifecycle_dev_mode_slug(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """Install lifecycle with dev slug should use --dev flag."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "install-lifecycle",
                "--report-slug",
                "backfill-dev-install",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        calls = [call[0][0] for call in mock_run.call_args_list]

        assert len(calls) >= 6
        assert "uninstall" in calls[0]
        assert "install --dev" in calls[1]
        assert "python -m openclaw_enhance.validation.live_probes" in calls[2]
        assert "dev-symlink" in calls[2]
        assert "status" in calls[3]
        assert "doctor" in calls[4]
        assert "uninstall" in calls[5]

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_workspace_routing_uses_routing_probe(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "workspace-routing",
                "--report-slug",
                "backfill-routing-yield",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        calls = [call[0][0] for call in mock_run.call_args_list]
        assert len(calls) == 1
        assert "python -m openclaw_enhance.validation.live_probes" in calls[0]
        assert "routing-yield" in calls[0]
        assert "--message" in calls[0]

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_workspace_routing_uses_recovery_probe(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "workspace-routing",
                "--report-slug",
                "backfill-recovery-worker",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        calls = [call[0][0] for call in mock_run.call_args_list]
        assert len(calls) == 1
        assert "python -m openclaw_enhance.validation.live_probes" in calls[0]
        assert "recovery-worker" in calls[0]
        assert "--message" in calls[0]

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_workspace_routing_uses_main_escalation_probe(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "workspace-routing",
                "--report-slug",
                "backfill-main-escalation",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        calls = [call[0][0] for call in mock_run.call_args_list]
        assert len(calls) == 1
        assert "python -m openclaw_enhance.validation.live_probes" in calls[0]
        assert "main-escalation" in calls[0]
        assert "routing-yield" not in calls[0]
        assert "recovery-worker" not in calls[0]
        assert "--message" in calls[0]

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_runtime_watchdog_uses_watchdog_probe(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "runtime-watchdog",
                "--report-slug",
                "backfill-watchdog-reminder",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        calls = [call[0][0] for call in mock_run.call_args_list]
        assert len(calls) == 2
        assert calls[0] == "openclaw hooks list"
        assert "python -m openclaw_enhance.validation.live_probes" in calls[1]
        assert "watchdog-reminder" in calls[1]

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_cli_surface_command_order(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """CLI surface should execute all shipped commands in order."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "cli-surface",
                "--report-slug",
                "backfill-cli-surface",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        calls = [call[0][0] for call in mock_run.call_args_list]
        envs = [call[1].get("env", {}) for call in mock_run.call_args_list]

        # Should have status, doctor, render commands, docs-check, and validate-feature self-surface
        assert any("status" in c for c in calls)
        assert any("doctor" in c for c in calls)
        assert any("render-workspace" in c for c in calls)
        assert any("render-skill" in c for c in calls)
        assert any("render-hook" in c for c in calls)
        assert any("docs-check" in c for c in calls)
        assert any("validate-feature" in c for c in calls)

        # Verify environment variable injection
        for env in envs:
            assert "OPENCLAW_ENHANCE_WORKSPACES_DIR" in env
            assert "workspaces" in env["OPENCLAW_ENHANCE_WORKSPACES_DIR"]
            assert env["OPENCLAW_HOME"] == str(mock_openclaw_home)
            assert env["OPENCLAW_CONFIG_PATH"].endswith("openclaw.json")


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


class TestValidateFeatureRecoveryDispatch:
    """Tests for recovery worker dispatch verification."""

    @patch("openclaw_enhance.validation.runner.subprocess.run")
    def test_recovery_dispatch_verified(
        self,
        mock_run: MagicMock,
        mock_openclaw_home: Path,
        reports_dir: Path,
    ):
        """Recovery probe should verify dispatch and corrected method."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                '{"ok": true, "probe": "recovery-worker", '
                '"marker": "PROBE_RECOVERY_WORKER_OK", "session_id": "ses_test123"}'
            ),
            stderr="",
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "validate-feature",
                "--feature-class",
                "workspace-routing",
                "--report-slug",
                "recovery-dispatch-test",
                "--openclaw-home",
                str(mock_openclaw_home),
                "--reports-dir",
                str(reports_dir),
            ],
        )

        assert result.exit_code == 0
        report_files = list(reports_dir.glob("*-recovery-dispatch-test-workspace-routing.md"))
        assert len(report_files) == 1

        content = report_files[0].read_text()
        assert "recovery-worker" in content
        assert "PROBE_RECOVERY_WORKER_OK" in content
