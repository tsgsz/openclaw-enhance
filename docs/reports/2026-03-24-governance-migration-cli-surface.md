# Validation Report: governance-migration

- **Date**: 2026-03-24
- **Feature Class**: cli-surface
- **Environment**: macOS /Users/tsgsz/.openclaw
- **Conclusion**: PASS

## Baseline State

- OpenClaw Home: `/Users/tsgsz/.openclaw`
- Installed: True
- Version: 0.1.0
- Config Exists: True (openclaw.json)

## Execution Log

### Command 1: ✓ PASS

```bash
python -m openclaw_enhance.cli status
```

- Exit Code: 0
- Duration: 0.08s

**stdout:**
```
Installation Path: /Users/tsgsz/.openclaw/openclaw-enhance
Installed: Yes
Version: 0.1.0
Install Time: 2026-03-23T14:32:26.912320
Components (34):
  - main-tool-gate
  - workspace:oe-specialist-finance
  - workspace:oe-watchdog
  - workspace:oe-orchestrator
  - workspace:oe-syshelper
  - workspace:oe-searcher
  - workspace:oe-specialist-km
  - workspace:oe-tool-recovery
  - workspace:oe-script_coder
  - workspace:oe-specialist-game-design
  - workspace:oe-specialist-creative
  - workspace:oe-specialist-ops
  - main-skill:oe-eta-estimator
  - main-skill:oe-toolcall-router
  - main-skill:oe-timeout-state-sync
  - hooks:assets
  - agent:oe-orchestrator
  - agent:oe-searcher
  - agent:oe-syshelper
  - agent:oe-script_coder
  - agent:oe-watchdog
  - agent:oe-tool-recovery
  - agent:oe-specialist-ops
  - agent:oe-specialist-finance
  - agent:oe-specialist-km
  - agent:oe-specialist-creative
  - agent:oe-specialist-game-design
  - agents:registry
  - hooks:subagent-spawn-enrich
  - agents:model-config
  - extension:oe-runtime
  - runtime:state
  - playbook
  - monitor:launchagent
```

### Command 2: ✓ PASS

```bash
python -m openclaw_enhance.cli status --json
```

- Exit Code: 0
- Duration: 0.08s

**stdout:**
```
{
  "installed": true,
  "version": "0.1.0",
  "install_path": "/Users/tsgsz/.openclaw/openclaw-enhance",
  "components": [
    "main-tool-gate",
    "workspace:oe-specialist-finance",
    "workspace:oe-watchdog",
    "workspace:oe-orchestrator",
    "workspace:oe-syshelper",
    "workspace:oe-searcher",
    "workspace:oe-specialist-km",
    "workspace:oe-tool-recovery",
    "workspace:oe-script_coder",
    "workspace:oe-specialist-game-design",
    "workspace:oe-specialist-creative",
    "workspace:oe-specialist-ops",
    "main-skill:oe-eta-estimator",
    "main-skill:oe-toolcall-router",
    "main-skill:oe-timeout-state-sync",
    "hooks:assets",
    "agent:oe-orchestrator",
    "agent:oe-searcher",
    "agent:oe-syshelper",
    "agent:oe-script_coder",
    "agent:oe-watchdog",
    "agent:oe-tool-recovery",
    "agent:oe-specialist-ops",
    "agent:oe-specialist-finance",
    "agent:oe-specialist-km",
    "agent:oe-specialist-creative",
    "agent:oe-specialist-game-design",
    "agents:registry",
    "hooks:subagent-spawn-enrich",
    "agents:model-config",
    "extension:oe-runtime",
    "runtime:state",
    "playbook",
    "monitor:launchagent"
  ],
  "locked": false,
  "lock_info": null,
  "install_time": "2026-03-23T14:32:26.912320"
}
```

### Command 3: ✓ PASS

```bash
python -m openclaw_enhance.cli doctor
```

- Exit Code: 0
- Duration: 0.07s

**stdout:**
```
Doctor checks passed.
```

### Command 4: ✓ PASS

```bash
python -m openclaw_enhance.cli cleanup-sessions --dry-run --json
```

- Exit Code: 0
- Duration: 0.07s

**stdout:**
```
{
  "safe_to_remove": [],
  "skipped_active": [],
  "skipped_uncertain": [],
  "removed": [],
  "dry_run": true
}
```

### Command 5: ✓ PASS

```bash
python -m openclaw_enhance.cli render-workspace oe-orchestrator
```

- Exit Code: 0
- Duration: 0.07s

**stdout:**
```
# Workspace: oe-orchestrator

**Path:** `/Users/tsgsz/workspace/openclaw-enhance/.worktrees/governance-migration/workspaces/oe-orchestrator`

---
schema_version: 1
agent_id: oe-orchestrator
workspace: oe-orchestrator
routing:
  description: High-capability dispatcher for project discovery, worker routing, and result synthesis.
  capabilities: [introspection, documentation, monitoring, recovery]
  accepts: [complex_tasks, multi_agent_tasks, orchestration_requests]
  rejects: [direct_worker_execution, main_session_mutation]
  output_kind: orchestration_report
  mutation_mode: repo_write
  can_spawn: true
  requires_tests: false
  session_access: read_only
  network_access: web_research
  repo_scope: full_repo
  cost_tier: premium
  model_tier: premium
  duration_band: long
  parallel_safe: false
  priority_boost: 3
  tool_classes: [repo_write, code_search, orchestration]
---
# AGENTS.md - Orchestrator Workspace

这个 workspace 是 `openclaw-enhance` 的调度面：负责识别项目、选择 worker、分发任务、收集结果并向主会话汇总。

## Session Startup

- 把 frontmatter 当作运行时发现元数据；worker 选择依赖 `workspaces/*/AGENTS.md` 的 frontmatter，而不是正文长描述。
- 先读 `TOOLS.md` 里的本地路径和仓库约定；不要把它当成第二份技能手册。
- **首先加载 `oe-memory-sync`**：主动获取 Main Session 的上下文（parent_session 历史、main memory 文件、project context、**Main 的 TOOLS.md**）。
  - Orchestrator 是 Main 的分身，必须继承 Main 的工具知识。Main 的 TOOLS.md 描述了系统可用的完整工具集、使用限制和配置，Orchestrator 在规划和 dispatch 时需要这些信息来准确判断能力边界。
- 根据任务加载对应 skill：
  - `oe-memory-sync`：获取 Main 会话上下文，理解用户之前和 main 聊了什么，以及 Main 拥有的工具集
  - `oe-project-registry`：项目发现、注册表位置、项目类型判断
  - `oe-worker-dispatch`：worker 分发、恢复流程与结果汇总
  - `oe-git-context`：git 历史和上下文注入
  - `oe-agentos-practice`：规划、实现与质量模式

## Role

- 对复杂任务做编排，而不是亲自承担所有执行细节。
- **Orchestrator Self-Execution Policy**: Orchestrator 是一个调度器，严禁静默吸收本应由 worker 执行的实质性工作。
  - **允许的自执行例外（Narrow Exceptions）**: 仅限于 worker 选择、dispatch 规划、checkpoint 通信、结果汇总（synthesis）以及类似的琐碎编排记账工作。
  - **必须分发的工作**: 任何实质性的调研（research）、内省（introspection）、编码（coding）、监控（monitoring）或其他符合 worker 职责的子任务，必须通过 `sessions_spawn` 分发给子 worker。
- **Proof Surfaces**: 系统通过两种互补的证明面验证调度行为：
  - **Runtime Surface**: 仅证明 Orchestrator 已启动、加载了正确的 workspace，并进入了可调度状态。这是弱证明，不保证实际分发。
  - **Child-Dispatch Surface**: 证明 Orchestrator 针对实质性任务确实完成了子 worker 分发，并能通过 transcript 归因到子 worker 会话。这是强证明，验证了调度策略的执行。
- 以最小权限原则选择 worker，并把多 worker 结果整理成主会话可消费的结论。

## Boundaries

- 不直接修改主会话配置、身份文件或用户偏好文件。
- 不在正文里重复 worker 的能力合同；worker 能力以各自 `AGENTS.md` frontmatter 为准。
- 详细 dispatch/recovery/checkpoint 规则只放在 `skills/*/SKILL.md` 中维护。
- `TOOLS.md` 只保留本地笔记；若出现通用流程或策略，迁回对应 skill。

## Skills

- `oe-memory-sync`：获取 Main Session 上下文（parent_session 历史、memory 文件、project context、**Main TOOLS.md**）
- `oe-project-registry`：发现项目、记录项目路径、给 dispatch 提供项目范围
- `oe-worker-dispatch`：负责任务拆分、worker 选择、轮次推进、恢复分支与汇总格式、**dispatch context enrichment（含 main tools）**
- `oe-git-context`：为 worker prompt 注入最近变更、文件历史与相关提交
- `oe-agentos-practice`：提供规划、实现、测试与重构约定

## Version

Version: 1.5.0
Last Updated: 2026-03-23


---

# TOOLS.md - Local Notes

Skills define how tools work. 这个文件只记录 `oe-orchestrator` 在本仓库里的本地路径和使用提醒。

## Local Paths

- Worker manifests: `workspaces/*/AGENTS.md`
- Worker skill contracts: `workspaces/*/skills/*/SKILL.md`
- Planning artifacts: `.sisyphus/plans/`
- Scratch notes: `.sisyphus/notepads/`
- Project registry: `~/.openclaw/openclaw-enhance/project-registry.json`

## Local Reminders

- 用 `render-workspace oe-orchestrator` 检查最终注入的 workspace 内容。
- routing 元数据放在 `AGENTS.md` frontmatter；具体流程和方法论放到相关 `SKILL.md`。
- 如果这里出现通用工具策略、dispatch 流程或 output 模板，说明内容放错层了，应该迁回 skill。

## Skill Map

- `oe-project-registry`：项目发现和注册表说明
- `oe-worker-dispatch`：worker 选择、dispatch 轮次、checkpoint、recovery、结果汇总
- `oe-git-context`：git 历史提取和 prompt 注入
- `oe-agentos-practice`：规划、实现和质量模式


---

# Workspace Skills

## oe-agentos-practice

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


---

## oe-domain-router

---
name: oe-domain-router
version: 1.0.0
description: Domain specialist routing for oe-orchestrator. Maps domain-specific tasks to specialized agents.
---

# oe-domain-router

Orchestrator 用于识别领域专家任务并路由到对应的 oe-specialist-* agent。

## 领域映射

| Domain | Agent | 职责 |
|--------|-------|------|
| finance | oe-specialist-finance | 财务分析、报表、投资决策 |
| ops | oe-specialist-ops | 运维诊断、tunnels/backup/launchd/服务检查 |
| km | oe-specialist-km | 知识管理、文档整理 |
| creative | oe-specialist-creative | 创意内容生成 |
| game-design | oe-specialist-game-design | 游戏设计文档 |

## 何时使用

- 用户任务明确属于某个高约束领域
- 需要领域特定的工具、技能或约束
- 任务需要专门的输出格式或验证规则

## Dispatch 协议

### 1. 项目选择（Orchestrator 负责）

```bash
python3 ~/.openclaw/openclaw-enhance/scripts/project_select.py \
  --task "<user_task>" \
  [--name "<project_name>"]
```

返回：`project_root` 和建议的 `output_relpath`

### 2. sessions_spawn 模板

```text
[Domain Specialist Task]

domain: <finance|ops|km|creative|game-design>
project_root: <abs path or empty>
output_relpath: <rel path or empty>

User task:
<paste user task verbatim>

Hard requirements:
1) Call session_status and parse session_id from sessionKey suffix
2) Write intermediate work to: sessions/session_<session_id>/out/
3) If project_root provided: write final artifact to <project_root>/<output_relpath>
4) Read sub_agents_state.json to find from_session_id
5) sessions_send summary (<= 20 lines) to from_session_id with:
   - type: "specialist_done"
   - status: completed|blocked|partial
   - artifacts: ["<abs paths>"]
   - summary: "<Status/Evidence/Decisions/Output path>"
6) Final reply: ANNOUNCE_SKIP
```

### 3. 输出路径默认值

- finance: `reports/finance/<YYYYMMDD-HHMM>/report.md`
- ops: `reports/ops/<YYYYMMDD-HHMM>/report.md`
- km: `reports/km/<YYYYMMDD-HHMM>/plan.md`
- creative: `assets/<YYYYMMDD-HHMM>/`
- game-design: `reports/game-design/<YYYYMMDD-HHMM>/report.md`

## Orchestrator 使用流程

1. 识别任务属于哪个 domain
2. 调用 project_select.py 获取 project_root
3. 构造 task prompt（使用上述模板）
4. sessions_spawn(agentId="oe-specialist-<domain>", task=...)
5. 等待 sessions_send 回传
6. 汇总结果返回给 Main

## 与 oe-worker-dispatch 的关系

- oe-worker-dispatch: 通用 worker 路由（searcher/syshelper/script_coder）
- oe-domain-router: 领域专家路由（specialist-*）
- 两者互补，不冲突


---

## oe-git-context

---
name: oe-git-context
version: 1.0.0
description: Git history and context injection for worker tasks
author: openclaw-enhance
tags: [orchestrator, git, context, history, workers]
---

# oe-git-context

Skill for extracting and injecting git context into worker tasks.

## Purpose

Git history provides crucial context for coding tasks. This skill:
- Extracts relevant git history
- Identifies recent changes and authors
- Finds related commits and files
- Injects context into worker prompts
- Tracks changes during task execution

## When to Use

Use this skill when:
- Starting work on existing code
- Debugging issues (find when introduced)
- Understanding code evolution
- Reviewing changes before/after work
- Providing context to subagents
- Tracking task-related changes

## Capabilities

### Context Extraction

#### Recent History
```bash
# Last N commits
git log -n 10 --oneline

# Recent commits with stats
git log -n 5 --stat

# Recent changes to specific file
git log -n 5 --follow -- src/module.py
```

#### File History
```bash
# Who changed this file
git log --follow --format="%h %an %s" -- src/file.py

# When was line added
git blame -L 10,20 src/file.py

# File evolution
git log --follow -p -- src/file.py
```

#### Branch Information
```bash
# Current branch
git branch --show-current

# Branches containing commit
git branch --contains abc123

# Branch divergence
git log --oneline --graph --left-right main...feature
```

### Context Types

#### 1. Recent Changes Context
Provides overview of recent activity

```markdown
## Recent Changes (Last 5 commits)

| Commit | Author | Message | Date |
|--------|--------|---------|------|
| abc123 | Alice | feat(auth): add OAuth support | 2 hours ago |
| def456 | Bob | fix(api): handle null responses | 5 hours ago |
| ... | ... | ... | ... |

### Files Changed Recently
- src/auth/oauth.py (added)
- src/api/handlers.py (modified)
- tests/test_oauth.py (added)
```

#### 2. File-Specific Context
Provides history for specific files being worked on

```markdown
## File History: src/auth/oauth.py

### Evolution
1. **Initial commit** (2 weeks ago) - Basic OAuth structure
2. **Add token refresh** (1 week ago) - Refresh token support
3. **Error handling** (3 days ago) - Better error messages
4. **OAuth support** (2 hours ago) - Added OAuth2 flow

### Authors
- Alice: 5 commits
- Bob: 2 commits

### Related Files (changed together)
- src/auth/token.py
- src/config/auth.py
```

#### 3. Related Commits Context
Finds commits related to a topic

```markdown
## Related Commits for "authentication"

Commits mentioning auth/authentication:
- abc123: feat(auth): add OAuth support
- def789: refactor(auth): extract auth logic
- xyz789: test(auth): add auth tests
```

#### 4. Line-Level Context
Blame information for specific code sections

```markdown
## Code Context (lines 45-55)

```python
def validate_token(token: str) -> bool:  # Alice, 2 days ago
    """Validate JWT token."""                   # Alice, 2 days ago
    try:                                        # Bob, 1 week ago
        payload = decode(token)                 # Alice, 2 days ago
        return payload["exp"] > time.time()    # Alice, 2 days ago
    except JWTError:                            # Bob, 1 week ago
        return False                            # Bob, 1 week ago
```

- Last modified by: Alice
- Context: "Add token validation"
- Related PR: #123
```

## Usage

### Extract Context for Task
```python
context = extract_git_context(
    project_path="/path/to/project",
    files=["src/auth/oauth.py", "src/api/handlers.py"],
    context_types=["recent", "file_history", "related"],
    depth=10  # commits to include
)
```

### Inject into Worker Prompt
```python
worker_prompt = f"""
{task_description}

## Git Context
{format_git_context(context)}

## Task
Implement the feature considering the above context.
"""
```

### Track Changes During Task
```python
# Before starting
baseline = get_git_snapshot(project_path)

# ... task execution ...

# After completing
changes = get_changes_since(baseline)
```

## Context Injection Strategies

### Strategy 1: Full History
Include complete recent history
- **Best for**: New contributors, complex tasks
- **Cost**: Higher token usage
- **Format**: All recent commits + file histories

### Strategy 2: Focused History
Include only relevant commits
- **Best for**: Focused changes, experienced developers
- **Cost**: Moderate token usage
- **Format**: Commits touching relevant files only

### Strategy 3: Summary Only
High-level overview
- **Best for**: Quick tasks, familiar codebase
- **Cost**: Low token usage
- **Format**: Statistics and key changes only

## Worker Integration

### searcher
```python
# Search task with git context
prompt = f"""
Research best practices for OAuth implementation.

Context: We're adding OAuth to an existing auth system.
Recent auth-related changes:
{git_context.recent_auth_commits}
"""
```

### script_coder
```python
# Coding task with git context
prompt = f"""
Add refresh token support to the OAuth implementation.

Current OAuth code (from git history):
{git_context.file_history('src/auth/oauth.py')}

Recent related changes:
{git_context.recent_changes}
"""
```

### syshelper
```python
# File exploration with git context
prompt = f"""
Find all files that changed in the last OAuth PR.

Reference commit: {git_context.recent_auth_commit}
Changed files: {git_context.changed_files}
"""
```

## Best Practices

1. **Selective Context**: Don't include all history - focus on relevant commits
2. **Recency Bias**: Recent changes are more relevant than old ones
3. **Author Awareness**: Note who made changes for potential questions
4. **Related Files**: Files changed together are often logically related
5. **Baseline Snapshots**: Record git state at task start for comparison

## Safety

### Read-Only Operations
All git operations in this skill are read-only:
- `git log`
- `git blame`
- `git show`
- `git diff`
- `git status`

### No Modifications
This skill never:
- Creates commits
- Changes branches
- Modifies files
- Runs `git checkout`, `git reset`, etc.

## Integration

### With oe-project-registry
Get project path from registry for context extraction

### With oe-worker-dispatch
Inject context into worker prompts automatically

### With planning-with-files
Include git context in task plans for reference

## Example: Complete Workflow

```python
# 1. Get project info
project = get_project("proj-001")

# 2. Extract context for task
context = extract_git_context(
    project_path=project.path,
    files=["src/auth/oauth.py"],
    context_types=["recent", "file_history"]
)

# 3. Create worker prompt with context
prompt = f"""
Add OAuth2 refresh token support.

Current implementation context:
{format_context(context)}

Requirements:
- Support refresh token flow
- Maintain backward compatibility
- Add appropriate tests
"""

# 4. Dispatch to worker
result = dispatch_task(
    agent_type="script_coder",
    task=prompt
)

# 5. Track changes
changes = get_task_changes(project.path)
```

## Output Formats

### Markdown Format
Default human-readable format with tables and sections

### JSON Format
Machine-readable for programmatic processing
```json
{
  "recent_commits": [...],
  "file_history": {
    "src/file.py": [...]
  },
  "related_commits": [...],
  "authors": {...}
}
```

### Compact Format
Token-optimized for LLM consumption
```
Recent: abc123 feat(auth): OAuth, def456 fix(api): nulls
Files: src/auth/oauth.py (Alice 5x, Bob 2x)
```


---

## oe-memory-sync

---
name: oe-memory-sync
version: 1.0.0
description: Main session context fetching for orchestrator startup
author: openclaw-enhance
tags: [orchestrator, memory, context, session, main]
---

# oe-memory-sync

Skill for fetching and synchronizing Main session context into the Orchestrator at startup.

## Purpose

When the Orchestrator starts (via `sessions_spawn` from Main), it needs to understand:
- What the user was discussing with Main before spawning Orch
- Key decisions or context from the conversation
- Main's memory files that might be relevant
- Current project context

This skill enables Orchestrator to proactively fetch this context at session start.

## When to Use

Use this skill when:
- Orchestrator session is starting (first turn)
- Task requires understanding prior conversation context
- Need to know user's goals/preferences from Main session
- Project context is unclear from task description alone

## Context Sources

### 1. Parent Session History

The `parent_session` ID is passed via spawn enrichment hook. Use `sessions_history` tool:

```python
# Get parent session messages
parent_history = sessions_history(parent_session_id)

# Extract key information:
# - User's original request
# - Main's analysis/responses
# - Any decisions made
# - Files mentioned or created
```

### 2. Main Workspace Memory Files

Main stores memories in `~/.openclaw/memory/` directory:

```python
# Common memory file patterns:
# - ~/.openclaw/memory/YYYY-MM-DD.md (daily memories)
# - ~/.openclaw/memory/projects/{project}/notes.md

# Read recent memory files to understand:
# - Ongoing projects
# - User preferences
# - Past decisions
```

### 3. Runtime State

Orchestrator can check `runtime-state.json` for:

```python
runtime_state = read("~/.openclaw/openclaw-enhance/runtime-state.json")
# Fields:
# - active_project: Currently active project
# - project_occupancy: Which orch owns which project
# - last_updated_utc: When state was last modified
```

### 4. Project Registry

For the active project, fetch details from `project-registry.json`:

```python
registry = read("~/.openclaw/openclaw-enhance/project-registry.json")
# Contains:
# - Project paths
# - Project types (permanent/temporary)
# - Git associations
```

### 5. Main TOOLS.md

Main's `TOOLS.md` describes the tool landscape visible to main session. Since the Orchestrator is Main's delegate for complex tasks, it must inherit Main's tool knowledge to make informed dispatch and planning decisions.

```python
# Main workspace path follows OpenClaw config resolution:
#   1. openclaw.json → agent.workspace (if set)
#   2. OPENCLAW_PROFILE env → ~/.openclaw/workspace-{profile}
#   3. Default → ~/.openclaw/workspace
#
# TOOLS.md location:
main_tools_path = f"{main_workspace_path}/TOOLS.md"

main_tools = read(main_tools_path)
# Contains:
# - Available MCP servers and their tool lists
# - Tool usage guidelines and restrictions
# - Custom tool configurations
# - Tool aliases and preferred invocations
```

**Why this matters:**
- Orchestrator needs to know which tools exist system-wide to correctly scope worker tasks
- Some tools are only available at main level; Orchestrator must know this boundary
- Tool restrictions/guidelines from main apply transitively to Orchestrator's planning

## Usage Pattern

### Session Startup Flow

```
Orchestrator Session Start
    │
    ▼
Load oe-memory-sync skill
    │
    ▼
Extract parent_session from context
    │
    ▼
Fetch Parent History ──► sessions_history(parent_session)
    │
    ▼
Fetch Main Memory ──► read memory/*.md files
    │
    ▼
Fetch Project Context ──► runtime-state.json + project-registry.json
    │
    ▼
Fetch Main Tools ──► read {main_workspace}/TOOLS.md
    │
    ▼
Synthesize Context
    │
    ▼
Inject into task understanding
```

### Implementation

```python
async def sync_main_context():
    """Fetch and synthesize Main session context."""
    
    # 1. Get parent session ID from spawn context
    parent_session = context.get("parent_session")
    if not parent_session:
        return {"status": "no_parent", "context": {}}
    
    # 2. Fetch parent session history
    history = sessions_history(parent_session, limit=50)
    history_summary = summarize_conversation(history)
    
    # 3. Fetch main memory files
    memory_files = glob(f"{main_workspace}/memory/*.md")
    memory_content = read_multiple(memory_files, limit=10)  # Recent 10
    
    # 4. Fetch project context
    runtime_state = read(runtime_state_path)
    registry = read(project_registry_path)
    active_project = runtime_state.get("active_project")
    project_info = registry.get_project(active_project) if active_project else None
    
    # 5. Fetch Main TOOLS.md
    main_workspace_path = resolve_main_workspace()  # ~/.openclaw/workspace
    main_tools_path = f"{main_workspace_path}/TOOLS.md"
    main_tools = read(main_tools_path) if file_exists(main_tools_path) else ""
    
    # 6. Synthesize into context
    context = {
        "parent_history_summary": history_summary,
        "main_memory": memory_content,
        "active_project": project_info,
        "parent_session_id": parent_session,
        "main_tools": main_tools,
    }
    
    return context
```

## Context Injection

After fetching, inject the context into Orchestrator's understanding:

```python
def inject_orch_context(context):
    """Inject fetched context into Orchestrator prompt."""
    parts = [f"""
## Main Session Context

### Prior Conversation Summary
{context['parent_history_summary']}

### Relevant Memory
{context['main_memory']}

### Active Project
{format_project_info(context['active_project'])}
"""]

    # Include Main's tool landscape if available
    if context.get('main_tools'):
        parts.append(f"""
### Main Tools
{context['main_tools']}
""")

    parts.append(f"""
### Task
{current_task_description}

Use the above context to better understand the user's intent and
provide more informed orchestration decisions.
The Main Tools section describes the full tool landscape available to main session.
Use this to inform dispatch decisions and worker task scoping.
""")
    return "\n".join(parts)
```

## Summarization Strategy

### Parent History Summary

Don't include full history — summarize key points:

```python
def summarize_conversation(history):
    """Extract key points from conversation history."""
    key_points = []
    
    for msg in history:
        if msg.role == "user":
            # Capture user's original request
            key_points.append(f"User request: {truncate(msg.content, 200)}")
        elif msg.role == "assistant" and msg.content:
            # Capture Main's significant responses
            if is_significant(msg):
                key_points.append(f"Main response: {truncate(msg.content, 200)}")
    
    return "\n".join(key_points[-10:])  # Last 10 significant points
```

### Memory Prioritization

Focus on recent and relevant memories:

1. **Today's memories** (highest priority)
2. **This week's memories** (high priority)
3. **Project-specific memories** (medium priority)
4. **Old memories** (low priority, skip unless directly relevant)

## Integration

### With oe-project-registry

Use project registry to identify which project context to fetch:
- Permanent projects have stable paths and git associations
- Temporary projects may have ephemeral context

### With oe-worker-dispatch

The fetched context should inform:
- Worker selection (what context matters for this task)
- Dispatch instructions (what context to pass to workers)
- Result synthesis (how to incorporate context into final answer)

### With planning-with-files

Memory context should be available when creating task plans:
```python
# In planning phase
context = await sync_main_context()
plan = create_plan(task, context=context)
```

## Safety

### Read-Only Operations

This skill only reads:
- `sessions_history()` - conversation history
- `read()` - memory files, state files
- `glob()` - finding memory files

### No Modifications

This skill never:
- Modifies session history
- Edits memory files
- Changes runtime state
- Sends messages to Main

## Error Handling

| Scenario | Response |
|----------|----------|
| No parent_session | Return empty context, log warning |
| Parent session not found | Log error, continue without history |
| Memory files missing | Continue without memory, log info |
| Runtime state unavailable | Use defaults, log warning |
| Main TOOLS.md missing | Continue with empty main_tools, log info |

## Example

```python
# Orchestrator session start
async def on_session_start():
    # Fetch Main context
    ctx = await sync_main_context()
    
    if ctx["parent_history_summary"]:
        print(f"📋 Parent conversation context available")
        print(f"   Project: {ctx['active_project']}")
    
    if ctx.get("main_tools"):
        print(f"🔧 Main tool landscape loaded")
    
    # Now proceed with task understanding
    task = current_task()
    enhanced_task = inject_orch_context(ctx, task)
    
    # Continue with orchestration...
```

## Output Schema

```yaml
context:
  parent_session_id: string
  parent_history_summary: string
  main_memory: string
  active_project:
    name: string
    path: string
    type: permanent | temporary
  main_tools: string          # Content of Main's TOOLS.md (empty string if unavailable)
  timestamp: ISO8601
  status: complete | partial | unavailable
```


---

## oe-project-registry

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


---

## oe-worker-dispatch

---
name: oe-worker-dispatch
version: 1.1.0
description: Subagent task dispatch and result synthesis for the Orchestrator
author: openclaw-enhance
tags: [orchestrator, dispatch, subagent, workers, parallel]
---

# oe-worker-dispatch

Skill for dispatching tasks to specialized subagents and synthesizing their results.

## Purpose

The Orchestrator delegates work to specialized subagents via the native `announce` mechanism. This skill provides:
- Task-to-agent matching
- Dispatch configuration
- Result collection
- Output synthesis
- Error handling

### Orchestrator Self-Execution Exception Policy

The Orchestrator is a dispatcher and MUST NOT silently absorb substantive worker-eligible work.

- **Allowed Self-Execution Exceptions**: Limited to worker selection, dispatch planning, checkpoint communication, result synthesis, and trivial orchestration bookkeeping.
- **Mandatory Dispatch**: Substantive research, introspection, coding, monitoring, and other worker-eligible subwork MUST become child `sessions_spawn` dispatches.
- **No Implicit Fallback**: If a task is eligible for a worker, the Orchestrator is prohibited from executing it directly.

### Dispatch Proof Surfaces

The system validates this policy through two distinct proof surfaces:
- **Runtime Surface (`routing-yield`)**: Proves the Orchestrator is active and has the `sessions_yield` tool. This is a surface-level check only.
- **Child-Dispatch Surface (`orchestrator-spawn`)**: Proves the Orchestrator actually called `sessions_spawn` for a worker-eligible task. This is the primary proof of the dispatch contract.

## When to Use

Use this skill when:
- Task complexity requires multiple agents
- Parallel execution can speed up work
- Specialized expertise is needed (search, scripting, etc.)
- Monitoring long-running tasks
- Aggregating results from multiple sources

## Bounded Orchestration Loop

The Orchestrator uses a bounded multi-round loop for complex work:

```
Assess -> PlanRound -> DispatchRound -> YieldForResults -> CollectResults -> EvaluateProgress
                                                                 ↓
                                         Complete  <- No more work needed
                                         Blocked   <- Needs main-session decision
                                         Re-dispatch <- Another round adds new evidence
```

### Round Outcomes

`EvaluateProgress` must classify each round into one of these outcomes:

- **Complete**: Enough evidence gathered; synthesize and return to main.
- **Blocked**: External decision required; surface a checkpoint.
- **Re-dispatch**: Another round is justified by new evidence or narrowed uncertainty.
- **Recovery Dispatch**: Tool-usage failure requires `oe-tool-recovery`.
- **Recovery-Assisted Retry**: Retry the original worker with a `RecoveredMethod`.
- **Escalated**: Recovery failed or retry failed; stop the orchestration.

### Orchestrator-Owned State

The loop state belongs to the Orchestrator, not to `AGENTS.md` body text:

| Field | Purpose |
|-------|---------|
| `task_id` | Unique identifier for this orchestration |
| `round_index` | Current round number |
| `max_rounds` | default: 3, hard cap: 5 |
| `pending_dispatches` | Workers currently outstanding |
| `received_results` | Results collected from completed workers |
| `blocked_items` | External decisions required from main |
| `dedupe_keys` | Prevent duplicate dispatches without new evidence |
| `recovery_attempts` | Per-step retry counter (max 1) |
| `recovered_methods` | Stored `RecoveredMethod` objects by failed step |
| `recovery_in_progress` | Prevent nested recovery dispatch |
| `termination_state` | `active`, `completed`, `blocked`, `exhausted`, `escalated` |
| `termination_reason` | Human-readable reason for termination |

### Loop Controls

- **Max rounds**: Default 3, hard cap 5.
- **Max dispatches per round**: Default 3, hard cap 5 concurrent workers.
- **Incrementality rule**: Only open a new round if it adds new evidence or reduces uncertainty.
- **Duplicate dispatch guard**: Same worker + objective + context cannot be resent without new evidence.
- **Blocker escalation**: Two consecutive no-progress evaluations should terminate as `blocked`.
- **Recovery Cap**: Max ONE recovery-assisted retry per failed step.
- **No Recovery Loops**: Recovery worker failure or retry failure escalates immediately.
- **No Worker Handoff**: Recovery never creates worker-to-worker handoff; the Orchestrator remains the sole dispatcher.

## Discovery-First Worker Routing

The Orchestrator discovers and selects workers dynamically from their `AGENTS.md` frontmatter rather than using hardcoded descriptions. This enables the system to adapt as workers evolve without modifying dispatch logic.

### Worker Discovery Workflow

To discover worker manifests and route tasks dynamically:

```
Enumerate → Parse → Catalog → Filter → Rank → Dispatch
```

#### 1. Enumerate Worker Manifests

First, discover worker manifests by scanning available workspaces:

Discover all available workers by scanning `workspaces/*/AGENTS.md`:

```python
# Pseudocode for discovery
workspaces = list_workspaces()  # ['oe-searcher', 'oe-syshelper', ...]
manifests = [parse_agent_manifest(read(f"workspaces/{w}/AGENTS.md")) 
             for w in workspaces]
```

**Note**: `oe-orchestrator` is excluded from worker selection (it's the dispatcher, not a worker).

#### 2. Parse Frontmatter

Each worker's `AGENTS.md` contains YAML frontmatter with routing metadata:

```yaml
---
schema_version: 1
agent_id: oe-searcher
workspace: oe-searcher
routing:
  description: "Research-focused agent for web search and documentation"
  capabilities: [research, documentation]
  accepts: [research_tasks, documentation_queries]
  rejects: [file_modifications, code_implementation]
  mutation_mode: read_only
  can_spawn: false
  requires_tests: false
  cost_tier: cheap
  model_tier: cheap
  tool_classes: [web_search, web_fetch, code_search]
---
```

#### 3. Build Candidate Catalog

Parse all manifests into a catalog of eligible workers:

```python
catalog = [manifest for manifest in manifests if manifest.is_valid]
```

Invalid manifests (missing required fields, unknown enum values) are excluded from selection.

#### 4. Hard-Filter by Constraints

Apply hard constraints based on task requirements:

| Task Requirement | Filter Criteria |
|------------------|-----------------|
| Need file write | `mutation_mode: repo_write` only |
| Read-only safe | `mutation_mode: read_only` or `none` |
| Session access | `session_access: read_only` or `runtime_only` |
| Can spawn subagents | `can_spawn: true` |
| Requires tests | `requires_tests: true` |
| Network research | `network_access: web_research` |

**Example**: For a "find all TODO comments" task:
- Must support: `read_only` or `none` mutation
- Prefers: `code_search` tool class
- Excludes: workers with `mutation_mode: repo_write`

#### 5. Rank by Least-Privilege Rules

Apply least-privilege ranking to select the narrowest capable worker:

For remaining candidates, rank by narrowest scope first:

**Priority Order:**
1. **Narrowest mutation scope**: `read_only` > `sandbox_write` > `repo_write`
2. **Lowest cost**: `cheap` > `standard` > `premium`
3. **Fewest capabilities**: Single-purpose workers > general workers
4. **Tool class match**: Exact match > partial match

**Example Rankings:**
- "Find TODOs in codebase": `oe-syshelper` (read-only, code search) > `oe-script_coder` (repo write)
- "Research async patterns": `oe-searcher` (web research) > `oe-script_coder` (can do it but overkill)
- "Fix bug and add tests": `oe-script_coder` (repo write, requires_tests)

#### 6. Special-Case Branches

Some workers have dedicated routing paths outside normal scoring:

##### ACP/OpenCode Branch (External Development Harness)

**Trigger**: User explicitly requests OpenCode/opencode/ACP harness execution. This branch is **opt-in only** and is not the default path for ordinary coding work.

**Detection signals** (ANY of the following explicit user intent signals):
- User says "用 opencode 改" / "让 opencode 去做" / "用 opencode 开发"
- User explicitly asks for OpenCode / opencode / ACP harness handling
- User explicitly names a harness agent such as "opencode" while asking the Orchestrator to delegate execution through that harness

**Non-triggers**:
- A normal coding task without an explicit OpenCode/opencode/ACP request
- A request for issue / worktree / PR / CI / merge workflow by itself
- Ordinary search, diagnosis, or script work that already fits `oe-searcher`, `oe-syshelper`, or `oe-script_coder`

**Flow**:
1. Confirm project context via `oe-project-registry` (project path, branch)
2. Dispatch via ACP runtime using `sessions_spawn`:

```json
{
  "task": "<detailed task description with workflow instructions>",
  "runtime": "acp",
  "agentId": "opencode",
  "mode": "persistent",
  "cwd": "<project_root_path>"
}
```

3. When the user also requests a formal development workflow, include that workflow explicitly inside the ACP task:
   - Create issue describing the work
   - Create git worktree for isolation
   - Implement changes with tests
   - Create PR with description
   - Run CI checks
   - Merge after approval

**Constraints**:
- Only dispatch to ACP when user explicitly requests OpenCode/opencode/ACP harness execution or explicitly names a harness agent for delegation
- Do NOT treat issue → worktree → implementation/tests → PR → CI → merge workflow alone as sufficient to enter ACP; workflow wording only enriches the ACP task after the explicit harness trigger is present
- Do NOT automatically route all coding tasks to opencode — `oe-script_coder` handles normal coding within the OpenClaw ecosystem
- ACP sessions have their own lifecycle; monitor via `oe-watchdog` for long-running sessions
- `agentId` must match an entry in `openclaw.json` → `acp.allowedAgents` (default: `["opencode", "codex", "claude"]`)

**Example**:
```
Task: "用 opencode 修复 openclaw-enhance 的 session 清理 bug，要先提 issue 再开 worktree 再 PR 再 merge"
Enumerate: Check if ACP harness requested → YES ("用 opencode")
Dispatch: sessions_spawn({ runtime: "acp", agentId: "opencode", mode: "persistent", cwd: "/path/to/openclaw-enhance", task: "..." })
```

**Note**: `opencode` is dispatched through ACP runtime, NOT as an OpenClaw native workspace agent. It runs outside OpenClaw's agent system via the ACPX bridge.

##### Tool Recovery Branch
**Trigger**: Tool-usage failure (`tool_not_found`, `invalid_parameters`, `permission_denied`, `tool_execution_error`)

**Flow**:
1. Detect failure in worker results
2. Check recovery eligibility (max 1 retry per failed step)
3. Dispatch `oe-tool-recovery` with failure context
4. Receive `RecoveredMethod` with corrected invocation
5. Retry original worker OR escalate if recovery fails

**Note**: `oe-tool-recovery` is never selected through normal ranking—it's only dispatched for recovery scenarios.

##### Watchdog Branch
**Trigger**: Timeout monitoring, session health checks

**Flow**:
1. Long-running task detected
2. Spawn `oe-watchdog` to monitor progress
3. Watchdog alerts on timeout or issues
4. Orchestrator handles timeout response

**Note**: `oe-watchdog` is typically spawned alongside main workers, not as primary task executor.

### Dispatch Decision Examples

**Example 1: Research task**
```
Task: "Find best practices for Python logging"
Enumerate: All 5 workers
Filter: None require write access
Rank: oe-searcher (research, cheap) > oe-syshelper (can search but less focused)
Dispatch: oe-searcher
```

**Example 2: Code modification**
```
Task: "Fix the auth bug and add tests"
Enumerate: All 5 workers
Filter: Requires mutation_mode: repo_write, requires_tests: true
Rank: oe-script_coder (only match)
Dispatch: oe-script_coder
```

**Example 3: Exploration task**
```
Task: "What files import the database module?"
Enumerate: All 5 workers
Filter: Read-only sufficient
Rank: oe-syshelper (introspection, read-only, cheap) > oe-searcher (could grep but not its focus)
Dispatch: oe-syshelper
```

## Dispatch Patterns

### Iterative Round-Based Dispatch (v2)

For complex tasks requiring multiple refinement rounds, use the bounded iterative pattern:

```
Round N: Plan → Dispatch → Yield → Collect → Evaluate
                                              ↓
                    Complete ←── No more work
                    Blocked  ←── Needs decision
                    Next Round ←── Refine and continue
```

**Round Structure:**

1. **Plan Round**: Define specific objectives for this round
2. **Dispatch Workers**: Spawn agents via `sessions_spawn` with unique dispatch identities
3. **Yield for Results**: Call `sessions_yield` to cleanly end turn
4. **Collect via Announce**: Receive results on next turn via auto-announce
5. **Evaluate Progress**: Classify results, update state, decide next action

**Important**: After calling `sessions_yield`, wait for auto-announced results. Do not poll or query session state while waiting.

#### Dispatch Identity & Deduplication

Each dispatch within a round must have:
- **Unique dispatch_id**: `round-{N}-{worker}-{objective}` format
- **Dedupe key**: Hash of (task_context, worker_type, objective)
- **Expected result schema**: What constitutes completion for this dispatch

**Duplicate Dispatch Guard:**
- Same dedupe key cannot be resent without new evidence
- If result is late/missing, check `pending_dispatches` before re-dispatching
- Document reason for any re-dispatch in round state

#### Failure Classification

Worker results are classified into four categories:

| Category | Signal | Action |
|----------|--------|--------|
| **Retriable** | Transient failure, incomplete context | Limit 1 retry with clarified instructions |
| **Tool-Usage Failure** | tool_not_found, invalid_parameters, permission_denied, tool_execution_error | Route to oe-tool-recovery (max 1 attempt per failed step) |
| **Reroutable** | Wrong worker chosen, task too large | Change worker or decompose into subtasks |
| **Escalated** | Design conflict, needs main decision | Yield `blocked` checkpoint to main |

#### Recovery Dispatch

When a **Tool-Usage Failure** (tool-usage failure) is detected, the Orchestrator dispatches to `oe-tool-recovery` to generate a `RecoveredMethod` (recovered_method).

**Context Passed to Recovery Worker:**
- `failed_step`: Identity of the failed step
- `tool_name`: Name of the tool that failed
- `failure_reason`: Error message or signal from the worker
- `exact_invocation`: The failed tool call string

**Handoff & Re-entry:**
1. **Dispatch**: Orchestrator spawns `oe-tool-recovery` with the failure context via `sessions_spawn`.
2. **Yield**: Orchestrator calls `sessions_yield` to await the recovery suggestion.
3. **Evaluate**: Orchestrator receives `RecoveredMethod` and evaluates the `retry_owner` decision.
4. **Retry**: If `retry_owner` is `self`, the Orchestrator re-dispatches the original worker with the `exact_invocation` from the recovery result.
5. **Reroute**: If `retry_owner` is `script_coder`, `searcher`, or `syshelper`, the Orchestrator dispatches to that agent type instead.
6. **Orchestrator Owned**: If `retry_owner` is `orchestrator`, the Orchestrator handles the retry directly.
7. **Escalate**: If recovery fails or the assisted retry fails, the Orchestrator terminates as `escalated`.

**Constraints:**
- **Max 1 recovery-assisted retry** per failed step.
- **No worker-to-worker handoff**: Recovery worker never communicates with the failed worker (explicitly forbid direct handoff).
- **No business task execution**: Recovery worker only diagnoses and suggests; it never performs the original task.
- **Leaf-node only**: Recovery worker cannot spawn other agents.

#### Recovery Flow Examples

**Scenario 1: Tool-not-found**
- **Signal**: Worker reports `tool 'websearch' not found`.
- **Recovery**: `oe-tool-recovery` identifies that `websearch_web_search_exa` should be used instead.
- **Action**: Orchestrator re-dispatches worker with corrected tool call.

**Scenario 2: Invalid-parameter**
- **Signal**: `Edit` tool fails with `oldString not found`.
- **Recovery**: `oe-tool-recovery` reads the file and provides the exact `oldString` with correct indentation.
- **Action**: Orchestrator re-dispatches worker with corrected parameters.

**Scenario 3: Recovery failure escalation**
- **Signal**: `oe-tool-recovery` cannot find a solution or the assisted retry fails.
- **Action**: Orchestrator terminates orchestration as `escalated`.

#### Checkpoint Visibility to Main

Orchestrator reports to main only at milestones:

**Always report:**
- `started`: Orchestration begins
- `blocked`: External decision required
- `terminal`: Complete, exhausted, or escalated

**Conditionally report:**
- `meaningful_progress`: After round N if significant new findings/artifacts

**Never report:**
- Individual worker success within a round
- Routine round boundaries
- Internal re-dispatch decisions

### Native Primitive Usage

- **`sessions_spawn`**: The only dispatch path for worker sessions.
- **`sessions_yield`**: The round-boundary wait primitive used by the Orchestrator.
- **`announce`**: Worker result delivery path back into the orchestration loop.

Workers remain single-round executors. They do not use `sessions_yield` themselves.

### Sequential Dispatch (Legacy Pattern)
```
Task A → Agent 1 → Result 1
              ↓
Task B → Agent 2 → Result 2
              ↓
        Synthesis
```

Use when:
- Tasks have dependencies
- Results of one inform the next
- Order matters

### Parallel Dispatch
```
Task A → Agent 1 → Result 1 ─┐
                             ├──→ Synthesis
Task B → Agent 2 → Result 2 ─┘
```

Use when:
- Tasks are independent
- Speed is important
- No dependencies between tasks

### Hierarchical Dispatch (v1 NOT Supported)

**⚠️ Worker-Level Orchestration Disabled in v1**

Workers remain **single-round executors** and cannot spawn or orchestrate other workers. All multi-level coordination must be handled by the orchestrator within the bounded loop.

**v1 Constraint**: Only the orchestrator may dispatch workers. Workers complete their task and return results directly.

## Native Subagent Dispatch

All dispatch is done through OpenClaw's native `sessions_spawn` tool. Do NOT create wrapper functions.

### Single Task Dispatch

Use `sessions_spawn` to dispatch to a specific agent:

```json
{
  "task": "Research FastAPI dependency injection patterns",
  "agentId": "oe-searcher",
  "label": "auth-research"
}
```

### Parallel Task Dispatch

Spawn multiple agents in parallel using separate `sessions_spawn` calls:

```json
// Spawn 1: Research topic A
{
  "task": "Research topic A",
  "agentId": "oe-searcher",
  "label": "research-a"
}

// Spawn 2: Research topic B
{
  "task": "Research topic B",
  "agentId": "oe-searcher",
  "label": "research-b"
}

// Spawn 3: Find related files
{
  "task": "Find related files",
  "agentId": "oe-syshelper",
  "label": "file-discovery"
}
```

### Dispatch with Monitoring

For long-running tasks, spawn a watchdog alongside the worker:

```json
// Main worker
{
  "task": "Long-running code generation task",
  "agentId": "oe-script_coder",
  "label": "code-gen",
  "runTimeoutSeconds": 1800
}

// Watchdog (optional, for monitoring)
{
  "task": "Monitor code-gen task for timeout",
  "agentId": "oe-watchdog",
  "label": "code-gen-monitor"
}
```

## Result Synthesis

### Synthesis Strategies

1. **Concatenation**: Simple append for independent results
2. **Merge**: Combine overlapping information
3. **Summarize**: Extract key points from verbose outputs
4. **Prioritize**: Rank results by relevance/confidence
5. **Cross-reference**: Validate across multiple agents

### Synthesis Template

When synthesizing results from multiple subagents:

```markdown
## Summary
[High-level overview]

## Detailed Results

### From [Agent Type] - [Task Name]
[Agent output from announce]

### From [Agent Type] - [Task Name]
[Agent output from announce]

## Synthesis
[Combined insights, conflicts resolved, conclusions drawn]

## Artifacts
- [File paths created/modified]

## Next Steps
1. [Action item 1]
2. [Action item 2]
```

## Error Handling

### Agent Failure

When a subagent fails (announces failure or times out):

1. Check announce status for error details
2. Retry with adjusted parameters if transient
3. Escalate to main if unrecoverable

```markdown
## Agent Failure Response

**Failed Agent**: [agent type]
**Error**: [from announce]
**Action**: [retry/escalate/alternative]
```

### Partial Results

When some agents succeed and others fail:
1. Capture successful results
2. Log failures with context
3. Synthesize available results
4. Report gaps to user

### Recovery Strategies
- **Retry**: Transient failures (network, etc.)
- **Fallback**: Alternative agent types
- **Decomposition**: Split failed task into smaller pieces
- **Escalation**: Hand to main session if unrecoverable

## Configuration

### Agent Timeouts
| Agent Type | Default Timeout | Max Timeout |
|------------|----------------|-------------|
| searcher | 5 min | 15 min |
| syshelper | 3 min | 10 min |
| script_coder | 10 min | 30 min |
| watchdog | 60 min | unlimited |

### Concurrency Limits
- Default: 3 concurrent agents
- Max: 5 concurrent agents
- Override via `maxConcurrent` in spawn calls

## Dispatch Context Enrichment

Before calling `sessions_spawn`, enrich the task prompt with relevant context from existing skills. This ensures workers have the information needed to succeed.

### Context Sources

| Context | Source Skill | What to Include |
|---------|-------------|------------------|
| Main session history | `oe-memory-sync` | Parent conversation summary, user intent |
| Main tool landscape | `oe-memory-sync` | Main's TOOLS.md — available MCP servers, tool restrictions, usage guidelines |
| Git context | `oe-git-context` | Recent commits, changed files, related history |
| Project info | `oe-project-registry` | Project type, path, branch status, coding conventions |

### Enrichment Flow

```
Before sessions_spawn:
    │
    ▼
1. Load project context ──► oe-project-registry
    │                          (project path, type, branch, status)
    ▼
2. Load git context ─────► oe-git-context
    │                          (recent commits, changed files)
    ▼
3. Load memory context ───► oe-memory-sync
    │                          (parent session summary + main tools)
    ▼
4. Synthesize enriched task
    │  (include main_tools when worker needs tool awareness)
    ▼
sessions_spawn(task=<enriched_task>, ...)
```

### Enriched Task Format

```markdown
## Task
{original_task_description}

## Project Context
- Path: {project_path}
- Type: {project_type}
- Branch: {branch_name} ({clean/dirty})

## Git Context
{recent_commits_formatted}

## Main Session Context
{parent_session_summary}

## Main Tools
{main_tools_content}

## Guidance
- Work in: {project_path}
- Follow project conventions
- Refer to Main Tools for available system capabilities and restrictions
```

### Implementation Pattern

```python
async def dispatch_with_context(worker_type, task, context_hints=None):
    """Dispatch task with enriched context from skills."""
    
    context_hints = context_hints or {}
    project_path = context_hints.get("project_path", detect_project())
    
    # 1. Get project context
    project_info = get_project_info(project_path)
    project_ctx = f"""\
- Path: {project_info.path}
- Type: {project_info.type}
- Branch: {project_info.branch} ({project_info.status})
"""
    
    # 2. Get git context (selective - only relevant files)
    related_files = context_hints.get("related_files", infer_related_files(task))
    git_ctx = gather_git_context(project_path, files=related_files, depth=5)
    
    # 3. Get memory context (includes main_tools)
    memory_ctx = await sync_main_context()
    parent_summary = memory_ctx.get("parent_history_summary", "N/A")
    main_tools = memory_ctx.get("main_tools", "")
    
    # 4. Compose enriched task
    enriched_task = f"""\
## Task
{task}

## Project Context
{project_ctx}

## Git Context
{git_ctx.format_compact()}

## Main Session Context
{parent_summary}
"""
    
    # Include main tools when available
    if main_tools:
        enriched_task += f"""\
## Main Tools
{main_tools}
"""
    
    enriched_task += f"""\
## Guidance
- Work in: {project_info.path}
- Follow project conventions for {project_info.type}
- Refer to Main Tools for available system capabilities and restrictions
"""
    
    # 5. Dispatch with enriched task
    await sessions_spawn(
        agent=worker_type,
        task=enriched_task,
        label=context_hints.get("label"),
    )
```

### Context Selection Guidelines

| Worker Type | Priority Context |
|-------------|------------------|
| `oe-script_coder` | Git changes, project type, coding conventions, main tools (for tool awareness) |
| `oe-searcher` | Main session intent, topic context, main tools (for available search tools) |
| `oe-syshelper` | Project structure, file locations, main tools (for introspection tools) |
| `oe-watchdog` | Session state, timeout expectations |
| `oe-tool-recovery` | Main tools (critical — needs full tool landscape to diagnose failures) |

### What NOT to Include

- Full blame history (too verbose)
- Unrelated project memories
- Conflicting information from multiple sources
- Credentials or sensitive data

### Integration with Skills

- **`oe-memory-sync`**: Call `sync_main_context()` to get parent session summary **and main tools**
- **`oe-git-context`**: Call `gather_git_context()` with related files
- **`oe-project-registry`**: Call `get_project_info()` or `detect_project()`

## Best Practices

1. **Match agent to task**: Don't use script_coder for simple searches
2. **Set appropriate timeouts**: Balance speed vs. completion
3. **Provide full context**: Agents need background to succeed
4. **Use parallel dispatch**: For independent tasks
5. **Synthesize don't concatenate**: Add value in synthesis step
6. **Handle failures gracefully**: Partial results are better than none
7. **Monitor long tasks**: Use watchdog for tasks > 10 minutes
8. **Never wrap sessions_spawn**: Use native tool directly
9. **Enrich dispatch context**: Always inject project, git, and memory context

## Integration

### With oe-project-registry
Project metadata informs agent selection and context

### With oe-eta-estimator
ETA estimates determine timeout configuration

### With planning-with-files
Task plans guide dispatch decisions

## Example: Complete Workflow

**Scenario**: Refactor auth module

1. **Assess task**
   - Estimated toolcalls: 8
   - Requires parallel: Yes
   - Action: Plan and dispatch

2. **Plan**
   - Create task plan using planning-with-files
   - Identify subtasks: research, file discovery, implementation

3. **Dispatch parallel research** (native sessions_spawn)
   - Spawn searcher: "Research auth patterns"
   - Spawn syshelper: "Find auth files"
   - Spawn searcher: "Look up test examples"
   - Wait for all to announce results

4. **Dispatch coding** (sequential, depends on research)
   - Spawn script_coder: "Refactor auth based on research"
   - Include research results in task context

5. **Synthesize**
   - Collect all announce results
   - Apply synthesis template
   - Return final result to main


---
```

### Command 6: ✓ PASS

```bash
python -m openclaw_enhance.cli render-skill oe-toolcall-router
```

- Exit Code: 0
- Duration: 0.07s

**stdout:**
```
---
name: oe-toolcall-router
version: 2.0.0
description: MANDATORY router. Main session is a ROUTER ONLY - all execution MUST go through sessions_spawn.
user-invocable: true
allowed-tools: "Read"
metadata:
  routing_heuristics:
    max_toolcalls: 0
    escalation_threshold: 0
---

# Toolcall Router

Main session is a **router only**. It does NOT execute tasks directly.

## Iron Rule

Main session is FORBIDDEN from using these tools:
- `edit`, `write`, `exec`, `process`, `browser`, `playwright`
- `web_search`, `web_fetch` (for research tasks)

Main session is ONLY allowed to use:
- `read` (read-only file access)
- `memory_search` (search memories)
- `sessions_spawn` (delegate to subagents)
- `sessions_list`, `sessions_history`, `session_status` (monitor sessions)
- `sessions_send` (communicate with subagents)
- `agents_list` (list available agents)
- `message` (reply to user)

## Routing Decision

For ANY user request that requires file modification, command execution, research, or analysis:

1. Immediately use `sessions_spawn` with `agentId: "oe-orchestrator"`
2. Do NOT attempt to do the work yourself
3. Do NOT use `edit`/`exec`/`write` even for "simple" tasks
4. Keep routing contract in this file as source of truth; no Python wrappers around routing execution

## Escalation Command

```json
{
  "task": "<restate user request clearly>",
  "agentId": "oe-orchestrator"
}
```

## Examples

### Config change request
- User: "把 litellm 里的 vertex 模型加到 openclaw"
- Action: `sessions_spawn` to `oe-orchestrator`
- NOT: Use `edit` to modify openclaw.json yourself

### Research request
- User: "搜索东南亚 iGaming 行业现状"
- Action: `sessions_spawn` to `oe-orchestrator`
- NOT: Use `web_search` yourself

### Heavy research + PPT + traceable data (issue #9 class)
- User: "基于公开来源做深度调研并输出 PPT，所有关键结论要有可追溯数据来源（issue #9）"
- Action: `sessions_spawn` to `oe-orchestrator` with the full heavy-task scope
- Required escalation payload:

```json
{
  "task": "基于公开来源做深度调研并输出 PPT，所有关键结论要有可追溯数据来源（issue #9）",
  "agentId": "oe-orchestrator"
}
```

- NOT: Stay in main to do web research, draft PPT, or gather citations directly

### Code task
- User: "写一个 hello world"
- Action: `sessions_spawn` to `oe-orchestrator`
- NOT: Use `write`/`exec` yourself

### Simple query (stays in main)
- User: "今天天气怎么样"
- Action: Reply directly (no tools needed)

### Read-only check (stays in main)
- User: "看看 openclaw.json 里有什么模型"
- Action: Use `read` to check, then reply
```

### Command 7: ✓ PASS

```bash
python -m openclaw_enhance.cli render-hook oe-subagent-spawn-enrich
```

- Exit Code: 0
- Duration: 0.07s

**stdout:**
```
---
name: oe-subagent-spawn-enrich
version: 1.0.0
event: subagent_spawning
priority: 100
description: Enriches subagent spawn events with task metadata
---

# oe-subagent-spawn-enrich Hook

Enriches `subagent_spawning` events with enhanced metadata for tracking and deduplication.

## Event Subscription

```yaml
hooks:
  - event: subagent_spawning
    handler: oe-subagent-spawn-enrich
    priority: 100
```

## Enrichment Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Unique identifier for this task invocation |
| `project` | string | Project context from runtime state |
| `parent_session` | string | Parent session ID that initiated the spawn |
| `eta_bucket` | string | Categorized ETA: "short" (<5min), "medium" (5-30min), "long" (>30min) |
| `dedupe_key` | string | Deterministic key for duplicate detection |

## Handler Interface

```typescript
interface SpawnEnrichInput {
  event: 'subagent_spawning';
  payload: {
    subagent_type: string;
    task_description: string;
    estimated_toolcalls?: number;
    estimated_duration_minutes?: number;
  };
  context: {
    session_id: string;
    project?: string;
    parent_session?: string;
  };
}

interface SpawnEnrichOutput {
  enriched_payload: {
    task_id: string;
    project: string;
    parent_session: string;
    eta_bucket: 'short' | 'medium' | 'long';
    dedupe_key: string;
  };
}
```

## Usage Example

```typescript
import { handler } from './handler';

const result = handler({
  event: 'subagent_spawning',
  payload: {
    subagent_type: 'oe-orchestrator',
    task_description: 'Refactor auth module',
    estimated_toolcalls: 5,
  },
  context: {
    session_id: 'sess_001',
    project: 'my-project',
  },
});

// result.enriched_payload:
// {
//   task_id: 'task_abc123_xyz789',
//   project: 'my-project',
//   parent_session: 'sess_001',
//   eta_bucket: 'medium',
//   dedupe_key: 'my-project:oe-orchestrator:a1b2c3d4:20240115'
// }
```

## Integration

This hook is consumed by the `openclaw-enhance-runtime` extension via the RuntimeBridge.
```

### Command 8: ✓ PASS

```bash
python -m openclaw_enhance.cli docs-check
```

- Exit Code: 0
- Duration: 0.08s

**stdout:**
```
Docs check passed.
```

### Command 9: ✓ PASS

```bash
python -m openclaw_enhance.cli validate-feature --feature-class docs-test-only --report-slug self-surface-smoke
```

- Exit Code: 0
- Duration: 0.16s

**stdout:**
```
Running validation for docs-test-only (slug: self-surface-smoke)...
Report written to: docs/reports/2026-03-24-self-surface-smoke-docs-test-only.md
Conclusion: EXEMPT
```
