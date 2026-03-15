# Orchestrator Tools Configuration

This TOOLS.md defines the available tools and their usage patterns for the `oe-orchestrator` workspace.

## Core Tools

### Read
**Purpose**: Read files and directories to gather context

**Usage Patterns**:
- Read project configuration files (`pyproject.toml`, `package.json`)
- Read planning files from `.sisyphus/plans/`
- Read skill definitions from `workspaces/oe-orchestrator/skills/`
- Read project metadata from registry

**Best Practices**:
- Always check file existence before reading
- Use offset/limit for large files
- Read AGENTS.md and TOOLS.md of target workspaces before dispatch

### Write
**Purpose**: Create and update files

**Usage Patterns**:
- Create task plans in `.sisyphus/plans/`
- Write subagent instructions
- Update project registry
- Create result synthesis documents

**Constraints**:
- Never overwrite without reading first
- Always include proper headers/metadata
- Use atomic writes when possible

### Bash
**Purpose**: Execute shell commands

**Usage Patterns**:
- Project discovery: `find`, `ls`, `git status`
- Git operations: `git log`, `git diff`, `git branch`
- Environment checks: `python --version`, `node --version`

**Security**:
- Read-only commands preferred
- Avoid destructive operations
- Validate inputs to prevent injection

### Glob
**Purpose**: Find files matching patterns

**Usage Patterns**:
- Find all projects: `**/pyproject.toml`
- Find skill files: `**/SKILL.md`
- Find test files: `**/test_*.py`
- Find planning files: `.sisyphus/**/*.md`

### Grep
**Purpose**: Search file contents

**Usage Patterns**:
- Search for dependencies in config files
- Find TODO comments across projects
- Locate specific function implementations
- Search for error patterns in logs

## LSP Tools

### lsp_goto_definition
**Purpose**: Jump to symbol definition

**Usage**: Navigate to function/class definitions when analyzing code

### lsp_find_references
**Purpose**: Find all usages of a symbol

**Usage**: Assess impact of changes before dispatching refactoring tasks

### lsp_symbols
**Purpose**: Get file outline or search workspace symbols

**Usage**: Understand file structure and find symbols quickly

### lsp_diagnostics
**Purpose**: Check for errors/warnings

**Usage**: Validate code health before and after changes

## Agent Management Tools

### call_omo_agent
**Purpose**: Spawn specialized subagents

**Usage Patterns**:
- Spawn `searcher` for research tasks
- Spawn `syshelper` for system introspection
- Spawn `script_coder` for script development
- Spawn `watchdog` for monitoring

**Parameters**:
- `description`: Clear task description
- `prompt`: Detailed instructions for the agent
- `run_in_background`: Set to `true` for async execution

**Best Practices**:
- Use `run_in_background=True` for parallel tasks
- Include full context in prompt
- Set clear expectations for output format

### background_output
**Purpose**: Retrieve results from background agents

**Usage Patterns**:
- Poll for completion status
- Retrieve partial results for progress updates
- Get final output after agent completes

### background_cancel
**Purpose**: Cancel running background tasks

**Usage Patterns**:
- Cancel tasks exceeding ETA
- Clean up on error conditions
- Stop parallel tasks when one fails

## Workspace Tools

### skill
**Purpose**: Load and execute skills

**Usage Patterns**:
- Load `oe-project-registry` for project discovery
- Load `oe-worker-dispatch` for subagent management
- Load `oe-git-context` for git operations
- Load `planning-with-files` for task planning

## Session Tools

### session_list
**Purpose**: List OpenCode sessions

**Usage**: Monitor active sessions for watchdog functionality

### session_read
**Purpose**: Read session history

**Usage**: Analyze past interactions for context

### session_search
**Purpose**: Search session messages

**Usage**: Find specific conversations or patterns

### session_info
**Purpose**: Get session metadata

**Usage**: Check session status and activity

## Web Tools

### webfetch
**Purpose**: Fetch web content

**Usage**: Retrieve documentation, API specs, or examples

### websearch_web_search_exa
**Purpose**: Search the web

**Usage**: Research topics, find libraries, look up best practices

### grep_app_searchGitHub
**Purpose**: Search GitHub code

**Usage**: Find real-world code examples for implementation patterns

### context7_resolve-library-id / context7_query-docs
**Purpose**: Query library documentation

**Usage**: Get up-to-date API documentation and examples

## Tool Selection Guide

### When to Use Each Tool

| Task Type | Primary Tools | Secondary Tools |
|-----------|--------------|-----------------|
| Project Discovery | Glob, Read | Bash, Grep |
| Task Planning | Write, Read | skill(planning-with-files) |
| Code Analysis | Read, lsp_symbols | lsp_goto_definition, lsp_find_references |
| Worker Dispatch | call_omo_agent | background_output, background_cancel |
| Result Synthesis | Read, Write | Grep, Glob |
| Git Context | Bash(git) | Read, Grep |
| Research | websearch_web_search_exa | webfetch, grep_app_searchGitHub |
| Monitoring | session_list, session_info | call_omo_agent(watchdog) |

## Output Formats

### Task Plan Format
```markdown
# Task Plan: [Name]

## Overview
Brief description

## Steps
1. [Step 1]
2. [Step 2]
...

## ETA
Estimated duration

## Subagents
- Agent 1: Task description
- Agent 2: Task description
```

### Dispatch Request Format
```yaml
agent_type: [searcher|syshelper|script_coder|watchdog]
task: Clear description
context:
  - Relevant file paths
  - Key constraints
  - Expected output
output_format: Structured format specification
timeout: Estimated duration
```

### Result Synthesis Format
```markdown
## Summary
Brief overview of completed work

## Results
### From [Agent 1]
- Result item 1
- Result item 2

### From [Agent 2]
- Result item 1

## Artifacts
- `/path/to/file1` - Description
- `/path/to/file2` - Description

## Next Steps
1. Recommended action 1
2. Recommended action 2
```

## Constraints

1. **Never modify main session state directly**
2. **Always validate inputs before bash commands**
3. **Use LSP tools for code intelligence over manual parsing**
4. **Prefer native subagent dispatch for parallel work**
5. **Always include ETA estimates with dispatches**
