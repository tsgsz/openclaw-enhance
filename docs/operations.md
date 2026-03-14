# Operations Guide

This guide covers day-to-day operations with `openclaw-enhance`.

## Overview

Once installed, `openclaw-enhance` operates transparently:
- **Main session** gets routing skills for task assessment
- **Complex tasks** automatically escalate to the orchestrator
- **Workers** handle specialized subtasks
- **Watchdog** monitors for timeouts

You interact with OpenClaw normally—the enhancement layer handles complexity behind the scenes.

**How Routing Works**: The `oe-toolcall-router` skill (a markdown contract in your workspace's `skills/` directory) guides the decision to stay in main or escalate to the orchestrator. Escalation happens via native `sessions_spawn` to `oe-orchestrator`. The orchestrator then manages a **bounded orchestration loop**, dispatching workers through the native announce chain and using `sessions_yield` to synchronize across turns.

## Using the Orchestrator

### When It Activates

The orchestrator is invoked when:
1. Task requires > 2 TOOLCALLs (estimated)
2. Task can be parallelized across multiple workers
3. Task expected duration > 5 minutes
4. Explicit user request: "Use orchestrator for this"

### Task Flow: Bounded Orchestration Loop

The orchestrator handles complex tasks using an iterative, round-based approach:

```
User Request → Main Session → oe-toolcall-router → oe-orchestrator
                                                      │
                                                      ▼
                                            ┌──────────────────┐
                                 ┌──────────┤  Dispatch Round  │◄─────────┐
                                 │          │ (sessions_spawn) │          │
                                 │          └────────┬─────────┘          │
                                 │                   │                    │
                                 │                   ▼                    │
                                 │          ┌──────────────────┐          │
                                 │          │   Yield Turn     │          │
                                 │          │ (sessions_yield) │          │
                                 │          └────────┬─────────┘          │
                                 │                   │                    │
                                 │                   ▼                    │
                                 │          ┌──────────────────┐          │
                                 │          │ Collect Results  │          │
                                 │          │ (auto-announce)  │          │
                                 │          └────────┬─────────┘          │
                                 │                   │                    │
                                 │                   ▼                    │
                                 │          ┌──────────────────┐          │
                                 │          │ Evaluate Progress│──────────┘
                                 │          └────────┬─────────┘
                                 │                   │
                                 └───────────────────┼────────────────────┐
                                                     ▼                    ▼
                                            ┌──────────────────┐   ┌──────────────┐
                                            │ Synthesize       │   │ Blocked/     │
                                            │ Return to Main   │   │ Exhausted    │
                                            └──────────────────┘   └──────────────┘
```

### Round Lifecycle

1. **Dispatch**: Orchestrator spawns specialized workers (`oe-searcher`, `oe-syshelper`, etc.) via `sessions_spawn`.
2. **Yield**: Orchestrator calls `sessions_yield` to end its current turn and wait for worker results.
3. **Collect**: Worker results are automatically announced to the orchestrator on its next turn.
4. **Evaluate**: Orchestrator analyzes results and decides whether to complete, re-dispatch for another round, or mark as blocked.

### Orchestrator Output Format

All orchestrator responses include:

```markdown
## Summary
Brief description of what was done

## Results
Synthesized output from workers

## Artifacts
- `/path/to/file1` - Description
- `/path/to/file2` - Description

## Next Steps
1. Recommendation 1
2. Recommendation 2
```

## Worker Roles

### oe-searcher

**Purpose**: Research, web search, documentation lookup

**When to use**:
- Looking up API documentation
- Researching libraries or frameworks
- Finding code examples
- Competitive analysis

**Example**:
```
"Research the best Python testing frameworks for async code"
"Find the OpenClaw documentation on hooks"
"Look up React Server Components best practices"
```

**Characteristics**:
- Uses cheaper model (cost-effective)
- Has sandbox read/write access
- Returns structured research summaries

### oe-syshelper

**Purpose**: System introspection, file operations, read-only discovery

**When to use**:
- Finding files matching patterns
- Reading configuration files
- Listing directory contents
- Searching code with grep

**Example**:
```
"Find all Python files that import requests"
"List the contents of src/ directory"
"Show me the git log for the last week"
```

**Characteristics**:
- Uses cheaper model (cost-effective)
- Read-only access (safe for exploration)
- Fast for file system operations

**Constraints**:
- Cannot modify files
- Cannot execute arbitrary bash commands
- Cannot access network resources

### oe-script_coder

**Purpose**: Script development, testing, automation

**When to use**:
- Writing utility scripts
- Creating test suites
- Building automation tools
- Prototyping solutions

**Example**:
```
"Write a Python script to parse JSONL files"
"Create a bash script to backup git repositories"
"Build a test harness for the API client"
```

**Characteristics**:
- Uses code-specialized model (Codex-class)
- Sandbox read/write access
- Can write, test, and iterate on code

**Workflow**:
1. Receive script requirements
2. Write initial implementation
3. Test in sandbox
4. Refine based on results
5. Return final script

### oe-watchdog

**Purpose**: Session monitoring, timeout detection, diagnostics

**When it's used**:
- Long-running tasks (> 30 minutes)
- Background monitoring
- Timeout suspicion handling
- System health checks

**Authority**:
- ✅ Confirm timeout suspicions
- ✅ Send reminders to sessions
- ✅ Read runtime state
- ✅ Update timeout state

- ❌ Kill processes
- ❌ Edit user repositories
- ❌ Modify non-owned config
- ❌ Access user credentials

### oe-tool-recovery

**Purpose**: Tool failure diagnosis and recovery suggestion

**When to use**:
- A tool call returns an error (syntax, schema, or logic)
- A tool call fails due to missing preconditions
- The orchestrator needs a precise correction for a failed step
- Diagnosing why a specific tool invocation failed

**Example**:
```
"The Write tool failed with 'oldString not found'"
"Why is the Bash command returning exit code 1?"
"Diagnose the failed Edit operation"
```

**Characteristics**:
- Uses reasoning-capable model for accurate diagnosis
- Read-only access (does not modify files)
- Leaf-node specialist (cannot spawn subagents)
- Returns structured `recovered_method` for retry

**Workflow**:
1. Receive failure context from orchestrator
2. Analyze error message and tool contract
3. Research external docs if needed
4. Formulate corrected invocation
5. Return recovery suggestion with confidence score

## Task Routing Examples

### Example 1: Simple Task (Stays on Main)

**User**: "What time is it?"

**Flow**:
1. `oe-eta-estimator` estimates 1 TOOLCALL
2. `oe-toolcall-router` decides: handle locally
3. Main session responds directly

### Example 2: Complex Task (Escalates to Orchestrator)

**User**: "Refactor the auth module to use JWT tokens"

**Flow**:
1. `oe-eta-estimator` estimates 8 TOOLCALLs, 20 minutes
2. `oe-toolcall-router` escalates to `oe-orchestrator`
3. Orchestrator:
   - Assesses task complexity
   - Creates execution plan
   - Dispatches:
     - `oe-syshelper` to find auth-related files
     - `oe-searcher` to research JWT best practices
     - `oe-script_coder` to implement changes
4. Synthesizes results
5. Returns to main session

### Example 3: Research Task

**User**: "Compare TypeScript vs Python for our new service"

**Flow**:
1. Main routes to orchestrator
2. Orchestrator dispatches:
   - `oe-searcher`: Research TypeScript ecosystem
   - `oe-searcher`: Research Python ecosystem
   - `oe-searcher`: Find comparison benchmarks
3. Synthesizes comparison report
4. Returns structured analysis

## Timeout Monitoring

### How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   monitor   │────▶│  Runtime    │────▶│  watchdog   │
│   script    │     │   Store     │     │   agent     │
└─────────────┘     └─────────────┘     └─────────────┘
   (1 min)             (state)             (confirm)
```

1. **Monitor script** runs every minute
2. Detects sessions exceeding expected duration
3. Writes `timeout_suspected` event to runtime store
4. **Watchdog** confirms or rejects the suspicion
5. If confirmed: sends reminder to original session

### Checking Timeout State

View current timeout state:

```bash
# Read runtime state directly
cat ~/.openclaw/openclaw-enhance/state/runtime-state.json | jq '.timeouts'
```

Or use the enhancement CLI:

```bash
python -m openclaw_enhance.cli status --json | jq '.timeouts'
```

### Timeout States

| State | Meaning | Action |
|-------|---------|--------|
| `suspected` | Monitor detected possible timeout | Waiting for watchdog confirmation |
| `confirmed` | Watchdog confirmed timeout | Reminder sent to session |
| `cleared` | Timeout resolved | No action needed |
| `escalated` | Escalated to user | Manual intervention may be needed |

### Configuring Timeouts

Default timeout thresholds (in `runtime-state.json`):

```json
{
  "timeout_policy": {
    "short_tasks": 5,
    "medium_tasks": 30,
    "long_tasks": 120
  }
}
```

Modify thresholds by editing the runtime state (use with caution):

```bash
# Edit runtime state
nano ~/.openclaw/openclaw-enhance/state/runtime-state.json
```

## Runtime State Management

### State Location

All runtime state is stored at:

```
~/.openclaw/openclaw-enhance/state/runtime-state.json
```

### State Structure

```json
{
  "version": "1.0.0",
  "last_updated_utc": "2026-03-13T10:30:00",
  "tasks": {
    "task_abc123": {
      "status": "active",
      "agent": "oe-orchestrator",
      "started_at": "2026-03-13T10:00:00",
      "eta_minutes": 20
    }
  },
  "timeouts": {
    "task_abc123": {
      "status": "suspected",
      "detected_at": "2026-03-13T10:25:00"
    }
  },
  "projects": {
    "my-project": {
      "path": "/home/user/projects/my-project",
      "type": "python",
      "last_accessed": "2026-03-13T10:00:00"
    }
  }
}
```

### Inspecting State

```bash
# Pretty-print full state
cat ~/.openclaw/openclaw-enhance/state/runtime-state.json | jq

# View active tasks
cat ~/.openclaw/openclaw-enhance/state/runtime-state.json | jq '.tasks'

# View timeout status
cat ~/.openclaw/openclaw-enhance/state/runtime-state.json | jq '.timeouts'

# View project registry
cat ~/.openclaw/openclaw-enhance/state/runtime-state.json | jq '.projects'
```

### Clearing Stale State

If state becomes inconsistent:

```bash
# Backup current state
cp ~/.openclaw/openclaw-enhance/state/runtime-state.json \
   ~/.openclaw/openclaw-enhance/state/runtime-state.json.bak.$(date +%s)

# Reset to empty state (use with caution)
echo '{"version": "1.0.0", "tasks": {}, "timeouts": {}, "projects": {}}' \
  > ~/.openclaw/openclaw-enhance/state/runtime-state.json
```

## CLI Commands

### Status

Check installation status:

```bash
python -m openclaw_enhance.cli status
```

With JSON output:

```bash
python -m openclaw_enhance.cli status --json
```

### Doctor

Run health checks:

```bash
python -m openclaw_enhance.cli doctor --openclaw-home "$HOME/.openclaw"
```

### Render Skills

View skill contracts:

```bash
python -m openclaw_enhance.cli render-skill oe-toolcall-router
python -m openclaw_enhance.cli render-skill oe-eta-estimator
python -m openclaw_enhance.cli render-skill oe-timeout-state-sync
```

### Render Workspaces

View workspace configurations:

```bash
python -m openclaw_enhance.cli render-workspace oe-orchestrator
python -m openclaw_enhance.cli render-workspace oe-watchdog
```

### Render Hooks

View hook contracts:

```bash
python -m openclaw_enhance.cli render-hook oe-subagent-spawn-enrich
```

## Best Practices

### 1. Let the Router Decide

Don't manually choose between main and orchestrator. Let `oe-toolcall-router` decide based on task complexity.

### 2. Provide Clear Task Descriptions

Better descriptions lead to better routing:

- ❌ "Fix the bug"
- ✅ "Fix the authentication bug where JWT tokens aren't validated on protected routes"

### 3. Monitor Long-Running Tasks

Check timeout state periodically for tasks > 30 minutes:

```bash
watch -n 30 'cat ~/.openclaw/openclaw-enhance/state/runtime-state.json | jq .timeouts'
```

### 4. Use Appropriate Workers

Don't force a specific worker—let the orchestrator choose. But you can hint:

- "Research..." → triggers searcher
- "Find files..." → triggers syshelper  
- "Write a script..." → triggers script_coder

### 5. Review Artifacts

Always check the `Artifacts` section in orchestrator responses for created/modified files.

## Common Workflows

### Adding a New Feature

1. Describe feature to main session
2. If complex, automatically routes to orchestrator
3. Orchestrator dispatches workers:
   - `syshelper`: Find relevant files
   - `searcher`: Research implementation patterns
   - `script_coder`: Implement changes
4. Review artifacts and results
5. Iterate if needed

### Debugging an Issue

1. Describe issue to main session
2. Routes to orchestrator for investigation
3. Orchestrator dispatches:
   - `syshelper`: Find error locations
   - `searcher`: Research solutions
4. Get synthesized fix recommendations
5. Apply fixes manually or via script_coder

### Code Review

1. Ask for code review
2. Orchestrator dispatches:
   - `syshelper`: Read code files
   - `searcher`: Research best practices
3. Get structured review with:
   - Issues found
   - Recommendations
   - Reference materials

## Troubleshooting Operations

See [Troubleshooting](troubleshooting.md) for:
- Worker routing issues
- Timeout false positives
- State corruption
- Performance problems

## Version

Operations Guide Version: 1.0.0
Last Updated: 2026-03-13
