"""Unit tests for live_probes helper functions."""

import json
from unittest.mock import MagicMock, patch

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
