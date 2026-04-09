# ADR 0003: Watchdog Authority Boundaries

## Status

Accepted (Updated for v2)

## v2 Architecture Note

In v2, the watchdog functionality is implemented differently than v1:
- **No oe-watchdog Agent**: The dedicated watchdog agent no longer exists
- **Timeout Detection**: Implemented via `monitor_runtime` script and runtime state
- **Session Monitoring**: Uses native OpenClaw mechanisms without dedicated agent

## Context

The watchdog system monitors OpenClaw sessions for timeouts and handles related diagnostics. It must be effective without compromising system security or user data.

Key questions:
1. What actions can the watchdog system take on suspected timeouts?
2. How does watchdog communicate with other sessions?
3. What are the limits of watchdog's authority?
4. How do we prevent watchdog from being a security risk?

## Decision

We define strict **authority boundaries** for the watchdog system:

### Permitted Actions

| Action | Description | Rationale |
|--------|-------------|-----------|
| Read runtime state | Access `~/.openclaw/openclaw-enhance/state/` | Required for timeout detection |
| Write timeout status | Update timeout entries in state | Confirms or rejects suspicions |
| Send session messages | Use `session_send` to notify original session | Alerts user of timeouts |
| Read session metadata | Check session status via OpenClaw API | Determines if session is truly stuck |
| Create diagnostic reports | Log findings for troubleshooting | Helps debug timeout issues |

### Prohibited Actions

| Action | Status | Rationale |
|--------|--------|-----------|
| Kill processes | ❌ PROHIBITED | Too destructive; violates non-invasive principle |
| Edit user repositories | ❌ PROHIBITED | Must not modify user code/data |
| Modify task queues | ❌ PROHIBITED | Could corrupt OpenClaw state |
| Access credentials | ❌ PROHIBITED | Security risk; not needed for timeout handling |
| Edit non-owned config | ❌ PROHIBITED | Only `openclaw-enhance` namespace allowed |
| Terminate sessions | ❌ PROHIBITED | Should notify, not force-close |
| Modify system settings | ❌ PROHIBITED | Out of scope; security risk |

### Authority Flow

```
Monitor Script (1 min interval)
        │
        │ Detects timeout suspicion
        ▼
┌───────────────────┐
│ Runtime State      │ ◄─── Watchdog reads/writes
│ (state.json)       │       only this file
└───────────────────┘
        │
        │ timeout_suspected event
        ▼
┌───────────────────┐
│ Timeout Detector   │ ◄─── Confirms/rejects suspicion
│ (Runtime State)    │       Sends reminder if confirmed
└───────────────────┘
        │
        │ Confirmed timeout
        ▼
┌───────────────────┐
│ Original Session  │ ◄─── Receives notification only
│ (user session)    │       No forced actions
└───────────────────┘
```

### Communication Protocol

**Monitor → State** (write only):
- Writes `timeout_suspected` events
- Never reads or modifies other state

**Detector ↔ State** (read/write):
- Reads suspicion events
- Updates status: `confirmed`, `rejected`, `cleared`
- Writes diagnostic notes

**Detector → Session** (notify only):
- Uses `session_send` to deliver reminders
- Message contains: timeout duration, suggested actions
- No commands or forced operations

## Consequences

### Positive

- **Security**: Limited attack surface; no access to user data or credentials
- **Non-invasive**: Cannot corrupt user work or OpenClaw state
- **Predictable**: Clear boundaries prevent unexpected behavior
- **Safe defaults**: Even if watchdog misbehaves, damage is contained

### Negative

- **Limited recovery**: Cannot auto-recover from stuck sessions
- **User dependency**: Requires user to act on timeout notifications
- **False positive risk**: Must rely on heuristics; may notify on healthy long tasks

### Neutral

- **Monitoring overhead**: Minimal; state file is small (~10KB)
- **Notification noise**: User may receive occasional false positives

## Mitigations

### False Positive Reduction

1. **Multi-factor detection**: Consider CPU, memory, and activity metrics
2. **Confirmation delay**: Wait 2-3 minutes before sending notification
3. **User acknowledgment**: Track if user has seen the notification
4. **Configurable thresholds**: Allow tuning timeout sensitivity

### Security Controls

1. **Read-only filesystem**: Watchdog has limited filesystem access
2. **Sandbox execution**: Runs in OpenClaw's sandbox environment
3. **Audit logging**: All state modifications logged
4. **No network access**: Cannot exfiltrate data

## Alternatives Considered

### 1. Give watchdog full administrative access

**Rejected**: Security risk; violates non-invasive principle; could corrupt user data.

### 2. Let watchdog kill stuck processes

**Rejected**: Too destructive; could interrupt important work; better to notify and let user decide.

### 3. Use external monitoring service

**Rejected**: Adds infrastructure dependency; more complex than needed; harder to secure.

### 4. No watchdog, rely on user monitoring

**Rejected**: Doesn't solve the problem of undetected stuck sessions; poor user experience.

## Implementation Details

### v2 Implementation

Location: `src/openclaw_enhance/watchdog/`

**Components**:
- `detector.py`: Timeout detection logic
- `state_sync.py`: Runtime state synchronization
- `monitor_runtime`: CLI entry point for monitoring

**Constraints**:
- Read access: `~/.openclaw/openclaw-enhance/state/`
- Write access: Same directory only
- No bash execution except for diagnostics
- No LSP/grep outside owned namespace

### Timeout State Machine

```
           ┌─────────────────┐
           │   monitor       │
           │   detects       │
           │   suspicion     │
           └────────┬────────┘
                    │ writes
                    ▼
           ┌─────────────────┐
           │  suspected      │
           └────────┬────────┘
                    │ detector reads
                    ▼
           ┌─────────────────┐
           │  detector        │
           │  confirms?      │
           └────────┬────────┘
              yes /   \ no
                 /     \
                ▼       ▼
        ┌──────────┐  ┌──────────┐
        │ confirmed│  │ rejected │
        └────┬─────┘  └──────────┘
             │
             ▼
        ┌──────────┐
        │ notify   │
        │ session  │
        └────┬─────┘
             │
             ▼
        ┌──────────┐
        │ cleared  │ ◄─── user acknowledges
        │ (final)  │
        └──────────┘
```

### Policy Configuration

Default thresholds in `runtime-state.json`:

```json
{
  "timeout_policy": {
    "short_max_minutes": 5,
    "medium_max_minutes": 30,
    "long_max_minutes": 120,
    "confirmation_delay_minutes": 3
  }
}
```

## Related Decisions

- [ADR 0001: Managed Namespace](0001-managed-namespace.md)
- [ADR 0002: Native Subagent Announce](0002-native-subagent-announce.md)

## References

- `src/openclaw_enhance/watchdog/detector.py`
- `src/openclaw_enhance/watchdog/state_sync.py`
- `src/openclaw_enhance/monitor_runtime.py`

## Date

2026-03-13 (Updated 2026-04-09 for v2)
