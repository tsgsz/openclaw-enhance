# Validation Report: backfill-recovery-worker

- **Date**: 2026-03-15
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
python -m openclaw_enhance.validation.live_probes recovery-worker --openclaw-home "$OPENCLAW_HOME" --message "请先尝试使用 websearch 工具搜索 Python async patterns；若失败，继续完成任务并报告最终采用的方法"
```

- Exit Code: 2
- Duration: 0.78s

**stderr:**
```
{"detail": "Invalid config at /Users/tsgsz/.openclaw/openclaw.json:\\n- <root>: Unrecognized key: \"openclawEnhance\"\nerror: required option '-m, --message <text>' not specified", "ok": false, "probe": "recovery-worker", "reason": "agent_list_failed"}
```
