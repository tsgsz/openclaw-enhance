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
- Duration: 15.46s

**stderr:**
```
{"detail": "Session aa83229c-8edc-4e61-95a8-5b645b809635 not in sessions list", "ok": false, "probe": "routing-yield", "reason": "session_not_found"}
```
