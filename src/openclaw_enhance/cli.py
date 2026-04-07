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
@click.option(
    "--target",
    type=click.Choice(["main", "global"]),
    default=None,
    help="Install skills to 'main' workspace or 'global' location",
)
@click.option(
    "--skill",
    "skill_name",
    default=None,
    help="Install specific skill by name (requires --target)",
)
def install(
    openclaw_home: Path,
    force: bool,
    dry_run: bool,
    dev_mode: bool,
    target: str | None,
    skill_name: str | None,
) -> None:
    """Install OpenClaw hooks, extensions, and optionally skills."""
    # Handle skill installation with target
    if target is not None:
        _install_skills(target, skill_name, dry_run)
        return

    # Original hook/extension installation behavior
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


def _inject_soul_to_main() -> None:
    """Inject SOUL content into main's SOUL.md file."""
    openclaw_home = Path.home() / ".openclaw"
    soul_file = openclaw_home / "workspace" / "main" / "SOUL.md"

    soul_content = """<!-- oe-soul-start -->
## Main Agent SOUL

You are the orchestration layer. Your rules:
1. NEVER directly execute large tasks (>5 tool calls or >15 min)
2. ALL complex tasks MUST be delegated via sessions_spawn
3. You only do: analyze → tag → spawn → synthesize
4. ETA must be announced upfront
<!-- oe-soul-end -->
"""

    # Create parent directory if it doesn't exist
    soul_file.parent.mkdir(parents=True, exist_ok=True)

    # Read existing content or start fresh
    if soul_file.exists():
        content = soul_file.read_text(encoding="utf-8")
    else:
        content = ""

    # Check if markers already exist
    if "<!-- oe-soul-start -->" in content and "<!-- oe-soul-end -->" in content:
        click.echo(f"SOUL already present in {soul_file}")
        return

    # Inject SOUL content
    if content:
        new_content = content.rstrip() + "\n\n" + soul_content
    else:
        new_content = soul_content

    soul_file.write_text(new_content, encoding="utf-8")
    click.echo(f"Injected SOUL into {soul_file}")


def _remove_soul_from_main() -> None:
    """Remove SOUL content from main's SOUL.md file."""
    openclaw_home = Path.home() / ".openclaw"
    soul_file = openclaw_home / "workspace" / "main" / "SOUL.md"

    if not soul_file.exists():
        click.echo(f"SOUL file does not exist: {soul_file}")
        return

    content = soul_file.read_text(encoding="utf-8")

    # Check if markers exist
    if "<!-- oe-soul-start -->" not in content or "<!-- oe-soul-end -->" not in content:
        click.echo(f"No SOUL markers found in {soul_file}")
        return

    # Remove content between markers
    lines = content.split("\n")
    result_lines = []
    skip = False

    for line in lines:
        if "<!-- oe-soul-start -->" in line:
            skip = True
            result_lines.append(line)
        elif "<!-- oe-soul-end -->" in line:
            skip = False
            result_lines.append(line)
        elif not skip:
            result_lines.append(line)

    new_content = "\n".join(result_lines).rstrip() + "\n"

    soul_file.write_text(new_content, encoding="utf-8")
    click.echo(f"Removed SOUL from {soul_file}")


def _install_skills(target: str, skill_name: str | None, dry_run: bool) -> None:
    from openclaw_enhance.manifest import add_skill, load_manifest

    openclaw_home = Path.home() / ".openclaw"

    if target == "main":
        skills_dir = openclaw_home / "workspace" / "main" / "skills"
    else:
        skills_dir = openclaw_home / "openclaw-enhance" / "skills"

    skills_dir.mkdir(parents=True, exist_ok=True)

    skills_source = Path(__file__).parent.parent.parent / "skills"

    if not skills_source.exists():
        raise click.ClickException(f"Skills source directory not found: {skills_source}")

    available_skills = [
        d.name for d in skills_source.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    ]

    skills_to_install = [skill_name] if skill_name else available_skills

    for skill in skills_to_install:
        if skill not in available_skills:
            raise click.ClickException(
                f"Skill not found: {skill}. Available: {', '.join(available_skills)}"
            )

        source_dir = skills_source / skill
        target_dir = skills_dir / skill

        if dry_run:
            click.echo(f"[dry-run] Would install skill '{skill}' to {target_dir}")
        else:
            import shutil

            if target_dir.exists():
                shutil.rmtree(target_dir)
            shutil.copytree(source_dir, target_dir)

            location = str(target_dir)
            add_skill(name=skill, location=location)
            click.echo(f"Installed skill '{skill}' to {location}")

    manifest = load_manifest()
    click.echo(f"\nManifest updated. Installed skills: {list(manifest.get('skills', {}).keys())}")

    if target == "main" and not dry_run:
        _inject_soul_to_main()


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
@click.option(
    "--target",
    type=click.Choice(["main", "global"]),
    default=None,
    help="Remove skills from 'main' workspace or 'global' location",
)
def uninstall(openclaw_home: Path | None, force: bool, target: str | None) -> None:
    """Uninstall OpenClaw hooks, extensions, and optionally skills."""
    if target is not None:
        _uninstall_skills(target)
        return

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


def _uninstall_skills(target: str) -> None:
    if target == "main":
        _remove_soul_from_main()

    from openclaw_enhance.manifest import load_manifest, remove_skill

    openclaw_home = Path.home() / ".openclaw"

    if target == "main":
        skills_dir = openclaw_home / "workspace" / "main" / "skills"
    else:
        skills_dir = openclaw_home / "openclaw-enhance" / "skills"

    manifest = load_manifest()
    skills = manifest.get("skills", {})

    removed = []
    for name, info in list(skills.items()):
        if info.get("location", "").startswith(str(skills_dir)):
            import shutil

            skill_path = Path(info["location"])
            if skill_path.exists():
                shutil.rmtree(skill_path)

            remove_skill(name)
            removed.append(name)

    if removed:
        click.echo(f"Removed skills from {skills_dir}: {', '.join(removed)}")
    else:
        click.echo(f"No skills found at {skills_dir}")


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
    from openclaw_enhance.manifest import load_manifest

    install_status = get_install_status()
    manifest = load_manifest()

    if output_json:
        click.echo(json.dumps({"install_status": install_status, "manifest": manifest}, indent=2))
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

        if manifest.get("skills"):
            click.echo(f"\nSkills ({len(manifest['skills'])}):")
            for name, info in manifest["skills"].items():
                click.echo(f"  - {name}: {info.get('location', 'unknown')}")

        if manifest.get("hooks"):
            click.echo(f"\nHooks ({len(manifest['hooks'])}):")
            for name, info in manifest["hooks"].items():
                enabled = "enabled" if info.get("enabled") else "disabled"
                click.echo(f"  - {name}: {enabled}")

        if install_status["locked"]:
            click.echo("\nStatus: Locked")
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
@click.option(
    "--openclaw-home",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Optional OpenClaw home root to scan instead of ./sessions",
)
def cleanup_sessions(
    dry_run: bool,
    execute: bool,
    output_json: bool,
    stale_threshold_hours: float,
    include_core_sessions: bool,
    include_logs: bool,
    openclaw_home: Path | None,
) -> None:
    """Classify and clean stale/orphaned session state."""
    from . import cleanup as cleanup_module
    from .runtime.project_state import _load_state

    effective_dry_run = dry_run or not execute
    del include_logs

    candidates = cleanup_module.discover_cleanup_candidates(
        openclaw_home=openclaw_home,
        working_directory=Path.cwd(),
    )

    state = _load_state()
    binding_status = state.get("ownership_contract", {})
    restart_epoch = state.get("restart_epoch", 0)

    report = cleanup_module.cleanup_paths(
        candidates,
        dry_run=effective_dry_run,
        stale_threshold_hours=stale_threshold_hours,
        include_core_sessions=include_core_sessions,
        binding_status=binding_status,
        restart_epoch=restart_epoch,
    )

    payload = cleanup_module.build_cleanup_report_payload(report)

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
        workspaces = list_workspaces()
        if workspaces:
            available = ", ".join(workspaces)
            raise click.ClickException(f"{e}. Available workspaces: {available}") from e
        else:
            raise click.ClickException(
                f"{e}. No workspaces registered. See docs for how to set up a workspace."
            ) from e


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


@cli.group(help="Manage migrated governance operations under openclaw-enhance.")
def governance() -> None:
    pass


@governance.command(
    "archive-sessions", help="Archive stale session files into an OE-managed archive root."
)
@click.option("--dry-run", is_flag=True, help="Preview archival without moving files")
@click.option("--execute", is_flag=True, help="Actually archive eligible session files")
@click.option("--json", "output_json", is_flag=True, help="Output JSON report")
@click.option("--stale-threshold-hours", type=float, default=24.0, show_default=True)
@click.option("--include-core-sessions", is_flag=True, help="Allow archive of core session files")
@click.option(
    "--archive-root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Override the OE-managed archive destination",
)
def governance_archive_sessions(
    dry_run: bool,
    execute: bool,
    output_json: bool,
    stale_threshold_hours: float,
    include_core_sessions: bool,
    archive_root: Path | None,
) -> None:
    from .governance.archive import archive_paths, discover_session_candidates
    from .governance.paths import managed_archive_root

    effective_dry_run = dry_run or not execute
    target_archive_root = archive_root or managed_archive_root()
    report = archive_paths(
        discover_session_candidates(Path.cwd() / "sessions"),
        archive_root=target_archive_root,
        dry_run=effective_dry_run,
        stale_threshold_hours=stale_threshold_hours,
        include_core_sessions=include_core_sessions,
    )
    payload = {
        "safe_to_archive": report.safe_to_archive,
        "skipped_active": report.skipped_active,
        "skipped_uncertain": report.skipped_uncertain,
        "archived": report.archived,
        "archive_root": report.archive_root,
        "dry_run": report.dry_run,
    }
    if output_json:
        click.echo(json.dumps(payload, indent=2))
        return
    click.echo(f"dry_run={report.dry_run}")
    click.echo(f"safe_to_archive={len(report.safe_to_archive)}")
    click.echo(f"archived={len(report.archived)}")


@governance.group(help="Manage legacy subagent bookkeeping files under OE control.")
def subagents() -> None:
    pass


@subagents.command("mark-done", help="Mark a child session done in the legacy subagent file.")
@click.option("--child", required=True)
@click.option("--suggestion", default="")
@click.option(
    "--subagents-file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
)
def governance_subagents_mark_done(
    child: str, suggestion: str, subagents_file: Path | None
) -> None:
    from .governance.paths import legacy_subagents_file
    from .governance.subagents import set_subagent_status

    target = subagents_file or legacy_subagents_file()
    set_subagent_status(target, child, "done", suggestion=suggestion)
    click.echo(f"updated {child} -> done")


@subagents.command("mark-dead", help="Mark a child session dead in the legacy subagent file.")
@click.option("--child", required=True)
@click.option("--suggestion", required=True)
@click.option(
    "--subagents-file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
)
def governance_subagents_mark_dead(
    child: str, suggestion: str, subagents_file: Path | None
) -> None:
    from .governance.paths import legacy_subagents_file
    from .governance.subagents import set_subagent_status

    target = subagents_file or legacy_subagents_file()
    set_subagent_status(target, child, "dead", suggestion=suggestion)
    click.echo(f"updated {child} -> dead")


@subagents.command(
    "set-status", help="Set arbitrary allowed child status in the legacy subagent file."
)
@click.option("--child", required=True)
@click.option("--status", required=True)
@click.option("--suggestion", default="")
@click.option(
    "--subagents-file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
)
def governance_subagents_set_status(
    child: str,
    status: str,
    suggestion: str,
    subagents_file: Path | None,
) -> None:
    from .governance.paths import legacy_subagents_file
    from .governance.subagents import set_subagent_status

    target = subagents_file or legacy_subagents_file()
    set_subagent_status(target, child, status, suggestion=suggestion)
    click.echo(f"updated {child} -> {status}")


@subagents.command("set-eta", help="Set ETA for a child session in the legacy subagent file.")
@click.option("--child", required=True)
@click.option("--eta", required=True)
@click.option(
    "--subagents-file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
)
def governance_subagents_set_eta(child: str, eta: str, subagents_file: Path | None) -> None:
    from .governance.paths import legacy_subagents_file
    from .governance.subagents import set_subagent_eta

    target = subagents_file or legacy_subagents_file()
    set_subagent_eta(target, child, eta)
    click.echo(f"updated {child} eta")


@subagents.command("merge-state", help="Merge state into the legacy subagent state file.")
@click.option("--child", required=True)
@click.option("--patch-json", required=True)
@click.option(
    "--subagents-state-file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
)
def governance_subagents_merge_state(
    child: str,
    patch_json: str,
    subagents_state_file: Path | None,
) -> None:
    from .governance.paths import legacy_subagents_state_file
    from .governance.subagents import merge_subagent_state

    target = subagents_state_file or legacy_subagents_state_file()
    merge_subagent_state(target, child, json.loads(patch_json))
    click.echo(f"merged state for {child}")


@governance.command(
    "diagnose", help="Run structured governance diagnostics using explicit OpenClaw probes."
)
@click.option("--json", "output_json", is_flag=True)
def governance_diagnose(output_json: bool) -> None:
    from .governance.health import diagnose

    payload = diagnose()
    if output_json:
        click.echo(json.dumps(payload, indent=2))
        return
    click.echo(payload["summary"])


@governance.command(
    "healthcheck", help="Report managed governance health paths and basic environment state."
)
@click.option(
    "--openclaw-home",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=Path.home() / ".openclaw",
)
@click.option("--json", "output_json", is_flag=True)
def governance_healthcheck(openclaw_home: Path, output_json: bool) -> None:
    from .governance.health import healthcheck

    payload = healthcheck(openclaw_home)
    if output_json:
        click.echo(json.dumps(payload, indent=2))
        return
    click.echo(f"openclaw_home={payload['openclaw_home']}")
    click.echo(f"managed_root={payload['managed_root']}")


@governance.command(
    "safe-restart", help="Evaluate restart safety and optionally restart the gateway."
)
@click.option("--dry-run", is_flag=True)
@click.option("--json", "output_json", is_flag=True)
def governance_safe_restart(dry_run: bool, output_json: bool) -> None:
    from .governance.restart import safe_restart

    payload = safe_restart(dry_run=dry_run)
    if output_json:
        click.echo(json.dumps(payload, indent=2))
        return
    click.echo(f"eligible={payload['eligible']}")
    click.echo(f"executed={payload['executed']}")


@governance.command("restart-resume", help="Restart immediately and emit a resume-required result.")
@click.option("--json", "output_json", is_flag=True)
def governance_restart_resume(output_json: bool) -> None:
    from .governance.restart import immediate_restart_resume

    payload = immediate_restart_resume()
    if output_json:
        click.echo(json.dumps(payload, indent=2))
        return
    click.echo(payload["followup"])


@cli.group("eta")
def eta_group() -> None:
    """ETA registry management for human-intuitive expectation protocol."""
    pass


@eta_group.command("register")
@click.option("--task-id", required=True, help="Unique task identifier")
@click.option("--child", "child_session_id", required=True, help="Child session ID")
@click.option("--parent", "parent_session_id", required=True, help="Parent session ID")
@click.option("--minutes", type=int, required=True, help="Estimated minutes to completion")
@click.option(
    "--first-update",
    "first_update_minutes",
    type=int,
    default=None,
    help="Minutes until first update (default: min(3, minutes//3))",
)
def eta_register(
    task_id: str,
    child_session_id: str,
    parent_session_id: str,
    minutes: int,
    first_update_minutes: int | None,
) -> None:
    """Register a new task with its ETA metadata."""
    import sys

    from openclaw_enhance.runtime.eta_registry import TaskETARegistry

    registry = TaskETARegistry()
    try:
        first_update = first_update_minutes or max(1, minutes // 3)
        registry.register(
            task_id=task_id,
            child_session_id=child_session_id,
            parent_session=parent_session_id,
            estimated_minutes=minutes,
            first_update_minutes=first_update,
        )
        click.echo(
            f"Registered task {task_id}: {minutes}min ETA, first update in {first_update}min"
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@eta_group.command("update")
@click.option("--task-id", required=True, help="Task identifier")
@click.option(
    "--state",
    required=True,
    type=click.Choice(["delayed", "blocked", "stalled", "completed_on_time", "completed_late"]),
    help="New state",
)
@click.option("--reason", default="", help="Human-readable reason for state change")
@click.option(
    "--remaining", type=int, default=None, help="New remaining minutes (for delayed/blocked)"
)
def eta_update(task_id: str, state: str, reason: str, remaining: int | None) -> None:
    """Update task state in the ETA registry."""
    import sys

    from openclaw_enhance.runtime.eta_registry import TaskETARegistry
    from openclaw_enhance.runtime.states import TaskState

    state_map = {
        "delayed": TaskState.DELAYED,
        "blocked": TaskState.BLOCKED,
        "stalled": TaskState.STALLED,
        "completed_on_time": TaskState.COMPLETED_ON_TIME,
        "completed_late": TaskState.COMPLETED_LATE,
    }

    registry = TaskETARegistry()
    try:
        record = registry.update_state(
            task_id,
            new_state=state_map[state],
            reason=reason,
            new_remaining_minutes=remaining,
        )
        if record:
            click.echo(f"Updated {task_id} to {state}: {reason}")
        else:
            click.echo(f"Task {task_id} not found", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@eta_group.command("status")
@click.option("--task-id", required=True, help="Task identifier")
def eta_status(task_id: str) -> None:
    """Show current ETA/status of a task."""
    import sys

    from openclaw_enhance.runtime.eta_registry import TaskETARegistry
    from openclaw_enhance.runtime.states import STATE_DESCRIPTIONS, TaskState

    registry = TaskETARegistry()
    record = registry.get(task_id)
    if not record:
        click.echo(f"Task {task_id} not found", err=True)
        sys.exit(1)

    state_label = STATE_DESCRIPTIONS.get(TaskState(record.current_state), record.current_state)
    click.echo(f"Task: {record.task_id}")
    click.echo(f"State: {state_label}")
    if record.new_remaining_minutes is not None:
        click.echo(
            f"ETA: {record.estimated_minutes}min original, "
            f"{record.new_remaining_minutes}min refreshed"
        )
    else:
        click.echo(f"ETA: {record.estimated_minutes}min")
    if record.state_reason:
        click.echo(f"Reason: {record.state_reason}")


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
