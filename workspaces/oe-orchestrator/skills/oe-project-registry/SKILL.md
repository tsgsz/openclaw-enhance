---
name: oe-project-registry
version: 2.0.0
description: Project discovery, registration, and context injection for the Orchestrator
author: openclaw-enhance
tags: [orchestrator, project, discovery, registry, git]
---

# oe-project-registry

Skill for discovering, registering, and managing projects within the OpenClaw workspace.

## Purpose

The Orchestrator uses this skill to decide which project to work in, manage permanent versus temporary project lifecycles, and provide git context for task startup. It ensures that work is scoped correctly and that project-level metadata is available to all workers.

## When to Use

Use this skill when:
- Orchestrator session starts and needs to identify the active project
- User requests work on a specific project
- Need to check if a project is already occupied by another Orchestrator
- Creating or registering new projects
- Gathering git context for a project before dispatching workers

## Project Types

The registry supports two kinds of projects:

- **permanent**: User-specified projects, typically linked to a GitHub repository. These require an occupancy lock to ensure only one Orchestrator session works on them at a time.
- **temporary**: Orchestrator-created projects for specific tasks. These do not require occupancy locks and are typically short-lived.

## Detection

Project detection is stat-based and fast. It identifies project roots by looking for specific indicator files. Lazy parsing is performed for `pyproject.toml` and `package.json` to extract additional metadata.

| Indicator File | Project Type | Subtype Detection |
|----------------|--------------|-------------------|
| `pyproject.toml` | python | poetry or setuptools |
| `package.json` | nodejs | npm |
| `Cargo.toml` | rust | cargo |
| `go.mod` | go | module |
| `pom.xml` | java | maven |
| `build.gradle` | java | gradle |
| `Gemfile` | ruby | bundler |
| `composer.json` | php | composer |
| `Makefile` | cpp | make |
| `CMakeLists.txt` | cpp | cmake |

## CLI Commands

Manage the registry using these CLI commands:

- `python -m openclaw_enhance.cli project list [--kind permanent|temporary|all] [--json]`
- `python -m openclaw_enhance.cli project scan <path> [--kind permanent] [--register]`
- `python -m openclaw_enhance.cli project info <path>`
- `python -m openclaw_enhance.cli project create <path> --name <name> --kind permanent|temporary [--github-remote <url>]`

## Resolution Chain

The Orchestrator determines the active project using this canonical priority order:

```
explicit path → active_project in runtime state → detect from cwd → "default"
```

## Occupancy Lock

For permanent projects, the Orchestrator must acquire a lock before starting work:

- Use `registry.acquire_for_work(path, session_id)` which returns `(True, None)` on success or `(False, owner_id)` if blocked.
- If blocked, the task should be routed to the owning Orchestrator session instead of starting a new one.
- Use `registry.release_after_work(path, session_id)` to release the lock when work is complete.

## Git Workflow

Before starting work on a project, the Orchestrator gathers git context to inject into the worker task:

- Call `gather_git_context(project_path)` to retrieve recent commits, current branch, status, and open PRs.
- After completing work, use `auto_commit(project_path, message)` if appropriate.
- `should_auto_commit()` verifies safety: the repository must not be in a detached HEAD state, must have a remote configured, and the tree must be clean within the project scope.

## Registry Storage

The project registry is stored as a JSON file at:
`~/.openclaw/openclaw-enhance/project-registry.json`

## v1 Scope

The following features are NOT included in the v1 implementation:

- No automatic branch creation or PR creation (unless explicitly requested by the user).
- No tracking of subpackages within monorepos.
- No background project scanning or automatic discovery.
- No GitHub API write operations.
- No automatic cleanup of temporary projects.
