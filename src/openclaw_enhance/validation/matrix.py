"""Shipped-feature coverage matrix for validation."""

from openclaw_enhance.validation.types import FeatureClass

SHIPPED_FEATURES = [
    {
        "slug": "backfill-core-install",
        "feature_class": FeatureClass.INSTALL_LIFECYCLE,
        "capability": "Core Installation",
    },
    {
        "slug": "backfill-dev-install",
        "feature_class": FeatureClass.INSTALL_LIFECYCLE,
        "capability": "Dev Mode (Symlinks)",
    },
    {
        "slug": "backfill-cli-surface",
        "feature_class": FeatureClass.CLI_SURFACE,
        "capability": "CLI Surface Area",
    },
    {
        "slug": "backfill-routing-yield",
        "feature_class": FeatureClass.WORKSPACE_ROUTING,
        "capability": "Orchestrator Yield",
    },
    {
        "slug": "backfill-recovery-worker",
        "feature_class": FeatureClass.WORKSPACE_ROUTING,
        "capability": "Recovery Worker",
    },
    {
        "slug": "backfill-watchdog-reminder",
        "feature_class": FeatureClass.RUNTIME_WATCHDOG,
        "capability": "Watchdog Hooks",
    },
]


def get_feature_entry(slug: str) -> dict | None:
    """Get feature entry by slug."""
    for entry in SHIPPED_FEATURES:
        if entry["slug"] == slug:
            return entry
    return None
