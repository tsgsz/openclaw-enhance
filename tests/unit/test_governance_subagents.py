import json
from pathlib import Path

import pytest

from openclaw_enhance.governance.subagents import (
    merge_subagent_state,
    read_subagent_state,
    read_subagents,
    set_subagent_eta,
    set_subagent_status,
)


def test_read_helpers_return_defaults_when_files_are_missing(tmp_path: Path) -> None:
    assert read_subagents(tmp_path / "missing-sub_agents.json") == {"version": 1, "sub_agents": []}
    assert read_subagent_state(tmp_path / "missing-sub_agents_state.json") == {
        "version": 1,
        "state": {},
    }


def test_set_subagent_status_updates_only_target_row(tmp_path: Path) -> None:
    path = tmp_path / "sub_agents.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "sub_agents": [
                    {"child_session_id": "child-a", "status": "running", "suggestion": ""},
                    {"child_session_id": "child-b", "status": "running", "suggestion": ""},
                ],
            }
        ),
        encoding="utf-8",
    )

    set_subagent_status(path, "child-b", "done", suggestion="finished")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["sub_agents"][0]["status"] == "running"
    assert payload["sub_agents"][1]["status"] == "done"
    assert payload["sub_agents"][1]["suggestion"] == "finished"


def test_set_subagent_eta_updates_target_row(tmp_path: Path) -> None:
    path = tmp_path / "sub_agents.json"
    path.write_text(
        json.dumps(
            {"version": 1, "sub_agents": [{"child_session_id": "child-a", "status": "running"}]}
        ),
        encoding="utf-8",
    )

    set_subagent_eta(path, "child-a", "15m")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["sub_agents"][0]["eta"] == "15m"


def test_merge_subagent_state_creates_and_updates_child_state(tmp_path: Path) -> None:
    path = tmp_path / "sub_agents_state.json"

    merge_subagent_state(path, "child-a", {"watchdog": {"last_seen": "2026-03-24T00:00:00Z"}})
    merge_subagent_state(path, "child-a", {"status": "suspicious"})

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["state"]["child-a"]["watchdog"] == {"last_seen": "2026-03-24T00:00:00Z"}
    assert payload["state"]["child-a"]["status"] == "suspicious"


def test_set_subagent_status_raises_for_missing_child(tmp_path: Path) -> None:
    path = tmp_path / "sub_agents.json"
    path.write_text(json.dumps({"version": 1, "sub_agents": []}), encoding="utf-8")

    with pytest.raises(KeyError):
        set_subagent_status(path, "missing-child", "done")
