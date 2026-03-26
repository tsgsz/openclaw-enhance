---
name: oe-script-publisher
version: 1.0.0
description: "把脚本以软链接发布到 ~/.openclaw/workspace/scripts/<group>/ 并维护 README（不复制/不搬运脚本实现）"
---

# Script Publisher（脚本发布技能）

目标：把“任意位置的脚本”发布为 OpenClaw 可长期维护的系统入口脚本，并满足：

- 发布产物是软链接入口：`~/.openclaw/workspace/scripts/<group>/<name>` -> `<real_script_path>`
- 脚本真实实现保留在原位置（通常是项目目录），不复制、不移动
- 每个 group 目录用一个 `README.md` 管理（自动更新“脚本清单”区块；可选维护每个脚本的用途/用法段落）
- `~/.openclaw/workspace/scripts/` 顶层不放脚本文件（只放 README + 分组目录）

## 分组约定（group）

- `governance`：会话治理、重启治理、anti-stuck、subagent SLA
- `services`：本地服务与桥接（litellm/local-embed/minimax bridge）
- `tunnels`：autossh 隧道与发布服务
- `tools`：小工具

## 使用方式

发布一个已有脚本（创建软链接入口；更新 group README 清单）：

```bash
bash ~/.openclaw/workspace/skills/script-publisher/scripts/publish_script.sh /path/to/foo.sh
```

指定 group（推荐用于新脚本首次发布）：

```bash
bash ~/.openclaw/workspace/skills/script-publisher/scripts/publish_script.sh /path/to/foo.py --group governance
```

指定入口名（默认取源文件 basename）：

```bash
bash ~/.openclaw/workspace/skills/script-publisher/scripts/publish_script.sh /path/to/foo.sh --group tools --name my_tool
```

更新 README 清单（不发布脚本）：

```bash
bash ~/.openclaw/workspace/skills/script-publisher/scripts/publish_script.sh --sync-readme governance
```

可选：为脚本在 group README 中写入用途/用法段落（传入一段 markdown）：

```bash
bash ~/.openclaw/workspace/skills/script-publisher/scripts/publish_script.sh \
  /path/to/foo.sh --group tools \
  --doc /path/to/foo.README.snippet.md
```

## 验收清单

- [ ] `~/.openclaw/workspace/scripts/<group>/<name>` 是软链接（指向真实脚本实现）
- [ ] 对应 group 的 `README.md` 中脚本清单已更新
