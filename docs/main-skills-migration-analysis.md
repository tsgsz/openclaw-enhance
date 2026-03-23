# Main Workspace Skills 迁移分析

## 需要废弃的 Skills（已有替代）

### Domain Entry Skills（被 oe-domain-router 替代）
- domain-creative → 废弃，使用 oe-specialist-creative
- domain-finance → 废弃，使用 oe-specialist-finance
- domain-km → 废弃，使用 oe-specialist-km
- domain-game-design → 废弃，使用 oe-specialist-game-design

## Main 专用 Skills（不迁移）

### 路由和控制
- oe-toolcall-router → Main 专用，强制路由行为
- oe-eta-estimator → Main 专用，任务估算
- oe-timeout-state-sync → Main 专用，超时同步

### 发布权限
- publish → Main 专用，只有 main 能对外发布

## 应该迁移到 Orchestrator 的 Skills

### 项目管理
- functonal-factory → 应该给 orchestrator（专家创建/派发）
- governance-agent-team → 应该给 orchestrator（团队协作）

### 内容处理
- social-content-producer → 应该给 orchestrator 或 specialist-creative
- script-publisher → 应该给 orchestrator（脚本发布流程）

## 全局通用 Skills（所有 agents 可用）

### 工具集成
- whisper-stt → 全局，语音转文字
- openai-whisper → 全局，语音处理
- minimax-mcp → 全局，MCP 集成
- mcporter → 全局，工具迁移

### 优化和管理
- memory-hygiene → 全局，内存清理
- context-budgeting → 全局，上下文管理
- token-saver → 全局，token 优化
- summarize → 全局，摘要生成

### 开发辅助
- find-skills → 全局，技能发现
- skillhub-preference → 全局，技能偏好
- workspace-script-guard → 全局，脚本保护
- picnan-checker → 全局，检查工具

## 建议操作

1. 废弃 4 个 domain-* skills
2. 保留 Main 专用 skills
3. 迁移 functonal-factory, governance-agent-team 到 orchestrator
4. 全局 skills 保持在 main，所有 agents 继承
