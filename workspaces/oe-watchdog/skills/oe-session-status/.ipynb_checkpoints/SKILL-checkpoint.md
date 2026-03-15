---
name: oe-session-status
version: 1.0.0
description: Session status monitoring and health checking utilities
author: openclaw-enhance
tags: [watchdog, session, status, health, monitoring]
---

# oe-session-status

Skill for monitoring session status and performing health checks.

## Purpose

This skill provides session monitoring capabilities:
- Active session enumeration
- Health status checking
- Activity pattern analysis
- Resource usage monitoring
- Status reporting

## When to Use

Use this skill when:
- Listing active sessions
- Checking system health
- Monitoring session activity
- Detecting inactive sessions
- Generating status reports

## Authority Boundaries

### ✅ ALLOWED
- List all sessions
- Read session metadata
- Check session health indicators
- Write status reports to runtime state
- Report findings to orchestrator

### ❌ PROHIBITED
- Modify session state
- Terminate sessions
- Access message content (unless needed for health check)
- Make operational decisions
- Modify project files outside runtime state

## Capabilities

### Session Enumeration

#### List Active Sessions
```python
def get_active_sessions():
    """Get list of active sessions."""
    sessions = session_list()
    
    # Filter to active (not closed)
    active = [
        s for s in sessions
        if s.get("status") != "closed"
    ]
    
    return active
```

#### Filter by Criteria
```python
def filter_sessions(sessions, **criteria):
    """Filter sessions by various criteria."""
    filtered = sessions
    
    if "min_duration" in criteria:
        filtered = [
            s for s in filtered
            if s.get("duration_minutes", 0) >= criteria["min_duration"]
        ]
    
    if "agent_type" in criteria:
        filtered = [
            s for s in filtered
            if criteria["agent_type"] in s.get("agents", [])
        ]
    
    if "since" in criteria:
        from datetime import datetime
        since_time = datetime.fromisoformat(criteria["since"])
        filtered = [
            s for s in filtered
            if datetime.fromisoformat(s.get("start_time")) >= since_time
        ]
    
    return filtered
```

### Health Checking

#### Basic Health Check
```python
def check_session_health(session_id):
    """Perform basic health check on session."""
    info = session_info(session_id=session_id)
    
    health = {
        "session_id": session_id,
        "exists": True,
        "status": info.get("status", "unknown"),
        "message_count": info.get("message_count", 0),
        "duration_minutes": calculate_duration(info),
        "last_activity_minutes": calculate_inactivity(info),
        "agents_used": info.get("agents", []),
    }
    
    # Determine health status
    if health["status"] == "closed":
        health["health"] = "closed"
    elif health["last_activity_minutes"] > 30:
        health["health"] = "stale"
    elif health["last_activity_minutes"] > 10:
        health["health"] = "warning"
    else:
        health["health"] = "healthy"
    
    return health
```

#### System Health Check
```python
def check_system_health():
    """Check overall system health."""
    sessions = get_active_sessions()
    
    health_checks = [
        check_session_health(s["id"]) for s in sessions
    ]
    
    # Aggregate stats
    healthy = sum(1 for h in health_checks if h["health"] == "healthy")
    warning = sum(1 for h in health_checks if h["health"] == "warning")
    stale = sum(1 for h in health_checks if h["health"] == "stale")
    
    return {
        "timestamp": datetime.now().isoformat(),
        "total_sessions": len(sessions),
        "healthy": healthy,
        "warning": warning,
        "stale": stale,
        "health_rate": healthy / len(sessions) if sessions else 1.0,
        "details": health_checks
    }
```

### Activity Analysis

#### Activity Patterns
```python
def analyze_activity_patterns(session_id, window_minutes=60):
    """Analyze activity patterns for a session."""
    info = session_info(session_id=session_id)
    
    # Get message timeline
    messages = session_read(session_id=session_id)
    
    if not messages:
        return {"session_id": session_id, "activity": "none"}
    
    # Calculate message frequency
    duration = calculate_duration(info)
    message_rate = len(messages) / duration if duration > 0 else 0
    
    # Identify activity bursts
    timestamps = [m.timestamp for m in messages]
    gaps = calculate_gaps(timestamps)
    
    return {
        "session_id": session_id,
        "total_messages": len(messages),
        "duration_minutes": duration,
        "message_rate": message_rate,
        "avg_gap_minutes": sum(gaps) / len(gaps) if gaps else 0,
        "max_gap_minutes": max(gaps) if gaps else 0,
        "activity_pattern": classify_pattern(message_rate, gaps)
    }

def classify_pattern(rate, gaps):
    """Classify activity pattern."""
    if rate < 0.1:
        return "inactive"
    elif max(gaps) > 30 if gaps else False:
        return "bursty"
    elif rate > 1:
        return "active"
    else:
        return "steady"
```

### Status Reporting

#### Generate Status Report
```python
def generate_status_report():
    """Generate comprehensive status report."""
    # Get system health
    system_health = check_system_health()
    
    # Get activity analysis for all sessions
    sessions = get_active_sessions()
    activity_analysis = [
        analyze_activity_patterns(s["id"]) for s in sessions
    ]
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "system_health": system_health,
        "activity_summary": {
            "total": len(activity_analysis),
            "inactive": sum(1 for a in activity_analysis if a["activity_pattern"] == "inactive"),
            "active": sum(1 for a in activity_analysis if a["activity_pattern"] == "active"),
            "bursty": sum(1 for a in activity_analysis if a["activity_pattern"] == "bursty"),
            "steady": sum(1 for a in activity_analysis if a["activity_pattern"] == "steady"),
        },
        "recommendations": generate_recommendations(system_health, activity_analysis)
    }
    
    # Write to runtime state
    Write(
        filePath=".runtime/status_report.json",
        content=json.dumps(report, indent=2)
    )
    
    return report

def generate_recommendations(health, activities):
    """Generate monitoring recommendations."""
    recommendations = []
    
    if health["stale"] > 0:
        recommendations.append(f"Investigate {health['stale']} stale sessions")
    
    if health["health_rate"] < 0.8:
        recommendations.append("System health below 80%, review active sessions")
    
    inactive_count = sum(1 for a in activities if a["activity_pattern"] == "inactive")
    if inactive_count > 3:
        recommendations.append(f"{inactive_count} inactive sessions detected")
    
    return recommendations
```

## Monitoring Workflows

### Workflow 1: Health Check Loop
```python
def continuous_health_monitoring(check_interval=300):
    """Continuously monitor session health."""
    import time
    
    while True:
        # Check all sessions
        health = check_system_health()
        
        # Log to runtime state
        Write(
            filePath=".runtime/health_log.json",
            content=json.dumps(health, indent=2)
        )
        
        # Report issues to orchestrator
        if health["warning"] > 0 or health["stale"] > 0:
            report_issues(health)
        
        # Wait before next check
        time.sleep(check_interval)
```

### Workflow 2: Status Dashboard
```python
def generate_dashboard():
    """Generate real-time status dashboard data."""
    # Get current state
    health = check_system_health()
    
    sessions = get_active_sessions()
    session_details = []
    
    for session in sessions:
        info = session_info(session_id=session["id"])
        activity = analyze_activity_patterns(session["id"])
        
        session_details.append({
            "id": session["id"],
            "status": info.get("status"),
            "health": check_session_health(session["id"]),
            "activity": activity,
            "agents": info.get("agents", [])
        })
    
    dashboard = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(sessions),
            "healthy": health["healthy"],
            "issues": health["warning"] + health["stale"]
        },
        "sessions": session_details
    }
    
    # Write to runtime state
    Write(
        filePath=".runtime/dashboard.json",
        content=json.dumps(dashboard, indent=2)
    )
    
    return dashboard
```

## Output Formats

### Health Check Result
```json
{
  "session_id": "abc123",
  "exists": true,
  "status": "active",
  "message_count": 25,
  "duration_minutes": 15,
  "last_activity_minutes": 2,
  "agents_used": ["searcher", "script_coder"],
  "health": "healthy"
}
```

### System Health Report
```json
{
  "timestamp": "2026-03-13T10:30:00Z",
  "total_sessions": 5,
  "healthy": 3,
  "warning": 1,
  "stale": 1,
  "health_rate": 0.6,
  "details": [...]
}
```

### Status Dashboard
```markdown
# Session Status Dashboard

## Last Updated: 2026-03-13T10:30:00Z

## Summary
- **Total Sessions**: 5
- **Healthy**: 3 (60%)
- **Issues**: 2 (40%)

## Session Details

### abc123 - ✅ Healthy
- Duration: 15m
- Last Activity: 2m ago
- Agents: searcher, script_coder
- Activity: active (1.7 msg/min)

### def456 - ⚠️ Warning
- Duration: 25m
- Last Activity: 12m ago
- Agents: syshelper
- Activity: steady (0.4 msg/min)

### ghi789 - 🔴 Stale
- Duration: 45m
- Last Activity: 35m ago
- Agents: watchdog
- Activity: inactive

## Recommendations
1. Investigate 1 stale session (ghi789)
2. Monitor 1 warning session (def456)
```

## Best Practices

1. **Regular Checks**: Monitor at regular intervals
2. **Log Everything**: Write all status to runtime state
3. **Threshold Tuning**: Adjust health thresholds based on patterns
4. **Report Only**: Let orchestrator decide actions
5. **Track Trends**: Monitor health trends over time

## Safety

### Read-Only Monitoring
- Only read session metadata
- Never modify session state
- Only write to runtime state
- Report without taking action

### Performance
- Batch operations when possible
- Use efficient queries
- Limit data volume
- Cache results when appropriate

## Integration

### With oe-watchdog Agent
This skill is designed for the oe-watchdog agent:
- Session monitoring
- Health checking
- Status reporting
- Dashboard generation

### With Orchestrator
- Provides status visibility
- Reports health issues
- Tracks system trends
- Supports decision-making

## Version

Version: 1.0.0
Last Updated: 2026-03-13
