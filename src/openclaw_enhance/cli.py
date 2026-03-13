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
