---
name: oe-publish
version: 1.0.0
description: 执行型技能（Runner）：oe-publish
tags: [publish, deployment, public-url, images, markdown]
---

> 运行说明：本技能为执行型技能，按当前 Runner 架构使用。

# 统一发布网关（publish）

## 描述
用于将图片、Markdown、前端网页或目录快照发布到公网。
**强制规则：严禁手动执行 `cp` 命令发布，必须调用 `publish_gateway.py` 脚本，它会自动根据文件类型分流路径并返回正确的 URL。**

## 核心工具
使用 `publish_gateway.py` 进行发布。
- **图片类** (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`, `.ico`): 发布到 `~/.openclaw/publish/img/<rand>/` $\rightarrow$ `https://benboerba.tingsongguan.com/img/<rand>/...`
- **文件与网页类** (`.html`, `.js`, `.css`, `.pdf`, `.zip`, `.json`, `.txt`, `.mp3`, `.mp4`): 发布到 `~/.openclaw/publish/file/<rand>/` $\rightarrow$ `https://benboerba.tingsongguan.com/file/<rand>/...`
- **Markdown 类** (`.md`, `.markdown`): 会生成 HTML 并返回 HTML 的 URL（同时保留原 md 文件与依赖资源）
- **目录**: 快照发布到 `file/<rand>/<dir>/`，并对目录内 Markdown 批量渲染 HTML

## 输入参数
1.  **source**: 要发布的文件路径或目录路径。
2.  **--sub-dir**: (可选) 发布到的子目录名（仍会在其下创建随机目录）。

## 运行示例

### 发布单张图片
```bash
python3 ~/.openclaw/workspace/skills/publish/scripts/publish_gateway.py /path/to/icon.png
```

### 发布整个前端游戏目录
```bash
python3 ~/.openclaw/workspace/skills/publish/scripts/publish_gateway.py /path/to/game-dir --sub-dir my-game
```
输出示例：
```json
{
  "status": "success",
  "category": "file",
  "local_path": "/Users/tsgsz/.openclaw/publish/file/my-game/game-dir",
  "url": "https://benboerba.tingsongguan.com/file/my-game/game-dir/"
}
```

## 约束
- 严禁使用任何第三方外部托管（如 Gist, Pastebin）。
- 发布成功后，必须向用户清晰反馈公网 URL。
