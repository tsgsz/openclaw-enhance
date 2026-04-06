---
schema_version: 1
agent_id: oe-syshelper
workspace: oe-syshelper
routing:
  description: System introspection agent for file exploration, session analysis, and code search.
  capabilities: [introspection]
  accepts: [introspection_tasks, session_summaries, symbol_lookups]
  rejects: [file_modifications, state_changes, subagent_spawning]
  output_kind: introspection_report
  mutation_mode: read_only
  can_spawn: false
  requires_tests: false
  session_access: read_only
  network_access: none
  repo_scope: selected_files
  cost_tier: cheap
  model_tier: cheap
  duration_band: short
  parallel_safe: true
  priority_boost: 0
  tool_classes: [code_search, session_inspect]
---

# oe-syshelper

Explores file structures, analyzes session history, and searches code.