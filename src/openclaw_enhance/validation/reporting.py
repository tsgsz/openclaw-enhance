"""Markdown report generation for validation results."""

from __future__ import annotations

from pathlib import Path

from openclaw_enhance.validation.types import ValidationReport


def generate_markdown_report(report: ValidationReport) -> str:
    """Generate markdown report from ValidationReport."""
    lines = [
        f"# Validation Report: {report.feature_name}",
        "",
        f"- **Date**: {report.timestamp.strftime('%Y-%m-%d')}",
        f"- **Feature Class**: {report.feature_class.value}",
        f"- **Environment**: {report.environment}",
        f"- **Conclusion**: {report.conclusion.value.upper()}",
        "",
        "## Baseline State",
        "",
        f"- OpenClaw Home: `{report.baseline.openclaw_home}`",
        f"- Installed: {report.baseline.is_installed}",
    ]

    if report.baseline.version:
        lines.append(f"- Version: {report.baseline.version}")

    lines.extend(
        [
            f"- Config Exists: {report.baseline.config_exists}",
            "",
            "## Execution Log",
            "",
        ]
    )

    if not report.results:
        lines.append("*No commands executed (exempt or early failure)*")
    else:
        for i, result in enumerate(report.results, 1):
            status = "✓ PASS" if result.is_success else "✗ FAIL"
            lines.extend(
                [
                    f"### Command {i}: {status}",
                    "",
                    f"```bash",
                    f"{result.command}",
                    f"```",
                    "",
                    f"- Exit Code: {result.exit_code}",
                    f"- Duration: {result.duration_seconds:.2f}s",
                    "",
                ]
            )

            if result.stdout:
                lines.extend(
                    [
                        "**stdout:**",
                        "```",
                        result.stdout.strip(),
                        "```",
                        "",
                    ]
                )

            if result.stderr:
                lines.extend(
                    [
                        "**stderr:**",
                        "```",
                        result.stderr.strip(),
                        "```",
                        "",
                    ]
                )

    if report.findings:
        lines.extend(
            [
                "## Findings",
                "",
            ]
        )
        for finding in report.findings:
            lines.append(f"- {finding}")
        lines.append("")

    return "\n".join(lines)


def write_report(report: ValidationReport, output_path: Path) -> None:
    """Write validation report to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = generate_markdown_report(report)
    output_path.write_text(content, encoding="utf-8")
