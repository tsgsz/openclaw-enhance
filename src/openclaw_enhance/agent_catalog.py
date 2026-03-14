"""Agent catalog and manifest parsing for worker routing."""

import re
from dataclasses import dataclass, field
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

    return AgentManifest(
        agent_id=agent_id,
        workspace=workspace,
        routing=routing,
        is_valid=len(errors) == 0,
        errors=errors,
    )
