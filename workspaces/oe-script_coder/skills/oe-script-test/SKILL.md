---
name: oe-script-test
version: 1.0.0
description: Script testing and validation utilities
author: openclaw-enhance
tags: [script_coder, testing, pytest, validation]
---

# oe-script-test

Skill for testing and validating scripts and code.

## Purpose

This skill provides testing capabilities:
- Test file creation
- Test execution
- Coverage analysis
- Validation workflows
- Debugging support

## When to Use

Use this skill when:
- Writing tests for new code
- Validating implementations
- Checking code quality
- Debugging failures
- Ensuring correctness

## Capabilities

### Test Creation

#### Basic Test Structure
```python
# test_module.py
def test_function_name():
    """Test that function_name behaves correctly."""
    # Arrange
    input_data = "test_input"
    expected = "test_output"
    
    # Act
    result = function_name(input_data)
    
    # Assert
    assert result == expected
```

#### Fixture Usage
```python
import pytest

@pytest.fixture
def sample_data():
    """Provide test data."""
    return {
        "key": "value",
        "number": 42
    }

def test_with_fixture(sample_data):
    """Test using fixture."""
    assert sample_data["number"] == 42
```

#### Parametrized Tests
```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("hello", 5),
    ("world", 5),
    ("", 0),
])
def test_string_length(input, expected):
    """Test string length calculation."""
    assert len(input) == expected
```

### Test Execution

#### Run All Tests
```bash
# Run all tests
pytest tests/ -v
```

#### Run Specific Tests
```bash
# Run specific test file
pytest tests/unit/test_module.py -v

# Run specific test function
pytest tests/unit/test_module.py::test_function -v

# Run tests matching pattern
pytest -k "test_auth" -v
```

#### Coverage Analysis
```bash
# Run with coverage
pytest --cov=src --cov-report=term-missing

# Generate HTML report
pytest --cov=src --cov-report=html
```

### Validation Workflows

#### Pre-Commit Validation
```python
# Step 1: Type check
Bash(command="mypy src/openclaw_enhance/")

# Step 2: Lint check
Bash(command="ruff check src/")

# Step 3: Run tests
Bash(command="pytest tests/ -q")

# Step 4: Verify no errors
if all_checks_pass:
    print("✅ All checks passed")
```

#### Post-Change Validation
```python
# After making changes:

# Step 1: Check affected files
changed_files = get_changed_files()

# Step 2: Run related tests
for file in changed_files:
    test_file = find_test_for(file)
    if test_file:
        Bash(command=f"pytest {test_file} -v")

# Step 3: Full test suite
Bash(command="pytest tests/ -q")
```

## Test Patterns

### Unit Test Pattern
```python
def test_unit_name():
    """Test specific unit of functionality."""
    # Setup
    obj = ClassUnderTest()
    
    # Execute
    result = obj.method(input_data)
    
    # Verify
    assert result == expected
    assert obj.state == expected_state
```

### Integration Test Pattern
```python
def test_integration_name():
    """Test component integration."""
    # Setup components
    component_a = ComponentA()
    component_b = ComponentB()
    
    # Connect components
    component_a.connect(component_b)
    
    # Execute workflow
    result = component_a.process(data)
    
    # Verify end-to-end
    assert result.success
    assert component_b.received_data == expected
```

### Edge Case Pattern
```python
def test_edge_case_empty_input():
    """Test behavior with empty input."""
    result = process([])
    assert result == []

def test_edge_case_invalid_input():
    """Test behavior with invalid input."""
    with pytest.raises(ValueError):
        process(None)
```

## Testing Utilities

### File System Tests
```python
import tempfile
from pathlib import Path

def test_file_operations():
    """Test file manipulation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        
        # Write
        test_file.write_text("content")
        
        # Read
        content = test_file.read_text()
        assert content == "content"
```

### Mocking
```python
from unittest.mock import Mock, patch

def test_with_mock():
    """Test using mocks."""
    mock_dependency = Mock()
    mock_dependency.method.return_value = "mocked"
    
    result = function_under_test(mock_dependency)
    
    assert result == "mocked"
    mock_dependency.method.assert_called_once()
```

### Async Testing
```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_async_function():
    """Test async code."""
    result = await async_function()
    assert result is not None
```

## Best Practices

1. **Test First**: Write tests before or alongside implementation
2. **Independent**: Each test should be independent
3. **Clear Names**: Test names describe what's being tested
4. **Arrange-Act-Assert**: Structure tests clearly
5. **Edge Cases**: Test boundary conditions
6. **Fast**: Keep tests fast for quick feedback

## Safety

### Test Isolation
- Use fixtures for setup/teardown
- Clean up resources after tests
- Don't modify global state
- Use temporary directories for file tests

### Coverage Goals
- Aim for >80% code coverage
- Focus on critical paths
- Test error handling
- Include integration tests

## Integration

### With oe-script_coder Agent
This skill is designed for the oe-script_coder agent:
- Writing tests for new code
- Validating implementations
- Debugging test failures
- Ensuring code quality

### Output Usage
Test outputs feed into:
- Code quality assurance
- CI/CD pipelines
- Code review processes
- Documentation

## Constraints & Workflow

### Testing Requirements
- **Mandatory**: All new code must have tests. Tests must pass before delivery.

### Prohibited Operations
- **session_list / session_read**: Cannot read session histories.
- **background_output / background_cancel**: No background task management.

### Tool Usage
- `Read`, `Write`, `Edit`, `Bash` are allowed for full file access and testing.
- Code intelligence tools (`lsp_goto_definition`, `lsp_diagnostics`) should be used for code validation.
- `pytest` is the standard testing tool.

## Version

Version: 1.1.0
Last Updated: 2026-03-15
