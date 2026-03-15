"""Live validation probes for real-environment testing."""

import sys
from pathlib import Path
import click


@click.group()
def cli():
    """Live validation probes."""
    pass


@cli.command("dev-symlink")
@click.option(
    "--openclaw-home",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    required=True,
    help="Path to OpenClaw home directory",
)
@click.option(
    "--workspace",
    required=True,
    help="Workspace name to check",
)
def dev_symlink(openclaw_home: Path, workspace: str):
    """Verify that a workspace is a symlink and print its target."""
    from openclaw_enhance.paths import managed_root

    # Use the parent of openclaw_home as user_home if it's .openclaw
    user_home = openclaw_home.parent if openclaw_home.name == ".openclaw" else None
    target_root = managed_root(user_home)
    workspace_path = target_root / "workspaces" / workspace

    if not workspace_path.exists():
        click.echo(f"Error: Workspace path {workspace_path} does not exist", err=True)
        sys.exit(1)

    if not workspace_path.is_symlink():
        click.echo(f"Error: Workspace path {workspace_path} is not a symlink", err=True)
        sys.exit(1)

    target = workspace_path.resolve()
    click.echo(f"Symlink: {workspace_path}")
    click.echo(f"Target: {target}")


if __name__ == "__main__":
    cli()
