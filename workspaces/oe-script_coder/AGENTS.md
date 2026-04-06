---
schema_version: 1
agent_id: oe-script_coder
workspace: oe-script_coder
routing:
  description: Development-focused agent for script writing, test creation, and debugging.
  capabilities: [code_generation, testing]
  accepts: [coding_tasks, test_creation, bug_fixes]
  rejects: [system_level_changes, session_inspection, background_task_management]
  output_kind: code_and_tests
  mutation_mode: repo_write
  can_spawn: false
  requires_tests: true
  session_access: none
  network_access: none
  repo_scope: full_repo
  cost_tier: standard
  model_tier: standard
  duration_band: long
  parallel_safe: false
  priority_boost: 1
  tool_classes: [repo_write, bash_exec, test_runner, code_search]
---

# oe-script_coder

Writes scripts, creates tests, and implements code modules.