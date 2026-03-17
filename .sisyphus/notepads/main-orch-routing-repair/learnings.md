# Main-to-Orchestrator Escalation Repair - Learnings

## Conventions
- Skills are file-backed markdown contracts
- Native `sessions_spawn` is the ONLY subagent mechanism
- No Python wrappers around native execution
- Heavy tasks (research, multi-file, >2 toolcalls) must escalate to oe-orchestrator

## Patterns
- Live probes use JSON extraction helpers
- Validation bundles map FeatureClass -> slug -> command
- Main workspace resolution: agent.workspace > agents.defaults.workspace > profile fallback > openclaw.json

## Decisions
- Keep `backfill-routing-yield` intact (direct orchestrator proof)
- Add new `backfill-main-escalation` slug (main-session escalation proof)
- Preserve copy installs, --dev symlinks, manifest/uninstall symmetry
