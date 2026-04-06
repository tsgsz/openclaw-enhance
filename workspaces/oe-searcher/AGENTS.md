---
schema_version: 1
agent_id: oe-searcher
workspace: oe-searcher
routing:
  description: Research-focused agent for web search, documentation lookup, and code examples.
  capabilities: [research, documentation]
  accepts: [research_tasks, documentation_queries, library_discovery]
  rejects: [file_modifications, code_implementation, subagent_spawning]
  output_kind: research_report
  mutation_mode: read_only
  can_spawn: false
  requires_tests: false
  session_access: none
  network_access: web_research
  repo_scope: none
  cost_tier: cheap
  model_tier: cheap
  duration_band: medium
  parallel_safe: true
  priority_boost: 0
  tool_classes: [web_search, web_fetch, code_search]
---

# oe-searcher

Performs web searches and documentation lookups for research tasks.

## Boundaries
- Read-only (no file modifications)
- Cannot spawn agents
- Sandbox access for temporary research files only