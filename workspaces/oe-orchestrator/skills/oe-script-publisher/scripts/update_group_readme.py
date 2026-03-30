#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BEGIN = "<!-- SCRIPTS:BEGIN -->"
END = "<!-- SCRIPTS:END -->"


def _entry_begin(name: str) -> str:
    return f"<!-- ENTRY:BEGIN {name} -->"


def _entry_end(name: str) -> str:
    return f"<!-- ENTRY:END {name} -->"


def build_list(group_dir: Path) -> str:
    items = []
    for p in sorted(group_dir.iterdir()):
        if not p.is_file():
            continue
        if p.name == "README.md":
            continue
        if p.name.startswith("."):
            continue
        items.append(p.name)

    if not items:
        return "(本目录暂无可执行脚本)\n"

    return "\n".join([f"- `{name}`" for name in items]) + "\n"


def ensure_block(text: str, listing: str) -> str:
    if BEGIN in text and END in text:
        pre, rest = text.split(BEGIN, 1)
        _, post = rest.split(END, 1)
        return pre + BEGIN + "\n" + listing + END + post

    # If no markers, append a managed section.
    tail = "\n\n## 本组脚本清单（自动维护）\n" + BEGIN + "\n" + listing + END + "\n"
    return text.rstrip() + tail


def ensure_entry_doc(text: str, entry_name: str, entry_doc: str) -> str:
    entry_doc = entry_doc.strip("\n") + "\n"

    begin = _entry_begin(entry_name)
    end = _entry_end(entry_name)
    heading = f"## {entry_name}"

    if heading not in text:
        block = "\n\n" + heading + "\n" + begin + "\n" + entry_doc + end + "\n"
        return text.rstrip() + block

    lines = text.splitlines(True)
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            header_idx = i
            break

    if header_idx is None:
        # Fallback: append if an odd formatting prevented detection.
        block = "\n\n" + heading + "\n" + begin + "\n" + entry_doc + end + "\n"
        return text.rstrip() + block

    # Find section end: next H2 heading or EOF.
    sec_start = header_idx + 1
    sec_end = len(lines)
    for j in range(sec_start, len(lines)):
        if lines[j].startswith("## "):
            sec_end = j
            break

    section = "".join(lines[sec_start:sec_end])
    if begin in section and end in section:
        pre, rest = section.split(begin, 1)
        _, post = rest.split(end, 1)
        new_section = pre + begin + "\n" + entry_doc + end + post
    else:
        # Insert managed block at the end of this section.
        if section and not section.endswith("\n"):
            section += "\n"
        new_section = (
            section.rstrip("\n") + "\n" + begin + "\n" + entry_doc + end + "\n"
        )

    out_lines = lines[:sec_start] + [new_section] + lines[sec_end:]
    return "".join(out_lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="update_group_readme.py",
        description="Update group README script listing and optional per-script docs.",
    )
    parser.add_argument("group_dir", nargs="?")
    parser.add_argument("readme_path", nargs="?")
    parser.add_argument("--update-entry", dest="entry_name", default="")
    parser.add_argument("--entry-md", dest="entry_md", default="")

    ns = parser.parse_args()
    if not ns.group_dir or not ns.readme_path:
        parser.print_help(sys.stderr)
        return 2

    group_dir = Path(ns.group_dir).expanduser().resolve()
    readme = Path(ns.readme_path).expanduser().resolve()

    if not group_dir.exists() or not group_dir.is_dir():
        print(f"Error: group_dir not found: {group_dir}", file=sys.stderr)
        return 2

    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="replace")
    else:
        text = ""

    listing = build_list(group_dir)
    out = ensure_block(text, listing)

    if ns.entry_name:
        if not ns.entry_md:
            print("Error: --entry-md is required with --update-entry", file=sys.stderr)
            return 2
        entry_md = Path(ns.entry_md).expanduser().resolve()
        if not entry_md.exists() or not entry_md.is_file():
            print(f"Error: entry snippet not found: {entry_md}", file=sys.stderr)
            return 2
        entry_doc = entry_md.read_text(encoding="utf-8", errors="replace")
        out = ensure_entry_doc(out, ns.entry_name, entry_doc)

    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text(out, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
