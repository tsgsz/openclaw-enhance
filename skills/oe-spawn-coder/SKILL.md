---
name: oe-spawn-coder
version: 2.0.0
description: Spawns a coding specialist subagent for file editing, implementation, refactoring, and bug fixing. Uses test-first approach with minimal context.
user-invocable: false
skill-type: spawn
tags: [code, coding, implement, refactor, write_code, fix_bug]
allowed-tools: "Read, Edit, Write, Glob, Grep, LSP"
metadata:
  spawns_subagent: true
  subagent_role: "coding-specialist"
  contract: "sessions_spawn with prompt+model only (no agentId)"
  requires_testing: true
  model_tier_policy: "Simple=cheap, Complex=mid/premium"
---

# Spawn Coder (v2)

Spawns a coding specialist subagent for code implementation tasks.

## When to Use

Use this skill when:
- Task has tag `code` from tag router
- User requests: file creation, code implementation, refactoring, bug fixes
- Implementation requires test-first approach
- Task complexity is known (simple → cheap, complex → mid/premium)

## Model Tier Selection

| Complexity | Tier | Rationale |
|------------|------|------------|
| Simple (single file, well-defined) | cheap | Fast, cost-effective for routine tasks |
| Moderate (multi-file, requires coordination) | mid | Balanced for implementation tasks |
| Complex (novel problem, architecture changes) | premium | High capability for difficult tasks |

## spawn_recipe() Function

Generates the `sessions_spawn` call for the coder subagent:

```python
def spawn_coder(task: str, complexity: str) -> dict:
    """
    Generate sessions_spawn call for coding subagent.
    
    Args:
        task: Full task description with context
        complexity: "simple" | "moderate" | "complex"
    
    Returns:
        sessions_spawn payload with prompt + model (no agentId)
    """
    # Select model tier based on complexity
    if complexity == "simple":
        model = "gpt-4o-mini"  # cheap tier
    elif complexity == "moderate":
        model = "claude-3.5-sonnet"  # mid tier
    else:  # complex
        model = "claude-opus-4-6"  # premium tier
    
    # Build coding specialist prompt
    prompt = build_coder_prompt(task)
    
    return {
        "prompt": prompt,
        "model": model
    }


def build_coder_prompt(task: str) -> str:
    """Build coding specialist prompt with test requirements."""
    return f"""你是编程专家。请执行以下任务：

## 任务
{task}

## 要求
1. 先分析需求，制定实现计划
2. 实现代码前先写测试（测试驱动开发）
3. 最小化上下文依赖 - 明确引用所需文件路径
4. 产出结构化：先测试，后实现，再验证
5. 完成后报告：修改的文件、测试结果、验证方法

## 约束
- 不修改 AGENTS.md、TOOLS.md 等运行时配置
- 使用适当的工具完成代码编写和测试
- 保持代码简洁，符合项目规范
"""
```

## sessions_spawn Contract (v2)

**MUST USE:** `prompt` + `model` only. **NO agentId.**

```json
{
  "prompt": "<coding specialist prompt with task + requirements>",
  "model": "<tier-selected-model>"
}
```

**NOT:**
```json
{
  "task": "...",
  "agentId": "oe-orchestrator"   // ❌ v1 style - DO NOT USE
}
```

## Coding Specialist Prompt Template

```markdown
你是编程专家。请执行以下任务：

## 任务
<task_description>

## 要求
1. **先分析后实现** - 理解需求，制定计划
2. **测试驱动开发** - 先写测试，再写实现
3. **最小化上下文** - 明确指定需要的文件路径
4. **结构化产出** - 测试 → 实现 → 验证
5. **完成后报告** - 修改的文件列表、测试结果、验证方法

## 约束
- 保持代码简洁，符合项目规范
- 不修改运行时配置文件
- 使用合适的工具完成代码编写和测试
```

## Test Requirements

The coder subagent MUST:

1. **Write tests FIRST** before implementation
2. **Run tests** to verify correctness
3. **Report test results** in structured format:
   ```
   ## 测试结果
   - 单元测试: PASS/FAIL
   - 集成测试: PASS/FAIL
   - 验证方法: <具体验证步骤>
   ```

4. **Test patterns to follow:**
   - Unit tests for functions/classes
   - Integration tests for workflows
   - Edge case coverage

## Example Spawn Calls

### Simple code fix (cheap model)

```json
{
  "prompt": "修复 users.py 中的 NoneType 错误。任务：检查 login 函数中 user.name 的空值处理。",
  "model": "gpt-4o-mini"
}
```

### Moderate implementation (mid model)

```json
{
  "prompt": "实现用户认证模块。任务：创建 auth.py，包含 JWT 生成、验证、刷新功能。需要为每个函数编写单元测试。",
  "model": "claude-3.5-sonnet"
}
```

### Complex refactoring (premium model)

```json
{
  "prompt": "重构整个数据层。任务：将 SQLAlchemy 模型迁移到 Prisma，重构所有 Repository 类，保持向后兼容。先写完整的测试套件。",
  "model": "claude-opus-4-6"
}
```

## Pre-Spawn Checklist

Before calling `sessions_spawn`:

1. ✅ **Task analyzed** - Code/implementation task confirmed
2. ✅ **Complexity classified** - Simple/Moderate/Complex determined
3. ✅ **Model tier selected** - Based on complexity
4. ✅ **No agentId** - Using prompt+model contract only
5. ✅ **Test requirements included** - Prompt emphasizes test-first
6. ✅ **Minimal context** - Task description is focused and specific