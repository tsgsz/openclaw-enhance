"""Integration tests for repo layout verification."""

from pathlib import Path

import pytest


class TestRepoLayout:
    """Tests that all planned directories exist."""

    @pytest.mark.parametrize(
        "directory",
        [
            "skills",
            "hooks",
            "extensions",
            "scripts",
            "src",
            "tests",
            "docs",
        ],
    )
    def test_directory_exists(self, directory: str, tmp_path: Path):
        """Each planned directory should exist in repo root."""
        # For integration test, check from repo root
        # Use the directory containing this test file to find repo root
        test_file = Path(__file__)
        repo_root = test_file.parent.parent.parent

        expected_dir = repo_root / directory
        assert expected_dir.exists(), f"Directory '{directory}' does not exist at {expected_dir}"
        assert expected_dir.is_dir(), f"'{directory}' exists but is not a directory"

    def test_src_package_structure(self):
        """Source package should have expected structure."""
        test_file = Path(__file__)
        repo_root = test_file.parent.parent.parent

        package_dir = repo_root / "src" / "openclaw_enhance"
        assert package_dir.exists(), f"Package directory {package_dir} does not exist"

        # Check expected files exist
        expected_files = ["__init__.py", "cli.py", "constants.py"]
        for filename in expected_files:
            file_path = package_dir / filename
            assert file_path.exists(), f"Expected file '{filename}' not found in package"

    def test_tests_directory_structure(self):
        """Tests directory should have unit and integration subdirs."""
        test_file = Path(__file__)
        repo_root = test_file.parent.parent.parent

        tests_dir = repo_root / "tests"

        unit_dir = tests_dir / "unit"
        integration_dir = tests_dir / "integration"

        assert unit_dir.exists(), "tests/unit directory does not exist"
        assert integration_dir.exists(), "tests/integration directory does not exist"
