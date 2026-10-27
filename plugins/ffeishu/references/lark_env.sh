#!/usr/bin/env bash
# lark-cli 通用工具层（L0 共享）— auth 前缀 + 预检 + 透传 + 私有配置读取。
# 只打包"所有飞书 skill 都要做"的事：账号前缀、PATH、auth 预检、日志行剥离、读 ccprivate 真值。
# 不含任何 skill 专属命令语法/schema（那些留在各自 skill）。
#
# 用法: source ~/.claude/skills/ffeishu/references/lark_env.sh
# 提供:
#   lark_auth_check                # auth 预检，ok 返回 0，失败返回 1
#   lark_call <cmd...>             # 透传 lark-cli，剥离 [lark-cli] 日志行，保留退出码
#   lark_conf_get <file> <key...>  # 从 ccprivate/conf 读 yaml 值（末键路径），如 lark_conf_get writing/case.yaml base_token
#   lark_conf_path <file>          # 返回 ccprivate/conf/<file> 绝对路径（不存在返回空）

# --- 账号前缀（marker 读，勿写死） ---
_LARK_MARKER="$HOME/.lark-cli-account"
if [[ -f "$_LARK_MARKER" ]]; then
    export LARKSUITE_CLI_CONFIG_DIR="$(grep '^configDir=' "$_LARK_MARKER" | cut -d= -f2)"
else
    echo "[lark-env] ERROR: $_LARK_MARKER 不存在，先跑 lark-switch.sh 选账号" >&2
    return 1 2>/dev/null || exit 1
fi
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac

lark_auth_check() {
    # grep 必须匹配空格变体（lark-cli 输出 `"ok": true`）
    lark-cli drive +search --query test --page-size 1 --as user 2>&1 \
        | sed '/^\[lark-cli\]/d' | grep -q '"ok": *true'
}

lark_call() {
    local out rc
    out="$("$@" 2>&1)"
    rc=$?
    printf '%s\n' "$out" | sed '/^\[lark-cli\]/d'
    return $rc
}

# 私有配置读取：真值存 ccprivate/conf/<file>，公开 skill 运行时读取。
#
# ⚠️ 实现已收敛到 plugin_env.sh 的单一实现（2026-10-27）。此前这里是**独立一份**，
# 与 fpdf/llm 等 15 处各自维护回退链，变量名还有 3 种并存 —— 改一处必漏其余。
# 现在 lark_conf_path / lark_conf_get 只是单实现的薄壳，保留旧名以免改动调用方。
_PLUGIN_ENV="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}/references/plugin_env.sh"
# shellcheck source=/dev/null
[[ -f "$_PLUGIN_ENV" ]] && source "$_PLUGIN_ENV"

lark_conf_path() {
    if declare -F skillconf_file >/dev/null; then
        skillconf_file "$1"
    else
        # 回退：plugin_env.sh 缺失时内联最小实现（不该发生，防脚本整体挂掉）
        local base="${CCPRIVATE_HOME:-${CCPRIVATE_DIR:-$HOME/git/ccprivate}}"
        [[ -f "$base/conf/$1" ]] && echo "$base/conf/$1"
    fi
}

lark_conf_get() {
    if declare -F skillconf_file_get >/dev/null; then
        skillconf_file_get "$@"
        return $?
    fi
    local rel="$1"; shift
    local f
    f="$(lark_conf_path "$rel")" || return 1
    python3 - "$f" "$@" <<'PYEOF'
import sys, yaml
path, keys = sys.argv[1], sys.argv[2:]
try:
    node = yaml.safe_load(open(path)) or {}
except Exception:
    sys.exit(1)
for k in keys:
    if isinstance(node, dict) and k in node:
        node = node[k]
    else:
        sys.exit(1)
print(node if not isinstance(node, bool) else str(node).lower())
PYEOF
}

# 文档索引查询 — 私有索引统一存 ccprivate/skill/ffeishu.yaml 的 doc_index（唯一真相源）。
# 查询: lark_doc_index [keyword]   # 空参 = 列全部；keyword 匹配 title/description/parent_doc
# 追加: lark_doc_index --add title url doc_token parent_doc "description"   # 幂等（按 doc_token 去重）
lark_doc_index() {
    local f
    # 单一实现解析路径；找不到也不硬编 $HOME/git/ccprivate（装机用户无此目录）
    f="$(skillconf_file skill/ffeishu.yaml 2>/dev/null || skillconf_file ../skill/ffeishu.yaml 2>/dev/null || true)"
    [[ -n "$f" && -f "$f" ]] || {
        echo "[doc-index] 未找到 ffeishu 配置（含 doc_index）；" >&2
        echo "  自用: 应存在于 \$(skillconf_ccprivate_root)/skill/ffeishu.yaml" >&2
        return 1
    }
    if [[ "${1:-}" == "--add" ]]; then
        local title="$2" url="$3" tok="$4" parent="$5" desc="${6:-}"
        [[ -n "$title" && -n "$url" ]] || { echo "[doc-index] --add need title url [doc_token] [parent] [desc]" >&2; return 2; }
        python3 - "$f" "$title" "$url" "$tok" "$parent" "$desc" <<'PYEOF'
import sys, yaml
path, title, url, tok, parent, desc = sys.argv[1:]
d = yaml.safe_load(open(path)) or {}
di = d.setdefault("doc_index", [])
# 自愈：历史遗留的「扁平碎片」格式（`- title:` / `- url:` 各成独立 list item，
# 来自逐行追加）会让 .get("url") 永远取不到 → 去重失效、每次 --add 重复插入。
# 检测到碎片即告警并中止，提示先重组（勿静默继续，否则碎片越攒越多）。
if any(isinstance(e, dict) and "title" not in e for e in di):
    sys.stderr.write("[doc-index] ⚠️ 检测到扁平碎片格式条目（字段各成独立 list item）"
                     "— 去重已失效。先重组 doc_index 为 dict 列表再 --add。\n")
    sys.exit(3)
for e in di:
    if e.get("url") == url:
        print("[doc-index] 已存在，跳过: " + url); sys.exit(0)
di.append({"title": title, "url": url, "doc_token": tok, "parent_doc": parent, "description": desc})
yaml.dump(d, open(path, "w"), allow_unicode=True, sort_keys=False, default_flow_style=False)
print("[doc-index] 已追加: " + title)
PYEOF
        return 0
    fi
    local kw="${1:-}"
    python3 - "$f" "$kw" <<'PYEOF'
import sys, yaml
path, kw = sys.argv[1], sys.argv[2]
d = yaml.safe_load(open(path)) or {}
di = d.get("doc_index", [])
kw = kw.lower() if kw else ""
hits = [e for e in di if not kw or kw in (e.get("title","") + e.get("description","") + e.get("parent_doc","")).lower()]
for e in sorted(hits, key=lambda x: x.get("created",""), reverse=True):
    print(f"{e.get('title','')} | {e.get('url','')} | parent={e.get('parent_doc','')}")
PYEOF
}
