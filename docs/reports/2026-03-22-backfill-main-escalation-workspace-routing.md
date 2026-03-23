# Validation Report: backfill-main-escalation

- **Date**: 2026-03-22
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
- Duration: 39.47s

**stdout:**
```
{"configured_model": "minimax/MiniMax-M2.1", "main_session_evidence": {"handoff_confirmed": true, "session_id": "0c7f8a76-6c12-4903-a88f-df671b254c8d", "transcript_path": "/Users/tsgsz/.openclaw/agents/main/sessions/0c7f8a76-6c12-4903-a88f-df671b254c8d.jsonl"}, "main_session_id": "0c7f8a76-6c12-4903-a88f-df671b254c8d", "main_transcript_path": "/Users/tsgsz/.openclaw/agents/main/sessions/0c7f8a76-6c12-4903-a88f-df671b254c8d.jsonl", "marker": "PROBE_MAIN_ESCALATION_OK", "ok": true, "orchestrator_session_evidence": {"session_id": "595aa163-cd1f-4500-bffa-178650eeed9b", "transcript_path": "/Users/tsgsz/.openclaw/agents/oe-orchestrator/sessions/595aa163-cd1f-4500-bffa-178650eeed9b.jsonl"}, "orchestrator_session_id": "595aa163-cd1f-4500-bffa-178650eeed9b", "orchestrator_transcript_path": "/Users/tsgsz/.openclaw/agents/oe-orchestrator/sessions/595aa163-cd1f-4500-bffa-178650eeed9b.jsonl", "probe": "main-escalation", "proof": "orchestrator_handoff_confirmed", "proof_request_id": "4c082966-bf75-4f72-aea5-3df6668e1644"}
```
