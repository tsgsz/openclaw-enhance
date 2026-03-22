"""CLI entry point for openclaw_enhance."""

import json
import sys
from pathlib import Path

import click

from openclaw_enhance.constants import PACKAGE_NAME, VERSION
from openclaw_enhance.runtime.support_matrix import SupportError, validate_environment
from openclaw_enhance.validation.types import FeatureClass, ValidationConclusion


@click.group()
@click.version_option(version=VERSION, prog_name=PACKAGE_NAME)
def cli() -> None:
    """OpenClaw Enhance - Managed lifecycle for OpenClaw hooks and extensions."""
    pass


@cli.command()
@click.option(
    "--openclaw-home",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=Path.home() / ".openclaw",
    help="Path to OpenClaw home directory",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force reinstall if already installed",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run preflight checks without installing",
)
@click.option(
    "--dev",
    "dev_mode",
    is_flag=True,
    help="Development mode: use symlinks instead of copying files (macOS/Linux only)",
)
def install(openclaw_home: Path, force: bool, dry_run: bool, dev_mode: bool) -> None:
    """Install OpenClaw hooks and extensions."""
    import openclaw_enhance.install as install_module

    # Run preflight checks
    preflight = install_module.preflight_checks(openclaw_home)

    if preflight.warnings:
        for warning in preflight.warnings:
            click.echo(f"Warning: {warning}", err=True)

    if not preflight.passed:
        for error in preflight.errors:
            click.echo(f"Error: {error}", err=True)
        raise click.ClickException("Preflight checks failed")

    if dry_run:
        click.echo("Preflight checks passed. Installation would proceed.")
        return

    try:
        result = install_module.install(openclaw_home, force=force, dev_mode=dev_mode)

        if result.success:
            click.echo(f"Success: {result.message}")
            if result.components_installed:
                click.echo(f"Installed components: {', '.join(result.components_installed)}")

            import os
            import subprocess

            if os.isatty(0):
                click.echo("Restarting gateway to load new extension code...")
                restart_result = subprocess.run(
                    ["openclaw", "gateway", "restart"],
                    capture_output=True,
                    text=True,
                )
                if restart_result.returncode == 0:
                    click.echo("Gateway restarted successfully.")
                else:
                    click.echo(
                        "Warning: Gateway restart failed. "
                        "Run 'openclaw gateway restart' manually to load new code.",
                        err=True,
                    )
        else:
            for error in result.errors:
                click.echo(f"Error: {error}", err=True)
            raise click.ClickException(result.message)

    except install_module.InstallError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command()
@click.option(
    "--openclaw-home",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Path to OpenClaw home directory (optional)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force uninstall even if checks fail",
)
def uninstall(openclaw_home: Path | None, force: bool) -> None:
    """Uninstall OpenClaw hooks and extensions."""
    from openclaw_enhance.install import uninstall as do_uninstall

    try:
        result = do_uninstall(openclaw_home, force=force)

        click.echo(f"Result: {result.message}")

        if result.components_removed:
            click.echo(f"Removed components: {', '.join(result.components_removed)}")

        if result.components_failed:
            click.echo(f"Failed components: {', '.join(result.components_failed)}", err=True)

        if not result.success and not force:
            raise click.ClickException(result.message)

    except Exception as exc:
        raise click.ClickException(f"Uninstall failed: {exc}") from exc


@cli.command()
@click.option(
    "--openclaw-home",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=Path.home() / ".openclaw",
)
def doctor(openclaw_home: Path) -> None:
    """Check system health and diagnose issues."""
    try:
        validate_environment(openclaw_home)
    except SupportError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo("Doctor checks passed.")


@cli.command()
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output in JSON format",
)
def status(output_json: bool) -> None:
    """Show current OpenClaw installation status."""
    from openclaw_enhance.install import get_install_status

    install_status = get_install_status()

    if output_json:
        click.echo(json.dumps(install_status, indent=2))
    else:
        click.echo(f"Installation Path: {install_status['install_path']}")
        click.echo(f"Installed: {'Yes' if install_status['installed'] else 'No'}")

        if install_status["installed"]:
            click.echo(f"Version: {install_status['version']}")
            click.echo(f"Install Time: {install_status.get('install_time', 'N/A')}")

            if install_status["components"]:
                click.echo(f"Components ({len(install_status['components'])}):")
                for component in install_status["components"]:
                    click.echo(f"  - {component}")

        if install_status["locked"]:
            click.echo("Status: Locked")
            if install_status.get("lock_info"):
                lock_info = install_status["lock_info"]
                click.echo(f"  Operation: {lock_info['operation']}")
                click.echo(f"  PID: {lock_info['pid']}")


@cli.command("cleanup-sessions")
@click.option("--dry-run", is_flag=True, help="Preview cleanup without deleting files")
@click.option("--execute", is_flag=True, help="Actually remove safe cleanup targets")
@click.option("--json", "output_json", is_flag=True, help="Output JSON report")
@click.option("--stale-threshold-hours", type=float, default=24.0, show_default=True)
@click.option(
    "--include-core-sessions",
    is_flag=True,
    help="Allow cleanup of eligible OpenClaw core sessions",
)
@click.option("--include-logs", is_flag=True, help="Include related logs when supported")
def cleanup_sessions(
    dry_run: bool,
    execute: bool,
    output_json: bool,
    stale_threshold_hours: float,
    include_core_sessions: bool,
    include_logs: bool,
) -> None:
    """Classify and clean stale/orphaned session state."""
    from openclaw_enhance.cleanup import CleanupCandidate, CleanupKind, cleanup_paths

    effective_dry_run = dry_run or not execute
    del include_logs

    # Minimal first-pass implementation for TDD: discover from ./sessions if present.
    candidates: list[CleanupCandidate] = []
    sessions_root = Path.cwd() / "sessions"
    if sessions_root.exists():
        for path in sessions_root.iterdir():
            candidates.append(
                CleanupCandidate(
                    path=path,
                    kind=CleanupKind.RUNTIME_STATE,
                    age_hours=72,
                    in_runtime_active_set=False,
                    held_by_project_occupancy=False,
                    has_recent_activity=False,
                )
            )

    report = cleanup_paths(
        candidates,
        dry_run=effective_dry_run,
        stale_threshold_hours=stale_threshold_hours,
        include_core_sessions=include_core_sessions,
    )

    payload = {
        "safe_to_remove": report.safe_to_remove,
        "skipped_active": report.skipped_active,
        "skipped_uncertain": report.skipped_uncertain,
        "removed": report.removed,
        "dry_run": report.dry_run,
    }

    if output_json:
        click.echo(json.dumps(payload, indent=2))
    else:
        click.echo(f"dry_run={report.dry_run}")
        click.echo(f"safe_to_remove={len(report.safe_to_remove)}")
        click.echo(f"skipped_active={len(report.skipped_active)}")
        click.echo(f"skipped_uncertain={len(report.skipped_uncertain)}")
        click.echo(f"removed={len(report.removed)}")


@cli.command("render-skill")
@click.argument("skill_name")
def render_skill(skill_name: str) -> None:
    """Render a skill contract by name.

    SKILL_NAME: Name of the skill to render (e.g., oe-toolcall-router)
    """
    from openclaw_enhance.skills_catalog import render_skill_contract

    try:
        contract = render_skill_contract(skill_name)
        click.echo(contract)
    except ValueError as e:
        raise click.ClickException(str(e)) from e


@cli.command("render-workspace")
@click.argument("workspace_name")
def render_workspace(workspace_name: str) -> None:
    """Render a workspace configuration by name.

    WORKSPACE_NAME: Name of the workspace to render (e.g., oe-orchestrator)
    """
    from openclaw_enhance.workspaces import list_workspaces, render_workspace

    try:
        rendered = render_workspace(workspace_name)
        click.echo(rendered)
    except ValueError as e:
        available = ", ".join(list_workspaces()) if list_workspaces() else "none"
        raise click.ClickException(f"{e}. Available workspaces: {available}") from e


# Registry of hook contracts for rendering
HOOK_CONTRACTS: dict[str, str] = {
    "oe-subagent-spawn-enrich": """---
name: oe-subagent-spawn-enrich
version: 1.0.0
event: subagent_spawning
priority: 100
description: Enriches subagent spawn events with task metadata
---

# oe-subagent-spawn-enrich Hook

Enriches `subagent_spawning` events with enhanced metadata for tracking and deduplication.

## Event Subscription

```yaml
hooks:
  - event: subagent_spawning
    handler: oe-subagent-spawn-enrich
    priority: 100
```

## Enrichment Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Unique identifier for this task invocation |
| `project` | string | Project context from runtime state |
| `parent_session` | string | Parent session ID that initiated the spawn |
| `eta_bucket` | string | Categorized ETA: "short" (<5min), "medium" (5-30min), "long" (>30min) |
| `dedupe_key` | string | Deterministic key for duplicate detection |

## Handler Interface

```typescript
interface SpawnEnrichInput {
  event: 'subagent_spawning';
  payload: {
    subagent_type: string;
    task_description: string;
    estimated_toolcalls?: number;
    estimated_duration_minutes?: number;
  };
  context: {
    session_id: string;
    project?: string;
    parent_session?: string;
  };
}

interface SpawnEnrichOutput {
  enriched_payload: {
    task_id: string;
    project: string;
    parent_session: string;
    eta_bucket: 'short' | 'medium' | 'long';
    dedupe_key: string;
  };
}
```

## Usage Example

```typescript
import { handler } from './handler';

const result = handler({
  event: 'subagent_spawning',
  payload: {
    subagent_type: 'oe-orchestrator',
    task_description: 'Refactor auth module',
    estimated_toolcalls: 5,
  },
  context: {
    session_id: 'sess_001',
    project: 'my-project',
  },
});

// result.enriched_payload:
// {
//   task_id: 'task_abc123_xyz789',
//   project: 'my-project',
//   parent_session: 'sess_001',
//   eta_bucket: 'medium',
//   dedupe_key: 'my-project:oe-orchestrator:a1b2c3d4:20240115'
// }
```

## Integration

This hook is consumed by the `openclaw-enhance-runtime` extension via the RuntimeBridge.
""",
}


def render_hook_contract(hook_name: str) -> str:
    """Render the contract for a hook.

    Args:
        hook_name: Name of the hook to render.

    Returns:
        Rendered hook contract as markdown string.

    Raises:
        ValueError: If hook name is unknown.
    """
    if hook_name not in HOOK_CONTRACTS:
        raise ValueError(f"Unknown hook: {hook_name}")
    return HOOK_CONTRACTS[hook_name]


@cli.command("render-hook")
@click.argument("hook_name")
def render_hook(hook_name: str) -> None:
    """Render a hook contract by name.

    HOOK_NAME: Name of the hook to render (e.g., oe-subagent-spawn-enrich)
    """
    try:
        contract = render_hook_contract(hook_name)
        click.echo(contract)
    except ValueError as e:
        available = ", ".join(HOOK_CONTRACTS.keys())
        raise click.ClickException(f"{e}. Available hooks: {available}") from e


@cli.command("docs-check")
def docs_check() -> None:
    """Validate documentation aligns with skill-first model."""
    from pathlib import Path

    src_dir = Path(__file__).parent
    project_root = src_dir.parent.parent

    target_files = [
        project_root / "AGENTS.md",
        project_root / "README.md",
        project_root / "docs" / "architecture.md",
        project_root / "docs" / "install.md",
        project_root / "docs" / "operations.md",
        project_root / "docs" / "troubleshooting.md",
        project_root / "docs" / "adr" / "0002-native-subagent-announce.md",
        project_root / "docs" / "opencode-iteration-handbook.md",
        project_root / "docs" / "testing-playbook.md",
        project_root / "docs" / "reports" / "INVENTORY.md",
    ]

    required_terms = ["sessions_spawn"]
    banned_terms = [
        "SkillRouter",
        "dispatch_task(",
        "dispatch_parallel(",
        "dispatch_with_watchdog(",
        "validate-feature --class",
    ]

    errors: list[str] = []

    missing_files = [f.relative_to(project_root) for f in target_files if not f.exists()]
    if missing_files:
        for mf in missing_files:
            errors.append(f"Missing file: {mf}")

    if errors:
        for err in errors:
            click.echo(f"Error: {err}", err=True)
        raise click.ClickException("Docs check failed")

    file_contents: dict[Path, str] = {}
    for f in target_files:
        try:
            content = f.read_text(encoding="utf-8")
            file_contents[f] = content
        except Exception as e:
            errors.append(f"Failed to read {f.relative_to(project_root)}: {e}")

    if errors:
        for err in errors:
            click.echo(f"Error: {err}", err=True)
        raise click.ClickException("Docs check failed")

    found_required = False
    for term in required_terms:
        for f, content in file_contents.items():
            if term in content:
                found_required = True
                break
        if found_required:
            break

    if not found_required:
        term = required_terms[0]
        errors.append(
            f"Required term not found: '{term}' must appear in at least one documentation file"
        )

    for term in banned_terms:
        for f, content in file_contents.items():
            if term in content:
                rel_path = f.relative_to(project_root)
                errors.append(f"Banned term '{term}' found in {rel_path}")

    agents_file = project_root / "AGENTS.md"
    if agents_file.exists():
        agents_content = agents_file.read_text(encoding="utf-8")
        if "opencode-iteration-handbook.md" not in agents_content:
            errors.append("AGENTS.md must link to docs/opencode-iteration-handbook.md")

    handbook_file = project_root / "docs" / "opencode-iteration-handbook.md"
    if handbook_file.exists():
        handbook_content = handbook_file.read_text(encoding="utf-8")
        required_handbook_sections = [
            "Current Design Status",
            "Source of Truth Map",
            "Permanent Progress Record",
            "Session State vs Permanent Memory",
            "Update Protocol",
        ]
        for section in required_handbook_sections:
            if f"## {section}" not in handbook_content:
                errors.append(f"Handbook missing required section: {section}")
    else:
        errors.append("Missing required file: docs/opencode-iteration-handbook.md")

    from openclaw_enhance.agent_catalog import validate_workspace_manifests

    manifest_errors = validate_workspace_manifests(project_root)
    if manifest_errors:
        errors.extend(manifest_errors)

    if errors:
        for err in errors:
            click.echo(f"Error: {err}", err=True)
        raise click.ClickException("Docs check failed")

    click.echo("Docs check passed.")


@cli.command("validate-feature")
@click.option(
    "--feature-class",
    type=click.Choice([fc.value for fc in FeatureClass]),
    required=True,
    help="Feature class to validate",
)
@click.option(
    "--report-slug",
    required=True,
    help="Short identifier for this validation run",
)
@click.option(
    "--openclaw-home",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=Path.home() / ".openclaw",
    help="Path to OpenClaw home directory",
)
@click.option(
    "--reports-dir",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=Path("docs/reports"),
    help="Directory to write reports to",
)
def validate_feature(
    feature_class: str,
    report_slug: str,
    openclaw_home: Path,
    reports_dir: Path,
) -> None:
    """Run real-environment validation for a feature."""
    from openclaw_enhance.validation.reporting import write_report
    from openclaw_enhance.validation.runner import run_scenario

    fc = FeatureClass(feature_class)

    click.echo(f"Running validation for {fc.value} (slug: {report_slug})...")

    report = run_scenario(
        feature_class=fc,
        slug=report_slug,
        openclaw_home=openclaw_home,
        reports_dir=reports_dir,
    )

    report_path = report.get_report_path(reports_dir, report_slug)
    write_report(report, report_path)

    click.echo(f"Report written to: {report_path}")
    click.echo(f"Conclusion: {report.conclusion.value.upper()}")

    if report.conclusion in (ValidationConclusion.PASS, ValidationConclusion.EXEMPT):
        return

    sys.exit(1)


_REGISTRY_PATH_ENVVAR = "OE_REGISTRY_PATH"


def _resolve_registry_path() -> Path:
    import os

    from openclaw_enhance.paths import managed_root

    env_path = os.environ.get(_REGISTRY_PATH_ENVVAR)
    if env_path:
        return Path(env_path)
    return managed_root() / "project-registry.json"


@cli.group()
def project() -> None:
    """Manage project registry (list, scan, create, info)."""
    pass


@project.command("list")
@click.option(
    "--kind",
    type=click.Choice(["permanent", "temporary", "all"]),
    default="all",
    help="Filter by project kind (default: all)",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON array")
def project_list(kind: str, output_json: bool) -> None:
    """List registered projects."""
    from openclaw_enhance.project.registry import ProjectRegistry

    registry = ProjectRegistry(_resolve_registry_path())
    kind_filter = None if kind == "all" else kind
    projects = registry.list_projects(kind=kind_filter)

    if output_json:
        click.echo(json.dumps(projects, indent=2, default=str))
        return

    if not projects:
        click.echo("No projects registered.")
        return

    header = f"{'Name':<30} {'Type':<12} {'Kind':<12} {'Path'}"
    click.echo(header)
    click.echo("-" * len(header))
    for p in projects:
        click.echo(
            f"{p.get('name', '?'):<30} "
            f"{p.get('type', '?'):<12} "
            f"{p.get('kind', '?'):<12} "
            f"{p.get('path', '?')}"
        )


@project.command("scan")
@click.argument("path", type=click.Path(exists=False))
@click.option(
    "--kind",
    type=click.Choice(["permanent", "temporary"]),
    default="permanent",
    help="Kind to assign if registering (default: permanent)",
)
@click.option("--register", is_flag=True, help="Persist detected project to registry")
def project_scan(path: str, kind: str, register: bool) -> None:
    """Detect project type at PATH."""
    from openclaw_enhance.project.detector import detect_project
    from openclaw_enhance.project.registry import ProjectRegistry

    target = Path(path).resolve()
    if not target.exists():
        click.echo(f"Error: path does not exist: {target}", err=True)
        sys.exit(2)

    info = detect_project(target)
    if info is None:
        click.echo(f"No project detected at {target}")
        sys.exit(0)

    click.echo(f"Detected: {info.type.value}")
    click.echo(f"Name:     {info.name}")
    click.echo(f"Subtype:  {info.subtype}")

    if register:
        registry = ProjectRegistry(_resolve_registry_path())
        registry.register(info, kind=kind)
        click.echo(f"Registered as {kind} project.")


@project.command("info")
@click.argument("path", type=click.Path(exists=False))
def project_info(path: str) -> None:
    """Show full project details from registry."""
    from openclaw_enhance.project.registry import ProjectRegistry

    target = Path(path).resolve()
    registry = ProjectRegistry(_resolve_registry_path())
    entry = registry.get(target)

    if entry is None:
        click.echo(f"Project not in registry: {target}", err=True)
        sys.exit(1)

    for key, value in entry.items():
        click.echo(f"{key}: {value}")


@project.command("create")
@click.argument("path", type=click.Path(exists=False))
@click.option("--name", required=True, help="Project name")
@click.option(
    "--kind",
    type=click.Choice(["permanent", "temporary"]),
    required=True,
    help="Project kind",
)
@click.option("--github-remote", default=None, help="GitHub remote URL")
def project_create(path: str, name: str, kind: str, github_remote: str | None) -> None:
    """Manually register a project at PATH."""
    from openclaw_enhance.project.detector import ProjectInfo, ProjectType, detect_project
    from openclaw_enhance.project.registry import ProjectRegistry

    target = Path(path).resolve()

    info = detect_project(target)
    if info is None:
        info = ProjectInfo(
            path=target,
            name=name,
            type=ProjectType.unknown,
        )

    registry = ProjectRegistry(_resolve_registry_path())
    registry.register(info, kind=kind, github_remote=github_remote)
    click.echo(f"Project '{name}' registered at {target} (kind={kind})")


def main() -> int:
    """Main entry point for the CLI."""
    try:
        cli()
        return 0
    except click.ClickException as e:
        e.show()
        return e.exit_code
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
