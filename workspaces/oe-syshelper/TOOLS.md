# Syshelper Tools Configuration

This TOOLS.md defines the available tools and their usage patterns for the `oe-syshelper` workspace.

## File System Tools

### Read
**Purpose**: Read files and directories

**Usage Patterns**:
- Read source code for analysis
- View configuration files
- Inspect directory listings
- Review documentation

**Constraints**:
- Read-only, no modifications
- Use offset/limit for large files

**Example**:
```python
# Read a source file
Read(filePath="/path/to/module.py")

# List directory contents
Read(filePath="/path/to/directory")
```

### Glob
**Purpose**: Find files matching patterns

**Usage Patterns**:
- Find all Python files: `**/*.py`
- Find test files: `**/test_*.py`
- Find configuration files: `**/pyproject.toml`
- Discover project structure

**Example**:
```python
# Find all Python files
Glob(pattern="**/*.py", path="/project/root")
```

### Grep
**Purpose**: Search file contents

**Usage Patterns**:
- Find function definitions
- Search for TODO comments
- Locate specific imports
- Find error patterns

**Example**:
```python
# Find all function definitions
grep(pattern="^def ", path="/project", include="*.py")
```

## Session Tools

### session_list
**Purpose**: List OpenCode sessions

**Usage Patterns**:
- Find active sessions
- Check session counts
- Filter by date range
- List recent sessions

**Example**:
```python
# List recent sessions
session_list(limit=10)
```

### session_read
**Purpose**: Read session message history

**Usage Patterns**:
- Analyze conversation flow
- Review decisions made
- Check task progress
- Find specific messages

**Example**:
```python
# Read session history
session_read(session_id="abc123", limit=50)
```

### session_search
**Purpose**: Search session messages

**Usage Patterns**:
- Find specific conversations
- Search for decisions
- Locate error messages
- Find mentions of specific topics

**Example**:
```python
# Search for error mentions
session_search(query="error|exception|fail", session_id="abc123")
```

### session_info
**Purpose**: Get session metadata

**Usage Patterns**:
- Check session duration
- View message counts
- See agent usage
- Check creation date

**Example**:
```python
# Get session metadata
session_info(session_id="abc123")
```

## LSP Tools

### lsp_goto_definition
**Purpose**: Jump to symbol definition

**Usage Patterns**:
- Find where functions are defined
- Locate class definitions
- Navigate to variable declarations
- Understand code structure

**Example**:
```python
# Find function definition
lsp_goto_definition(
    filePath="/path/to/file.py",
    line=10,
    character=5
)
```

### lsp_find_references
**Purpose**: Find all usages of a symbol

**Usage Patterns**:
- Find all function calls
- Locate variable usages
- Assess impact of changes
- Understand dependencies

**Example**:
```python
# Find all references
lsp_find_references(
    filePath="/path/to/file.py",
    line=10,
    character=5
)
```

### lsp_symbols
**Purpose**: Get file outline or workspace symbols

**Usage Patterns**:
- Understand file structure
- Find symbols quickly
- Navigate large files
- List all classes/functions

**Example**:
```python
# Get file symbols
lsp_symbols(filePath="/path/to/file.py", scope="document")

# Search workspace symbols
lsp_symbols(filePath="/path/to/file.py", scope="workspace", query="MyClass")
```

### lsp_diagnostics
**Purpose**: Check for errors/warnings

**Usage Patterns**:
- Validate code health
- Find syntax errors
- Check type issues
- Verify before reporting

**Example**:
```python
# Check diagnostics
lsp_diagnostics(filePath="/path/to/file.py")
```

## Shell Tools

### Bash
**Purpose**: Execute read-only shell commands

**Usage Patterns**:
- List directory contents: `ls -la`
- Check file existence: `test -f file`
- View git status: `git status`
- Read git log: `git log --oneline -10`

**Constraints**:
- Read-only commands only
- No file modifications
- No state changes

**Allowed Commands**:
- `ls`, `find`, `cat`, `head`, `tail`
- `grep` (read-only)
- `git log`, `git status`, `git branch`
- `wc`, `du` (informational)

**Prohibited Commands**:
- `rm`, `mv`, `cp`
- `git checkout`, `git reset`
- Redirections (`>`, `>>`)
- Any write operation

**Example**:
```python
# Safe read-only commands
Bash(command="ls -la /path/to/dir")
Bash(command="git log --oneline -5")
```

## Tool Selection Guide

### By Task Type

| Task Type | Primary Tools | Secondary Tools |
|-----------|--------------|-----------------|
| File Exploration | Glob, Read | Bash(ls) |
| Code Navigation | lsp_symbols, lsp_goto_definition | Read |
| Find Usages | lsp_find_references | Grep |
| Session Analysis | session_read, session_info | session_search |
| Project Structure | Glob | Read, Bash(find) |
| Code Health | lsp_diagnostics | Read |
| Git History | Bash(git) | Read |
| Search Content | Grep | Glob |

### Introspection Workflow

1. **Start with Glob** to discover files
2. **Use LSP tools** for code understanding
3. **Read specific files** for details
4. **Analyze sessions** for context
5. **Report findings** without modifications

## Output Formats

### System Report Structure
```markdown
# System Report: [Topic]

## Summary
Brief overview of findings

## File Locations
- `/path/to/file1` - Description
- `/path/to/file2` - Description

## Code Structure
### Symbols Found
- `function_name()` - Line 10
- `ClassName` - Line 25

## Relationships
- Function A → calls → Function B
- Class X → inherits → Class Y

## Session Context
- Session: abc123
- Messages: 25
- Last activity: 5 minutes ago
```

## Constraints

### Read-Only Guarantee
All operations are strictly read-only:
- ✅ Read files and directories
- ✅ Search and explore
- ✅ Analyze code structure
- ✅ Inspect sessions
- ❌ Write or modify files
- ❌ Execute write commands
- ❌ Change system state
- ❌ Spawn agents

### Safety Enforcement
- Tool-level restrictions prevent writes
- Bash limited to read-only commands
- No file modification tools available
- Pure introspection only

## Version

Version: 1.0.0
Last Updated: 2026-03-13
