# Validation Report: harness-routing-test

- **Date**: 2026-03-15
- **Feature Class**: workspace-routing
- **Environment**: macOS /Users/tsgsz/.openclaw
- **Conclusion**: PRODUCT_FAILURE

## Baseline State

- OpenClaw Home: `/Users/tsgsz/.openclaw`
- Installed: False
- Config Exists: True (openclaw.json)

## Execution Log

### Command 1: ✗ FAIL

```bash
python -m openclaw_enhance.validation.live_probes routing-yield --openclaw-home "$OPENCLAW_HOME" --message "帮我规划一个复杂任务，先并行搜索两个方向，再汇总一个执行计划"
```

- Exit Code: 2
- Duration: 2.77s

**stderr:**
```
{"detail": "Config warnings:\\n- plugins.entries.minimax-mcp-search: plugin not found: minimax-mcp-search (stale config entry ignored; remove it from plugins config)\nConfig warnings:\\n- plugins.entries.minimax-mcp-search: plugin not found: minimax-mcp-search (stale config entry ignored; remove it from plugins config)\nConfig warnings:\\n- plugins.entries.minimax-mcp-search: plugin not found: minimax-mcp-search (stale config entry ignored; remove it from plugins config)\nerror: unknown command 'chat'", "ok": false, "probe": "routing-yield", "reason": "openclaw_chat_failed"}
```
