# Watchdog Tools Configuration

This TOOLS.md defines the available tools and their usage patterns for the `oe-watchdog` workspace.

## Monitoring Tools (Allowed)

### session_list
**Purpose**: List OpenCode sessions for monitoring

**Usage Patterns**:
- Find all active sessions
- Check session counts
- Filter by date/time
- Identify long-running sessions

**Example**:
```python
# List active sessions
session_list(limit=50)

# Filter by recent date
session_list(from_date="2026-03-13")
```

### session_read
**Purpose**: Read session messages for timeout detection

**Usage Patterns**:
- Check last message timestamp
- Verify if session is making progress
- Detect stuck sessions
- Review recent activity

**Constraints**:
- Read-only, no modifications
- Use for timeout confirmation only

**Example**:
```python
# Read recent messages
session_read(session_id="abc123", limit=20)
```

### session_info
**Purpose**: Get session metadata

**Usage Patterns**:
- Check session duration
- Get message counts
- See creation time
- Check last activity

**Example**:
```python
# Get session metadata
info = session_info(session_id="abc123")
# Check: info.message_count, elapsed time
```

### session_search
**Purpose**: Search session content for progress verification

**Usage Patterns**:
- Find specific messages
- Check for error patterns
- Verify task completion
- Search for progress indicators

**Example**:
```python
# Search for completion markers
session_search(query="completed|done|finished", session_id="abc123")
```

## File Tools (Runtime State Only)

### Read
**Purpose**: Read runtime state and configuration

**Usage Patterns**:
- Read monitoring configuration
- Check existing timeout logs
- View runtime state store

**Scope**:
- ✅ Runtime state files only (`.runtime/`)
- ✅ Configuration files
- ❌ Project source files (read-only, no modifications)

**Example**:
```python
# Read runtime state
Read(filePath=".runtime/timeout_log.json")

# Read monitoring config
Read(filePath=".runtime/watchdog_config.yaml")
```

### Write
**Purpose**: Write to runtime state store only

**Usage Patterns**:
- Log timeout events
- Record reminder deliveries
- Update monitoring status
- Write health check results

**Scope**:
- ✅ Runtime state directory only
- ✅ Timeout event logs
- ✅ Status records
- ❌ Project files
- ❌ Source code
- ❌ Configuration files

**Example**:
```python
# Log timeout event
Write(
    filePath=".runtime/timeout_events.json",
    content=json.dumps(event_data)
)
```

## Shell Tools (Read-Only)

### Bash
**Purpose**: Execute read-only status checks

**Usage Patterns**:
- Check file existence
- Get directory listings
- Read timestamps
- View system status

**Constraints**:
- Read-only commands only
- No file modifications
- No test execution
- No git operations

**Allowed Commands**:
- `ls`, `find` (listing only)
- `cat`, `head`, `tail`
- `test -f`, `test -d`
- `date`, `stat`

**Prohibited Commands**:
- `rm`, `mv`, `cp`, `touch`
- `git *` (any git command)
- `pytest`, `python` (test execution)
- Redirections (`>`, `>>`)
- Pipes to write operations

**Example**:
```python
# Check file existence
Bash(command="test -f .runtime/config.yaml && echo exists")

# Get timestamp
Bash(command="stat -c %Y .runtime/last_check")
```

## Prohibited Tools

### Explicitly Forbidden
The following tools are **NOT AVAILABLE** to the Watchdog:

| Tool | Reason |
|------|--------|
| `Edit` | Not available - Cannot modify files |
| `Write` (to project) | Not available - Only runtime state allowed |
| `call_omo_agent` | Not available - Cannot spawn agents |
| `websearch_web_search_exa` | Not available - Use searcher for web queries |
| `background_output` | Not available - No background task management |
| `background_cancel` | Not available - No task cancellation |
| `Grep` | Not available - Not needed for monitoring |
| `Glob` | Not available - Not needed for monitoring |
| `LSP Tools` | Not available - Not needed for monitoring |

**Note**: Reminder delivery uses the SessionSender protocol (implemented in notifier.py), not a direct tool call.

### Why These Are Prohibited
- **Edit/Write(project)**: Watchdog has narrow authority
- **call_omo_agent**: Watchdog doesn't coordinate other agents
- **websearch**: Use searcher agent for web queries
- **background_***: Watchdog doesn't manage background tasks
- **Grep/Glob/LSP**: Not relevant for session monitoring

## Tool Selection Guide

### By Monitoring Task

| Task Type | Primary Tools | Notes |
|-----------|--------------|-------|
| List Sessions | session_list | Find active sessions |
| Check Duration | session_info | Get elapsed time |
| Verify Progress | session_read | Check recent messages |
| Search Activity | session_search | Find specific events |
| Log Timeout | Write (runtime) | Write to `.runtime/` |
| Read Config | Read (runtime) | Read from `.runtime/` |
| Check Status | Bash (read-only) | File existence, timestamps |

### Monitoring Workflow

1. **List sessions** with session_list
2. **Check metadata** with session_info (duration, activity)
3. **Verify progress** with session_read or session_search
4. **Confirm timeout** if elapsed > ETA
5. **Log event** with Write to runtime state
6. **Report status** to orchestrator

## Output Formats

### Monitoring Report Structure
```markdown
# Watchdog Report: [Timestamp]

## Sessions Monitored
| Session | Messages | Duration | ETA | Status |
|---------|----------|----------|-----|--------|
| abc123 | 25 | 15m | 10m | ⚠️ TIMEOUT |
| def456 | 40 | 5m | 10m | ✓ OK |

## Timeout Events
- Session abc123: Elapsed 15m > ETA 10m
  - Action: Logged to runtime state
  - Status: Awaiting orchestrator decision

## Runtime State Updates
- Timeout events logged: 1
- Last check: 2026-03-13T10:30:00Z
```

### Timeout Event Log Format
```json
{
  "timestamp": "2026-03-13T10:30:00Z",
  "event_type": "timeout_detected",
  "session_id": "abc123",
  "elapsed_minutes": 15,
  "eta_minutes": 10,
  "messages_count": 25,
  "last_activity": "2026-03-13T10:25:00Z",
  "action_taken": "logged_to_runtime_state"
}
```

## Constraints

### Narrow Authority Enforcement

#### ✅ ALLOWED
- Read session metadata and messages
- Write to runtime state only
- Read runtime configuration
- Execute read-only status commands
- Report status to orchestrator

#### ❌ PROHIBITED
- Modify project files
- Write outside runtime state
- Execute tests or scripts
- Run git commands
- Spawn agents
- Make implementation decisions
- Change workspace configurations

### Runtime State Scope

**Can Write To:**
- `.runtime/timeout_log.json`
- `.runtime/watchdog_status.json`
- `.runtime/health_checks.json`
- `.runtime/reminder_log.json`
- Other files in `.runtime/` directory

**Cannot Write To:**
- Source code files
- Test files
- Configuration files (project-level)
- Documentation files
- Any file outside `.runtime/`

## Safety

### Read-Only Guarantee
- Session inspection is read-only
- No session state modifications
- No message sending capability
- Pure monitoring and reporting

### Narrow Scope
- Limited to monitoring functions
- Cannot escalate privileges
- Cannot bypass restrictions
- All actions logged to runtime state

### Decision Authority
- Watchdog detects and reports
- Orchestrator makes decisions
- No autonomous actions
- No recovery attempts

## Emergency Procedures

### If Tool Violation Detected
1. Log to runtime state
2. Report to orchestrator
3. Continue within authorized scope

### If Scope Violation Attempted
- Tool will fail with authorization error
- Log attempt to runtime state
- Report to orchestrator

## Version

Version: 1.0.0
Last Updated: 2026-03-13
