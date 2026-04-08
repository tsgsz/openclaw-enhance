---
name: oe-publish
version: 2.0.0
description: Publishing skill for files, images, markdown, and directories to public URLs. Uses publish_gateway.py for automatic routing.
user-invocable: true
skill-type: utility
tags: [publish, deployment, public-url, images, markdown]
allowed-tools: "Read, message"
metadata:
  architecture_version: "2.0"
  requires_gateway: true
---

# oe-publish (v2)

Publish files to public URLs using the centralized publish gateway.

## Iron Rule

**MUST use `publish_gateway.py`** - Never manually execute `cp` commands or other publishing methods. The gateway automatically routes based on file type.

## File Type Routing

| File Type | Extension | Publish Path | Public URL |
|-----------|-----------|--------------|------------|
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`, `.ico` | `~/.openclaw/publish/img/<rand>/` | `https://benboerba.tingsongguan.com/img/<rand>/...` |
| Files/Web | `.html`, `.js`, `.css`, `.pdf`, `.zip`, `.json`, `.txt`, `.mp3`, `.mp4` | `~/.openclaw/publish/file/<rand>/` | `https://benboerba.tingsongguan.com/file/<rand>/...` |
| Markdown | `.md`, `.markdown` | Generates HTML | Returns HTML URL (preserves md + resources) |
| Directories | `<dir>` | Snapshots to `file/<rand>/<dir>/` | Batch renders Markdown to HTML |

## Input Parameters

1. **source**: File path or directory path to publish.
2. **--sub-dir** (optional): Subdirectory name under the category (random directory still created).

## Usage

### Publish single image
```bash
python3 ~/.openclaw/workspace/skills/publish/scripts/publish_gateway.py /path/to/icon.png
```

### Publish entire frontend game directory
```bash
python3 ~/.openclaw/workspace/skills/publish/scripts/publish_gateway.py /path/to/game-dir --sub-dir my-game
```

### Output format
```json
{
  "status": "success",
  "category": "file",
  "local_path": "/Users/tsgsz/.openclaw/publish/file/my-game/game-dir",
  "url": "https://benboerba.tingsongguan.com/file/my-game/game-dir/"
}
```

## Constraints

- **FORBIDDEN**: Use of any third-party external hosting (Gist, Pastebin, imgur, etc.)
- **MANDATORY**: After successful publish, clearly feedback the public URL to user
- **MANDATORY**: Use `publish_gateway.py` only - no manual `cp`, `scp`, or curl uploads

## Workflow

1. Validate file/directory exists
2. Execute `publish_gateway.py` with appropriate parameters
3. Parse JSON output for status and URL
4. If success: reply with public URL
5. If failure: report error message
