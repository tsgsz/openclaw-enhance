import json
from pathlib import Path
from datetime import datetime

import pytest
from openclaw_enhance.paths import runtime_state_file, ensure_managed_directories
from openclaw_enhance.runtime.project_state import (
    get_active_project,
    set_active_project,
    acquire_project,
    release_project,
    get_project_owner,
)


@pytest.fixture
def tmp_home(tmp_path):
    """Fixture for a temporary user home directory."""
    return tmp_path


def test_backward_compatible_load(tmp_home):
    """Test loading old-format state without new fields."""
    ensure_managed_directories(tmp_home)
    state_file = runtime_state_file(tmp_home)

    old_state = {
        "schema_version": 1,
        "last_updated_utc": datetime.utcnow().isoformat(),
        "doctor_last_ok": True,
    }
    state_file.write_text(json.dumps(old_state), encoding="utf-8")

    # Should return None without error
    assert get_active_project(user_home=tmp_home) is None
    assert get_project_owner("/any/path", user_home=tmp_home) is None


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
