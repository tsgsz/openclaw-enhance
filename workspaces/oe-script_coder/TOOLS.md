# Script Coder Tools Configuration

This TOOLS.md defines the available tools and their usage patterns for the `oe-script_coder` workspace.

## File Management Tools

### Read
**Purpose**: Read files and directories for context

**Usage Patterns**:
- Read existing code for patterns
- View requirements and specifications
- Check existing tests for structure
- Review configuration files

**Best Practices**:
- Read existing similar code before writing
- Check project style guidelines
- Understand dependencies first

**Example**:
```python
# Read existing module for patterns
Read(filePath="src/openclaw_enhance/workspaces.py")
```

### Write
**Purpose**: Create new files

**Usage Patterns**:
- Create new Python modules
- Write test files
- Create configuration files
- Add documentation

**Best Practices**:
- Always read first to avoid overwriting
- Include proper headers
- Follow project conventions
- Add docstrings and comments

**Example**:
```python
# Create new module
Write(
    filePath="src/new_module.py",
    content="# New module\n..."
)
```

### Edit
**Purpose**: Modify existing files

**Usage Patterns**:
- Fix bugs in existing code
- Add new functions to modules
- Update configurations
- Refactor code

**Best Practices**:
- Read file first
- Make precise, targeted edits
- Preserve existing style
- Test after changes

**Example**:
```python
# Add function to existing module
Edit(
    filePath="src/module.py",
    oldString="# End of file",
    newString="def new_function():\n    pass\n\n# End of file"
)
```

### Glob
**Purpose**: Find files matching patterns

**Usage Patterns**:
- Find all Python files
- Locate test files
- Discover project structure
- Find configuration files

**Example**:
```python
# Find all test files
Glob(pattern="**/test_*.py")
```

### Grep
**Purpose**: Search file contents

**Usage Patterns**:
- Find function definitions
- Locate TODO comments
- Search for patterns to refactor
- Find imports

**Example**:
```python
# Find all test functions
grep(pattern="def test_", include="*.py")
```

## Code Intelligence Tools

### lsp_goto_definition
**Purpose**: Navigate to symbol definitions

**Usage Patterns**:
- Find where functions are defined
- Understand code structure
- Navigate to imported modules

**Example**:
```python
lsp_goto_definition(
    filePath="src/module.py",
    line=10,
    character=5
)
```

### lsp_find_references
**Purpose**: Find all symbol usages

**Usage Patterns**:
- Assess impact of changes
- Find all call sites
- Understand dependencies

**Example**:
```python
lsp_find_references(
    filePath="src/module.py",
    line=10,
    character=5
)
```

### lsp_symbols
**Purpose**: Get file/workspace symbols

**Usage Patterns**:
- Understand file structure
- Find symbols quickly
- Navigate large files

**Example**:
```python
lsp_symbols(filePath="src/module.py", scope="document")
```

### lsp_diagnostics
**Purpose**: Check for errors/warnings

**Usage Patterns**:
- Validate code before committing
- Find type errors
- Check for syntax issues
- Ensure code quality

**Example**:
```python
lsp_diagnostics(filePath="src/module.py")
```

## Execution Tools

### Bash
**Purpose**: Execute commands and run tests

**Usage Patterns**:
- Run tests: `pytest tests/ -v`
- Check Python syntax: `python -m py_compile file.py`
- Format code: `ruff format .`
- Type check: `mypy src/`

**Best Practices**:
- Run tests after changes
- Check types with mypy
- Format code before delivery
- Validate with LSP first

**Example**:
```python
# Run tests
Bash(command="pytest tests/unit/test_module.py -v")

# Type check
Bash(command="mypy src/openclaw_enhance/module.py")
```

### call_omo_agent
**Purpose**: Spawn searcher for research (limited use)

**Usage Patterns**:
- Research library APIs
- Find best practices
- Get code examples
- Verify implementation approaches

**Constraints**:
- Only spawn searcher
- Not for general use
- Emergency research only

**Example**:
```python
# Spawn searcher for research
call_omo_agent(
    subagent_type="searcher",
    prompt="Find best practices for pytest fixtures",
    run_in_background=True
)
```

## Tool Selection Guide

### By Development Task

| Task Type | Primary Tools | Secondary Tools |
|-----------|--------------|-----------------|
| New Feature | Write, Read | lsp_symbols |
| Bug Fix | Read, Edit | lsp_find_references |
| Test Writing | Write, Read | Bash(pytest) |
| Refactoring | Read, Edit, lsp_find_references | Bash(tests) |
| Code Review | Read, lsp_diagnostics | Grep |
| Exploration | Glob, Read | lsp_symbols |

### Development Workflow

1. **Read existing code** for patterns and context
2. **Explore structure** with Glob and lsp_symbols
3. **Implement** with Write or Edit
4. **Validate** with lsp_diagnostics
5. **Test** with Bash(pytest)
6. **Deliver** with verification output

## Output Formats

### Implementation Report Structure
```markdown
# Implementation: [Task]

## Summary
Brief description of what was implemented

## Files Created
- `/path/to/new_file.py` - Description

## Files Modified
- `/path/to/existing.py` - Changes made

## Implementation Details
Key design decisions

## Test Coverage
```
$ pytest tests/ -v
===================
passed: 5
failed: 0
```

## Type Check
```
$ mypy src/
Success: no issues found
```
```

## Code Standards

### Python Code Requirements
- Type hints (Python 3.10+)
- Docstrings for all public functions
- Error handling with try/except
- Logging for important operations
- pytest for testing

### Test Requirements
- All code must have tests
- Tests must pass
- Aim for >80% coverage
- Use fixtures for setup
- Test edge cases

### Documentation
- Module docstrings
- Function docstrings (Google style)
- Inline comments for complex logic
- Type hints

## Constraints

### Development Boundaries
- Can modify project files within scope
- Cannot modify system files
- Cannot change workspace configurations
- Cannot spawn agents except searcher for research

### Testing Requirements
- All code must be tested
- Tests must pass before delivery
- Use pytest for Python
- Include integration tests where appropriate

## Version

Version: 1.0.0
Last Updated: 2026-03-13
