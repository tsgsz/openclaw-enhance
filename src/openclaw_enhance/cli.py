"""CLI entry point for openclaw_enhance."""

import json
import sys
from pathlib import Path

import click

from openclaw_enhance.constants import PACKAGE_NAME, VERSION
from openclaw_enhance.runtime.support_matrix import SupportError, validate_environment


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
def install(openclaw_home: Path, force: bool, dry_run: bool) -> None:
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
        result = install_module.install(openclaw_home, force=force)

        if result.success:
            click.echo(f"Success: {result.message}")
            if result.components_installed:
                click.echo(f"Installed components: {', '.join(result.components_installed)}")
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
    ]

    required_terms = ["sessions_spawn"]
    banned_terms = [
        "SkillRouter",
        "dispatch_task(",
        "dispatch_parallel(",
        "dispatch_with_watchdog(",
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
