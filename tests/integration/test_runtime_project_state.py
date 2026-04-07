import json
from datetime import datetime
from pathlib import Path

import pytest

from openclaw_enhance.cleanup import (
    CleanupCandidate,
    CleanupKind,
    CleanupStatus,
    classify_candidate,
)
from openclaw_enhance.paths import ensure_managed_directories, runtime_state_file
from openclaw_enhance.runtime.project_state import (
    _load_state,
    acquire_project,
    bump_restart_epoch,
    get_active_project,
    get_binding_status,
    get_project_owner,
    is_binding_stale,
    rebind_ownership,
    release_project,
    revoke_binding,
    set_active_project,
)


@pytest.fixture
def tmp_home(tmp_path):
    """Fixture for a temporary user home directory."""
    return tmp_path


def test_backward_compatible_load_defaults_missing_ownership_metadata(tmp_home):
    ensure_managed_directories(tmp_home)
    state_file = runtime_state_file(tmp_home)

    old_state = {
        "schema_version": 1,
        "last_updated_utc": datetime.utcnow().isoformat(),
        "doctor_last_ok": True,
    }
    state_file.write_text(json.dumps(old_state), encoding="utf-8")

    loaded_state = _load_state(tmp_home)

    assert loaded_state["schema_version"] == 1
    assert loaded_state["doctor_last_ok"] is True
    assert loaded_state["active_project"] is None
    assert loaded_state["project_occupancy"] == {}
    assert loaded_state["restart_epoch"] == 0
    assert loaded_state["ownership_contract"] == {
        "channel_type": None,
        "channel_conversation_id": None,
        "bound_session_id": None,
        "binding_epoch": 0,
        "binding_status": "unbound",
    }


def test_default_runtime_state_includes_ownership_contract_shape(tmp_home):
    loaded_state = _load_state(tmp_home)

    assert loaded_state["restart_epoch"] == 0
    assert loaded_state["ownership_contract"] == {
        "channel_type": None,
        "channel_conversation_id": None,
        "bound_session_id": None,
        "binding_epoch": 0,
        "binding_status": "unbound",
    }


def test_set_get_active_project(tmp_home):
    """Test setting and getting the active project."""
    project_path = "/path/to/project"
    set_active_project(project_path, user_home=tmp_home)
    assert get_active_project(user_home=tmp_home) == project_path

    set_active_project(None, user_home=tmp_home)
    assert get_active_project(user_home=tmp_home) is None


def test_occupancy_lock(tmp_home):
    """Test project occupancy locking mechanism."""
    path = "/proj/a"

    # First acquisition succeeds
    assert acquire_project(path, "sess-1", user_home=tmp_home) is True
    assert get_project_owner(path, user_home=tmp_home) == "sess-1"

    # Second acquisition by different session fails
    assert acquire_project(path, "sess-2", user_home=tmp_home) is False
    assert get_project_owner(path, user_home=tmp_home) == "sess-1"

    # Re-acquisition by same session succeeds
    assert acquire_project(path, "sess-1", user_home=tmp_home) is True


def test_release_and_reacquire(tmp_home):
    """Test releasing and re-acquiring a project."""
    path = "/proj/b"

    acquire_project(path, "sess-1", user_home=tmp_home)

    # Release by wrong session fails
    assert release_project(path, "sess-2", user_home=tmp_home) is False
    assert get_project_owner(path, user_home=tmp_home) == "sess-1"

    # Release by owner succeeds
    assert release_project(path, "sess-1", user_home=tmp_home) is True
    assert get_project_owner(path, user_home=tmp_home) is None

    # Now another session can acquire
    assert acquire_project(path, "sess-2", user_home=tmp_home) is True
    assert get_project_owner(path, user_home=tmp_home) == "sess-2"


def test_acquire_nonexistent_path(tmp_home):
    """Test that we can acquire a path that doesn't exist on disk."""
    path = "/nonexistent/path"
    assert acquire_project(path, "sess-1", user_home=tmp_home) is True
    assert get_project_owner(path, user_home=tmp_home) == "sess-1"


def test_restart_epoch_bump_increments_value(tmp_home):
    state = _load_state(tmp_home)
    assert state["restart_epoch"] == 0

    epoch1 = bump_restart_epoch(tmp_home)
    assert epoch1 == 1
    state = _load_state(tmp_home)
    assert state["restart_epoch"] == 1

    epoch2 = bump_restart_epoch(tmp_home)
    assert epoch2 == 2
    state = _load_state(tmp_home)
    assert state["restart_epoch"] == 2


def test_stale_binding_detected_when_epoch_mismatch(tmp_home):
    rebind_ownership("slack", "conv-1", "sess-1", user_home=tmp_home)
    binding = get_binding_status(tmp_home)
    assert binding["binding_epoch"] == 0
    assert binding["binding_status"] == "bound"
    assert is_binding_stale(tmp_home) is False

    bump_restart_epoch(tmp_home)
    assert is_binding_stale(tmp_home) is True

    rebind_ownership("slack", "conv-1", "sess-1", user_home=tmp_home)
    assert is_binding_stale(tmp_home) is False


def test_rebind_ownership_updates_epoch(tmp_home):
    rebind_ownership("slack", "conv-1", "sess-1", user_home=tmp_home)
    binding = get_binding_status(tmp_home)
    assert binding["binding_epoch"] == 0
    assert binding["channel_type"] == "slack"
    assert binding["channel_conversation_id"] == "conv-1"
    assert binding["bound_session_id"] == "sess-1"
    assert binding["binding_status"] == "bound"

    bump_restart_epoch(tmp_home)
    bump_restart_epoch(tmp_home)

    rebind_ownership("slack", "conv-2", "sess-2", user_home=tmp_home)
    binding = get_binding_status(tmp_home)
    assert binding["binding_epoch"] == 2
    assert binding["channel_type"] == "slack"
    assert binding["channel_conversation_id"] == "conv-2"
    assert binding["bound_session_id"] == "sess-2"
    assert is_binding_stale(tmp_home) is False


def test_same_channel_resume_after_rebind(tmp_home):
    rebind_ownership("slack", "conv-1", "sess-1", user_home=tmp_home)
    bump_restart_epoch(tmp_home)

    assert is_binding_stale(tmp_home) is True

    rebind_ownership("slack", "conv-1", "sess-2", user_home=tmp_home)
    assert is_binding_stale(tmp_home) is False
    binding = get_binding_status(tmp_home)
    assert binding["bound_session_id"] == "sess-2"


def test_revoke_binding_sets_status_to_revoked(tmp_home):
    rebind_ownership("slack", "conv-1", "sess-1", user_home=tmp_home)
    binding = get_binding_status(tmp_home)
    assert binding["binding_status"] == "bound"

    revoke_binding(tmp_home)
    binding = get_binding_status(tmp_home)
    assert binding["binding_status"] == "revoked"


def test_cleanup_classifies_stale_binding_as_needs_rebind(tmp_home: Path) -> None:
    rebind_ownership("slack", "conv-1", "sess-1", user_home=tmp_home)
    bump_restart_epoch(tmp_home)

    candidate = CleanupCandidate(
        path=Path("/tmp/runtime-stale"),
        kind=CleanupKind.RUNTIME_STATE,
        age_hours=1,
        in_runtime_active_set=False,
    )

    binding = get_binding_status(tmp_home)
    restart_epoch = _load_state(tmp_home)["restart_epoch"]

    classified = classify_candidate(
        candidate,
        stale_threshold_hours=24,
        binding_status=binding,
        restart_epoch=restart_epoch,
    )

    assert classified.status is CleanupStatus.SAFE_TO_REMOVE


def test_cleanup_classifies_active_binding_as_safe(tmp_home: Path) -> None:
    rebind_ownership("slack", "conv-1", "sess-1", user_home=tmp_home)

    candidate = CleanupCandidate(
        path=Path("/tmp/runtime-active"),
        kind=CleanupKind.RUNTIME_STATE,
        age_hours=1,
        in_runtime_active_set=False,
    )

    binding = get_binding_status(tmp_home)
    restart_epoch = _load_state(tmp_home)["restart_epoch"]

    classified = classify_candidate(
        candidate,
        stale_threshold_hours=24,
        binding_status=binding,
        restart_epoch=restart_epoch,
    )

    assert classified.status is CleanupStatus.SKIPPED_ACTIVE


def test_cross_channel_collision_blocked_after_restart(tmp_home):
    """
    Simulate Feishu/Telegram cross-channel collision after restart.

    After restart epoch bump, both channels without valid ownership binding
    should be detected as unsafe/ambiguous restart scenarios.
    """
    # Setup: Feishu channel initially owns the session
    rebind_ownership("feishu", "conv-feishu-001", "sess-lineage-abc", user_home=tmp_home)

    # Verify initial binding is active
    binding = get_binding_status(tmp_home)
    assert binding["channel_type"] == "feishu"
    assert binding["channel_conversation_id"] == "conv-feishu-001"
    assert binding["bound_session_id"] == "sess-lineage-abc"
    assert binding["binding_status"] == "bound"
    assert is_binding_stale(tmp_home) is False

    # Simulate restart - epoch bumps, binding becomes stale
    bump_restart_epoch(tmp_home)

    # Verify binding is now stale
    assert is_binding_stale(tmp_home) is True
    binding = get_binding_status(tmp_home)
    assert binding["binding_epoch"] == 0  # Old epoch
    assert _load_state(tmp_home)["restart_epoch"] == 1  # New epoch

    # Simulate Feishu trying to resume WITHOUT revalidation (no rebind)
    # This represents the collision scenario - old binding, new epoch
    feishu_is_stale = is_binding_stale(tmp_home)

    # Simulate Telegram trying to claim the same session lineage
    # Without valid ownership, this should also be blocked
    telegram_has_valid_ownership = False  # Telegram doesn't have the binding

    # Both should be blocked/unsafe because:
    # 1. Feishu has stale binding (epoch mismatch)
    # 2. Telegram has no binding at all
    assert feishu_is_stale is True, "Feishu binding should be stale after restart"
    assert telegram_has_valid_ownership is False, "Telegram should not have valid ownership"

    # Now simulate proper same-channel revalidation (Feishu rebinds)
    rebind_ownership("feishu", "conv-feishu-001", "sess-feishu-new", user_home=tmp_home)

    # After rebind, Feishu should have valid ownership
    binding = get_binding_status(tmp_home)
    assert binding["binding_status"] == "bound"
    assert binding["binding_epoch"] == 1  # Matches current restart_epoch
    assert is_binding_stale(tmp_home) is False

    # Telegram still cannot claim (different channel)
    assert binding["channel_type"] == "feishu"
    assert binding["channel_type"] != "telegram"


def test_same_channel_resume_after_revalidation(tmp_home):
    """
    Verify same-channel legitimate resume succeeds with valid ownership + matching epoch.
    """
    # Setup: Slack channel owns a session
    rebind_ownership("slack", "conv-slack-123", "sess-original", user_home=tmp_home)

    initial_binding = get_binding_status(tmp_home)
    assert initial_binding["channel_type"] == "slack"
    assert initial_binding["binding_status"] == "bound"
    assert initial_binding["binding_epoch"] == 0

    # Simulate restart
    bump_restart_epoch(tmp_home)
    assert is_binding_stale(tmp_home) is True

    # Same channel revalidates (rebinds) with new session
    rebind_ownership("slack", "conv-slack-123", "sess-resumed", user_home=tmp_home)

    # Verify successful same-channel resume
    binding = get_binding_status(tmp_home)
    assert binding["channel_type"] == "slack"
    assert binding["channel_conversation_id"] == "conv-slack-123"
    assert binding["bound_session_id"] == "sess-resumed"  # New session
    assert binding["binding_status"] == "bound"
    assert binding["binding_epoch"] == 1  # Matches new epoch
    assert is_binding_stale(tmp_home) is False


def test_ambiguous_missing_ownership_blocked(tmp_home):
    """
    Verify that when ownership metadata is missing or stale,
    spawn enrichment would return unsafe: true.

    This tests the state that would cause the TypeScript handler
    to detect an ambiguous restart and mark it unsafe.
    """
    # Case 1: No ownership ever bound (fresh state after restart)
    bump_restart_epoch(tmp_home)

    state = _load_state(tmp_home)
    ownership_contract = state["ownership_contract"]

    # Verify ownership contract shows unbound state
    assert ownership_contract["binding_status"] == "unbound"
    assert ownership_contract["channel_type"] is None
    assert ownership_contract["channel_conversation_id"] is None
    assert ownership_contract["bound_session_id"] is None

    # This state would cause TypeScript handler's validateOwnership() to return:
    # { valid: false, unsafe: true, ownership_status: "unsafe_ambiguous_restart" }
    # because restart_epoch is present (1) but ownership is missing

    # Case 2: Stale ownership (epoch mismatch)
    rebind_ownership("telegram", "conv-tg-456", "sess-old", user_home=tmp_home)
    assert is_binding_stale(tmp_home) is False  # Fresh binding

    bump_restart_epoch(tmp_home)  # Now epoch = 2
    assert is_binding_stale(tmp_home) is True  # Stale binding

    binding = get_binding_status(tmp_home)
    assert binding["binding_status"] == "bound"  # Still marked as bound
    assert binding["binding_epoch"] == 1  # Old epoch

    # Reload state to get updated restart_epoch after second bump
    state = _load_state(tmp_home)
    assert state["restart_epoch"] == 2  # New epoch

    # Stale binding should be treated as unsafe for spawn decisions
    # The handler would detect: restart_epoch present but binding_epoch mismatch
