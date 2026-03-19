"""Unit tests for project detector."""

import json

from openclaw_enhance.project.detector import (
    ProjectType,
    detect_project,
    find_project_root,
)


def test_detect_python_poetry(tmp_path):
    """Test detect python from pyproject.toml with [tool.poetry]."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.poetry]\nname = "test-project"\n'
        '[tool.poetry.group.dev.dependencies]\npytest = "^7.0.0"',
        encoding="utf-8",
    )

    info = detect_project(tmp_path)
    assert info is not None
    assert info.type == ProjectType.python
    assert info.subtype == "poetry"
    assert info.name == "test-project"
    assert info.metadata.get("has_pytest") is True


def test_detect_nodejs(tmp_path):
    """Test detect nodejs from package.json."""
    package_json = tmp_path / "package.json"
    package_json.write_text(
        json.dumps({"name": "node-project", "devDependencies": {"typescript": "^5.0.0"}}),
        encoding="utf-8",
    )

    info = detect_project(tmp_path)
    assert info is not None
    assert info.type == ProjectType.nodejs
    assert info.subtype == "npm"
    assert info.name == "node-project"
    assert info.metadata.get("has_typescript") is True


def test_detect_rust(tmp_path):
    """Test detect rust from Cargo.toml."""
    cargo_toml = tmp_path / "Cargo.toml"
    cargo_toml.write_text('[package]\nname = "rust-project"', encoding="utf-8")

    info = detect_project(tmp_path)
    assert info is not None
    assert info.type == ProjectType.rust
    assert info.subtype == "cargo"


def test_detect_go(tmp_path):
    """Test detect go from go.mod."""
    go_mod = tmp_path / "go.mod"
    go_mod.write_text("module github.com/test/go-project", encoding="utf-8")

    info = detect_project(tmp_path)
    assert info is not None
    assert info.type == ProjectType.go
    assert info.subtype == "module"


def test_detect_no_markers(tmp_path):
    """Test no markers in empty dir."""
    info = detect_project(tmp_path)
    assert info is None


def test_detect_mixed_markers_priority(tmp_path):
    """Test mixed markers (pyproject.toml + package.json) -> python wins."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "py-project"', encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"name": "node-project"}), encoding="utf-8")

    info = detect_project(tmp_path)
    assert info is not None
    assert info.type == ProjectType.python
    assert info.name == "py-project"


def test_find_project_root_git(tmp_path):
    """Test find_project_root walks up from subdir to parent with .git."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    subdir = tmp_path / "src" / "module"
    subdir.mkdir(parents=True)

    root = find_project_root(subdir)
    assert root == tmp_path.resolve()


def test_find_project_root_nested(tmp_path):
    """Test nested project: subdir with package.json, parent with .git -> subdir indicator wins."""
    # Parent has .git
    (tmp_path / ".git").mkdir()

    # Subdir has package.json
    subdir = tmp_path / "frontend"
    subdir.mkdir()
    (subdir / "package.json").write_text(json.dumps({"name": "frontend"}), encoding="utf-8")

    # find_project_root should find the closest indicator/git
    # In our implementation, we check .git first, then indicators.
    # Wait, the requirement says: ".git closest to cwd wins."
    # My implementation checks .git at current level, then indicators
    # at current level, then moves up.
    # So if subdir has package.json and parent has .git, it should
    # find package.json in subdir first.

    root = find_project_root(subdir)
    assert root == subdir.resolve()


def test_find_project_root_none(tmp_path):
    """Test find_project_root returns None for path with no git/indicators."""
    root = find_project_root(tmp_path)
    assert root is None
