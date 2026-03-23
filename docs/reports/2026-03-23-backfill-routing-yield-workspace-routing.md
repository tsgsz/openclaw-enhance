# Validation Report: backfill-routing-yield

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
python -m openclaw_enhance.validation.live_probes routing-yield --openclaw-home "$OPENCLAW_HOME" --message "帮我规划一个复杂任务，先并行搜索两个方向，再汇总一个执行计划"
```

- Exit Code: 0
- Duration: 20.29s

**stdout:**
```
{"config_path": "/Users/tsgsz/.openclaw/openclaw.json", "configured_model": "minimax/MiniMax-M2.1", "marker": "PROBE_ROUTING_YIELD_OK", "ok": true, "probe": "routing-yield", "proof": "runtime_surface", "runtime_identity_confirmed": false, "runtime_surface_valid": true, "runtime_workspace": "/Users/tsgsz/.openclaw/openclaw-enhance/workspaces/oe-orchestrator", "session_id": "7d551891-00ad-44e5-a0b4-8e272e379b19", "tool_surface_has_sessions_yield": true, "transcript_path": "/Users/tsgsz/.openclaw/agents/oe-orchestrator/sessions/7d551891-00ad-44e5-a0b4-8e272e379b19.jsonl"}
```
