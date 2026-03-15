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
