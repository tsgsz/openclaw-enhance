#!/usr/bin/env python3
import argparse
import json
import secrets
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from publish_md import SnapshotPublisher  # noqa: E402

# 配置映射
CONFIG = {
    "img": {
        "exts": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"},
        "local_dir": "~/.openclaw/publish/img/",
        "url_base": "https://benboerba.tingsongguan.com/img/",
    },
    "file": {
        "exts": {
            ".html",
            ".js",
            ".css",
            ".pdf",
            ".zip",
            ".json",
            ".txt",
            ".mp3",
            ".mp4",
        },
        "local_dir": "~/.openclaw/publish/file/",
        "url_base": "https://benboerba.tingsongguan.com/file/",
    },
}


MD_EXTS = {".md", ".markdown"}


def rand_id(nbytes: int = 6) -> str:
    return secrets.token_hex(nbytes)


def publish(source_path: str, sub_dir: str = "") -> dict:
    src = Path(source_path).expanduser()
    if not src.exists():
        return {"status": "error", "message": f"Source not found: {source_path}"}

    ext = src.suffix.lower()

    file_base = Path(CONFIG["file"]["local_dir"]).expanduser()
    img_base = Path(CONFIG["img"]["local_dir"]).expanduser()
    file_url_base = CONFIG["file"]["url_base"].rstrip("/")
    img_url_base = CONFIG["img"]["url_base"].rstrip("/")

    file_base = file_base / sub_dir if sub_dir else file_base
    img_base = img_base / sub_dir if sub_dir else img_base
    file_url_base = file_url_base + (f"/{sub_dir}" if sub_dir else "")
    img_url_base = img_url_base + (f"/{sub_dir}" if sub_dir else "")

    # Markdown file: snapshot + external assets + render html
    if src.is_file() and ext in MD_EXTS:
        rid = rand_id()
        pub = SnapshotPublisher(
            str(src), publish_id=rid, base_dir=file_base, url_base=file_url_base
        )
        url = pub.publish(render_html=True)
        if not url:
            return {"status": "error", "message": "publish markdown failed"}
        return {
            "status": "success",
            "category": "markdown",
            "local_path": str(pub.target_root),
            "url": url,
        }

    # Directory: snapshot + render html
    if src.is_dir():
        rid = rand_id()
        pub = SnapshotPublisher(
            str(src), publish_id=rid, base_dir=file_base, url_base=file_url_base
        )
        url = pub.publish(render_html=True)
        if not url:
            return {"status": "error", "message": "publish directory failed"}
        return {
            "status": "success",
            "category": "file",
            "local_path": str(pub.target_root),
            "url": url,
        }

    rid = rand_id()

    category = "file"
    if src.is_file() and ext in CONFIG["img"]["exts"]:
        category = "img"

    if category == "img":
        target_dir = img_base / rid
        url_prefix = img_url_base + f"/{rid}/"
    else:
        target_dir = file_base / rid
        url_prefix = file_url_base + f"/{rid}/"

    target_dir.mkdir(parents=True, exist_ok=True)

    # 执行发布
    # 单文件(非 markdown)
    target_path = target_dir / src.name
    shutil.copy2(src, target_path)
    final_url = url_prefix + src.name

    return {
        "status": "success",
        "category": category,
        "local_path": str(target_path),
        "url": final_url,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenClaw 统一发布网关")
    parser.add_argument("source", help="要发布的文件或目录路径")
    parser.add_argument("--sub-dir", help="可选子目录名称", default="")
    args = parser.parse_args()

    result = publish(args.source, args.sub_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "error":
        sys.exit(1)
