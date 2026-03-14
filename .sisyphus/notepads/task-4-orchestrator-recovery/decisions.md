## Architectural Decisions
- oe-tool-recovery is a leaf-node specialist, ensuring it doesn't spawn further agents.
- Orchestrator remains the sole authority for retries and escalation, maintaining control over the bounded loop.
