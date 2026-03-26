#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
用法:
  publish_script.sh <real_script_path> [--group <governance|services|tunnels|tools>] [--name <entry_name>] [--doc <snippet_md>] [--no-readme]
  publish_script.sh --sync-readme <governance|services|tunnels|tools>

说明:
  - 发布产物是软链接入口: ~/.openclaw/workspace/scripts/<group>/<name> -> <real_script_path>
  - 真实脚本实现保留在原位置(不 copy/move)
  - 默认: group=tools, 会更新 group README 的脚本清单
  - --doc 可选: 传入一段 markdown, 写入/覆盖 group README 中同名脚本段落
USAGE
}

OPENCLAW_HOME="$HOME/.openclaw"
WS_SCRIPTS="$OPENCLAW_HOME/workspace/scripts"
SKILL_DIR="$OPENCLAW_HOME/workspace/skills/script-publisher"
UPDATER="$SKILL_DIR/scripts/update_group_readme.py"

sync_readme_only=false
if [[ "${1:-}" == "--sync-readme" ]]; then
  sync_readme_only=true
  group="${2:-}"
  if [[ -z "$group" ]]; then
    usage
    exit 2
  fi
  case "$group" in
    governance|services|tunnels|tools) ;;
    *)
      echo "Error: invalid group: $group" >&2
      exit 2
      ;;
  esac
  python3 "$UPDATER" "$WS_SCRIPTS/$group" "$WS_SCRIPTS/$group/README.md"
  echo "OK: synced README: $WS_SCRIPTS/$group/README.md"
  exit 0
fi

src="${1:-}"
shift || true

if [[ -z "$src" ]]; then
  usage
  exit 2
fi

group="tools"
dest_name=""
do_readme=true
doc_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --group)
      group="${2:-tools}"
      shift 2
      ;;
    --name)
      dest_name="${2:-}"
      shift 2
      ;;
    --doc)
      doc_path="${2:-}"
      shift 2
      ;;
    --no-readme)
      do_readme=false
      shift
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ ! -f "$src" ]]; then
  echo "Error: file not found: $src" >&2
  exit 2
fi

base=$(basename "$src")
if [[ -n "$dest_name" ]]; then
  if [[ "$dest_name" == */* ]]; then
    echo "Error: --name must be a filename, not a path" >&2
    exit 2
  fi
  base="$dest_name"
fi

case "$group" in
  governance|services|tunnels|tools) ;;
  *)
    echo "Error: invalid --group: $group" >&2
    exit 2
    ;;
esac

dst_dir="$WS_SCRIPTS/$group"
dst="$dst_dir/$base"

mkdir -p "$dst_dir"

src_abs=$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$src")
dst_abs=$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$dst")

if [[ -e "$dst" || -L "$dst" ]]; then
  if [[ -d "$dst" && ! -L "$dst" ]]; then
    echo "Error: destination is a directory: $dst" >&2
    exit 3
  fi
  rm -f "$dst"
fi

ln -s "$src_abs" "$dst"

if [[ "$do_readme" == "true" ]]; then
  python3 "$UPDATER" "$dst_dir" "$dst_dir/README.md"

  if [[ -n "$doc_path" ]]; then
    if [[ ! -f "$doc_path" ]]; then
      echo "Error: --doc file not found: $doc_path" >&2
      exit 2
    fi
    python3 "$UPDATER" "$dst_dir" "$dst_dir/README.md" --update-entry "$base" --entry-md "$doc_path"
  fi
fi

echo "OK: published"
echo "  group  : $group"
echo "  entry  : $dst_abs"
echo "  target : $src_abs"

if [[ "$do_readme" == "true" ]]; then
  echo "  readme : $dst_dir/README.md"
fi
