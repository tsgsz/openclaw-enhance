---
name: oe-agentos-practice
version: 1.0.0
description: AgentOS pattern implementation for coding tasks
author: openclaw-enhance
tags: [orchestrator, agentos, patterns, coding, best-practices]
---

# oe-agentos-practice

Skill for implementing AgentOS patterns and best practices in coding tasks.

## Purpose

AgentOS patterns provide structured approaches to common coding tasks. This skill helps the Orchestrator:
- Apply consistent patterns across projects
- Ensure code quality and maintainability
- Follow established conventions
- Generate boilerplate efficiently

## When to Use

Use this skill when:
- Starting new features or modules
- Refactoring existing code
- Creating tests or documentation
- Setting up project structure
- Implementing common patterns

## Core Patterns

### 1. Skill-Based Development

**Pattern**: Encapsulate capabilities in reusable skills

```python
# Structure
skills/
  my-skill/
    SKILL.md          # Contract and documentation
    implementation/   # Code (if needed)
    tests/            # Tests for the skill
```

**Usage**:
- Define clear contracts in SKILL.md
- Version skills independently
- Test skills in isolation
- Document usage examples

### 2. File-Based Planning

**Pattern**: Use files for task planning and tracking

```
.sisyphus/
  plans/
    feature-x.md      # The plan
  notepads/
    feature-x/
      learnings.md    # Patterns discovered
      issues.md       # Problems encountered
      decisions.md    # Architectural choices
```

**Usage**:
- Create plan before complex work
- Record learnings during implementation
- Document decisions with rationale
- Track issues for resolution

### 3. Atomic Commits

**Pattern**: Each commit does one thing completely

```
✓ feat(auth): add JWT token validation
✓ test(auth): add tests for JWT validation
✓ refactor(auth): extract token parsing to helper
✗ feat(auth): add JWT and fix logout bug
```

**Usage**:
- One logical change per commit
- Commit passes tests
- Clear commit messages
- Related changes grouped

### 4. Test-First Development

**Pattern**: Write tests before implementation

```python
# 1. Write test (fails)
def test_calculate_total():
    assert calculate_total([1, 2, 3]) == 6

# 2. Implement (passes)
def calculate_total(items):
    return sum(items)

# 3. Refactor (still passes)
def calculate_total(items: list[int]) -> int:
    return sum(items)
```

**Usage**:
- Red-Green-Refactor cycle
- Tests define requirements
- Refactor with confidence
- Maintain coverage

### 5. Incremental Implementation

**Pattern**: Build features in small, working increments

```
Increment 1: Basic structure (compiles/runs)
Increment 2: Core functionality (basic cases work)
Increment 3: Error handling (edge cases covered)
Increment 4: Optimization (performance improved)
```

**Usage**:
- Each increment is deployable
- Get feedback early
- Reduce risk
- Easier debugging

## Coding Conventions

### Python

**Project Structure**:
```
project/
  src/
    package/
      __init__.py
      module.py
  tests/
    unit/
    integration/
  docs/
  pyproject.toml
```

**Code Style**:
- Use `ruff` for linting/formatting
- Type hints required for public APIs
- Docstrings: Google style
- Maximum line length: 100

**Testing**:
- `pytest` for test framework
- Tests in `tests/` directory
- Mirror source structure in tests
- Use fixtures for common setup

### JavaScript/TypeScript

**Project Structure**:
```
project/
  src/
  tests/
  dist/
  package.json
  tsconfig.json
```

**Code Style**:
- Use `eslint` and `prettier`
- Prefer TypeScript
- Explicit return types on exports

## Implementation Workflows

### New Feature Workflow

1. **Plan**: Create `.sisyphus/plans/feature.md`
2. **Design**: Document approach in decisions.md
3. **Interface**: Define public API first
4. **Tests**: Write tests for the interface
5. **Implement**: Code to pass tests
6. **Refactor**: Clean up while tests pass
7. **Document**: Update docs with examples
8. **Review**: Self-review against checklist

### Refactoring Workflow

1. **Identify**: Find code to refactor
2. **Test Coverage**: Ensure tests exist
3. **Characterization**: Write tests for current behavior
4. **Small Steps**: One refactoring at a time
5. **Verify**: Tests pass after each step
6. **Commit**: Commit after each refactoring

### Bug Fix Workflow

1. **Reproduce**: Create failing test
2. **Isolate**: Find minimal reproduction
3. **Fix**: Make minimal change to fix
4. **Test**: Ensure test passes
5. **Regression**: Check for similar bugs
6. **Document**: Update changelog/issue

## Code Generation Templates

### Python Module Template
```python
"""Brief module description.

Longer description if needed.
"""

from __future__ import annotations

__all__ = ["public_function"]


def public_function(arg: str) -> str:
    """Short description.
    
    Longer description.
    
    Args:
        arg: Description of arg
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When arg is invalid
        
    Example:
        >>> public_function("test")
        'result'
    """
    return arg.upper()
```

### Test Template
```python
"""Tests for module_name."""

import pytest

from package.module import function


class TestFunctionName:
    """Test cases for function_name."""
    
    def test_happy_path(self):
        """Test normal operation."""
        result = function("input")
        assert result == "expected"
    
    def test_edge_case_empty(self):
        """Test with empty input."""
        result = function("")
        assert result == ""
    
    def test_error_invalid_input(self):
        """Test error handling."""
        with pytest.raises(ValueError, match="expected message"):
            function(None)
```

## Quality Checklists

### Before Committing Code
- [ ] Tests pass (`pytest`)
- [ ] Linting passes (`ruff`)
- [ ] Type checking passes (`mypy`)
- [ ] Docstrings complete
- [ ] No debug code left
- [ ] Commit message follows convention

### Before Creating PR
- [ ] All tests pass
- [ ] Code reviewed (self or peer)
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] No merge conflicts

### Before Marking Complete
- [ ] Feature works as specified
- [ ] Edge cases handled
- [ ] Error messages helpful
- [ ] Performance acceptable
- [ ] No known issues

## Integration

### With oe-worker-dispatch
Use script_coder agents for implementation following these patterns

### With oe-project-registry
Apply patterns appropriate to project type

### With planning-with-files
Record patterns used in notepads

## Example: Complete Feature Implementation

```
1. Create plan
   .sisyphus/plans/user-auth.md
   
2. Design decisions
   .sisyphus/notepads/user-auth/decisions.md
   - "Using JWT for stateless auth"
   - "Token expiry: 24 hours"
   
3. Define interface
   src/auth/interface.py
   
4. Write tests
   tests/unit/test_auth.py
   
5. Implement
   src/auth/jwt_handler.py
   
6. Refactor
   Extract common utilities
   
7. Document
   docs/auth.md
   
8. Review
   Check against quality checklist
```
