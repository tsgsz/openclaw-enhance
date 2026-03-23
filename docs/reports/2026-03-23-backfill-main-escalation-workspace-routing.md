# Validation Report: backfill-main-escalation

- **Date**: 2026-03-23
- **Feature Class**: workspace-routing
- **Environment**: macOS /Users/tsgsz/.openclaw
- **Conclusion**: PASS

## Baseline State

- OpenClaw Home: `/Users/tsgsz/.openclaw`
- Installed: True
- Version: 0.1.0
- Config Exists: True (openclaw.json)

## Execution Log

### Command 1: ✓ PASS

```bash
python -m openclaw_enhance.validation.live_probes main-escalation --openclaw-home "$OPENCLAW_HOME" --message "搜索 2025 年整个东南亚 iGaming 行业现状，给出 2026 年判断，并先设计一个 20 页左右的 PPT 大纲（包含内容、数据和讲稿），保证数据真实可追溯。"
```

- Exit Code: 0
- Duration: 28.01s

**stdout:**
```
{"configured_model": "minimax/MiniMax-M2.1", "main_session_evidence": {"handoff_confirmed": true, "session_id": "a4859d58-d84f-42de-aff0-9cf3de3a4df0", "transcript_path": "/Users/tsgsz/.openclaw/agents/main/sessions/a4859d58-d84f-42de-aff0-9cf3de3a4df0.jsonl"}, "main_session_id": "a4859d58-d84f-42de-aff0-9cf3de3a4df0", "main_transcript_path": "/Users/tsgsz/.openclaw/agents/main/sessions/a4859d58-d84f-42de-aff0-9cf3de3a4df0.jsonl", "marker": "PROBE_MAIN_ESCALATION_OK", "ok": true, "orchestrator_session_evidence": {"session_id": "01d85483-3ca8-45b4-a082-830a694a0b16", "transcript_path": "/Users/tsgsz/.openclaw/agents/oe-orchestrator/sessions/01d85483-3ca8-45b4-a082-830a694a0b16.jsonl"}, "orchestrator_session_id": "01d85483-3ca8-45b4-a082-830a694a0b16", "orchestrator_transcript_path": "/Users/tsgsz/.openclaw/agents/oe-orchestrator/sessions/01d85483-3ca8-45b4-a082-830a694a0b16.jsonl", "probe": "main-escalation", "proof": "orchestrator_handoff_confirmed", "proof_request_id": "33b897b8-94b1-41b7-8a10-6cc97d5b74a9"}
```
