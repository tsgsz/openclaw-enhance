"""Project type detection and data model."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

try:
    import tomllib  # type: ignore[import-not-found]
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[import-not-found,no-redef]
    except ImportError:
        tomllib = None


class ProjectType(str, Enum):
    """Detected project type based on indicator files."""

    python = "python"
    nodejs = "nodejs"
    rust = "rust"
    go = "go"
    java = "java"
    ruby = "ruby"
    php = "php"
    cpp = "cpp"
    unknown = "unknown"


class ProjectKind(str, Enum):
    """Project lifecycle kind."""

    permanent = "permanent"
    temporary = "temporary"


@dataclass(frozen=True)
class ProjectInfo:
    """Information about a detected project."""

    path: Path
    name: str
    type: ProjectType
    subtype: str = ""
    kind: ProjectKind = ProjectKind.permanent
    indicator_file: str = ""
    indicator_mtime: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


def _parse_pyproject(path: Path) -> tuple[str, str, dict[str, Any]]:
    """Lazy parser for pyproject.toml."""
    if not tomllib:
        return "", "", {}

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return "", "", {}

    name = ""
    subtype = "setuptools"
    metadata = {}

    # Try poetry first
    poetry = data.get("tool", {}).get("poetry", {})
    if poetry:
        name = poetry.get("name", "")
        subtype = "poetry"
        dev_deps = poetry.get("group", {}).get("dev", {}).get("dependencies", {})
        if "pytest" in dev_deps or "pytest" in poetry.get("dev-dependencies", {}):
            metadata["has_pytest"] = True
    else:
        # Try PEP 621 [project]
        project = data.get("project", {})
        if project:
            name = project.get("name", "")
            # Check for pytest in optional-dependencies or dependencies
            deps = str(project.get("dependencies", [])) + str(
                project.get("optional-dependencies", {})
            )
            if "pytest" in deps:
                metadata["has_pytest"] = True

    return name, subtype, metadata


def _parse_package_json(path: Path) -> tuple[str, str, dict[str, Any]]:
    """Lazy parser for package.json."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return "", "", {}

    name = data.get("name", "")
    subtype = "npm"
    metadata = {}

    deps = data.get("dependencies", {})
    dev_deps = data.get("devDependencies", {})
    if "typescript" in deps or "typescript" in dev_deps:
        metadata["has_typescript"] = True

    return name, subtype, metadata


# Mapping filename -> (ProjectType, default_subtype, lazy_parser_or_None)
INDICATOR_MAP: dict[
    str, tuple[ProjectType, str, Callable[[Path], tuple[str, str, dict[str, Any]]] | None]
] = {
    "pyproject.toml": (ProjectType.python, "setuptools", _parse_pyproject),
    "package.json": (ProjectType.nodejs, "npm", _parse_package_json),
    "Cargo.toml": (ProjectType.rust, "cargo", None),
    "go.mod": (ProjectType.go, "module", None),
    "pom.xml": (ProjectType.java, "maven", None),
    "build.gradle": (ProjectType.java, "gradle", None),
    "Gemfile": (ProjectType.ruby, "bundler", None),
    "composer.json": (ProjectType.php, "composer", None),
    "Makefile": (ProjectType.cpp, "make", None),
    "CMakeLists.txt": (ProjectType.cpp, "cmake", None),
}


def detect_project(path: Path) -> ProjectInfo | None:
    """Detect project type from directory."""
    for filename, (ptype, default_subtype, parser) in INDICATOR_MAP.items():
        indicator = path / filename
        if indicator.exists():
            name = path.name
            subtype = default_subtype
            metadata = {}

            if parser:
                p_name, p_subtype, p_metadata = parser(indicator)
                if p_name:
                    name = p_name
                if p_subtype:
                    subtype = p_subtype
                if p_metadata:
                    metadata = p_metadata

            return ProjectInfo(
                path=path.resolve(),
                name=name,
                type=ptype,
                subtype=subtype,
                indicator_file=filename,
                indicator_mtime=indicator.stat().st_mtime,
                metadata=metadata,
            )
    return None


def find_project_root(path: Path) -> Path | None:
    """Walk up from path to find project root.

    Finds .git dir OR first indicator file. .git closest to cwd wins.
    """
    current = path.resolve()
    while current != current.parent:
        # Check for .git first as it's a strong indicator of a project root
        if (current / ".git").exists():
            return current

        # Check for indicators
        for filename in INDICATOR_MAP:
            if (current / filename).exists():
                return current

        current = current.parent

    return None
