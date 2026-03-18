"""Integration tests for the project CLI command group.

Tests the `openclaw-enhance project` commands using Click's CliRunner
with isolated temp registry files.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from openclaw_enhance.cli import cli


@pytest.fixture
def runner(tmp_path: Path) -> CliRunner:
    """CliRunner with isolated registry via env var."""
    registry_path = tmp_path / "test-registry.json"
    return CliRunner(
        env={"OE_REGISTRY_PATH": str(registry_path)},
    )


@pytest.fixture
def registry_path(tmp_path: Path) -> Path:
    """Return the temp registry path matching the runner env."""
    return tmp_path / "test-registry.json"


class TestProjectListEmpty:
    """project list on empty registry."""

    def test_project_list_empty(self, runner: CliRunner) -> None:
        """List with no registered projects should exit 0 and not error."""
        result = runner.invoke(cli, ["project", "list"], catch_exceptions=False)
        assert result.exit_code == 0, f"Unexpected exit: {result.output}"

    def test_project_list_empty_json(self, runner: CliRunner) -> None:
        """List --json on empty registry should return empty JSON array."""
        result = runner.invoke(cli, ["project", "list", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 0


class TestProjectCreateAndList:
    """project create + project list."""

    def test_project_create_and_list(self, runner: CliRunner, tmp_path: Path) -> None:
        """Create a project then list — it should appear."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        # Add a pyproject.toml so detector works
        (project_dir / "pyproject.toml").write_text('[project]\nname = "my-project"\n')

        # Create
        result = runner.invoke(
            cli,
            [
                "project",
                "create",
                str(project_dir),
                "--name",
                "my-project",
                "--kind",
                "permanent",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, f"Create failed: {result.output}"

        # List
        result = runner.invoke(cli, ["project", "list", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "my-project"
        assert data[0]["kind"] == "permanent"

    def test_project_create_with_github_remote(self, runner: CliRunner, tmp_path: Path) -> None:
        """Create with --github-remote stores the remote URL."""
        project_dir = tmp_path / "remote-proj"
        project_dir.mkdir()
        (project_dir / "package.json").write_text('{"name": "remote-proj"}')

        result = runner.invoke(
            cli,
            [
                "project",
                "create",
                str(project_dir),
                "--name",
                "remote-proj",
                "--kind",
                "temporary",
                "--github-remote",
                "https://github.com/example/remote-proj",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        result = runner.invoke(cli, ["project", "list", "--json"], catch_exceptions=False)
        data = json.loads(result.output)
        assert data[0]["github_remote"] == "https://github.com/example/remote-proj"


class TestProjectScan:
    """project scan."""

    def test_project_scan_detects_python(self, runner: CliRunner, tmp_path: Path) -> None:
        """Scan a directory with pyproject.toml should detect python."""
        project_dir = tmp_path / "pyproj"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text('[project]\nname = "pyproj"\n')

        result = runner.invoke(
            cli,
            ["project", "scan", str(project_dir)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "python" in result.output.lower()

    def test_project_scan_with_register(self, runner: CliRunner, tmp_path: Path) -> None:
        """Scan with --register should persist to registry."""
        project_dir = tmp_path / "regproj"
        project_dir.mkdir()
        (project_dir / "Cargo.toml").write_text("[package]\nname = 'regproj'\n")

        result = runner.invoke(
            cli,
            ["project", "scan", str(project_dir), "--register"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        # Verify it's now in the registry
        result = runner.invoke(cli, ["project", "list", "--json"], catch_exceptions=False)
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["kind"] == "permanent"  # default kind

    def test_project_scan_nonexistent_path(self, runner: CliRunner, tmp_path: Path) -> None:
        """Scan a non-existent path should exit 2."""
        result = runner.invoke(
            cli,
            ["project", "scan", str(tmp_path / "does-not-exist")],
            catch_exceptions=False,
        )
        assert result.exit_code == 2


class TestProjectInfo:
    """project info."""

    def test_project_info_registered(self, runner: CliRunner, tmp_path: Path) -> None:
        """Info on a registered project should exit 0 and show details."""
        project_dir = tmp_path / "infotest"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text('[project]\nname = "infotest"\n')

        # Register first
        runner.invoke(
            cli,
            [
                "project",
                "create",
                str(project_dir),
                "--name",
                "infotest",
                "--kind",
                "permanent",
            ],
            catch_exceptions=False,
        )

        # Info
        result = runner.invoke(
            cli,
            ["project", "info", str(project_dir)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "infotest" in result.output

    def test_project_info_unregistered(self, runner: CliRunner, tmp_path: Path) -> None:
        """Info on an unregistered path should exit 1."""
        result = runner.invoke(
            cli,
            ["project", "info", str(tmp_path / "unknown")],
            catch_exceptions=False,
        )
        assert result.exit_code == 1


class TestProjectListKindFilter:
    """project list --kind filter."""

    def test_project_list_filter_by_kind(self, runner: CliRunner, tmp_path: Path) -> None:
        """List filtered by kind returns only matching projects."""
        # Create permanent project
        perm_dir = tmp_path / "perm"
        perm_dir.mkdir()
        (perm_dir / "pyproject.toml").write_text('[project]\nname = "perm"\n')
        runner.invoke(
            cli,
            ["project", "create", str(perm_dir), "--name", "perm", "--kind", "permanent"],
            catch_exceptions=False,
        )

        # Create temporary project
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        (temp_dir / "package.json").write_text('{"name": "temp"}')
        runner.invoke(
            cli,
            ["project", "create", str(temp_dir), "--name", "temp", "--kind", "temporary"],
            catch_exceptions=False,
        )

        # List all
        result = runner.invoke(cli, ["project", "list", "--json"], catch_exceptions=False)
        all_data = json.loads(result.output)
        assert len(all_data) == 2

        # List permanent only
        result = runner.invoke(
            cli,
            ["project", "list", "--kind", "permanent", "--json"],
            catch_exceptions=False,
        )
        perm_data = json.loads(result.output)
        assert len(perm_data) == 1
        assert perm_data[0]["kind"] == "permanent"

        # List temporary only
        result = runner.invoke(
            cli,
            ["project", "list", "--kind", "temporary", "--json"],
            catch_exceptions=False,
        )
        temp_data = json.loads(result.output)
        assert len(temp_data) == 1
        assert temp_data[0]["kind"] == "temporary"
