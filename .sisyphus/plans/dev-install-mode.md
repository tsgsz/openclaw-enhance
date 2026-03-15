# Development Install Mode (开发安装模式)

## TL;DR

> **Quick Summary**: 添加 `--dev` 选项到 install 命令，使用符号链接代替文件复制，实现源码修改后无需重装即可生效。
> 
> **Deliverables**:
> - CLI 添加 `--dev` 选项
> - `_sync_workspaces()` 和 `sync_main_skills()` 支持 symlink 模式
> - Manifest 记录 symlink 标记
> - Uninstall 正确处理 symlink
> - 文档更新
> 
> **Estimated Effort**: Quick
> **Parallel Execution**: NO - sequential (CLI → installer → tests → docs)
> **Critical Path**: Task 1 → Task 2 → Task 3 → Task 4

---

## Context

### Original Request
用户希望添加开发安装模式，使用软链接而不是复制文件，以便实时调试。

### Interview Summary
**当前行为**:
- `openclaw-enhance install` 使用 `shutil.copytree()` 复制文件
- 源: `src/openclaw_enhance/workspaces/*`
- 目标: `~/.openclaw/openclaw-enhance/workspaces/*`
- 修改源码后需要重新安装才能生效

**期望行为**:
- `openclaw-enhance install --dev` 使用符号链接
- 修改源码后立即生效，无需重新安装
- 支持实时调试和开发迭代

### Research Findings
- 安装入口: `src/openclaw_enhance/cli.py:37`
- 核心逻辑: `src/openclaw_enhance/install/installer.py:374`
- 需要修改的函数:
  - `_sync_workspaces()` - installer.py:181 (使用 `shutil.copytree`)
  - `sync_main_skills()` - main_skill_sync.py:20 (使用 `shutil.copy2`)

---

## Work Objectives

### Core Objective
为 install 命令添加 `--dev` 选项，使用符号链接代替文件复制，实现开发模式安装。

### Concrete Deliverables
- CLI 命令支持 `--dev` 选项
- Workspaces 使用 symlink 安装
- Main skills 使用 symlink 安装
- Manifest 正确记录 symlink 状态
- Uninstall 正确处理 symlink（删除链接，不删除源文件）
- 文档更新：install.md 添加开发模式说明

### Definition of Done
- [x] `openclaw-enhance install --dev` 创建符号链接而非复制文件
- [x] 修改源码后无需重装即可生效
- [x] `openclaw-enhance uninstall` 删除链接但保留源文件
- [x] 单元测试和集成测试通过
- [x] 文档更新完成

### Must Have
- `--dev` 选项传递到 installer 核心逻辑
- `_sync_workspaces()` 支持 symlink 模式
- `sync_main_skills()` 支持 symlink 模式
- Manifest 记录 `is_symlink: bool` 字段
- Preflight 检查操作系统（Windows 上报错）
- Uninstall 识别 symlink 并正确删除

### Must NOT Have (Guardrails)
- 不修改 hooks 同步逻辑（hooks 较小，复制即可）
- 不添加 "混合模式"（部分 symlink 部分 copy）
- 不支持 Windows（文档明确说明仅支持 macOS/Linux）
- 不添加 `--dev` 到 `uninstall` 命令（通过 manifest 自动识别）
- 不使用相对路径符号链接（必须使用绝对路径）

---

## Verification Strategy

> ZERO HUMAN INTERVENTION - all verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: Tests-after
- **Framework**: pytest

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.txt`.

---

## Execution Strategy

### Parallel Execution Waves

> Sequential execution - each task depends on previous.

```
Wave 1 (CLI + Installer Core):
├── Task 1: Add --dev option to CLI [quick]
└── Task 2: Modify _sync_workspaces() and sync_main_skills() [quick]

Wave 2 (Manifest + Uninstall):
├── Task 3: Update manifest to track symlinks [quick]
└── Task 4: Update uninstall to handle symlinks [quick]

Wave 3 (Tests + Docs):
├── Task 5: Add unit tests [quick]
├── Task 6: Add integration tests [quick]
└── Task 7: Update documentation [writing]
```

### Dependency Matrix
- Task 1 blocks Task 2
- Task 2 blocks Task 3, Task 4
- Task 3, Task 4 block Task 5, Task 6
- Task 5, Task 6 block Task 7

---

## TODOs

- [x] 1. Add --dev option to CLI command

  **What to do**:
  - 在 `src/openclaw_enhance/cli.py` 的 `install` 命令添加 `--dev` 选项
  - 将 `dev_mode` 参数传递给 `install_module.install()`
  - 添加 preflight 检查：Windows 上使用 --dev 时报错

  **Must NOT do**:
  - 不添加 `--link` 别名（保持简单）
  - 不在 CLI 层做符号链接逻辑（应该在 installer 层）

  **Recommended Agent Profile**:
  - Category: `quick`
  - Skills: []

  **Parallelization**:
  - Can Run In Parallel: NO
  - Parallel Group: Wave 1
  - Blocks: Task 2
  - Blocked By: None

  **References**:
  - Pattern: `src/openclaw_enhance/cli.py:20-70` - 现有 install 命令定义
  - Pattern: `src/openclaw_enhance/cli.py:27-35` - 现有选项定义模式

  **Acceptance Criteria**:
  - [ ] `openclaw-enhance install --help` 显示 `--dev` 选项
  - [ ] `dev_mode` 参数正确传递到 `install_module.install()`

  **QA Scenarios**:
  ```
  Scenario: CLI 接受 --dev 选项
    Tool: Bash
    Steps: 运行 `python -m openclaw_enhance.cli install --help | grep -q "\-\-dev"`
    Expected: 帮助文本包含 --dev 选项
    Evidence: .sisyphus/evidence/task-1-cli-help.txt
  ```

  **Commit**: YES | Message: `feat(cli): add --dev option for development install` | Files: `src/openclaw_enhance/cli.py`

- [x] 2. Modify _sync_workspaces() and sync_main_skills() to support symlinks

  **Status**: ✅ COMPLETED
  
  **Changes made**:
  - 添加了 `dev_mode` 参数到 `_sync_workspaces()` 和 `sync_main_skills()`
  - 实现了条件逻辑：dev_mode 时创建符号链接，否则复制文件
  - 使用绝对路径创建符号链接
  - 更新了 `install()` 主函数以传递 dev_mode
  - 添加了 Windows 平台检查到 preflight_checks

  **Commit**: `feat(install): support symlink mode in workspace sync`

- [x] 3. Update manifest to track symlink status

  **What to do**:
  - 在 `src/openclaw_enhance/install/manifest.py:ComponentInstall` 添加 `is_symlink: bool = False` 字段
  - 在 `_sync_workspaces()` 和 `sync_main_skills()` 中设置 `is_symlink=True` 当使用 dev_mode
  - 确保 manifest 序列化/反序列化正确处理新字段

  **Must NOT do**:
  - 不升级 manifest schema 版本（向后兼容）

  **Recommended Agent Profile**:
  - Category: `quick`
  - Skills: []

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 2 (with Task 4)
  - Blocks: Task 5, Task 6
  - Blocked By: Task 2

  **References**:
  - Pattern: `src/openclaw_enhance/install/manifest.py:21-40` - ComponentInstall dataclass
  - Pattern: `src/openclaw_enhance/install/installer.py:205-212` - 创建 ComponentInstall 实例

  **Acceptance Criteria**:
  - [ ] `ComponentInstall` 有 `is_symlink` 字段
  - [ ] Dev mode 安装的 manifest 记录 `is_symlink=True`

  **QA Scenarios**:
  ```
  Scenario: Manifest 记录 symlink 状态
    Tool: Bash
    Steps:
      1. 执行 dev mode 安装
      2. 读取 manifest.json
      3. 验证 workspace 组件有 is_symlink=true
    Expected: Manifest 正确记录 symlink 标记
    Evidence: .sisyphus/evidence/task-3-manifest-symlink.txt
  ```

  **Commit**: YES | Message: `feat(manifest): track symlink status in ComponentInstall` | Files: `src/openclaw_enhance/install/manifest.py`, `src/openclaw_enhance/install/installer.py`

- [x] 4. Update uninstall to handle symlinks correctly

  **What to do**:
  - 修改 `src/openclaw_enhance/install/uninstaller.py` 的卸载逻辑
  - 检查 manifest 中的 `is_symlink` 字段
  - 如果是 symlink，使用 `path.unlink()` 删除链接
  - 如果不是 symlink，使用 `shutil.rmtree()` 删除目录
  - 确保不会误删源文件

  **Must NOT do**:
  - 不删除符号链接指向的源文件

  **Recommended Agent Profile**:
  - Category: `quick`
  - Skills: []

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 2 (with Task 3)
  - Blocks: Task 5, Task 6
  - Blocked By: Task 2

  **References**:
  - Pattern: `src/openclaw_enhance/install/uninstaller.py` - 卸载逻辑
  - API: `Path.is_symlink()` - 检查是否为符号链接
  - API: `Path.unlink()` - 删除符号链接

  **Acceptance Criteria**:
  - [ ] Uninstall 正确识别 symlink
  - [ ] Uninstall 删除 symlink 但不删除源文件

  **QA Scenarios**:
  ```
  Scenario: Uninstall 删除 symlink 但保留源文件
    Tool: Bash
    Steps:
      1. Dev mode 安装
      2. 记录源文件路径
      3. 执行 uninstall
      4. 验证 symlink 已删除
      5. 验证源文件仍存在
    Expected: Symlink 删除，源文件保留
    Evidence: .sisyphus/evidence/task-4-uninstall-symlink.txt
  ```

  **Commit**: YES | Message: `fix(uninstall): handle symlinks correctly` | Files: `src/openclaw_enhance/install/uninstaller.py`

- [x] 5. Add unit tests for symlink functionality

  **What to do**:
  - 在 `tests/unit/` 添加测试：
    - `test_sync_workspaces_dev_mode()` - 验证 workspace symlink 创建
    - `test_sync_main_skills_dev_mode()` - 验证 skill symlink 创建
    - `test_manifest_tracks_symlink()` - 验证 manifest 记录
  - 使用 `tmp_path` fixture 创建临时目录
  - 验证符号链接指向正确的源路径

  **Recommended Agent Profile**:
  - Category: `quick`
  - Skills: [`test-driven-development`]

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 3 (with Task 6)
  - Blocks: Task 7
  - Blocked By: Task 3, Task 4

  **References**:
  - Pattern: `tests/unit/test_agent_catalog.py` - 单元测试模式
  - Pattern: `tests/integration/test_install_uninstall.py` - 安装测试模式

  **Acceptance Criteria**:
  - [ ] `pytest tests/unit/ -k symlink` 通过

  **QA Scenarios**:
  ```
  Scenario: 单元测试通过
    Tool: Bash
    Steps: 运行 `pytest tests/unit/ -k symlink -v`
    Expected: 所有 symlink 相关测试通过
    Evidence: .sisyphus/evidence/task-5-unit-tests.txt
  ```

  **Commit**: YES | Message: `test(install): add unit tests for dev mode` | Files: `tests/unit/test_install_dev_mode.py`

- [x] 6. Add integration tests for dev mode install/uninstall

  **What to do**:
  - 在 `tests/integration/` 添加端到端测试：
    - `test_install_dev_mode_creates_symlinks()` - 完整安装流程
    - `test_uninstall_removes_symlinks_not_source()` - 卸载不删源文件
    - `test_dev_mode_changes_reflect_immediately()` - 修改源码立即生效
  - 使用真实的 openclaw_home 环境

  **Recommended Agent Profile**:
  - Category: `quick`
  - Skills: [`test-driven-development`]

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 3 (with Task 5)
  - Blocks: Task 7
  - Blocked By: Task 3, Task 4

  **References**:
  - Pattern: `tests/integration/test_install_uninstall.py` - 集成测试模式

  **Acceptance Criteria**:
  - [ ] `pytest tests/integration/test_install_dev_mode.py -v` 通过

  **QA Scenarios**:
  ```
  Scenario: 集成测试通过
    Tool: Bash
    Steps: 运行 `pytest tests/integration/test_install_dev_mode.py -v`
    Expected: 所有集成测试通过
    Evidence: .sisyphus/evidence/task-6-integration-tests.txt
  ```

  **Commit**: YES | Message: `test(install): add integration tests for dev mode` | Files: `tests/integration/test_install_dev_mode.py`

- [x] 7. Update documentation for dev mode

  **What to do**:
  - 更新 `docs/install.md` 添加开发模式说明
  - 添加使用示例：`openclaw-enhance install --dev`
  - 说明 dev 模式仅支持 macOS/Linux
  - 说明 dev 模式的优势和使用场景

  **Recommended Agent Profile**:
  - Category: `writing`
  - Skills: []

  **Parallelization**:
  - Can Run In Parallel: NO
  - Parallel Group: Wave 3
  - Blocks: None
  - Blocked By: Task 5, Task 6

  **References**:
  - Pattern: `docs/install.md` - 现有安装文档

  **Acceptance Criteria**:
  - [ ] `docs/install.md` 包含 `--dev` 选项说明
  - [ ] 文档说明平台限制（macOS/Linux only）

  **QA Scenarios**:
  ```
  Scenario: 文档包含 dev 模式说明
    Tool: Bash
    Steps: 运行 `grep -q "\-\-dev" docs/install.md`
    Expected: 文档包含 --dev 选项说明
    Evidence: .sisyphus/evidence/task-7-docs-updated.txt
  ```

  **Commit**: YES | Message: `docs(install): add development mode documentation` | Files: `docs/install.md`

---

## Final Verification Wave

- [x] F1. Functional verification - quick

  **What to do**: 手动验证完整的开发模式工作流
  
  **QA Scenarios**:
  ```
  Scenario: 完整开发模式工作流
    Tool: Bash
    Steps:
      1. 卸载现有安装: openclaw-enhance uninstall
      2. 开发模式安装: openclaw-enhance install --dev
      3. 验证 symlink: ls -la ~/.openclaw/openclaw-enhance/workspaces/
      4. 修改源文件: echo "# test" >> workspaces/oe-searcher/AGENTS.md
      5. 验证立即生效: cat ~/.openclaw/openclaw-enhance/workspaces/oe-searcher/AGENTS.md
      6. 卸载: openclaw-enhance uninstall
      7. 验证源文件保留: test -f workspaces/oe-searcher/AGENTS.md
    Expected: 所有步骤成功，源文件未被删除
    Evidence: .sisyphus/evidence/f1-dev-mode-workflow.txt
  ```

  **Pass Condition**: 开发模式安装、修改、卸载流程完整可用

---

## Commit Strategy

- Task 1: CLI 选项添加
- Task 2: Installer 核心逻辑
- Task 3: Manifest 更新
- Task 4: Uninstall 处理
- Task 5: 单元测试
- Task 6: 集成测试
- Task 7: 文档更新

---

## Success Criteria

### Verification Commands
```bash
# 安装开发模式
openclaw-enhance install --dev

# 验证 symlink
ls -la ~/.openclaw/openclaw-enhance/workspaces/ | grep -q "^l"

# 测试通过
pytest tests/unit/test_install_dev_mode.py -v
pytest tests/integration/test_install_dev_mode.py -v
```

### Final Checklist
- [x] `--dev` 选项可用
- [x] Workspaces 使用 symlink 安装
- [x] 修改源码立即生效
- [x] Uninstall 保留源文件
- [x] 所有测试通过
- [x] 文档更新完成
