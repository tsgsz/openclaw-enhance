"""Agent catalog and manifest parsing for worker routing."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

VALID_CAPABILITIES = {
    "research",
    "documentation",
    "code_generation",
    "testing",
    "introspection",
    "monitoring",
    "recovery",
}

VALID_MODEL_TIERS = {"cheap", "standard", "premium"}


@dataclass(frozen=True)
class AgentManifest:
    """Metadata for a worker agent extracted from AGENTS.md frontmatter."""

    agent_id: str = ""
    workspace: str = ""
    routing: dict[str, Any] = field(default_factory=dict)
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)


def parse_agent_manifest(content: str) -> AgentManifest:
    """Parse agent manifest from AGENTS.md frontmatter.

    Args:
        content: Full content of AGENTS.md file.

    Returns:
        AgentManifest with parsed data or validation errors.
    """
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)

    if not frontmatter_match:
        return AgentManifest(is_valid=False, errors=["No frontmatter found in content"])

    try:
        data = yaml.safe_load(frontmatter_match.group(1))
    except yaml.YAMLError as e:
        return AgentManifest(is_valid=False, errors=[f"Invalid YAML: {e}"])

    if not isinstance(data, dict):
        return AgentManifest(is_valid=False, errors=["Frontmatter must be a YAML dictionary"])

    errors = []

    agent_id = data.get("agent_id", "")
    if not agent_id:
        errors.append("Missing required field: agent_id")

    workspace = data.get("workspace", "")
    if not workspace:
        errors.append("Missing required field: workspace")

    routing = data.get("routing", {})
    if not routing:
        errors.append("Missing required field: routing")
    elif isinstance(routing, dict):
        capabilities = routing.get("capabilities", [])
        if capabilities:
            invalid_caps = [c for c in capabilities if c not in VALID_CAPABILITIES]
            if invalid_caps:
                errors.append(f"Invalid capabilities: {invalid_caps}")

        model_tier = routing.get("model_tier")
        if model_tier and model_tier not in VALID_MODEL_TIERS:
            errors.append(f"Invalid model_tier: {model_tier}")

    schema_version = data.get("schema_version")
    if not schema_version:
        errors.append("Missing required field: schema_version")

    tool_names = routing.get("tool_names", []) if isinstance(routing, dict) else []
    if tool_names:
        errors.append("Conflicting metadata: tool_names must not contain exact tool names")

    return AgentManifest(
        agent_id=agent_id,
        workspace=workspace,
        routing=routing,
        is_valid=len(errors) == 0,
        errors=errors,
    )


def validate_workspace_manifests(workspace_dir: Path) -> list[str]:
    """Validate all worker AGENTS.md manifests in workspace directory.

    Args:
        workspace_dir: Root directory containing workspaces/ subdirectory.

    Returns:
        List of validation error messages (empty if all valid).
    """
    errors = []
    workspaces_path = workspace_dir / "workspaces"

    if not workspaces_path.exists():
        return [f"Workspaces directory not found: {workspaces_path}"]

    for agents_file in workspaces_path.glob("*/AGENTS.md"):
        # Skip orchestrator - it's not a worker and doesn't need worker frontmatter
        if "oe-orchestrator" in str(agents_file):
            continue

        try:
            content = agents_file.read_text(encoding="utf-8")
            manifest = parse_agent_manifest(content)

            if not manifest.is_valid:
                rel_path = agents_file.relative_to(workspace_dir)
                for error in manifest.errors:
                    errors.append(f"{rel_path}: {error}")
        except Exception as e:
            rel_path = agents_file.relative_to(workspace_dir)
            errors.append(f"{rel_path}: Failed to read file: {e}")

    return errors
