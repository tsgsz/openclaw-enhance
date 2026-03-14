## Architectural Decisions
- oe-tool-recovery is a leaf-node specialist, ensuring it doesn't spawn further agents.
- Orchestrator remains the sole authority for retries and escalation, maintaining control over the bounded loop.

- Added 'tool_recovery' agent type to 'oe-worker-dispatch' skill to formalize its role in the orchestration loop.
- Explicitly forbade worker-to-worker direct handoff in the dispatch skill to maintain the Orchestrator as the sole authority for task distribution.
- Integrated 'recovered_method' schema and 'retry_owner' logic into the dispatch flow documentation to ensure consistent handoff between recovery and retry phases.
