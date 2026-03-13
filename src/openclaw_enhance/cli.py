"""CLI entry point for openclaw_enhance."""

import sys
from pathlib import Path

import click

from openclaw_enhance.constants import PACKAGE_NAME, VERSION
from openclaw_enhance.runtime.support_matrix import SupportError, validate_environment


@click.group()
@click.version_option(version=VERSION, prog_name=PACKAGE_NAME)
def cli() -> None:
    pass


@cli.command()
def install() -> None:
    """Install OpenClaw hooks and extensions."""
    click.echo("Install command not yet implemented.")


@cli.command()
def uninstall() -> None:
    """Uninstall OpenClaw hooks and extensions."""
    click.echo("Uninstall command not yet implemented.")


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
def status() -> None:
    """Show current OpenClaw installation status."""
    click.echo("Status command not yet implemented.")


@cli.command("render-skill")
@click.argument("skill_name")
def render_skill(skill_name: str) -> None:
    """Render a skill contract by name.

    SKILL_NAME: Name of the skill to render (e.g., oe-toolcall-router)
    """
    from openclaw_enhance.skills_catalog import render_skill_contract, SKILL_CONTRACTS

    try:
        contract = render_skill_contract(skill_name)
        click.echo(contract)
    except ValueError as e:
        available = ", ".join(SKILL_CONTRACTS.keys())
        raise click.ClickException(f"{e}. Available skills: {available}") from e


@cli.command("render-workspace")
@click.argument("workspace_name")
def render_workspace(workspace_name: str) -> None:
    """Render a workspace configuration by name.

    WORKSPACE_NAME: Name of the workspace to render (e.g., oe-orchestrator)
    """
    from openclaw_enhance.workspaces import render_workspace, list_workspaces

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
