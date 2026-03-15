---
name: oe-project-registry
version: 1.0.0
description: Project discovery and management for the Orchestrator
author: openclaw-enhance
tags: [orchestrator, project, discovery, registry]
---

# oe-project-registry

Skill for discovering, registering, and managing projects within the OpenClaw workspace.

## Purpose

The Orchestrator needs to understand the project landscape to make intelligent decisions about:
- Where to execute tasks
- What type of project is being worked on
- Which workspace configuration to apply
- How to route subagents

## When to Use

Use this skill when:
- Starting work in an unknown directory
- Need to identify project type (Python, Node.js, Rust, etc.)
- Determining workspace selection for tasks
- Creating new projects
- Listing available projects

## Capabilities

### Project Discovery
Automatically detect project types by examining:
- `pyproject.toml` → Python project
- `package.json` → Node.js project
- `Cargo.toml` → Rust project
- `go.mod` → Go project
- `pom.xml` / `build.gradle` → Java project
- `Gemfile` → Ruby project
- `composer.json` → PHP project
- `Makefile` / `CMakeLists.txt` → C/C++ project

### Project Registry
Maintain a registry of discovered projects:
```json
{
  "projects": [
    {
      "id": "unique-project-id",
      "name": "Project Name",
      "type": "python",
      "path": "/absolute/path",
      "workspace": "oe-orchestrator",
      "detected_at": "2026-03-13T10:00:00Z",
      "metadata": {
        "python_version": "3.12",
        "dependencies": ["fastapi", "pydantic"],
        "test_framework": "pytest"
      }
    }
  ]
}
```

### Workspace Selection
Recommend appropriate workspace based on:
- Project type
- Task requirements
- Available skills
- Resource constraints

## Usage

### Discover Projects
```python
# Scan directory for projects
projects = discover_projects("/path/to/scan")

# Returns list of Project objects
[
  Project(
    id="proj-001",
    name="openclaw-enhance",
    type="python",
    path="/home/user/workspace/openclaw-enhance",
    workspace="oe-orchestrator"
  )
]
```

### Register Project
```python
# Manually register a project
register_project(
  path="/path/to/project",
  name="My Project",
  workspace="oe-orchestrator"
)
```

### Get Project Info
```python
# Retrieve project details
project = get_project("proj-001")
# Returns Project object with full metadata
```

### Select Workspace
```python
# Recommend workspace for task
workspace = select_workspace(
  project_id="proj-001",
  task_type="refactoring",
  complexity="high"
)
# Returns: "oe-orchestrator" or other appropriate workspace
```

## Project Types

| Indicator File | Project Type | Default Workspace |
|----------------|--------------|-------------------|
| `pyproject.toml` | python | oe-orchestrator |
| `setup.py` | python | oe-orchestrator |
| `package.json` | nodejs | oe-orchestrator |
| `Cargo.toml` | rust | oe-orchestrator |
| `go.mod` | golang | oe-orchestrator |
| `pom.xml` | java-maven | oe-orchestrator |
| `build.gradle` | java-gradle | oe-orchestrator |
| `Gemfile` | ruby | oe-orchestrator |
| `composer.json` | php | oe-orchestrator |
| `Makefile` | c/cpp | oe-orchestrator |
| `CMakeLists.txt` | c/cpp | oe-orchestrator |
| `requirements.txt` | python-legacy | oe-orchestrator |

## Registry Storage

The project registry is stored at:
```
~/.openclaw/openclaw-enhance/project-registry.json
```

## Integration

### With oe-worker-dispatch
Project metadata informs agent selection and configuration

### With oe-git-context
Git history is scoped to the selected project

### With planning-with-files
Project type determines planning templates

## Best Practices

1. **Scan before starting work** in unfamiliar directories
2. **Register projects explicitly** when auto-detection fails
3. **Update registry** when project structure changes
4. **Validate paths** before accessing projects
5. **Cache results** for frequently accessed projects

## Example Workflow

```
User: "Work on the auth module"
  ↓
Orchestrator: "Let me discover available projects"
  ↓
[Scan current directory]
  ↓
Found: openclaw-enhance (Python)
  ↓
"Working on openclaw-enhance. What would you like to do with the auth module?"
```
