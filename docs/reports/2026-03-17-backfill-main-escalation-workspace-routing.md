# Validation Report: backfill-main-escalation

- **Date**: 2026-03-17
- **Feature Class**: workspace-routing
- **Environment**: macOS /Users/tsgsz/.openclaw
- **Conclusion**: PRODUCT_FAILURE

## Baseline State

- OpenClaw Home: `/Users/tsgsz/.openclaw`
- Installed: True
- Version: 0.1.0
- Config Exists: True (openclaw.json)

## Execution Log

### Command 1: ✗ FAIL

```bash
python -m openclaw_enhance.validation.live_probes main-escalation --openclaw-home "$OPENCLAW_HOME" --message "搜索 2025 年整个东南亚 iGaming 行业现状，给出 2026 年判断，并先设计一个 20 页左右的 PPT 大纲（包含内容、数据和讲稿），保证数据真实可追溯。"
```

- Exit Code: 2
- Duration: 18.66s

**stderr:**
```
{"detail": "4192a822-e5b9-48c0-81e7-f4eaa76033d6", "ok": false, "probe": "main-escalation", "reason": "orchestrator_handoff_missing"}
```
