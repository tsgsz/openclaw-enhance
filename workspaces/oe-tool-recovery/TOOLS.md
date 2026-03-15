# Tool Recovery Tools Configuration

This TOOLS.md defines the available tools and usage patterns for the `oe-tool-recovery` workspace.

## Read-Only Analysis Tools

### Read
**Purpose**: Inspect tool contracts, code, and local documentation

**Usage Patterns**:
- Read tool definitions before suggesting corrected invocations
- Inspect source files to confirm parameter names and constraints
- Review local markdown docs for tool-specific guidance

### Glob
**Purpose**: Locate relevant files quickly

**Usage Patterns**:
- Find `TOOLS.md` or `AGENTS.md` files for contract inspection
- Discover related implementation files for failed tools
- Identify workspace-specific documentation paths

### Grep
**Purpose**: Search for exact tool names, parameter keys, and error patterns

**Usage Patterns**:
- Find examples of successful tool usage
- Search for known error strings or validation messages
- Locate schema fields and option names

### Bash
**Purpose**: Perform read-only environment inspection

**Usage Patterns**:
- Check file presence with safe read-only commands
- Inspect environment variables relevant to tool failures
- Review repository state needed to explain a failure

**Constraints**:
- Read-only commands only
- No file modification, deletion, or agent spawning

## External Reference Tools

### websearch_web_search_exa
**Purpose**: Search for external tool and API documentation

**Usage Patterns**:
- Research third-party CLI/API behavior
- Find current docs for failed external integrations
- Verify deprecations or version-specific usage changes

### webfetch
**Purpose**: Retrieve authoritative documentation pages

**Usage Patterns**:
- Pull exact API docs for quoted error messages
- Capture reference material for corrected invocation syntax
- Compare local assumptions against official docs

### context7_query-docs
**Purpose**: Query library-specific documentation after resolving the library ID

**Usage Patterns**:
- Inspect package APIs implicated in a failed tool call
- Verify argument names and supported behaviors
- Retrieve concise implementation examples

## Recovery Constraints

- All tools are advisory only; the workspace does not execute the recovered business task
- No write access to project files or runtime state
- No subagent spawning or background task management
- Recommendations must be based on direct evidence from contracts, source, docs, or environment inspection

## Prohibited Tools

- Write/Edit - Cannot modify files
- call_omo_agent
- sessions_spawn
- background_output
- background_cancel
