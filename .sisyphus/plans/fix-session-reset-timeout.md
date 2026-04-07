# Fix Session Reset Timeout

## TL;DR

> **Quick Summary**: 修改 OpenClaw session 空闲超时配置，从 10 分钟延长到 120 分钟（2小时），解决飞书对话频繁丢失上下文的问题。
> 
> **Deliverables**: 
> - 修改 `~/.openclaw/openclaw.json` 配置
> - 重启 OpenClaw gateway 服务
> - 验证配置生效
> 
> **Estimated Effort**: Quick
> **Parallel Execution**: NO - sequential
> **Critical Path**: 修改配置 → 重启服务 → 验证

---

## Context

### 问题描述
用户在飞书对话中连续遇到上下文丢失问题，Agent 反复询问用户已经说过的信息。

### 根本原因（已确认）
经过深度调查，找到确凿证据：

1. **配置文件证据**: `~/.openclaw/openclaw.json` 第 825 行设置 `idleMinutes: 10`
2. **源代码证据**: OpenClaw 核心代码 `auth-profiles-B5ypC5S-.js` 中的 `archiveFileOnDisk()` 函数创建 `.reset` 文件
3. **实际数据证据**: 4 次 reset 都发生在空闲超过 10 分钟后（46-47 分钟，因为清理任务每小时运行）

### 触发机制
```
空闲 10 分钟 → 标记为可 reset → 等待清理任务（每小时） → 执行 reset → 上下文丢失
```

---

## Work Objectives

### Core Objective
将 session 空闲超时从 10 分钟延长到 120 分钟（2小时），避免飞书异步对话场景下的频繁 reset。

### Concrete Deliverables
- `~/.openclaw/openclaw.json` 中 `session.reset.idleMinutes` 从 10 改为 120
- OpenClaw gateway 服务重启完成
- 配置生效验证通过

### Definition of Done
- [ ] 配置文件已修改：`idleMinutes: 120`
- [ ] Gateway 服务已重启
- [ ] Gateway 日志显示新配置已加载
- [ ] 备份原配置文件

### Must Have
- 修改前备份原配置
- 重启服务使配置生效
- 验证配置已加载

### Must NOT Have (Guardrails)
- 不修改其他配置项
- 不删除或破坏配置文件
- 不影响其他 OpenClaw 功能

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (OpenClaw 已安装)
- **Automated tests**: None（配置修改无需测试）
- **Framework**: N/A

### QA Policy
每个任务包含 agent-executed QA scenarios。证据保存到 `.sisyphus/evidence/`。

---

## Execution Strategy

### Sequential Execution (3 tasks)

```
Task 1: 备份并修改配置
  ↓
Task 2: 重启 gateway 服务
  ↓
Task 3: 验证配置生效
```

---

## TODOs

- [ ] 1. 备份并修改 OpenClaw 配置

  **What to do**:
  - 备份当前配置：`cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak.session-timeout`
  - 修改 `~/.openclaw/openclaw.json` 第 825 行
  - 将 `"idleMinutes": 10` 改为 `"idleMinutes": 120`
  - 验证 JSON 格式正确（使用 `jq` 验证）

  **Must NOT do**:
  - 不修改其他配置项
  - 不破坏 JSON 格式

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 2
  - **Blocked By**: None

  **References**:
  - `~/.openclaw/openclaw.json:822-833` - Session 配置段落
  - 调查报告：空闲超时设置为 10 分钟导致频繁 reset

  **Acceptance Criteria**:
  - [ ] 备份文件已创建：`~/.openclaw/openclaw.json.bak.session-timeout`
  - [ ] 配置已修改：`jq '.session.reset.idleMinutes' ~/.openclaw/openclaw.json` 返回 `120`
  - [ ] JSON 格式正确：`jq . ~/.openclaw/openclaw.json > /dev/null` 无错误

  **QA Scenarios**:
  ```
  Scenario: 验证配置修改成功
    Tool: Bash
    Preconditions: 配置文件已修改
    Steps:
      1. 运行：jq '.session.reset.idleMinutes' ~/.openclaw/openclaw.json
      2. 验证输出为：120
      3. 运行：jq . ~/.openclaw/openclaw.json > /dev/null
      4. 验证退出码为 0（JSON 格式正确）
    Expected Result: idleMinutes 值为 120，JSON 格式无错误
    Failure Indicators: 值不是 120，或 jq 报错
    Evidence: .sisyphus/evidence/task-1-config-modified.txt
  ```

  **Evidence to Capture**:
  - [ ] 配置修改前后对比
  - [ ] jq 验证输出

  **Commit**: YES
  - Message: `fix: increase session idle timeout from 10min to 120min`
  - Files: `~/.openclaw/openclaw.json`
  - Pre-commit: `jq . ~/.openclaw/openclaw.json > /dev/null`

---

- [ ] 2. 重启 OpenClaw Gateway 服务

  **What to do**:
  - 停止 gateway：`launchctl stop ai.openclaw.gateway`
  - 等待 3 秒确保完全停止
  - 启动 gateway：`launchctl start ai.openclaw.gateway`
  - 等待 5 秒让服务启动
  - 验证服务运行：`launchctl list | grep ai.openclaw.gateway`

  **Must NOT do**:
  - 不使用 `kill -9` 强制杀进程
  - 不重启其他 OpenClaw 服务

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 3
  - **Blocked By**: Task 1

  **References**:
  - `~/Library/LaunchAgents/ai.openclaw.gateway.plist` - Gateway 服务配置

  **Acceptance Criteria**:
  - [ ] Gateway 服务已停止：`launchctl list | grep ai.openclaw.gateway` 显示状态变化
  - [ ] Gateway 服务已启动：进程存在且运行中
  - [ ] 日志文件有新内容：`~/.openclaw/logs/gateway.log` 有启动日志

  **QA Scenarios**:
  ```
  Scenario: 验证 gateway 重启成功
    Tool: Bash
    Preconditions: 配置已修改
    Steps:
      1. 运行：launchctl stop ai.openclaw.gateway
      2. 等待 3 秒
      3. 运行：launchctl start ai.openclaw.gateway
      4. 等待 5 秒
      5. 运行：launchctl list | grep ai.openclaw.gateway
      6. 验证输出包含进程 PID（非 "-"）
      7. 运行：tail -20 ~/.openclaw/logs/gateway.log
      8. 验证包含最近的启动日志
    Expected Result: Gateway 进程运行中，日志显示启动成功
    Failure Indicators: 进程不存在，或日志无新内容
    Evidence: .sisyphus/evidence/task-2-gateway-restarted.txt
  ```

  **Evidence to Capture**:
  - [ ] launchctl list 输出
  - [ ] Gateway 启动日志

  **Commit**: NO

---

- [ ] 3. 验证配置生效

  **What to do**:
  - 检查 gateway 日志中是否加载了新配置
  - 搜索日志：`grep -i "session.*idle\|idleMinutes" ~/.openclaw/logs/gateway.log | tail -10`
  - 验证配置值：`jq '.session.reset.idleMinutes' ~/.openclaw/openclaw.json`
  - 输出验证报告

  **Must NOT do**:
  - 不修改日志文件

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None
  - **Blocked By**: Task 2

  **References**:
  - `~/.openclaw/logs/gateway.log` - Gateway 运行日志

  **Acceptance Criteria**:
  - [ ] 配置文件显示：`idleMinutes: 120`
  - [ ] Gateway 日志显示服务已重启
  - [ ] 无错误日志

  **QA Scenarios**:
  ```
  Scenario: 验证新配置已加载
    Tool: Bash
    Preconditions: Gateway 已重启
    Steps:
      1. 运行：jq '.session.reset.idleMinutes' ~/.openclaw/openclaw.json
      2. 验证输出：120
      3. 运行：tail -50 ~/.openclaw/logs/gateway.log | grep -i "error\|fail"
      4. 验证无致命错误
      5. 运行：launchctl list | grep ai.openclaw.gateway
      6. 验证进程运行中
    Expected Result: 配置为 120，无错误，服务运行正常
    Failure Indicators: 配置不是 120，或有错误日志，或服务未运行
    Evidence: .sisyphus/evidence/task-3-config-verified.txt
  ```

  **Evidence to Capture**:
  - [ ] 配置验证输出
  - [ ] Gateway 状态
  - [ ] 日志检查结果

  **Commit**: NO

---

## Success Criteria

### Verification Commands
```bash
# 验证配置
jq '.session.reset.idleMinutes' ~/.openclaw/openclaw.json
# Expected: 120

# 验证服务运行
launchctl list | grep ai.openclaw.gateway
# Expected: 进程 PID 存在

# 验证无错误
tail -50 ~/.openclaw/logs/gateway.log | grep -i error
# Expected: 无致命错误
```

### Final Checklist
- [ ] 配置已修改：`idleMinutes: 120`
- [ ] 备份文件已创建
- [ ] Gateway 服务运行正常
- [ ] 无错误日志

---

## 后续观察

修改完成后，建议观察：

1. **短期验证（1小时内）**：
   - 在飞书发送消息
   - 等待 15-20 分钟
   - 再次发送消息
   - 验证 Agent 是否保留上下文

2. **中期验证（24小时内）**：
   - 检查是否还有 `.reset` 文件生成
   - 查看 `~/.openclaw/agents/main/sessions/` 目录

3. **长期监控**：
   - 观察内存使用是否增加
   - 如果内存压力大，可以调整为 60 分钟

---

## 回滚方案

如果出现问题，立即回滚：

```bash
# 恢复原配置
cp ~/.openclaw/openclaw.json.bak.session-timeout ~/.openclaw/openclaw.json

# 重启服务
launchctl stop ai.openclaw.gateway
launchctl start ai.openclaw.gateway
```
