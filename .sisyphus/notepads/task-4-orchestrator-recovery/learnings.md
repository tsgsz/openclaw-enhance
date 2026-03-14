## Tool Recovery Integration
- Orchestrator loop state extended with recovery_attempts, recovered_methods, and recovery_in_progress.
- EvaluateProgress decision outcomes now include Recovery Dispatch and Recovery-Assisted Retry.
- Strict constraints: Max 1 retry per step, no recovery loops, no worker-to-worker handoff.
