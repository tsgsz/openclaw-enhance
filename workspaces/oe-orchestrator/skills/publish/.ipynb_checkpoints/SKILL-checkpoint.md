---
name: publish
description: 执行型技能（Runner）：publish
---

> 运行说明：本技能为执行型技能，按当前 Runner 架构使用。

# 文件发布工具（publish）

## 描述
用于将图片或 Markdown 发布到公网（本地反代图床）。
当用户确认发布时，文件会复制到 `~/.openclaw/img/` 或 `~/.openclaw/publish/file/`。

## 输入
- 本地文件路径（图片、Markdown、目录快照）
- 发布类型：`image|file|markdown-snapshot`
- 是否对 Markdown 做依赖重写（默认是）

## 输出
- 可访问公网 URL
- 发布位置（本地路径）
- 失败时给出可执行修复建议

## 用法

### 发布图片
```bash
cp /path/to/image.png ~/.openclaw/img/
echo "已发布: https://benboerba.tingsongguan.com/img/image.png"
```

### 发布文件/Markdown
```bash
cp /path/to/note.md ~/.openclaw/publish/file/
echo "已发布: https://benboerba.tingsongguan.com/file/note.md"
```

### 智能发布 Markdown (自动处理依赖)
自动扫描 Markdown 中的图片和文件引用，上传依赖并替换链接。
```bash
python3 ~/.openclaw/workspace/skills/publish/scripts/publish_md.py /path/to/note.md
```
输出示例：
```
处理文件: note.md
   -> 📦 已复制依赖: image.png -> img/image_a1b2c3d4.png
✅ 发布成功!
🌐 访问链接: https://benboerba.tingsongguan.com/file/note_hash.md
```

## 交互流程
1. 生成内容后，询问用户：“是否发布？”
2. 如果是普通文件 -> `cp`。
3. 如果是 Markdown 且包含本地引用 -> 推荐使用 `publish_md.py`。
4. 输出 URL 并提示预览方式。
