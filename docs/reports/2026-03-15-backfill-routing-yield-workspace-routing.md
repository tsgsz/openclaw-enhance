# Validation Report: backfill-routing-yield

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
python -m openclaw_enhance.validation.live_probes routing-yield --openclaw-home "$OPENCLAW_HOME" --message "帮我规划一个复杂任务，先并行搜索两个方向，再汇总一个执行计划"
```

- Exit Code: 2
- Duration: 0.70s

**stderr:**
```
{"detail": "Invalid config at /Users/tsgsz/.openclaw/openclaw.json:\\n- <root>: Unrecognized key: \"openclawEnhance\"\nerror: unknown command 'chat'", "ok": false, "probe": "routing-yield", "reason": "openclaw_chat_failed"}
```
