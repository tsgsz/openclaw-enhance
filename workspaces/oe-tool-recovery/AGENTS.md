---
schema_version: 1
agent_id: oe-tool-recovery
workspace: oe-tool-recovery
routing:
  description: Leaf-node recovery specialist for failure diagnosis and recovery suggestions.
  capabilities: [recovery]
  accepts: [failed_tool_context]
  rejects: [business_task_execution, file_modifications, agent_spawning]
  output_kind: recovery_suggestion
  mutation_mode: read_only
  can_spawn: false
  requires_tests: false
  session_access: none
  network_access: web_research
  repo_scope: selected_files
  cost_tier: standard
  model_tier: standard
  duration_band: medium
  parallel_safe: true
  priority_boost: 1
  tool_classes: [web_search, doc_fetch, code_search]
---

# oe-tool-recovery

Leaf-node recovery specialist for failure diagnosis and recovery suggestions.

## Boundaries

- Read-only diagnosis; cannot execute fixes or modify files
- Cannot spawn agents or take over business tasks