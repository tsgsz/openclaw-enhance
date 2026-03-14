"""Shipped-feature coverage matrix for validation."""

from openclaw_enhance.validation.types import FeatureClass

SHIPPED_FEATURES = [
    {
        "slug": "backfill-core-install",
        "feature_class": FeatureClass.INSTALL_LIFECYCLE,
        "capability": "Core Installation",
        "proof_expectations": [
            "status shows installed: true",
            "doctor checks pass",
            "files exist in ~/.openclaw/openclaw-enhance",
        ],
    },
    {
        "slug": "backfill-dev-install",
        "feature_class": FeatureClass.INSTALL_LIFECYCLE,
        "capability": "Dev Mode (Symlinks)",
        "proof_expectations": [
            "install --dev succeeds",
            "workspaces are symlinked to source",
        ],
    },
    {
        "slug": "backfill-cli-surface",
        "feature_class": FeatureClass.CLI_SURFACE,
        "capability": "CLI Surface Area",
        "proof_expectations": [
            "status output shows installation status",
            "status --json returns valid JSON",
            "doctor command passes",
            "render-workspace shows workspace content",
            "render-skill shows skill definition",
            "render-hook shows hook logic",
            "docs-check passes",
            "validate-feature self-surface produces EXEMPT report",
        ],
    },
    {
        "slug": "backfill-routing-yield",
        "feature_class": FeatureClass.WORKSPACE_ROUTING,
        "capability": "Orchestrator Yield",
        "proof_expectations": [
            "oe-orchestrator workspace renders with sessions_yield references",
            "TestBoundedLoopContract integration tests verify runtime contract",
            "tests programmatically confirm yield primitives and round states exist",
        ],
    },
    {
        "slug": "backfill-recovery-worker",
        "feature_class": FeatureClass.WORKSPACE_ROUTING,
        "capability": "Recovery Worker",
        "proof_expectations": [
            "tool 'websearch' not found triggers recovery dispatch",
            "oe-tool-recovery recommends websearch_web_search_exa",
            "integration test verifies recovery contract",
        ],
    },
    {
        "slug": "backfill-watchdog-reminder",
        "feature_class": FeatureClass.RUNTIME_WATCHDOG,
        "capability": "Watchdog Hooks",
        "proof_expectations": [
            "hooks are registered in config.json",
            "watchdog detects timeouts",
        ],
    },
]


def get_feature_entry(slug: str) -> dict | None:
    """Get feature entry by slug."""
    for entry in SHIPPED_FEATURES:
        if entry["slug"] == slug:
            return entry
    return None
