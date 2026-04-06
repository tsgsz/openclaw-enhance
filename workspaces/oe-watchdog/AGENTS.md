---
schema_version: 1
agent_id: oe-watchdog
workspace: oe-watchdog
routing:
  description: Monitoring agent for timeout detection, status tracking, and reminder delivery.
  capabilities: [monitoring]
  accepts: [monitoring_tasks, health_check_requests]
  rejects: [file_modifications, code_changes, test_execution, git_operations]
  output_kind: monitoring_report
  mutation_mode: runtime_only
  can_spawn: false
  requires_tests: false
  session_access: runtime_only
  network_access: none
  repo_scope: none
  cost_tier: cheap
  model_tier: cheap
  duration_band: short
  parallel_safe: true
  priority_boost: 2
  tool_classes: [session_inspect, state_write]
---

# oe-watchdog

Monitors session timeouts and delivers health check reminders.