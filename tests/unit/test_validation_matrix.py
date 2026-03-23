"""Tests for validation matrix module."""

from openclaw_enhance.validation.matrix import SHIPPED_FEATURES, get_feature_entry
from openclaw_enhance.validation.types import FeatureClass


def test_canonical_slugs_present():
    """Verify all canonical backfill slugs are in the matrix."""
    required_slugs = {
        "backfill-core-install",
        "backfill-dev-install",
        "backfill-cli-surface",
        "backfill-routing-yield",
        "backfill-recovery-worker",
        "backfill-main-escalation",
        "backfill-watchdog-reminder",
    }

    actual_slugs = {entry["slug"] for entry in SHIPPED_FEATURES}

    assert required_slugs == actual_slugs, f"Missing slugs: {required_slugs - actual_slugs}"


def test_feature_class_mapping():
    """Verify each entry has valid feature class."""
    for entry in SHIPPED_FEATURES:
        assert "feature_class" in entry
        assert isinstance(entry["feature_class"], FeatureClass)


def test_workspace_routing_canonical_entries_are_distinct():
    workspace_routing_entries = [
        entry
        for entry in SHIPPED_FEATURES
        if entry["feature_class"] == FeatureClass.WORKSPACE_ROUTING
    ]

    assert [entry["slug"] for entry in workspace_routing_entries] == [
        "backfill-routing-yield",
        "backfill-recovery-worker",
        "backfill-main-escalation",
    ]

    main_escalation_entry = get_feature_entry("backfill-main-escalation")
    assert main_escalation_entry is not None
    assert main_escalation_entry["capability"] == "Main-to-Orchestrator Escalation"
    assert (
        "probe emits PROBE_MAIN_ESCALATION_OK marker on success"
        in main_escalation_entry["proof_expectations"]
    )


def test_get_feature_entry_by_slug():
    """Verify lookup by slug works."""
    entry = get_feature_entry("backfill-core-install")
    assert entry is not None
    assert entry["slug"] == "backfill-core-install"
    assert entry["feature_class"] == FeatureClass.INSTALL_LIFECYCLE


def test_get_feature_entry_missing():
    """Verify missing slug returns None."""
    entry = get_feature_entry("nonexistent-slug")
    assert entry is None
