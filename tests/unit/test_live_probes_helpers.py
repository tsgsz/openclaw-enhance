"""Unit tests for live_probes helper functions."""

import json
import os
from unittest.mock import MagicMock, patch

from openclaw_enhance.validation import live_probes
from openclaw_enhance.validation.live_probes import (
    _ensure_bootstrap_ready,
    _get_transcript_path,
    _search_transcript,
)


class TestGetTranscriptPath:
    """Tests for _get_transcript_path helper."""

    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_extracts_transcript_path_from_sessions_json(self, mock_run, tmp_path):
        """Should extract transcriptPath from sessions JSON."""
        sessions_json = {
            "sessions": [
                {
                    "sessionId": "test-session-123",
                    "transcriptPath": (
                        "~/.openclaw/agents/oe-orchestrator/sessions/test-session-123.jsonl"
                    ),
                }
            ]
        }
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(sessions_json), stderr="")

        result = _get_transcript_path("oe-orchestrator", "test-session-123", tmp_path, {})

        assert result is not None
        assert "test-session-123.jsonl" in str(result)

    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_returns_none_when_session_not_found(self, mock_run, tmp_path):
        """Should return None when session ID not in list."""
        sessions_json = {"sessions": [{"sessionId": "other-session", "transcriptPath": "/path"}]}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(sessions_json), stderr="")

        result = _get_transcript_path("oe-orchestrator", "missing-session", tmp_path, {})

        assert result is None

    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_falls_back_to_default_transcript_location(self, mock_run, tmp_path):
        transcript = tmp_path / "agents" / "oe-orchestrator" / "sessions" / "test-session-123.jsonl"
        transcript.parent.mkdir(parents=True)
        transcript.write_text("{}\n", encoding="utf-8")
        sessions_json = {"sessions": [{"sessionId": "test-session-123"}]}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(sessions_json), stderr="")

        result = _get_transcript_path("oe-orchestrator", "test-session-123", tmp_path, {})

        assert result == transcript


class TestSearchTranscript:
    """Tests for _search_transcript helper."""

    def test_finds_terms_in_transcript(self, tmp_path):
        """Should find all search terms in transcript."""
        transcript = tmp_path / "test.jsonl"
        transcript.write_text('{"tool": "sessions_yield"}\n{"agent": "oe-orchestrator"}\n')

        result = _search_transcript(transcript, "sessions_yield", "oe-orchestrator")

        assert result is True

    def test_returns_false_when_term_missing(self, tmp_path):
        """Should return False when any term is missing."""
        transcript = tmp_path / "test.jsonl"
        transcript.write_text('{"tool": "sessions_yield"}\n')

        result = _search_transcript(transcript, "sessions_yield", "missing_term")

        assert result is False

    def test_returns_false_when_file_missing(self, tmp_path):
        """Should return False when transcript file doesn't exist."""
        transcript = tmp_path / "nonexistent.jsonl"

        result = _search_transcript(transcript, "any_term")

        assert result is False


class TestEnsureBootstrapReady:
    """Tests for _ensure_bootstrap_ready helper."""

    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_returns_true_when_no_bootstrap_file(self, mock_run, tmp_path):
        """Should return True when BOOTSTRAP.md doesn't exist."""
        workspace = tmp_path / "openclaw-enhance" / "workspaces" / "oe-orchestrator"
        workspace.mkdir(parents=True)

        result = _ensure_bootstrap_ready("oe-orchestrator", tmp_path, {})

        assert result is True
        mock_run.assert_not_called()

    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_attempts_bootstrap_when_file_exists(self, mock_run, tmp_path):
        """Should attempt bootstrap via CLI when BOOTSTRAP.md exists."""
        workspace = tmp_path / "openclaw-enhance" / "workspaces" / "oe-orchestrator"
        workspace.mkdir(parents=True)
        bootstrap_file = workspace / "BOOTSTRAP.md"
        bootstrap_file.write_text("Bootstrap required")

        mock_run.return_value = MagicMock(returncode=0)

        _ensure_bootstrap_ready("oe-orchestrator", tmp_path, {})

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "openclaw" in call_args
        assert "agent" in call_args
        assert "--agent" in call_args
        assert "oe-orchestrator" in call_args


class TestMainSessionCommand:
    @patch("openclaw_enhance.validation.live_probes._resolve_main_session_entrypoint")
    def test_build_main_command_includes_session_id(self, mock_entrypoint):
        mock_entrypoint.return_value = "agent"

        build_main_cmd = getattr(live_probes, "_build_main_session_command")
        cmd = build_main_cmd(
            "main-escalation",
            "hello",
            {},
            "session-abc",
        )

        assert cmd[:4] == ["openclaw", "agent", "--agent", "main"]
        assert "--session-id" in cmd
        assert "session-abc" in cmd


class TestMainSessionExtraction:
    def test_extract_main_session_id_prefers_agent_meta(self):
        parsed = {
            "result": {
                "meta": {
                    "agentMeta": {"sessionId": "agent-meta-id"},
                    "systemPromptReport": {"sessionId": "system-prompt-id"},
                }
            }
        }

        extract_main_session_id = getattr(live_probes, "_extract_main_session_id")
        assert extract_main_session_id(parsed) == "agent-meta-id"


class TestTranscriptDeltaSearch:
    def test_search_transcript_segment_respects_start_line(self, tmp_path):
        transcript = tmp_path / "probe.jsonl"
        transcript.write_text(
            "old line sessions_spawn\nnew line oe-orchestrator\n", encoding="utf-8"
        )

        search_segment = getattr(live_probes, "_search_transcript_segment")
        assert search_segment(transcript, 1, "sessions_spawn") is True
        assert search_segment(transcript, 2, "sessions_spawn") is False

    def test_latest_main_transcript_snapshot_returns_newest(self, tmp_path):
        sessions_dir = tmp_path / "agents" / "main" / "sessions"
        sessions_dir.mkdir(parents=True)
        old_file = sessions_dir / "old.jsonl"
        new_file = sessions_dir / "new.jsonl"
        old_file.write_text("old\n", encoding="utf-8")
        new_file.write_text("new\n", encoding="utf-8")

        old_stat = old_file.stat()
        new_stat = new_file.stat()
        old_file.touch()
        new_file.touch()
        os.utime(old_file, (old_stat.st_atime, old_stat.st_mtime - 10))
        os.utime(new_file, (new_stat.st_atime, new_stat.st_mtime + 10))

        latest_snapshot = getattr(live_probes, "_latest_main_transcript_snapshot")
        snapshot = latest_snapshot(tmp_path)
        assert snapshot is not None
        transcript_path, line_count = snapshot
        assert transcript_path == new_file
        assert line_count == 1
