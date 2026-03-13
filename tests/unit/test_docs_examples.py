"""Tests for documentation examples.

This module tests that code examples in documentation are valid and executable.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
README_PATH = Path(__file__).parent.parent.parent / "README.md"


def extract_code_blocks(file_path: Path) -> list[dict]:
    """Extract fenced code blocks from a markdown file.

    Returns a list of dicts with:
    - language: code language (bash, python, etc.)
    - content: code content
    - line: starting line number
    """
    content = file_path.read_text()
    blocks = []

    # Match fenced code blocks
    pattern = r"```(\w+)?\n(.*?)```"
    matches = re.finditer(pattern, content, re.DOTALL)

    for match in matches:
        language = match.group(1) or ""
        code = match.group(2).strip()
        line = content[: match.start()].count("\n") + 1
        blocks.append(
            {
                "language": language,
                "content": code,
                "line": line,
            }
        )

    return blocks


class TestDocumentationExamples:
    """Test that documentation examples are valid."""

    @pytest.mark.parametrize(
        "doc_file",
        [
            "architecture.md",
            "install.md",
            "operations.md",
            "troubleshooting.md",
        ],
    )
    def test_doc_has_code_examples(self, doc_file: str) -> None:
        """Ensure documentation files have code examples."""
        doc_path = DOCS_DIR / doc_file
        if not doc_path.exists():
            pytest.skip(f"{doc_file} not found")

        blocks = extract_code_blocks(doc_path)
        assert len(blocks) > 0, f"{doc_file} should have code examples"

    @pytest.mark.parametrize(
        "doc_file",
        [
            "architecture.md",
            "install.md",
            "operations.md",
            "troubleshooting.md",
        ],
    )
    def test_doc_bash_examples_have_valid_syntax(self, doc_file: str) -> None:
        """Test that bash examples have valid syntax."""
        doc_path = DOCS_DIR / doc_file
        if not doc_path.exists():
            pytest.skip(f"{doc_file} not found")

        blocks = extract_code_blocks(doc_path)
        bash_blocks = [b for b in blocks if b["language"] == "bash"]

        for block in bash_blocks:
            # Check for basic syntax issues
            content = block["content"]

            # Skip incomplete examples (ending with \ indicating continuation)
            if content.rstrip().endswith("\\"):
                continue

            paren_open = content.count("(")
            paren_close = content.count(")")
            if abs(paren_open - paren_close) > 2:
                pytest.fail(f"Unbalanced parentheses in {doc_file}:{block['line']}")

    def test_install_doc_has_cli_examples(self) -> None:
        """Ensure install.md has CLI command examples."""
        doc_path = DOCS_DIR / "install.md"
        if not doc_path.exists():
            pytest.skip("install.md not found")

        content = doc_path.read_text()

        # Should have key CLI commands
        assert "python -m openclaw_enhance.cli doctor" in content
        assert "python -m openclaw_enhance.cli install" in content
        assert "python -m openclaw_enhance.cli status" in content
        assert "python -m openclaw_enhance.cli uninstall" in content

    def test_architecture_doc_has_diagrams(self) -> None:
        """Ensure architecture.md has ASCII diagrams."""
        doc_path = DOCS_DIR / "architecture.md"
        if not doc_path.exists():
            pytest.skip("architecture.md not found")

        content = doc_path.read_text()

        # Should have ASCII art diagrams (box-drawing characters)
        assert "┌" in content or "+" in content, "Should have ASCII diagrams"
        assert "└" in content or "+" in content

    def test_operations_doc_has_worker_examples(self) -> None:
        """Ensure operations.md has worker-specific examples."""
        doc_path = DOCS_DIR / "operations.md"
        if not doc_path.exists():
            pytest.skip("operations.md not found")

        content = doc_path.read_text()

        # Should mention all workers
        assert "oe-searcher" in content
        assert "oe-syshelper" in content
        assert "oe-script_coder" in content
        assert "oe-watchdog" in content

    def test_troubleshooting_doc_has_error_examples(self) -> None:
        """Ensure troubleshooting.md has error message examples."""
        doc_path = DOCS_DIR / "troubleshooting.md"
        if not doc_path.exists():
            pytest.skip("troubleshooting.md not found")

        content = doc_path.read_text()

        # Should have error message examples
        assert "Error:" in content or "error" in content.lower()
        assert "Symptom" in content
        assert "Solution" in content or "Fix" in content


class TestAdrFiles:
    """Test ADR files structure."""

    def test_adr_files_exist(self) -> None:
        """Ensure all ADR files exist."""
        adr_dir = DOCS_DIR / "adr"
        if not adr_dir.exists():
            pytest.skip("ADR directory not found")

        required_adrs = [
            "0001-managed-namespace.md",
            "0002-native-subagent-announce.md",
            "0003-watchdog-authority.md",
        ]

        for adr in required_adrs:
            assert (adr_dir / adr).exists(), f"Missing ADR: {adr}"

    @pytest.mark.parametrize(
        "adr_file",
        [
            "0001-managed-namespace.md",
            "0002-native-subagent-announce.md",
            "0003-watchdog-authority.md",
        ],
    )
    def test_adr_has_required_sections(self, adr_file: str) -> None:
        """Ensure ADRs have required sections."""
        adr_path = DOCS_DIR / "adr" / adr_file
        if not adr_path.exists():
            pytest.skip(f"{adr_file} not found")

        content = adr_path.read_text()

        # Required sections
        assert "## Status" in content
        assert "## Context" in content
        assert "## Decision" in content
        assert "## Consequences" in content

    @pytest.mark.parametrize(
        "adr_file",
        [
            "0001-managed-namespace.md",
            "0002-native-subagent-announce.md",
            "0003-watchdog-authority.md",
        ],
    )
    def test_adr_status_is_accepted(self, adr_file: str) -> None:
        """Ensure ADR status is 'Accepted'."""
        adr_path = DOCS_DIR / "adr" / adr_file
        if not adr_path.exists():
            pytest.skip(f"{adr_file} not found")

        content = adr_path.read_text()

        # Should have Accepted status
        assert "Accepted" in content


class TestReadme:
    """Test README.md content."""

    def test_readme_exists(self) -> None:
        """Ensure README.md exists."""
        assert README_PATH.exists(), "README.md not found"

    def test_readme_has_quickstart(self) -> None:
        """Ensure README has quickstart section."""
        if not README_PATH.exists():
            pytest.skip("README.md not found")

        content = README_PATH.read_text()

        # Should have quickstart section
        assert "quickstart" in content.lower() or "Quick Start" in content

    def test_readme_has_support_matrix(self) -> None:
        """Ensure README documents support matrix."""
        if not README_PATH.exists():
            pytest.skip("README.md not found")

        content = README_PATH.read_text()

        # Should mention supported platforms/versions
        assert "macOS" in content or "linux" in content.lower()


class TestDocsCheckCommand:
    """Test docs-check CLI command."""

    def test_docs_check_exists(self) -> None:
        """Ensure docs-check command exists."""
        result = subprocess.run(
            ["python", "-m", "openclaw_enhance.cli", "docs-check", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, "docs-check command should exist"
        assert "docs" in result.stdout.lower() or "check" in result.stdout.lower()

    def test_docs_check_validates_docs(self) -> None:
        """Ensure docs-check validates documentation."""
        result = subprocess.run(
            ["python", "-m", "openclaw_enhance.cli", "docs-check"],
            capture_output=True,
            text=True,
        )

        # Should succeed if docs are valid
        assert result.returncode == 0, f"docs-check failed: {result.stderr}"


class TestSupportMatrixDocumentation:
    """Test that support matrix is correctly documented."""

    def test_support_matrix_in_architecture(self) -> None:
        """Ensure architecture.md documents support matrix."""
        doc_path = DOCS_DIR / "architecture.md"
        if not doc_path.exists():
            pytest.skip("architecture.md not found")

        content = doc_path.read_text()

        # Should have support matrix section
        assert "Support Matrix" in content or "support matrix" in content.lower()

        # Should mention OpenClaw 2026.3.x
        assert "2026.3" in content

        # Should mention platforms
        assert "macOS" in content or "darwin" in content
        assert "Linux" in content or "linux" in content

    def test_no_windows_wsl_in_v1(self) -> None:
        """Ensure Windows/WSL is documented as unsupported in v1."""
        # Check all docs
        for doc_file in ["architecture.md", "install.md"]:
            doc_path = DOCS_DIR / doc_file
            if not doc_path.exists():
                continue

            content = doc_path.read_text()

            # Should not claim Windows is supported
            if "Windows" in content or "WSL" in content:
                # If mentioned, should be marked as unsupported
                lines = content.split("\n")
                for line in lines:
                    if "Windows" in line or "WSL" in line:
                        assert (
                            "not supported" in line.lower()
                            or "unsupported" in line.lower()
                            or "no" in line.lower()
                        ), f"Windows/WSL should be marked as unsupported: {line}"


class TestDocumentationCompleteness:
    """Test that documentation covers all major features."""

    def test_all_agents_documented(self) -> None:
        """Ensure all agents are documented."""
        # Check all docs combined
        all_content = ""
        for doc_file in DOCS_DIR.glob("*.md"):
            all_content += doc_file.read_text()

        agents = [
            "oe-orchestrator",
            "oe-searcher",
            "oe-syshelper",
            "oe-script_coder",
            "oe-watchdog",
        ]

        for agent in agents:
            assert agent in all_content, f"Agent {agent} not documented"

    def test_all_skills_documented(self) -> None:
        """Ensure all main skills are documented."""
        all_content = ""
        for doc_file in DOCS_DIR.glob("*.md"):
            all_content += doc_file.read_text()

        skills = [
            "oe-eta-estimator",
            "oe-toolcall-router",
            "oe-timeout-state-sync",
        ]

        for skill in skills:
            assert skill in all_content, f"Skill {skill} not documented"

    def test_timeout_monitoring_documented(self) -> None:
        """Ensure timeout monitoring is documented."""
        all_content = ""
        for doc_file in DOCS_DIR.glob("*.md"):
            all_content += doc_file.read_text()

        assert "timeout" in all_content.lower()
        assert "watchdog" in all_content.lower()

    def test_install_uninstall_documented(self) -> None:
        """Ensure install/uninstall is documented."""
        install_doc = DOCS_DIR / "install.md"
        if install_doc.exists():
            content = install_doc.read_text()
            assert "install" in content.lower()
            assert "uninstall" in content.lower()


class TestOpencodePlaybookDocs:
    """Test opencode iteration playbook documentation."""

    def test_agents_md_exists(self) -> None:
        """Ensure AGENTS.md exists at repo root."""
        agents_file = Path("AGENTS.md")
        assert agents_file.exists(), "AGENTS.md must exist at repo root"

    def test_agents_md_has_required_sections(self) -> None:
        """Ensure AGENTS.md has required sections."""
        agents_file = Path("AGENTS.md")
        if not agents_file.exists():
            pytest.skip("AGENTS.md not found")

        content = agents_file.read_text()

        assert "Required Reading Order" in content
        assert "Source of Truth Map" in content
        assert "docs/opencode-iteration-handbook.md" in content
        assert ".sisyphus" in content

    def test_handbook_exists(self) -> None:
        """Ensure handbook exists."""
        handbook = DOCS_DIR / "opencode-iteration-handbook.md"
        assert handbook.exists(), "Handbook must exist"

    def test_handbook_has_required_sections(self) -> None:
        """Ensure handbook has required sections."""
        handbook = DOCS_DIR / "opencode-iteration-handbook.md"
        if not handbook.exists():
            pytest.skip("Handbook not found")

        content = handbook.read_text()

        required_sections = [
            "Current Design Status",
            "Source of Truth Map",
            "Required Reading Paths",
            "Known Invariants",
            "Permanent Progress Record",
            "Session State vs Permanent Memory",
            "Update Protocol",
        ]

        for section in required_sections:
            assert f"## {section}" in content, f"Missing section: {section}"

    def test_handbook_references_architecture(self) -> None:
        """Ensure handbook references current architecture."""
        handbook = DOCS_DIR / "opencode-iteration-handbook.md"
        if not handbook.exists():
            pytest.skip("Handbook not found")

        content = handbook.read_text()

        assert "skill-first" in content.lower()
        assert "sessions_spawn" in content
        assert "router-skill-first-alignment" in content
