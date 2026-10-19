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

SRC=""; WORD=0; TRANS=0; TITLE=""; PARENT=""; SLUG=""; COLUMNS="flow"; KEEPREFS=0
while [ $# -gt 0 ]; do
    case "$1" in
        --word)    WORD=1 ;;
        --trans)   TRANS=1 ;;
        --title)   TITLE="$2"; shift ;;
        --parent)  PARENT="$2"; shift ;;
        --slug)    SLUG="$2"; shift ;;
        --columns) COLUMNS="$2"; shift ;;
        --keep-refs) KEEPREFS=1 ;;
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

# 前置依赖：跑 setup.sh 补缺（装 poppler 等）。硬阻断项（uv/lark-cli/授权）缺失则停；
# 软缺项（如 poppler 无 sudo 装不上）只告警 —— 解析走 pymupdf，不依赖它。
if ! bash "$HERE/setup.sh" --quiet >/dev/null 2>&1; then
    info "依赖有缺项，尝试自动补齐..."
    bash "$HERE/setup.sh" >&2 || true
    # 复查硬依赖
    for hard in uv lark-cli; do
        command -v "$hard" >/dev/null 2>&1 || { bad "缺少必需依赖: $hard"; exit 1; }
    done
fi

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

# --- 2. 渲染 XML（先原文；若 --trans 再产译文 XML）---
info "[2/4] 渲染 DocxXML..."
PAGE_TITLE="${TITLE:-$SLUG}"
KEEP_ARG=(); [ "$KEEPREFS" = "1" ] && KEEP_ARG=(--keep-refs)
( cd "$WORKDIR" && python3 "$HERE/render.py" "$SLUG" --workdir . --title "$PAGE_TITLE" \
    --columns "$COLUMNS" "${KEEP_ARG[@]}" --out "$WORKDIR/$SLUG.xml" ) 2>&1 | grep -v '^$' >&2 || true
[ -s "$WORKDIR/$SLUG.xml" ] || { bad "渲染失败"; exit 1; }
ok "渲染完成：$(wc -c <"$WORKDIR/$SLUG.xml") 字符"

TRANS_XML=""
if [ "$TRANS" = "1" ]; then
    info "[2b] 翻译 + 渲染译文版..."
    if uv run --quiet "$HERE/translate.py" "$SLUG" --workdir "$WORKDIR" \
        --target "${FPDF_TRANS_TARGET:-zh}" >"$WORKDIR/.trans.out" 2>"$WORKDIR/.trans.err"; then
        TRANS_MAP="$(tail -1 "$WORKDIR/.trans.out" | python3 -c "import json,sys; print(json.load(sys.stdin).get('trans_map',''))" 2>/dev/null)"
        ( cd "$WORKDIR" && python3 "$HERE/render.py" "$SLUG" --workdir . \
            --title "$PAGE_TITLE（译文）" --translate-map "$TRANS_MAP" \
            --columns "$COLUMNS" "${KEEP_ARG[@]}" --out "$WORKDIR/$SLUG.zh.xml" ) 2>&1 | grep -v '^$' >&2 || true
        [ -s "$WORKDIR/$SLUG.zh.xml" ] && { TRANS_XML="$WORKDIR/$SLUG.zh.xml"; ok "译文版渲染完成"; } \
            || bad "译文版渲染失败"
    else
        bad "翻译失败：$(tail -3 "$WORKDIR/.trans.err" | tr '\n' ' ')"
    fi
fi

# --- 3. 上传飞书 ---
info "[3/4] 上传飞书..."
export LARKSUITE_CLI_CONFIG_DIR="$(grep '^configDir=' "$HOME/.lark-cli-account" | cut -d= -f2)"
export PATH="$HOME/.local/bin:$PATH"
DOC_ID=""; DOC_URL=""; TRANS_ID=""; TRANS_URL=""

# 父节点：--parent 显式给 > fpdf.yaml > ffeishu.yaml 的 wiki_nodes.default
# （fpdf.yaml 自己的可能是裸 token 串，ffeishu.yaml 是 {token:} 嵌套 dict，都要吃）
if [ -z "$PARENT" ]; then
    PARENT="$(python3 -c "
import yaml,os
for p in [os.path.expanduser('~/git/ccprivate/skill/fpdf.yaml'), os.path.expanduser('~/git/ccprivate/skill/ffeishu.yaml')]:
    if os.path.isfile(p):
        d=yaml.safe_load(open(p)) or {}
        n=(d.get('wiki_nodes') or {}).get('default')
        if isinstance(n, dict): n=n.get('token')
        if n: print(n); break
" 2>/dev/null)"
fi

upload_doc() {   # $1=xml文件名(相对WORKDIR) $2=标题  → 设 DOC_ID/DOC_URL
    local xmlf="$1" title="$2"
    local args=(--api-version v2 --as user --doc-format xml --content "@./$xmlf" --title "$title")
    [ -n "$PARENT" ] && args+=(--parent-token "$PARENT")
    local out
    out="$( cd "$WORKDIR" && lark-cli docs +create "${args[@]}" 2>&1 | sed '/^\[lark-cli\]/d' )"
    DOC_ID="$(printf '%s' "$out" | grep -oP '"document_id":\s*"\K[^"]+' | head -1)"
    DOC_URL="$(printf '%s' "$out" | grep -oP '"url":\s*"\K[^"]+' | head -1)"
    [ -n "$DOC_ID" ] || { bad "上传失败："; printf '%s\n' "$out" >&2; return 1; }
    return 0
}

info "[3/4] 上传飞书..."
upload_doc "$SLUG.xml" "$PAGE_TITLE" || exit 1
ok "原文文档：$DOC_URL"

if [ -n "$TRANS_XML" ]; then
    ORIG_ID="$DOC_ID"; ORIG_URL="$DOC_URL"
    upload_doc "$SLUG.zh.xml" "$PAGE_TITLE（译文）" || true
    if [ -n "$DOC_ID" ]; then
        TRANS_ID="$DOC_ID"; TRANS_URL="$DOC_URL"; ok "译文文档：$TRANS_URL"
    fi
    DOC_ID="$ORIG_ID"; DOC_URL="$ORIG_URL"
fi

# --- 4. 可选 Word 导出（原文 + 译文各导一份）---
WORD_PATH=""; WORD_ZH=""
export_word() {   # $1=doc_id $2=附加后缀  → echo 落盘路径
    local id="$1" suffix="${2:-}" out tmpw exp_dir
    exp_dir="${FPDF_WORD_DIR:-$(dirname "$SRC")}"
    # lark-cli 导出有路径沙箱：只能落 cwd / /tmp / ~/files。先导到 /tmp 再 move。
    local tmpd; tmpd="$(mktemp -d /tmp/fpdf-exp.XXXXXX)"
    out="$( lark-cli drive +export --doc-type docx --token "$id" \
        --file-extension docx --output-dir "$tmpd" --overwrite 2>&1 | sed '/^\[lark-cli\]/d' )"
    tmpw="$(printf '%s' "$out" | grep -oP '"saved_path":\s*"\K[^"]+' | head -1)"
    if [ -n "$tmpw" ] && [ -f "$tmpw" ]; then
        mkdir -p "$exp_dir"
        local dest="$exp_dir/$(basename "${tmpw%.docx}")${suffix}.docx"
        mv -f "$tmpw" "$dest" && echo "$dest"
    else
        bad "Word 导出失败：$(printf '%s' "$out" | grep -oP '"message":\s*"\K[^"]+' | head -1)" >&2
    fi
    rm -rf "$tmpd"
}

if [ "$WORD" = "1" ]; then
    info "[4/4] 导出 Word..."
    WORD_PATH="$(export_word "$DOC_ID" "")"
    [ -n "$WORD_PATH" ] && ok "Word(原文)：$WORD_PATH"
    if [ -n "$TRANS_ID" ]; then
        WORD_ZH="$(export_word "$TRANS_ID" ".译文")"
        [ -n "$WORD_ZH" ] && ok "Word(译文)：$WORD_ZH"
    fi
else
    info "[4/4] 跳过 Word 导出"
fi

# 记录到索引（原文 + 译文两条，各自按 doc_token 去重）
python3 - "$PAGE_TITLE" "$DOC_URL" "$DOC_ID" "$SRC" "$TRANS_URL" "$TRANS_ID" <<'PYEOF' >&2 2>&1 || true
import sys, os, yaml
title, url, tok, src, turl, ttok = sys.argv[1:7]
f = os.path.expanduser("~/git/ccprivate/skill/fpdf.yaml")
d = yaml.safe_load(open(f)) if os.path.isfile(f) else {}
d = d or {}
di = d.setdefault("doc_index", [])
def add(t, u, k, note=""):
    if k and not any(isinstance(e, dict) and e.get("doc_token") == k for e in di):
        di.append({"title": t, "url": u, "doc_token": k, "source": src, "note": note})
add(title, url, tok)
if ttok:
    add(title + "（译文）", turl, ttok, "translation")
yaml.dump(d, open(f, "w"), allow_unicode=True, sort_keys=False)
PYEOF

# 机器可读结果
python3 - "$SLUG" "$WORKDIR" "$DOC_ID" "$DOC_URL" "$TRANS_ID" "$TRANS_URL" "${WORD_PATH:-}" "${WORD_ZH:-}" "$ITEMS" <<'PYEOF'
import json, sys
slug, wd, did, url, tid, turl, word, word_zh, items = sys.argv[1:10]
print(json.dumps({"slug": slug, "workdir": wd,
                  "doc_id": did, "doc_url": url,
                  "trans_doc_id": tid, "trans_doc_url": turl,
                  "word_path": word, "word_trans_path": word_zh,
                  "items": int(items or 0)}, ensure_ascii=False))
PYEOF