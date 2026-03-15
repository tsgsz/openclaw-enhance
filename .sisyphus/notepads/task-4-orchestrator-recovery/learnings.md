## Tool Recovery Integration
- Orchestrator loop state extended with recovery_attempts, recovered_methods, and recovery_in_progress.
- EvaluateProgress decision outcomes now include Recovery Dispatch and Recovery-Assisted Retry.
- Strict constraints: Max 1 retry per step, no recovery loops, no worker-to-worker handoff.

- Recovery routing requires explicit classification of tool-usage failures (tool_not_found, invalid_parameters, etc.) to trigger the specialized recovery flow.
- Literal grep verification in task contracts requires careful attention to casing and the inclusion of specific strings (e.g., "tool-usage failure", "recovered_method") even if they are redundant to the prose.
