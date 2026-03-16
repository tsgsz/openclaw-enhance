"""Command execution and scenario orchestration for real-environment validation."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from openclaw_enhance.validation.guardrails import verify_ownership
from openclaw_enhance.validation.model_pin import pinned_openclaw_runtime_model
from openclaw_enhance.validation.types import (
    BaselineState,
    CommandResult,
    FeatureClass,
    ValidationConclusion,
    ValidationReport,
    get_bundle_commands,
)


def _resolve_config_path(openclaw_home: Path) -> Path:
    openclaw_json = openclaw_home / "openclaw.json"
    if openclaw_json.exists():
        return openclaw_json
    return openclaw_home / "config.json"


def _capture_baseline(openclaw_home: Path) -> BaselineState:
    from openclaw_enhance.install.manifest import load_manifest
    from openclaw_enhance.paths import managed_root

    target_root = managed_root(openclaw_home.parent)
    manifest = load_manifest(target_root)
    is_installed = manifest is not None
    version = manifest.version if manifest else None
    config_path = _resolve_config_path(openclaw_home)

    return BaselineState(
        openclaw_home=openclaw_home,
        is_installed=is_installed,
        version=version,
        config_exists=config_path.exists(),
    )


def execute_command(cmd: str, openclaw_home: Path) -> CommandResult:
    """Execute a single command and capture output.

    Args:
        cmd: Command string to execute.
        openclaw_home: Path to OpenClaw home directory.

    Returns:
        CommandResult with captured output and timing.
    """
    start = time.time()

    env = os.environ.copy()
    project_root = Path(__file__).parent.parent.parent.parent
    config_path = _resolve_config_path(openclaw_home)
    env["OPENCLAW_ENHANCE_WORKSPACES_DIR"] = str(project_root / "workspaces")
    env["OPENCLAW_HOME"] = str(openclaw_home)
    env["OPENCLAW_CONFIG_PATH"] = str(config_path)

    manages_model_pin = "python -m openclaw_enhance.validation.live_probes" in cmd
    if manages_model_pin:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=openclaw_home.parent,
            env=env,
        )
    else:
        with pinned_openclaw_runtime_model(config_path):
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=openclaw_home.parent,
                env=env,
            )
    duration = time.time() - start

    return CommandResult(
        command=cmd,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        duration_seconds=duration,
    )


def run_scenario(
    feature_class: FeatureClass,
    slug: str,
    openclaw_home: Path,
    reports_dir: Path,
) -> ValidationReport:
    """Execute validation scenario for a feature class.

    Args:
        feature_class: Feature class to validate.
        slug: Short identifier for this validation run.
        openclaw_home: Path to OpenClaw home directory.
        reports_dir: Directory to write reports to.

    Returns:
        ValidationReport with execution results.
    """
    if feature_class == FeatureClass.DOCS_TEST_ONLY:
        baseline = BaselineState(openclaw_home=openclaw_home, is_installed=False)
        docs_check_result = execute_command(
            "python -m openclaw_enhance.cli docs-check", openclaw_home
        )
        return ValidationReport(
            feature_name=slug,
            feature_class=feature_class,
            conclusion=ValidationConclusion.EXEMPT,
            environment=f"macOS {openclaw_home}",
            baseline=baseline,
            results=[docs_check_result],
            findings=["Exempt from real-environment testing (docs-check executed for evidence)"],
        )

    baseline = _capture_baseline(openclaw_home)

    initial_guardrail_state = None
    if feature_class == FeatureClass.INSTALL_LIFECYCLE:
        from openclaw_enhance.validation.guardrails import (
            capture_baseline_state as capture_guardrail_state,
        )

        try:
            initial_guardrail_state = capture_guardrail_state(openclaw_home)
            verify_ownership(initial_guardrail_state)
        except Exception as e:
            return ValidationReport(
                feature_name=slug,
                feature_class=feature_class,
                conclusion=ValidationConclusion.ENVIRONMENT_FAILURE,
                environment=f"macOS {openclaw_home}",
                baseline=baseline,
                findings=[f"Readiness check failed: {e}"],
            )

    commands = get_bundle_commands(feature_class, slug)
    results = []

    for cmd in commands:
        result = execute_command(cmd, openclaw_home)
        results.append(result)

        if result.exit_code == 127:
            return ValidationReport(
                feature_name=slug,
                feature_class=feature_class,
                conclusion=ValidationConclusion.ENVIRONMENT_FAILURE,
                environment=f"macOS {openclaw_home}",
                baseline=baseline,
                results=results,
                findings=[f"Environment failure: {cmd} not found"],
            )

    if feature_class == FeatureClass.INSTALL_LIFECYCLE and initial_guardrail_state is not None:
        from openclaw_enhance.validation.guardrails import (
            capture_baseline_state as capture_guardrail_state,
        )
        from openclaw_enhance.validation.guardrails import (
            verify_cleanup_success,
        )

        try:
            final_guardrail_state = capture_guardrail_state(openclaw_home)
            cleanup_ok = verify_cleanup_success(initial_guardrail_state, final_guardrail_state)
            if not cleanup_ok:
                return ValidationReport(
                    feature_name=slug,
                    feature_class=feature_class,
                    conclusion=ValidationConclusion.PRODUCT_FAILURE,
                    environment=f"macOS {openclaw_home}",
                    baseline=baseline,
                    results=results,
                    findings=["Cleanup verification failed: state not restored"],
                )
        except Exception as e:
            return ValidationReport(
                feature_name=slug,
                feature_class=feature_class,
                conclusion=ValidationConclusion.ENVIRONMENT_FAILURE,
                environment=f"macOS {openclaw_home}",
                baseline=baseline,
                results=results,
                findings=[f"Cleanup verification error: {e}"],
            )

    all_passed = all(r.is_success for r in results)
    conclusion = ValidationConclusion.PASS if all_passed else ValidationConclusion.PRODUCT_FAILURE

    return ValidationReport(
        feature_name=slug,
        feature_class=feature_class,
        conclusion=conclusion,
        environment=f"macOS {openclaw_home}",
        baseline=baseline,
        results=results,
    )


def build_report_path(reports_dir: Path, slug: str, feature_class: FeatureClass) -> Path:
    """Generate standard report path.

    Args:
        reports_dir: Directory to write reports to.
        slug: Short identifier for this validation run.
        feature_class: Feature class being validated.

    Returns:
        Path to report file.
    """
    from datetime import datetime

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{date_str}-{slug}-{feature_class.value}.md"
    return reports_dir / filename
