---
name: oe-tool-recovery
version: 1.0.0
description: Diagnose failed tool calls and produce evidence-backed recovery instructions
author: openclaw-enhance
tags: [tool-recovery, debugging, contracts, recovery]
---

# oe-tool-recovery

Skill for diagnosing failed tool invocations and returning a precise `recovered_method`.

Leaf Node recovery skill for the `oe-tool-recovery` workspace.

## Purpose

This skill helps the recovery worker:
- analyze the failed invocation and error output
- inspect local tool contracts and source-backed usage patterns
- check preconditions that may have caused the failure
- gather external documentation when local evidence is insufficient
- return a corrected invocation with explicit prerequisites

## When to Use

Use this skill when:
- a tool call fails with schema or parameter errors
- a precondition is missing or incorrect
- a third-party API or CLI behaves differently than expected
- the orchestrator needs a retry plan but should not guess

## Recovery Workflow

1. Read the failed tool call context and exact error
2. Inspect the local contract in `TOOLS.md`, source, or docs
3. Verify any file, path, or environment preconditions
4. Use external docs only if local evidence is incomplete
5. Return one evidence-backed `recovered_method`

## Output Contract

The result should include:
- `failed_step`
- `tool_name`
- `failure_reason`
- `exact_invocation`
- `preconditions`
- `evidence_source`
- `confidence`
- `retry_owner`
- optional `fallback_tool`
- `max_retries`
- `required_inputs`

## Guardrails

- Do not execute the retry yourself
- Do not modify files
- Do not expand into the original business task
- Prefer local contract evidence over guesswork

## Constraints

- Advisory only; no direct task execution
- Read-only investigation and documentation lookup only
- No file edits, git actions, or agent spawning
- Return one narrow recovery method instead of multiple speculative options

### Tool Restrictions

- **Read-Only**: Allowed tools include `Read`, `Glob`, `Grep`, `Bash` (read-only), `websearch_web_search_exa`, `webfetch`, `context7_query-docs`.
- **Prohibited Tools**: `Write`, `Edit`, `call_omo_agent`, `sessions_spawn`, `background_output`, `background_cancel`.
