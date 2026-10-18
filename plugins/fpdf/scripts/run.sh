#!/usr/bin/env bash
# fpdf 编排器 — 一个 PDF 走完全链路，产出飞书文档（可选 Word 导出、译文版）。
#
# 用法（通常由 SKILL.md 的 AI 流程调用，不必手敲）：
#   run.sh <pdf路径> [--word] [--trans] [--title T] [--parent TOKEN] [--slug S] [--columns flow|grid]
#
# 设计：本脚本只做「确定性机械步骤」，判断类决策（标题、父文档、翻译）留在 SKILL.md。
# 每一步打印可读进度到 stderr；最后一行 stdout 是 JSON 结果（机器可读）。

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$HERE")"

ok()   { printf '\033[32m✓\033[0m %s\n' "$*" >&2; }
bad()  { printf '\033[31m✗\033[0m %s\n' "$*" >&2; }
info() { printf '\033[36m→\033[0m %s\n' "$*" >&2; }

SRC=""; WORD=0; TRANS=0; TITLE=""; PARENT=""; SLUG=""; COLUMNS="flow"
while [ $# -gt 0 ]; do
    case "$1" in
        --word)    WORD=1 ;;
        --trans)   TRANS=1 ;;
        --title)   TITLE="$2"; shift ;;
        --parent)  PARENT="$2"; shift ;;
        --slug)    SLUG="$2"; shift ;;
        --columns) COLUMNS="$2"; shift ;;
        -*)        bad "未知参数 $1"; exit 2 ;;
        *)         SRC="$1" ;;
    esac
    shift
done

[ -n "$SRC" ] || { bad "用法: run.sh <pdf路径> [--word] [--trans] ..."; exit 2; }

# Windows 路径 → WSL 路径（用户从资源管理器复制的是 C:\... 或 C:/...）
case "$SRC" in
    [A-Za-z]:[\\/]*) SRC="$(echo "$SRC" | sed -E 's#^([A-Za-z]):[\\/]#/mnt/\L\1/#; s#\\#/#g')" ;;
    /mnt/[a-z]/*)    : ;;
    /*)              : ;;
    *)               SRC="$(realpath "$SRC" 2>/dev/null || echo "$SRC")" ;;
esac
[ -f "$SRC" ] || { bad "文件不存在: $SRC"; exit 2; }

# 工作目录：仓库外（避免 auto-sync 把版权材料推进公开库）
WORK_ROOT="${FPDF_WORK_ROOT:-$HOME/pdf-work}"
# slug 用 python 生成：sed 的 [一-龥] 字符范围在 LANG=C.UTF-8 下报
# "Invalid collation character"（LC_COLLATE 不支持该范围），会静默产出空 slug。
[ -n "$SLUG" ] || SLUG="$(python3 -c "
import re,sys,os
s=os.path.splitext(os.path.basename(sys.argv[1]))[0]
s=re.sub(r'[^\w一-鿿-]+','-',s,flags=re.UNICODE).strip('-')
print(s)
" "$SRC" 2>/dev/null)"
[ -n "$SLUG" ] || SLUG="document"
WORKDIR="$WORK_ROOT/$SLUG"
mkdir -p "$WORKDIR"

info "源文件: $SRC"
info "工作目录: $WORKDIR"

# --- 1. 解析（Precision 档，带结构）---
info "[1/4] 解析（MinerU Precision）..."
if ! uv run --quiet "$HERE/parse.py" "$SRC" --outdir "$WORKDIR" --slug "$SLUG" >"$WORKDIR/.parse.out" 2>"$WORKDIR/.parse.err"; then
    bad "解析失败："; cat "$WORKDIR/.parse.err" >&2; exit 1
fi
PARSE_JSON="$(tail -1 "$WORKDIR/.parse.out")"
ITEMS="$(printf '%s' "$PARSE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('items',0))" 2>/dev/null || echo 0)"
if [ "$ITEMS" = "0" ]; then
    bad "解析未返回结构条目（content_list 为空）→ 无法排版。检查 MinerU 档位/token。"
    cat "$WORKDIR/.parse.err" >&2; exit 1
fi
ok "解析完成：$ITEMS 条结构条目"

# --- 2. 渲染 XML ---
info "[2/4] 渲染 DocxXML..."
PAGE_TITLE="${TITLE:-$SLUG}"
( cd "$WORKDIR" && python3 "$HERE/render.py" "$SLUG" --workdir . --title "$PAGE_TITLE" \
    --columns "$COLUMNS" --out "$WORKDIR/$SLUG.xml" ) 2>&1 | grep -v '^$' >&2 || true
[ -s "$WORKDIR/$SLUG.xml" ] || { bad "渲染失败"; exit 1; }
ok "渲染完成：$(wc -c <"$WORKDIR/$SLUG.xml") 字符"

# --- 3. 上传飞书 ---
info "[3/4] 上传飞书..."
export LARKSUITE_CLI_CONFIG_DIR="$(grep '^configDir=' "$HOME/.lark-cli-account" | cut -d= -f2)"
export PATH="$HOME/.local/bin:$PATH"
CREATE_ARGS=(--api-version v2 --as user --doc-format xml --content "@./$SLUG.xml" --title "$PAGE_TITLE")
if [ -n "$PARENT" ]; then
    CREATE_ARGS+=(--parent-token "$PARENT")
else
    # wiki_nodes.default 两种形态都要吃：fpdf.yaml 用自己的（可能直接是 token 串
    # 或 {token:}），回落 ffeishu.yaml 时是 {token: ...} 嵌套 dict。
    DEF_NODE="$(python3 -c "
import yaml,os
for p in [os.path.expanduser('~/git/ccprivate/skill/fpdf.yaml'), os.path.expanduser('~/git/ccprivate/skill/ffeishu.yaml')]:
    if os.path.isfile(p):
        d=yaml.safe_load(open(p)) or {}
        n=(d.get('wiki_nodes') or {}).get('default')
        if isinstance(n, dict): n=n.get('token')
        if n: print(n); break
" 2>/dev/null)"
    [ -n "$DEF_NODE" ] && CREATE_ARGS+=(--parent-token "$DEF_NODE")
fi
CREATE_OUT="$( cd "$WORKDIR" && lark-cli docs +create "${CREATE_ARGS[@]}" 2>&1 | sed '/^\[lark-cli\]/d' )"
DOC_ID="$(printf '%s' "$CREATE_OUT" | grep -oP '"document_id":\s*"\K[^"]+' | head -1)"
DOC_URL="$(printf '%s' "$CREATE_OUT" | grep -oP '"url":\s*"\K[^"]+' | head -1)"
[ -n "$DOC_ID" ] || { bad "上传失败："; printf '%s\n' "$CREATE_OUT" >&2; exit 1; }
ok "飞书文档：$DOC_URL"

# --- 4. 可选 Word 导出 ---
WORD_PATH=""
if [ "$WORD" = "1" ]; then
    info "[4/4] 导出 Word..."
    EXP_DIR="${FPDF_WORD_DIR:-$(dirname "$SRC")}"
    export_out="$( lark-cli drive +export --doc-type docx --token "$DOC_ID" \
        --file-extension docx --output-dir "$EXP_DIR" --overwrite 2>&1 | sed '/^\[lark-cli\]/d' )"
    WORD_PATH="$(printf '%s' "$export_out" | grep -oP '"saved_path":\s*"\K[^"]+' | head -1)"
    [ -n "$WORD_PATH" ] && ok "Word：$WORD_PATH" || bad "Word 导出失败"
else
    info "[4/4] 跳过 Word 导出"
fi

# 记录到索引
python3 - "$PAGE_TITLE" "$DOC_URL" "$DOC_ID" "$SRC" <<'PYEOF' >&2 2>&1 || true
import sys, os, yaml
title, url, tok, src = sys.argv[1:5]
f = os.path.expanduser("~/git/ccprivate/skill/fpdf.yaml")
d = yaml.safe_load(open(f)) if os.path.isfile(f) else {}
d = d or {}
di = d.setdefault("doc_index", [])
if not any(e.get("doc_token") == tok for e in di if isinstance(e, dict)):
    di.append({"title": title, "url": url, "doc_token": tok, "source": src})
    yaml.dump(d, open(f, "w"), allow_unicode=True, sort_keys=False)
PYEOF

# 机器可读结果
python3 - "$SLUG" "$WORKDIR" "$DOC_ID" "$DOC_URL" "${WORD_PATH:-}" "$ITEMS" <<'PYEOF'
import json, sys
slug, wd, did, url, word, items = sys.argv[1:7]
print(json.dumps({"slug": slug, "workdir": wd, "doc_id": did, "doc_url": url,
                  "word_path": word, "items": int(items or 0)}, ensure_ascii=False))
PYEOF