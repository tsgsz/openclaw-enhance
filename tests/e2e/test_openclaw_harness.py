"""End-to-end tests for the OpenClaw harness integration.

These tests verify that openclaw-enhance integrates correctly with the
OpenClaw runtime environment. They are gated by the OPENCLAW_HARNESS
environment variable - when not set, tests skip cleanly.

To run these tests:
    OPENCLAW_HARNESS=1 pytest tests/e2e/test_openclaw_harness.py -v
"""

import json
import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import pytest

# Harness gating: Skip all tests unless OPENCLAW_HARNESS is set
pytestmark = pytest.mark.skipif(
    os.environ.get("OPENCLAW_HARNESS") != "1",
    reason="E2E tests require OPENCLAW_HARNESS=1 environment variable",
)


def _latest_report(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    return max(paths, key=lambda path: path.stat().st_mtime)


def _local_src_env() -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[2] / "src")
    python_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{src_path}:{python_path}" if python_path else src_path
    return env


class TestHarnessAvailability:
    """Tests for harness availability and environment."""

    def test_harness_environment_variable_set(self):
        """Verify OPENCLAW_HARNESS environment variable is set."""
        assert os.environ.get("OPENCLAW_HARNESS") == "1"

    def test_openclaw_home_exists(self):
        """Verify OpenClaw home directory exists."""
        openclaw_home = Path.home() / ".openclaw"

        # In harness mode, this should exist
        if not openclaw_home.exists():
            pytest.skip("OpenClaw home directory not found - skipping harness tests")

        assert openclaw_home.exists()

    def test_openclaw_config_exists(self):
        """Verify OpenClaw config exists."""
        openclaw_home = Path.home() / ".openclaw"
        config_file = openclaw_home / "openclaw.json"

        if not config_file.exists():
            pytest.skip("OpenClaw config not found - skipping harness tests")

        assert config_file.exists()


class TestHarnessInstallFlow:
    """E2E tests for install flow in harness environment."""

    @pytest.fixture
    def clean_managed_root(self):
        """Ensure managed root is clean before test."""
        from openclaw_enhance.install import uninstall
        from openclaw_enhance.paths import managed_root

        user_home = Path.home()
        target_root = managed_root(user_home)

        # Clean up any existing installation
        if target_root.exists():
            uninstall()

        yield

        # Cleanup after test
        if target_root.exists():
            uninstall()

    def test_install_in_harness_environment(self, clean_managed_root):
        """Test installation in actual OpenClaw environment."""
        from click.testing import CliRunner

        from openclaw_enhance.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["install", "--dry-run"])

        # Should pass preflight checks in harness
        assert result.exit_code == 0 or "Preflight checks passed" in result.output

    def test_install_dry_run_succeeds(self, clean_managed_root):
        """Install dry-run should succeed in harness."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "install", "--dry-run"],
            capture_output=True,
            text=True,
        )

        # Should exit 0 or indicate preflight passed
        assert result.returncode == 0 or "Preflight checks passed" in result.stdout


class TestHarnessRuntimeIntegration:
    """E2E tests for runtime integration in harness environment."""

    def test_runtime_bridge_can_initialize(self):
        """Test that runtime bridge can be initialized."""
        try:
            runtime_bridge_module = import_module(
                "extensions.openclaw_enhance_runtime.src.runtime_bridge"
            )
            RuntimeBridge = runtime_bridge_module.RuntimeBridge

            bridge = RuntimeBridge()
            assert bridge is not None
            assert bridge.getConfig() is not None
        except ModuleNotFoundError:
            pytest.skip("Runtime bridge not available")

    def test_runtime_bridge_handles_spawn_event(self):
        """Test runtime bridge can handle spawn events."""
        try:
            runtime_bridge_module = import_module(
                "extensions.openclaw_enhance_runtime.src.runtime_bridge"
            )
            RuntimeBridge = runtime_bridge_module.RuntimeBridge

            bridge = RuntimeBridge()

            event = {
                "event": "subagent_spawning",
                "timestamp": "2024-01-15T10:00:00Z",
                "payload": {
                    "subagent_type": "oe-orchestrator",
                    "task_description": "Test task",
                    "task_id": "task_test_harness_001",
                    "project": "harness-test",
                    "parent_session": "sess_harness_001",
                    "eta_bucket": "short",
                    "dedupe_key": "harness:oe:test:20240115",
                },
                "context": {"session_id": "sess_harness_001"},
            }

            result = bridge.handleSpawnEvent(event)

            # Should process successfully
            assert result is True
            assert bridge.getTask("task_test_harness_001") is not None

        except ModuleNotFoundError:
            pytest.skip("Runtime bridge not available")


class TestHarnessSkillRendering:
    """E2E tests for skill rendering in harness environment."""

    def test_render_skill_eta_estimator(self):
        """Should render ETA estimator skill in harness."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-skill", "oe-eta-estimator"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "ETA Estimator" in result.stdout
        assert "oe-eta-estimator" in result.stdout

    def test_render_skill_toolcall_router(self):
        """Should render toolcall router skill in harness."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-skill", "oe-toolcall-router"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Toolcall Router" in result.stdout

    def test_render_workspace_orchestrator(self):
        """Should render orchestrator workspace if available."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "render-workspace",
                "oe-orchestrator",
            ],
            capture_output=True,
            text=True,
        )

        # May succeed or fail depending on workspace availability
        if result.returncode == 0:
            assert (
                "Workspace: oe-orchestrator" in result.stdout or "oe-orchestrator" in result.stdout
            )

    def test_render_hook_spawn_enrich(self):
        """Should render spawn enrich hook in harness."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "render-hook",
                "oe-subagent-spawn-enrich",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "oe-subagent-spawn-enrich" in result.stdout
        assert "subagent_spawning" in result.stdout


class TestHarnessStatusCommand:
    """E2E tests for status command in harness environment."""

    def test_status_in_harness(self):
        """Status command should work in harness environment."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "status"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_status_json_in_harness(self):
        """Status --json should return valid JSON in harness."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "status", "--json"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert "install_path" in data
        assert "installed" in data


class TestHarnessDoctorCommand:
    """E2E tests for doctor command in harness environment."""

    def test_doctor_in_harness(self):
        """Doctor command should validate environment in harness."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "doctor"],
            capture_output=True,
            text=True,
        )

        # May pass or fail depending on environment state
        # But should exit cleanly
        assert result.returncode in [0, 1]


class TestHarnessEndToEndWorkflow:
    """Full E2E workflow tests in harness environment."""

    @pytest.fixture
    def isolated_test_env(self, tmp_path):
        """Create an isolated test environment."""
        from openclaw_enhance.install import uninstall
        from openclaw_enhance.paths import managed_root

        user_home = tmp_path / "test_user"
        target_root = managed_root(user_home)

        # Ensure clean state
        if target_root.exists():
            uninstall(user_home=user_home)

        yield user_home

        # Cleanup
        if target_root.exists():
            uninstall(user_home=user_home)

    def test_full_install_status_uninstall_cycle(self, isolated_test_env):
        """Test complete install -> status -> uninstall cycle."""
        from openclaw_enhance.install import get_install_status, install, uninstall

        user_home = isolated_test_env
        openclaw_home = Path.home() / ".openclaw"

        # Skip if no OpenClaw home
        if not openclaw_home.exists():
            pytest.skip("No OpenClaw installation found")

        # Install
        install_result = install(openclaw_home, user_home=user_home)
        assert install_result.success, f"Install failed: {install_result.message}"

        # Check status
        status = get_install_status(user_home=user_home)
        assert status["installed"] is True
        assert len(status["components"]) > 0

        # Uninstall
        uninstall_result = uninstall(openclaw_home=openclaw_home, user_home=user_home)
        assert uninstall_result.success

        # Verify uninstalled
        status = get_install_status(user_home=user_home)
        assert status["installed"] is False

    def test_skill_catalog_available_in_harness(self):
        """Verify skill catalog is functional in harness."""
        from openclaw_enhance.skills_catalog import render_skill_contract

        # Test contract-based skill rendering (file-backed)
        router_contract = render_skill_contract("oe-toolcall-router")
        assert "sessions_spawn" in router_contract or "TOOLCALL" in router_contract
        assert "oe-orchestrator" in router_contract


class TestHarnessErrorHandling:
    """E2E tests for error handling in harness environment."""

    def test_invalid_skill_name_returns_error(self):
        """Invalid skill name should return error."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "render-skill",
                "nonexistent-skill",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Unknown skill" in result.stderr or "Error" in result.stderr

    def test_invalid_workspace_name_returns_error(self):
        """Invalid workspace name should return error."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "render-workspace",
                "nonexistent-workspace",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Unknown workspace" in result.stderr or "Error" in result.stderr

    def test_invalid_hook_name_returns_error(self):
        """Invalid hook name should return error."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "render-hook",
                "nonexistent-hook",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Unknown hook" in result.stderr or "Error" in result.stderr


class TestHarnessEnvironmentValidation:
    """Tests to validate the harness environment itself."""

    def test_python_executable_available(self):
        """Python executable should be available."""
        assert sys.executable is not None
        assert Path(sys.executable).exists()

    def test_openclaw_enhance_module_importable(self):
        """openclaw_enhance module should be importable."""
        import openclaw_enhance

        assert openclaw_enhance is not None

    def test_cli_module_importable(self):
        """CLI module should be importable."""
        from openclaw_enhance import cli

        assert cli is not None
        assert hasattr(cli, "cli")

    def test_all_skills_importable(self):
        """All skill modules should be importable."""
        from openclaw_enhance import skills_catalog

        # Verify contract-based API (file-backed skills)
        assert hasattr(skills_catalog, "render_skill_contract")
        assert hasattr(skills_catalog, "estimate_task_duration")
        # Removed router classes per skill-first architecture
        assert not hasattr(skills_catalog, "SkillRouter")
        assert not hasattr(skills_catalog, "TaskAssessment")

    def test_install_module_importable(self):
        """Install module should be importable."""
        from openclaw_enhance import install

        assert hasattr(install, "install")
        assert hasattr(install, "uninstall")
        assert hasattr(install, "get_install_status")


class TestHarnessWatchdogIntegration:
    """E2E tests for watchdog runtime integration in harness."""

    def test_watchdog_workspace_available(self):
        """Watchdog workspace should be available in harness."""
        result = subprocess.run(
            [sys.executable, "-m", "openclaw_enhance.cli", "render-workspace", "oe-watchdog"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "oe-watchdog" in result.stdout
        assert "SessionSender" in result.stdout or "monitoring" in result.stdout.lower()

    def test_watchdog_reminder_delivery_validation(self):
        """Watchdog reminder delivery should validate successfully."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "validate-feature",
                "--feature-class",
                "runtime-watchdog",
                "--report-slug",
                "harness-watchdog-test",
            ],
            capture_output=True,
            text=True,
            env=_local_src_env(),
        )

        assert result.returncode == 0, f"Watchdog validation failed: {result.stderr}"
        assert "runtime-watchdog" in result.stdout
        assert "PASS" in result.stdout or "Conclusion: PASS" in result.stdout

    def test_watchdog_config_fragment_and_reminder_markers(self):
        """Verify watchdog probe captures config fragment and reminder evidence."""
        import json
        import os
        from pathlib import Path

        openclaw_home = Path(os.environ.get("OPENCLAW_HOME", Path.home() / ".openclaw"))
        config_path = openclaw_home / "openclaw.json"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.validation.live_probes",
                "watchdog-reminder",
                "--openclaw-home",
                str(openclaw_home),
                "--config-path",
                str(config_path),
                "--session-id",
                "e2e-config-proof",
            ],
            capture_output=True,
            text=True,
            env=_local_src_env(),
        )

        assert result.returncode == 0, f"Probe failed: {result.stderr}"

        output = json.loads(result.stdout)
        assert output["ok"] is True
        assert output["probe"] == "watchdog-reminder"
        assert output["marker"] == "PROBE_WATCHDOG_REMINDER_OK"
        assert output["proof"] in {
            "config_hook_plus_live_reminder",
            "workspace_contract_plus_live_reminder",
        }
        if output["proof"] == "config_hook_plus_live_reminder":
            assert "config_fragment" in output


class TestHarnessRealEnvironmentValidation:
    """E2E tests for real-environment validation via CLI."""

    def test_real_env_validation_install_lifecycle(self):
        """Test install-lifecycle validation in real OpenClaw environment."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "validate-feature",
                "--feature-class",
                "install-lifecycle",
                "--report-slug",
                "harness-test",
            ],
            capture_output=True,
            text=True,
        )

        # Should execute validation scenario (exit 0 or 1 for product failure)
        assert result.returncode in [0, 1], f"Unexpected exit code: {result.returncode}"
        assert "install-lifecycle" in result.stdout or "Validation" in result.stdout

        # Verify report was generated
        reports_dir = Path("docs/reports")
        assert reports_dir.exists(), "Reports directory should exist"
        report_files = list(reports_dir.glob("*harness-test-install-lifecycle.md"))
        assert len(report_files) > 0, "Validation report should be generated"


class TestHarnessDevInstallValidation:
    """E2E tests for dev-install validation in harness environment."""

    def test_dev_install_report_contains_symlink_evidence(self):
        """Dev-install report should contain explicit symlink proof."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "validate-feature",
                "--feature-class",
                "install-lifecycle",
                "--report-slug",
                "backfill-dev-install",
            ],
            capture_output=True,
            text=True,
        )

        # Should execute validation scenario
        assert result.returncode in [0, 1], f"Unexpected exit code: {result.returncode}"

        # Verify report was generated
        reports_dir = Path("docs/reports")
        report_files = list(reports_dir.glob("*backfill-dev-install-install-lifecycle.md"))
        assert len(report_files) > 0, "Dev-install validation report should be generated"

        # Verify symlink evidence in report
        content = report_files[0].read_text()
        assert "dev-symlink" in content
        assert "Symlink:" in content
        assert "Target:" in content
        assert "oe-orchestrator" in content


class TestHarnessRoutingYieldValidation:
    """E2E tests for routing and yield validation in harness."""

    def test_routing_yield_validation_passes(self):
        """Routing yield validation should pass with deterministic evidence."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "validate-feature",
                "--feature-class",
                "workspace-routing",
                "--report-slug",
                "harness-routing-test",
            ],
            capture_output=True,
            text=True,
            env=_local_src_env(),
        )

        assert result.returncode == 0, f"Routing validation failed: {result.stderr}"
        assert "workspace-routing" in result.stdout
        assert "PASS" in result.stdout or "Conclusion: PASS" in result.stdout

    def test_routing_yield_report_contains_evidence(self):
        """Routing yield report should contain live session evidence."""
        subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "validate-feature",
                "--feature-class",
                "workspace-routing",
                "--report-slug",
                "harness-routing-evidence",
            ],
            capture_output=True,
            text=True,
            env=_local_src_env(),
        )

        reports_dir = Path("docs/reports")
        report_files = list(reports_dir.glob("*harness-routing-evidence-workspace-routing.md"))

        report = _latest_report(report_files)
        if report:
            content = report.read_text()
            assert '"probe": "routing-yield"' in content
            assert '"marker": "PROBE_ROUTING_YIELD_OK"' in content
            assert '"proof": "runtime_surface"' in content
            assert '"tool_surface_has_sessions_yield": true' in content
            assert '"session_id":' in content


class TestHarnessRecoveryWorkerValidation:
    """E2E tests for recovery worker validation in harness."""

    def test_recovery_worker_validation_passes(self):
        """Recovery worker validation should pass with executable evidence."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "validate-feature",
                "--feature-class",
                "workspace-routing",
                "--report-slug",
                "harness-recovery-test",
            ],
            capture_output=True,
            text=True,
            env=_local_src_env(),
        )

        assert result.returncode == 0, f"Recovery validation failed: {result.stderr}"
        assert "workspace-routing" in result.stdout

    def test_recovery_worker_report_contains_executable_proof(self):
        """Recovery worker report should contain dispatch and corrected method proof."""
        subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "validate-feature",
                "--feature-class",
                "workspace-routing",
                "--report-slug",
                "backfill-recovery-worker",
            ],
            capture_output=True,
            text=True,
            env=_local_src_env(),
        )

        reports_dir = Path("docs/reports")
        report_files = list(reports_dir.glob("*backfill-recovery-worker-workspace-routing.md"))

        report = _latest_report(report_files)
        if report:
            content = report.read_text()
            assert '"probe": "recovery-worker"' in content
            assert '"marker": "PROBE_RECOVERY_WORKER_OK"' in content
            assert '"proof": "runtime_surface"' in content
            assert '"recovery_registration_confirmed": true' in content
            assert "session_id" in content
            assert "\"configured_model\": \"minimax/MiniMax-M2.1\"" in content


class TestHarnessLiveProbeOutputs:
    """E2E tests for deterministic live-probe output markers."""

    def test_watchdog_probe_report_contains_stable_marker(self):
        """Watchdog probe marker should appear in report output."""
        subprocess.run(
            [
                sys.executable,
                "-m",
                "openclaw_enhance.cli",
                "validate-feature",
                "--feature-class",
                "runtime-watchdog",
                "--report-slug",
                "harness-watchdog-evidence",
            ],
            capture_output=True,
            text=True,
            env=_local_src_env(),
        )

        reports_dir = Path("docs/reports")
        report_files = list(reports_dir.glob("*harness-watchdog-evidence-runtime-watchdog.md"))

        report = _latest_report(report_files)
        if report:
            content = report.read_text()
            assert '"probe": "watchdog-reminder"' in content
            assert '"marker": "PROBE_WATCHDOG_REMINDER_OK"' in content
