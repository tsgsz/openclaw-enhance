---
schema_version: 1
agent_id: oe-orchestrator
workspace: oe-orchestrator
routing:
  description: High-capability dispatcher for project discovery, worker routing, result synthesis, and publishing operations.
  capabilities: [introspection, documentation, monitoring, recovery, publishing]
  accepts: [complex_tasks, multi_agent_tasks, orchestration_requests]
  rejects: [direct_worker_execution, main_session_mutation]
  output_kind: orchestration_report
  mutation_mode: repo_write
  can_spawn: true
  requires_tests: false
  session_access: read_only
  network_access: web_research
  repo_scope: full_repo
  cost_tier: premium
  model_tier: premium
  duration_band: long
  parallel_safe: false
  priority_boost: 3
  tool_classes: [repo_write, code_search, orchestration]
---

# oe-orchestrator

High-capability dispatcher for project discovery, worker routing, result synthesis, and publishing operations.

## Boundaries

- Dispatchers delegate execution to workers; does not absorb substantive work
- Cannot modify main session config, identity files, or user preferences
- Worker capabilities defined by frontmatter, not duplicated in body