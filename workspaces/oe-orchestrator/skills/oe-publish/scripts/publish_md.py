#!/usr/bin/env python3
import argparse
import hashlib
import os
import re
import secrets
import shutil
from pathlib import Path
from typing import List, Optional

import markdown as _markdown

# 配置
PUBLISH_ROOT = Path(os.path.expanduser("~/.openclaw/publish"))
FILE_DIR = PUBLISH_ROOT / "file"
URL_BASE = "https://benboerba.tingsongguan.com/file"


MD_EXTS = {".md", ".markdown"}


def rand_id(nbytes: int = 6) -> str:
    return secrets.token_hex(nbytes)


def _rewrite_md_links_to_html(text: str) -> str:
    def repl(match):
        label = match.group(1)
        link = match.group(2)

        if link.startswith(("http:", "https:", "//", "mailto:", "#")):
            return match.group(0)

        if link.lower().endswith(".md"):
            link = link[:-3] + ".html"
        elif link.lower().endswith(".markdown"):
            link = link[: -len(".markdown")] + ".html"

        return f"[{label}]({link})"

    # Only non-image links.
    return re.sub(r"(?<!!)\[(.*?)\]\((.*?)\)", repl, text)


def _wrap_html(title: str, body_html: str) -> str:
    css = """
    :root { color-scheme: light; }
    body { margin: 0; padding: 32px 20px; font: 16px/1.55 ui-serif, Georgia, serif;
           color: #111; background: #fff; }
    main { max-width: 900px; margin: 0 auto; }
    pre, code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    pre { padding: 12px 14px; background: #f6f6f6; border-radius: 10px; overflow: auto; }
    code { background: #f6f6f6; padding: 0 0.25em; border-radius: 6px; }
    pre code { background: transparent; padding: 0; }
    a { color: #0b5fff; text-decoration: none; }
    a:hover { text-decoration: underline; }
    img { max-width: 100%; height: auto; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; }
    th { background: #f3f3f3; text-align: left; }
    """.strip()

    return (
        "<!doctype html>\n"
        '<html lang="zh">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>{title}</title>\n"
        f"  <style>{css}</style>\n"
        "</head>\n"
        "<body>\n"
        "  <main>\n"
        f"  {body_html}\n"
        "  </main>\n"
        "</body>\n"
        "</html>\n"
    )


def render_markdown_file(md_path: Path) -> Path:
    md_path = Path(md_path)
    text = md_path.read_text(encoding="utf-8", errors="replace")
    text = _rewrite_md_links_to_html(text)

    body = _markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "toc"],
        output_format="html",
    )
    html = _wrap_html(md_path.name, body)
    html_path = md_path.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    return html_path


def render_markdown_tree(root: Path) -> List[Path]:
    root = Path(root)
    out = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in MD_EXTS:
            continue
        out.append(render_markdown_file(p))
    return out


def pick_entry_html(root: Path) -> Optional[Path]:
    root = Path(root)
    prefer = ["README.html", "index.html", "home.html"]
    for name in prefer:
        p = root / name
        if p.exists() and p.is_file():
            return p
    for p in root.rglob("*.html"):
        if p.is_file():
            return p
    return None


class SnapshotPublisher:
    def __init__(
        self,
        source_path,
        publish_id: str = "",
        base_dir: Path = FILE_DIR,
        url_base: str = URL_BASE,
    ):
        self.source_path = Path(source_path).resolve()
        self.rand = publish_id or rand_id()
        self.target_root = Path(base_dir) / self.rand
        self.external_dir = self.target_root / "_assets"
        self.url_base = url_base.rstrip("/")

    def publish(self, render_html: bool = True):
        if not self.source_path.exists():
            return None

        # 1. 如果是文件，当作单文件目录处理
        if self.source_path.is_file():
            self.target_root.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.source_path, self.target_root)
            copied = self.target_root / self.source_path.name
            if copied.suffix.lower() in MD_EXTS:
                self.process_file(copied)
                if render_html:
                    html = render_markdown_file(copied)
                    return f"{self.url_base}/{self.rand}/{html.name}"
                return f"{self.url_base}/{self.rand}/{copied.name}"

            return f"{self.url_base}/{self.rand}/{self.source_path.name}"

        # 2. 如果是目录，完整拷贝
        target_dir = self.target_root / self.source_path.name
        shutil.copytree(self.source_path, target_dir)
        self.external_dir.mkdir(exist_ok=True)

        # 3. 遍历处理所有 Markdown
        entry_points = []
        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.lower().endswith((".md", ".markdown")):
                    full_path = Path(root) / file
                    self.process_file(full_path)

                    if render_html:
                        render_markdown_file(full_path)

                    # 记录相对路径作为入口
                    rel_path = full_path.relative_to(target_dir)
                    if file.lower() in ["readme.md", "index.md", "home.md"]:
                        entry_points.insert(0, rel_path)  # 优先
                    else:
                        entry_points.append(rel_path)

        # 返回入口 URL
        main_entry = entry_points[0] if entry_points else ""

        if not main_entry:
            return f"{self.url_base}/{self.rand}/{self.source_path.name}/"

        if render_html:
            main_entry = str(main_entry)
            if main_entry.lower().endswith(".md"):
                main_entry = main_entry[:-3] + ".html"
            elif main_entry.lower().endswith(".markdown"):
                main_entry = main_entry[: -len(".markdown")] + ".html"

        return f"{self.url_base}/{self.rand}/{self.source_path.name}/{main_entry}"

    def process_file(self, md_path):
        """处理单个文件中的外部引用"""
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        def replace_link(match):
            full_match = match.group(0)
            text = match.group(1)
            link = match.group(2)

            # 跳过网络链接和锚点
            if link.startswith(("http:", "https:", "//", "mailto:", "#")):
                return full_match

            # 尝试解析路径
            try:
                # 链接相对于当前 md 文件的位置
                link_path = (md_path.parent / link).resolve()
            except Exception:
                return full_match

            # 检查链接是否指向快照目录外部
            # (注意：md_path 已经在 target_root 里了，所以 link_path 是基于 target_root 解析的)
            # 但原始链接是指向源文件的外部。我们需要判断这个文件是否被包含在 copytree 里了。

            # 简单判断：如果文件存在于 target_root 内，则不需要改链接（相对路径保持有效）
            if self.is_subpath(link_path, self.target_root):
                return full_match

            # 如果文件不存在（说明原链接指向了源目录外部，copytree 没带过来）
            # 我们需要去源目录找它
            # 计算原始文件的真实路径
            # 1. 计算 md 在 target 中的相对路径
            rel_to_root = md_path.relative_to(self.target_root)
            # 2. 映射回 source 中的绝对路径
            if self.source_path.is_file():
                original_md_path = self.source_path
            else:
                original_md_path = self.source_path / rel_to_root

            try:
                original_target = (original_md_path.parent / link).resolve()
            except Exception:
                return full_match

            if original_target.exists():
                # 这是一个外部依赖，搬运到 _assets
                asset_name = (
                    f"{original_target.stem}_"
                    f"{self.get_hash(original_target)}"
                    f"{original_target.suffix}"
                )
                dest_path = self.external_dir / asset_name

                if not dest_path.exists():
                    shutil.copy2(original_target, dest_path)
                    # print(f"   -> 搬运外部资源: {original_target.name}")

                # 计算新链接：从当前 md 到 _assets/xxx 的相对路径
                # 比如 md 在 root/sub/a.md, assets 在 root/_assets/
                # 路径应该是 ../_assets/xxx
                rel_link = os.path.relpath(dest_path, md_path.parent)

                prefix = "!" if full_match.startswith("!") else ""
                return f"{prefix}[{text}]({rel_link})"

            return full_match

        # 替换
        content = re.sub(r"!\[(.*?)\]\((.*?)\)", replace_link, content)
        content = re.sub(r"(?<!!)\[(.*?)\]\((.*?)\)", replace_link, content)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)

    def is_subpath(self, path, parent):
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    def get_hash(self, path):
        hasher = hashlib.md5()
        with open(path, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()[:8]


def main():
    ap = argparse.ArgumentParser(description="Publish markdown/file/dir snapshots")
    ap.add_argument("paths", nargs="+", help="path(s) to publish")
    ap.add_argument("--no-render-html", action="store_true")
    args = ap.parse_args()

    for p in args.paths:
        target = Path(p)
        if not target.exists():
            continue

        publisher = SnapshotPublisher(target)
        url = publisher.publish(render_html=not args.no_render_html)
        if url:
            print(f"✅ 发布成功: {target.name}")
            print(f"🌐 {url}")


if __name__ == "__main__":
    main()
