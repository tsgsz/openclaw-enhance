---
name: oe-session-inspect
version: 1.0.0
description: Session state analysis and introspection utilities
author: openclaw-enhance
tags: [syshelper, session, introspection, monitoring]
---

# oe-session-inspect

Skill for analyzing OpenCode session state and history.

## Purpose

This skill provides session introspection capabilities:
- Session history analysis
- Progress tracking
- Conversation flow understanding
- Activity pattern detection
- Metadata extraction

## When to Use

Use this skill when:
- Analyzing what happened in a session
- Tracking task progress
- Finding specific conversations
- Checking session health
- Investigating issues

## Capabilities

### Session Listing

#### List All Sessions
```python
# Get all sessions
all_sessions = session_list()

# Filter by date
recent = session_list(from_date="2026-03-01")

# Limit results
top_10 = session_list(limit=10)
```

#### Filter by Project
```python
# Find sessions for specific project
project_sessions = [
    s for s in session_list()
    if "project_name" in str(s).lower()
]
```

### Session Reading

#### Read Full History
```python
# Get all messages
history = session_read(session_id="abc123")

# Limit to recent messages
recent = session_read(session_id="abc123", limit=50)
```

#### Search Within Session
```python
# Find specific content
results = session_search(
    query="error|exception|fail",
    session_id="abc123"
)

# Search all sessions
global_results = session_search(query="deployment")
```

### Metadata Analysis

#### Get Session Info
```python
# Get metadata
info = session_info(session_id="abc123")

# Check properties
message_count = info.message_count
duration = info.duration
agents_used = info.agents
```

#### Compare Sessions
```python
# Compare multiple sessions
sessions = [session_info(s) for s in ["abc123", "def456"]]
# Analyze patterns
```

### Progress Analysis

#### Check Task Completion
```python
# Search for completion markers
completed = session_search(
    query="completed|done|finished|delivered",
    session_id="abc123"
)

# Check last message
history = session_read(session_id="abc123", limit=1)
last_message = history[-1] if history else None
```

#### Detect Stuck Sessions
```python
# Check for inactivity
info = session_info(session_id="abc123")
if info.last_activity_minutes > 30:
    # Potentially stuck
    pass
```

## Analysis Workflows

### Workflow 1: Session Summary
```python
# Step 1: Get metadata
info = session_info(session_id="abc123")

# Step 2: Read history
history = session_read(session_id="abc123")

# Step 3: Identify key events
events = session_search(
    query="plan|decide|implement|test",
    session_id="abc123"
)

# Step 4: Generate summary
summary = {
    "session_id": "abc123",
    "duration": info.duration,
    "messages": info.message_count,
    "key_events": events,
    "outcome": detect_outcome(history)
}
```

### Workflow 2: Find Related Sessions
```python
# Step 1: Search for topic
topic_sessions = session_search(query="authentication")

# Step 2: Get metadata for each
session_details = [
    session_info(s) for s in topic_sessions
]

# Step 3: Find patterns
related = [
    s for s in session_details
    if s.message_count > 10
]
```

### Workflow 3: Health Check
```python
# Step 1: List active sessions
active = session_list()

# Step 2: Check each for issues
for session_id in active:
    info = session_info(session_id)
    history = session_read(session_id, limit=20)
    
    # Check for errors
    errors = session_search(
        query="error|fail|exception",
        session_id=session_id
    )
    
    # Report status
    status = {
        "session": session_id,
        "healthy": len(errors) == 0,
        "errors": len(errors),
        "duration": info.duration
    }
```

## Output Formats

### Session Summary Report
```markdown
# Session Analysis: abc123

## Metadata
- **Session ID**: abc123
- **Duration**: 45 minutes
- **Messages**: 25
- **Agents Used**: searcher, script_coder

## Activity Timeline
1. **10:00** - Session started
2. **10:05** - Task received
3. **10:10** - Research phase
4. **10:30** - Implementation
5. **10:45** - Completed

## Key Decisions
- Used FastAPI for API layer
- Chose PostgreSQL for database
- Implemented async handlers

## Outcome
✅ Task completed successfully
```

### Health Status Report
```markdown
# Session Health Report

## Active Sessions: 5

### Session abc123
- **Status**: ✅ Healthy
- **Duration**: 15m
- **Last Activity**: 2m ago
- **Issues**: None

### Session def456
- **Status**: ⚠️ Warning
- **Duration**: 60m
- **Last Activity**: 30m ago
- **Issues**: No recent progress
```

## Best Practices

1. **Respect Privacy**: Only access necessary session data
2. **Read-Only**: Never modify session state
3. **Efficient Queries**: Use search instead of reading full history
4. **Metadata First**: Check session_info before reading history
5. **Aggregate Carefully**: Be mindful of volume when listing

## Safety

### Privacy Guidelines
- Only access sessions you have permission to view
- Don't expose sensitive information in reports
- Respect user confidentiality
- Focus on patterns, not personal content

### Performance
- Use limit parameters to control data volume
- Prefer session_search over session_read for large sessions
- Cache results when doing multiple analyses

## Integration

### With oe-syshelper Agent
This skill is designed for the oe-syshelper agent:
- Session exploration
- Progress tracking
- Health monitoring
- Historical analysis

### Output Usage
Session analysis feeds into:
- Watchdog monitoring
- Orchestrator planning
- Debugging investigations

## Constraints & Boundaries

- **Read-Only Guarantee**:
  - Pure information retrieval. No state changes.
  - Creating or modifying files is prohibited (`Write`, `Edit`).
  - Executing write operations in Bash (`>`, `rm`, etc.) is prohibited.
- **Prohibited Tools**:
  - `call_omo_agent`, `background_output`, `background_cancel`
  - `websearch_web_search_exa` (use `oe-searcher` instead)
  - Changing session state (`session_send`)
- Any attempt to use prohibited tools will fail, as read-only constraints are enforced.

## Version

Version: 1.1.0
Last Updated: 2026-03-15
