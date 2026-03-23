"""Unit tests for live_probes helper functions."""

import json
import os
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from openclaw_enhance.validation import live_probes
from openclaw_enhance.validation.live_probes import (
    _ensure_bootstrap_ready,
    _get_transcript_path,
    _probe_env,
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

    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_extracts_transcript_path_when_sessions_output_has_trailing_logs(
        self, mock_run, tmp_path
    ):
        sessions_json = {
            "sessions": [
                {
                    "sessionId": "test-session-123",
                    "transcriptPath": "/tmp/test-session-123.jsonl",
                }
            ]
        }
        mixed_output = json.dumps(sessions_json) + "\n[plugins] loaded extension\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=mixed_output, stderr="")

        result = _get_transcript_path("oe-orchestrator", "test-session-123", tmp_path, {})

        assert result is not None
        assert str(result).endswith("test-session-123.jsonl")


class TestProbeEnv:
    def test_sets_pinned_openclaw_paths_when_home_is_dot_openclaw(self, tmp_path):
        openclaw_home = tmp_path / ".openclaw"
        openclaw_home.mkdir(parents=True)

        env = _probe_env(openclaw_home)

        assert env["OPENCLAW_HOME"] == str(openclaw_home.parent)
        assert env["OPENCLAW_CONFIG_PATH"] == str(openclaw_home / "config.json")


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

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=1, stdout="", stderr=""),
        ]

        _ensure_bootstrap_ready("oe-orchestrator", tmp_path, {})

        assert mock_run.call_count >= 1
        call_args = mock_run.call_args_list[0][0][0]
        assert "openclaw" in call_args
        assert "agent" in call_args
        assert "--agent" in call_args
        assert "oe-orchestrator" in call_args
        assert "--local" in call_args
        assert "oe-orchestrator-bootstrap" in call_args

    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_allows_stale_bootstrap_markers_when_runtime_is_runnable(
        self,
        mock_run,
        tmp_path,
    ):
        workspace = tmp_path / "openclaw-enhance" / "workspaces" / "oe-orchestrator"
        workspace.mkdir(parents=True)
        (workspace / "BOOTSTRAP.md").write_text("Bootstrap required", encoding="utf-8")
        (workspace / "IDENTITY.md").write_text(
            "# Identity\n_(pick something you like)_\n",
            encoding="utf-8",
        )

        runtime_ready_output = {
            "result": {
                "meta": {
                    "agentMeta": {"sessionId": "runtime-session"},
                    "systemPromptReport": {
                        "workspaceDir": str(workspace),
                        "tools": {"entries": [{"name": "sessions_yield"}]},
                    },
                }
            }
        }

        def _side_effect(cmd, **_kwargs):
            if cmd[:5] == ["openclaw", "agent", "--agent", "oe-orchestrator", "--local"]:
                message = cmd[8] if len(cmd) > 8 else ""
                if "Complete bootstrap" in message:
                    return MagicMock(returncode=0, stdout="", stderr="")
                if "Runtime readiness check" in message:
                    return MagicMock(
                        returncode=0,
                        stdout=json.dumps(runtime_ready_output),
                        stderr="",
                    )
            raise AssertionError(f"Unexpected subprocess call: {cmd}")

        mock_run.side_effect = _side_effect

        result = _ensure_bootstrap_ready("oe-orchestrator", tmp_path, {})

        assert result is True


class TestMainSessionCommand:
    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_main_entrypoint_prefers_supported_agent_command(self, mock_run):
        def _side_effect(cmd, **_kwargs):
            if cmd == ["openclaw", "agent", "--help"]:
                return MagicMock(
                    returncode=0, stdout="Usage: openclaw agent [OPTIONS]\n", stderr=""
                )
            raise AssertionError(f"Unexpected subprocess call: {cmd}")

        mock_run.side_effect = _side_effect

        resolve_entrypoint = getattr(live_probes, "_resolve_main_session_entrypoint")
        assert resolve_entrypoint({}) == "agent"

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

    @patch("openclaw_enhance.validation.live_probes._resolve_main_session_entrypoint")
    def test_build_main_command_uses_isolated_session_mode_for_agent_entrypoint(
        self, mock_entrypoint
    ):
        mock_entrypoint.return_value = "agent"

        build_main_cmd = getattr(live_probes, "_build_main_session_command")
        cmd = build_main_cmd(
            "main-escalation",
            "route this heavy task",
            {},
            "session-local",
        )

        assert cmd[:4] == ["openclaw", "agent", "--agent", "main"]
        assert "--local" not in cmd
        assert "--agent" in cmd
        assert "main" in cmd

    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_unsupported_main_entrypoint_returns_machine_readable_failure(self, mock_run, tmp_path):
        def _side_effect(cmd, **_kwargs):
            if cmd == ["openclaw", "agent", "--help"]:
                return MagicMock(returncode=2, stdout="", stderr="unknown command 'agent'\n")
            if cmd == ["openclaw", "chat", "--help"]:
                return MagicMock(returncode=2, stdout="", stderr="unknown command 'chat'\n")
            raise AssertionError(f"Unexpected subprocess call: {cmd}")

        mock_run.side_effect = _side_effect

        runner = CliRunner()
        result = runner.invoke(
            live_probes.cli,
            [
                "main-escalation",
                "--openclaw-home",
                str(tmp_path),
                "--message",
                "route this heavy task",
            ],
        )

        assert result.exit_code == 2
        payload = json.loads(result.stderr)
        assert payload["ok"] is False
        assert payload["probe"] == "main-escalation"
        assert payload["reason"] == "main_entrypoint_unsupported"


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

    def test_extract_main_session_id_supports_local_output_meta_shape(self):
        parsed = {
            "meta": {
                "agentMeta": {"sessionId": "local-meta-id"},
                "systemPromptReport": {"sessionId": "local-system-prompt-id"},
            }
        }

        extract_main_session_id = getattr(live_probes, "_extract_main_session_id")
        assert extract_main_session_id(parsed) == "local-meta-id"


class TestMainEscalationFailureReason:
    @patch("openclaw_enhance.validation.live_probes._get_transcript_path")
    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_main_escalation_returns_orchestrator_handoff_missing_when_request_never_leaves_main(
        self,
        mock_run,
        mock_transcript_path,
        tmp_path,
    ):
        openclaw_home = tmp_path / ".openclaw"
        openclaw_home.mkdir(parents=True)
        main_transcript = tmp_path / "main-transcript.jsonl"
        main_transcript.write_text('{"tool":"none"}\n', encoding="utf-8")
        mock_transcript_path.return_value = main_transcript

        parsed_main = {
            "result": {
                "meta": {
                    "agentMeta": {"sessionId": "main-session-only"},
                }
            }
        }

        def _side_effect(cmd, **_kwargs):
            if cmd == ["openclaw", "agent", "--help"]:
                return MagicMock(
                    returncode=0, stdout="Usage: openclaw agent [OPTIONS]\n", stderr=""
                )
            if cmd[:4] == ["openclaw", "agent", "--agent", "main"]:
                return MagicMock(returncode=0, stdout=json.dumps(parsed_main), stderr="")
            raise AssertionError(f"Unexpected subprocess call: {cmd}")

        mock_run.side_effect = _side_effect

        runner = CliRunner()
        result = runner.invoke(
            live_probes.cli,
            [
                "main-escalation",
                "--openclaw-home",
                str(openclaw_home),
                "--message",
                "heavy task should escalate",
            ],
        )

        assert result.exit_code == 2
        payload = json.loads(result.stderr)
        assert payload["ok"] is False
        assert payload["probe"] == "main-escalation"
        assert payload["reason"] == "orchestrator_handoff_missing"

    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_main_escalation_attributes_to_transcript_growth_not_stale_latest_file(
        self,
        mock_run,
        tmp_path,
    ):
        openclaw_home = tmp_path / ".openclaw"
        openclaw_home.mkdir(parents=True)

        sessions_dir = openclaw_home / "agents" / "main" / "sessions"
        sessions_dir.mkdir(parents=True)
        stale_transcript = sessions_dir / "stale-main.jsonl"
        live_transcript = sessions_dir / "active-main.jsonl"
        stale_transcript.write_text('{"tool":"none"}\n', encoding="utf-8")
        live_transcript.write_text('{"event":"before"}\n', encoding="utf-8")

        stale_stat = stale_transcript.stat()
        live_stat = live_transcript.stat()
        os.utime(stale_transcript, (stale_stat.st_atime, stale_stat.st_mtime + 20))
        os.utime(live_transcript, (live_stat.st_atime, live_stat.st_mtime - 20))

        orchestrator_transcript = tmp_path / "orchestrator-transcript.jsonl"
        orchestrator_transcript.write_text('{"event":"spawned"}\n', encoding="utf-8")

        parsed_main = {
            "result": {
                "meta": {
                    "agentMeta": {
                        "sessionId": "missing-from-disk",
                    }
                }
            }
        }

        def _side_effect(cmd, **_kwargs):
            if cmd == ["openclaw", "agent", "--help"]:
                return MagicMock(
                    returncode=0, stdout="Usage: openclaw agent [OPTIONS]\n", stderr=""
                )

            if cmd[:4] == ["openclaw", "agent", "--agent", "main"]:
                probe_message = cmd[cmd.index("-m") + 1]
                with live_transcript.open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(
                            {
                                "tool": "sessions_spawn",
                                "agentId": "oe-orchestrator",
                                "task": probe_message,
                            }
                        )
                        + "\n"
                    )
                with orchestrator_transcript.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"task": probe_message}) + "\n")
                stale_now = stale_transcript.stat()
                os.utime(stale_transcript, (stale_now.st_atime, stale_now.st_mtime + 40))
                return MagicMock(returncode=0, stdout=json.dumps(parsed_main), stderr="")

            if cmd == ["openclaw", "sessions", "--agent", "main", "--json"]:
                sessions_payload = {
                    "sessions": [
                        {
                            "sessionId": "active-main",
                            "transcriptPath": str(live_transcript),
                        },
                        {
                            "sessionId": "stale-main",
                            "transcriptPath": str(stale_transcript),
                        },
                    ]
                }
                return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

            if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
                sessions_payload = {
                    "sessions": [
                        {
                            "sessionId": "orch-session-456",
                            "transcriptPath": str(orchestrator_transcript),
                        }
                    ]
                }
                return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

            raise AssertionError(f"Unexpected subprocess call: {cmd}")

        mock_run.side_effect = _side_effect

        runner = CliRunner()
        result = runner.invoke(
            live_probes.cli,
            [
                "main-escalation",
                "--openclaw-home",
                str(openclaw_home),
                "--message",
                "heavy task should escalate",
            ],
        )

        assert result.exit_code == 0, result.output or result.stderr
        payload = json.loads(result.output)
        assert payload["ok"] is True
        assert payload["main_session_id"] == "active-main"
        assert payload["main_session_evidence"]["transcript_path"] == str(live_transcript)
        assert payload["proof_request_id"]

    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_main_escalation_reattributes_when_returned_session_exists_but_did_not_grow(
        self,
        mock_run,
        tmp_path,
    ):
        openclaw_home = tmp_path / ".openclaw"
        openclaw_home.mkdir(parents=True)

        sessions_dir = openclaw_home / "agents" / "main" / "sessions"
        sessions_dir.mkdir(parents=True)
        stale_transcript = sessions_dir / "returned-stale.jsonl"
        live_transcript = sessions_dir / "active-main.jsonl"
        stale_transcript.write_text('{"tool":"none"}\n', encoding="utf-8")
        live_transcript.write_text('{"event":"before"}\n', encoding="utf-8")

        orchestrator_transcript = tmp_path / "orchestrator-transcript.jsonl"
        orchestrator_transcript.write_text('{"event":"spawned"}\n', encoding="utf-8")

        parsed_main = {
            "result": {
                "meta": {
                    "agentMeta": {
                        "sessionId": "returned-stale",
                    }
                }
            }
        }

        def _side_effect(cmd, **_kwargs):
            if cmd == ["openclaw", "agent", "--help"]:
                return MagicMock(
                    returncode=0, stdout="Usage: openclaw agent [OPTIONS]\n", stderr=""
                )

            if cmd[:4] == ["openclaw", "agent", "--agent", "main"]:
                probe_message = cmd[cmd.index("-m") + 1]
                with live_transcript.open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(
                            {
                                "tool": "sessions_spawn",
                                "agentId": "oe-orchestrator",
                                "task": probe_message,
                            }
                        )
                        + "\n"
                    )
                with orchestrator_transcript.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"task": probe_message}) + "\n")
                return MagicMock(returncode=0, stdout=json.dumps(parsed_main), stderr="")

            if cmd == ["openclaw", "sessions", "--agent", "main", "--json"]:
                sessions_payload = {
                    "sessions": [
                        {
                            "sessionId": "returned-stale",
                            "transcriptPath": str(stale_transcript),
                        },
                        {
                            "sessionId": "active-main",
                            "transcriptPath": str(live_transcript),
                        },
                    ]
                }
                return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

            if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
                sessions_payload = {
                    "sessions": [
                        {
                            "sessionId": "orch-session-456",
                            "transcriptPath": str(orchestrator_transcript),
                        }
                    ]
                }
                return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")

            raise AssertionError(f"Unexpected subprocess call: {cmd}")

        mock_run.side_effect = _side_effect

        runner = CliRunner()
        result = runner.invoke(
            live_probes.cli,
            [
                "main-escalation",
                "--openclaw-home",
                str(openclaw_home),
                "--message",
                "heavy task should escalate",
            ],
        )

        assert result.exit_code == 0, result.output or result.stderr
        payload = json.loads(result.output)
        assert payload["ok"] is True
        assert payload["main_session_id"] == "active-main"
        assert payload["main_session_evidence"]["transcript_path"] == str(live_transcript)
        assert payload["proof_request_id"]

    @patch("openclaw_enhance.validation.live_probes._get_transcript_path")
    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_main_escalation_accepts_orchestrator_sessions_json_with_trailing_logs(
        self,
        mock_run,
        mock_transcript_path,
        tmp_path,
    ):
        openclaw_home = tmp_path / ".openclaw"
        openclaw_home.mkdir(parents=True)
        main_transcript = tmp_path / "main-transcript.jsonl"
        main_transcript.write_text(
            '{"tool":"sessions_spawn","agentId":"oe-orchestrator"}\n',
            encoding="utf-8",
        )

        orchestrator_transcript = tmp_path / "orchestrator-transcript.jsonl"
        orchestrator_transcript.write_text('{"event":"spawned"}\n', encoding="utf-8")

        def _transcript_side_effect(agent_id, session_id, *_args, **_kwargs):
            if agent_id == "main" and session_id == "main-session-123":
                return main_transcript
            if agent_id == "oe-orchestrator" and session_id == "orch-session-456":
                return orchestrator_transcript
            raise AssertionError(f"Unexpected transcript lookup: {(agent_id, session_id)}")

        mock_transcript_path.side_effect = _transcript_side_effect

        parsed_main = {
            "result": {
                "meta": {
                    "agentMeta": {
                        "sessionId": "main-session-123",
                    }
                }
            }
        }

        def _side_effect(cmd, **_kwargs):
            if cmd == ["openclaw", "agent", "--help"]:
                return MagicMock(
                    returncode=0, stdout="Usage: openclaw agent [OPTIONS]\n", stderr=""
                )

            if cmd[:4] == ["openclaw", "agent", "--agent", "main"]:
                probe_message = cmd[cmd.index("-m") + 1]
                with main_transcript.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"task": probe_message}) + "\n")
                with orchestrator_transcript.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"task": probe_message}) + "\n")
                return MagicMock(returncode=0, stdout=json.dumps(parsed_main), stderr="")

            if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
                sessions_payload = {
                    "sessions": [
                        {
                            "sessionId": "orch-session-456",
                            "transcriptPath": str(orchestrator_transcript),
                        }
                    ]
                }
                mixed_output = json.dumps(sessions_payload) + "\n[plugins] loaded extension\n"
                return MagicMock(returncode=0, stdout=mixed_output, stderr="")

            raise AssertionError(f"Unexpected subprocess call: {cmd}")

        mock_run.side_effect = _side_effect

        runner = CliRunner()
        result = runner.invoke(
            live_probes.cli,
            [
                "main-escalation",
                "--openclaw-home",
                str(openclaw_home),
                "--message",
                "heavy task should escalate",
            ],
        )

        assert result.exit_code == 0, result.output or result.stderr
        payload = json.loads(result.output)
        assert payload["ok"] is True
        assert payload["orchestrator_session_id"] == "orch-session-456"
        assert payload["proof_request_id"]

    @patch("openclaw_enhance.validation.live_probes._get_transcript_path")
    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_main_escalation_requires_request_id_in_spawn_evidence(
        self,
        mock_run,
        mock_transcript_path,
        tmp_path,
    ):
        openclaw_home = tmp_path / ".openclaw"
        openclaw_home.mkdir(parents=True)
        main_transcript = tmp_path / "main-transcript.jsonl"
        main_transcript.write_text(
            '{"tool":"sessions_spawn","agentId":"oe-orchestrator"}\n',
            encoding="utf-8",
        )
        mock_transcript_path.return_value = main_transcript

        parsed_main = {
            "result": {
                "meta": {
                    "agentMeta": {
                        "sessionId": "main-session-123",
                    }
                }
            }
        }

        def _side_effect(cmd, **_kwargs):
            if cmd == ["openclaw", "agent", "--help"]:
                return MagicMock(
                    returncode=0, stdout="Usage: openclaw agent [OPTIONS]\n", stderr=""
                )
            if cmd[:4] == ["openclaw", "agent", "--agent", "main"]:
                return MagicMock(returncode=0, stdout=json.dumps(parsed_main), stderr="")
            raise AssertionError(f"Unexpected subprocess call: {cmd}")

        mock_run.side_effect = _side_effect

        runner = CliRunner()
        result = runner.invoke(
            live_probes.cli,
            [
                "main-escalation",
                "--openclaw-home",
                str(openclaw_home),
                "--message",
                "heavy task should escalate",
            ],
        )

        assert result.exit_code == 2
        payload = json.loads(result.stderr)
        assert payload["ok"] is False
        assert payload["reason"] == "orchestrator_handoff_missing"


class TestOrchestratorSessionAttribution:
    def test_extract_orchestrator_child_session_key_from_segment(self, tmp_path):
        transcript = tmp_path / "main.jsonl"
        transcript.write_text(
            "\n".join(
                [
                    json.dumps({"message": {"role": "assistant", "content": []}}),
                    json.dumps(
                        {
                            "message": {
                                "role": "toolResult",
                                "details": {
                                    "childSessionKey": "agent:oe-orchestrator:subagent:test-key"
                                },
                            }
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        extract_key = getattr(live_probes, "_extract_orchestrator_child_session_key_from_segment")
        assert extract_key(transcript, 1) == "agent:oe-orchestrator:subagent:test-key"

    @patch("openclaw_enhance.validation.live_probes._get_transcript_path")
    @patch("openclaw_enhance.validation.live_probes.subprocess.run")
    def test_resolve_orchestrator_session_by_child_key(
        self, mock_run, mock_transcript_path, tmp_path
    ):
        orchestrator_transcript = tmp_path / "orchestrator-session.jsonl"
        orchestrator_transcript.write_text("{}\n", encoding="utf-8")
        mock_transcript_path.return_value = orchestrator_transcript

        sessions_payload = {
            "sessions": [
                {
                    "key": "agent:oe-orchestrator:subagent:test-key",
                    "sessionId": "orch-session-789",
                }
            ]
        }

        def _side_effect(cmd, **_kwargs):
            if cmd == ["openclaw", "sessions", "--agent", "oe-orchestrator", "--json"]:
                return MagicMock(returncode=0, stdout=json.dumps(sessions_payload), stderr="")
            raise AssertionError(f"Unexpected subprocess call: {cmd}")

        mock_run.side_effect = _side_effect

        resolve_by_key = getattr(live_probes, "_resolve_orchestrator_session_by_child_key")
        result = resolve_by_key(tmp_path, {}, "agent:oe-orchestrator:subagent:test-key", attempts=1)
        assert result == ("orch-session-789", orchestrator_transcript)


class TestTranscriptDeltaSearch:
    def test_find_first_line_with_term_returns_first_fresh_match(self, tmp_path):
        transcript = tmp_path / "probe-lines.jsonl"
        request_id = "request-id-line-anchor"
        transcript.write_text(
            "\n".join(
                [
                    json.dumps({"message": {"role": "assistant", "content": "old unrelated line"}}),
                    json.dumps(
                        {"message": {"role": "assistant", "content": f"fresh {request_id}"}}
                    ),
                    json.dumps({"tool": "sessions_spawn", "agentId": "oe-searcher"}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        find_first = getattr(live_probes, "_find_first_line_with_term")
        assert find_first(transcript, 1, request_id) == 2
        assert find_first(transcript, 3, request_id) is None

    def test_extract_spawned_worker_and_child_key_from_nested_local_transcript(self, tmp_path):
        transcript = tmp_path / "orchestrator-local.jsonl"
        request_id = "request-id-local-nested"
        worker_agent_id = "oe-orchestrator"
        child_session_key = "agent:oe-orchestrator:subagent:nested-child-key"
        transcript.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "message",
                            "message": {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"[orchestrator-spawn probe request-id: {request_id}] do work",
                                    }
                                ],
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "type": "message",
                            "message": {
                                "role": "assistant",
                                "content": [
                                    {
                                        "type": "toolCall",
                                        "name": "sessions_spawn",
                                        "arguments": {
                                            "task": f"[{request_id}] nested task",
                                            "agentId": worker_agent_id,
                                        },
                                    }
                                ],
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "type": "message",
                            "message": {
                                "role": "toolResult",
                                "toolName": "sessions_spawn",
                                "details": {
                                    "childSessionKey": child_session_key,
                                },
                            },
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        extract_agent = getattr(live_probes, "_extract_spawned_worker_agent_id_from_segment")
        extract_key = getattr(live_probes, "_extract_child_session_key_from_segment")

        assert extract_agent(transcript, 1, request_id) == worker_agent_id
        assert extract_key(transcript, 1) == child_session_key

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
