# Main-to-Orchestrator Escalation Repair - Decisions

## Task 1: Main-Session Probe Entrypoint
- Must determine actual CLI command, not assume `openclaw chat`
- Evidence: previous runtime proof failed with "unknown command 'chat'"
- Approach: Verify CLI capabilities before implementing probe

## Task 4: Path/Sync Coverage
- Expand tests BEFORE changing runtime code
- Cover profile-based and openclaw.json-based resolution
- Drive red proof to identify actual defect location
