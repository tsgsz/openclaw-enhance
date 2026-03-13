"""CLI entry point for openclaw_enhance."""

import sys

import click

from openclaw_enhance.constants import PACKAGE_NAME, VERSION


@click.group()
@click.version_option(version=VERSION, prog_name=PACKAGE_NAME)
def cli() -> None:
    """OpenClaw Enhance - Hybrid Python/TypeScript toolchain for OpenClaw-native hooks and extensions."""
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
def doctor() -> None:
    """Check system health and diagnose issues."""
    click.echo("Doctor command not yet implemented.")


@cli.command()
def status() -> None:
    """Show current OpenClaw installation status."""
    click.echo("Status command not yet implemented.")


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
