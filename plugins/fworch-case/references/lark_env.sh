#!/usr/bin/env bash
# fworch-case 工具层：通用 lark-cli 工具（前缀/预检/透传）来自共享层，
# 本文件只加案例库专属：schema 常量 + 打分检索调度。
#
# source 本文件后可用：
#   lark_auth_check / lark_call          # 通用（来自共享层）
#   fworch-case_search <query> [professional] [limit]   # 打分检索
# 用法: source "$(dirname "${BASH_SOURCE[0]}")/lark_env.sh"

# --- 共享工具层：lark_auth_check / lark_call / 账号前缀 / PATH ---
_FWORCH_CASE_SHARED="${FWORCH_CASE_LARK_ENV:-$HOME/.claude/skills/ffeishu/references/lark_env.sh}"
if [[ -f "$_FWORCH_CASE_SHARED" ]]; then
    source "$_FWORCH_CASE_SHARED"
else
    # 回退：共享层缺失时内联最小实现（新机 sync 前）
    _LARK_MARKER="$HOME/.lark-cli-account"
    if [[ -f "$_LARK_MARKER" ]]; then
        export LARKSUITE_CLI_CONFIG_DIR="$(grep '^configDir=' "$_LARK_MARKER" | cut -d= -f2)"
    else
        echo "[lark-env] ERROR: $_LARK_MARKER 不存在，先跑 lark-switch.sh 选账号" >&2
    fi
    case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac
    lark_auth_check() {
        lark-cli drive +search --query test --page-size 1 --as user 2>&1 \
            | sed '/^\[lark-cli\]/d' | grep -q '"ok": *true'
    }
    lark_call() {
        local out rc; out="$("$@" 2>&1)"; rc=$?
        printf '%s\n' "$out" | sed '/^\[lark-cli\]/d'; return $rc
    }
fi

# --- schema 真值：从 ccprivate/conf/writing/case.yaml 读（公开仓库零真实值） ---
# 缺配置时给出提示并留空，调用方（fworch-case_search 等）会因空 token 报错而非静默错连。
case "${FCASELIB_BT:-}" in
  "") FCASELIB_BT="$(lark_conf_get writing/case.yaml base_token 2>/dev/null)" ;;
esac
case "${FCASELIB_TID:-}" in
  "") FCASELIB_TID="$(lark_conf_get writing/case.yaml table_id 2>/dev/null)" ;;
esac
case "${FCASELIB_VIEW:-}" in
  "") FCASELIB_VIEW="$(lark_conf_get writing/case.yaml view_id 2>/dev/null)" ;;
esac
case "${CASELIB_WIKI_ROOT:-}" in
  "") CASELIB_WIKI_ROOT="$(lark_conf_get writing/case.yaml wiki_root_node 2>/dev/null)" ;;
esac
case "${CASELIB_SPACE_ID:-}" in
  "") CASELIB_SPACE_ID="$(lark_conf_get writing/case.yaml space_id 2>/dev/null)" ;;
esac
export FCASELIB_BT FCASELIB_TID FCASELIB_VIEW CASELIB_WIKI_ROOT CASELIB_SPACE_ID
[[ -z "$FCASELIB_BT" ]] && echo "[fworch-case] 未找到案例库配置（ccprivate/conf/writing/case.yaml 的 base_token），先补配置。" >&2
export FCASELIB_SCORE_THRESHOLD="${FCASELIB_SCORE_THRESHOLD:-20}"
export FCASELIB_W_DOMAIN="${FCASELIB_W_DOMAIN:-3}"
export FCASELIB_W_METHOD="${FCASELIB_W_METHOD:-2}"
export FCASELIB_W_KEYWORD="${FCASELIB_W_KEYWORD:-1}"

# 拉全量记录（用于打分），field 按字典序给齐打分所需字段
_fworch-case_list_all() {
    lark_call lark-cli base +record-list \
        --base-token "$FCASELIB_BT" --table-id "$FCASELIB_TID" \
        --field-id "案例名称" --field-id "公司" --field-id "专业领域" \
        --field-id "业务职能" --field-id "分析方法/模型" --field-id "摘要" \
        --field-id "案例主文档" --field-id "编号" \
        --format json --limit 200 --as user
}

fworch-case_search() {
    local query="$1" professional="${2:-}" limit="${3:-3}"
    [[ -z "$query" ]] && { echo "usage: fworch-case_search <query> [professional] [limit]" >&2; return 2; }

    lark_auth_check || { echo "AUTH_FAILED" >&2; return 1; }

    local all
    all="$(_fworch-case_list_all)" || { echo "LIST_FAILED" >&2; return 1; }

    local n
    n=$(printf '%s' "$all" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    rows = d.get("data", {}).get("data", [])
    print(len(rows))
except Exception:
    print(0)
') || n=0

    if (( n <= FCASELIB_SCORE_THRESHOLD )); then
        local cmd_extra=()
        if [[ -n "$professional" ]]; then
            cmd_extra=(--filter-json "{\"logic\":\"and\",\"conditions\":[[\"专业领域\",\"==\",\"$professional\"]]}")
        fi
        lark_call lark-cli base +record-search \
            --base-token "$FCASELIB_BT" --table-id "$FCASELIB_TID" \
            --keyword "$query" \
            --search-field "案例名称" --search-field "公司" --search-field "摘要" \
            --search-field "分析方法/模型" --search-field "专业领域" --search-field "业务职能" \
            --field-id "案例名称" --field-id "编号" --field-id "公司" --field-id "专业领域" \
            --field-id "摘要" --field-id "案例主文档" \
            --format json --limit "$limit" --as user \
            "${cmd_extra[@]}"
        return 0
    fi

    # 大库：全量打分降序
    printf '%s' "$all" | QUERY="$query" PROFESSIONAL="$professional" LIMIT="$limit" \
        python3 -c '
import sys, json, os
query = os.environ["QUERY"]
professional = os.environ["PROFESSIONAL"]
limit = int(os.environ["LIMIT"] or 3)
w_domain = int(os.environ.get("FCASELIB_W_DOMAIN", 3))
w_method = int(os.environ.get("FCASELIB_W_METHOD", 2))
w_keyword = int(os.environ.get("FCASELIB_W_KEYWORD", 1))
d = json.load(sys.stdin)
rows = d.get("data", {}).get("data", [])
fields = d.get("data", {}).get("fields", [])
rids = d.get("data", {}).get("record_id_list", [])
q = query.lower()
hits = []
for i, row in enumerate(rows):
    rec = dict(zip(fields, row))
    name = rec.get("案例名称") or ""
    company = rec.get("公司") or ""
    domain = rec.get("专业领域") or ""
    meth = rec.get("分析方法/模型") or ""
    summary = rec.get("摘要") or ""
    url = rec.get("案例主文档") or ""
    score = 0
    if domain and (domain == professional or (professional and professional in domain)):
        score += w_domain
    m = meth if isinstance(meth, str) else ",".join(meth) if isinstance(meth, list) else ""
    if q in m.lower():
        score += w_method
    hay = " ".join(str(x) for x in (name, company, summary))
    if q in hay.lower():
        score += w_keyword
    if score > 0:
        hits.append({
            "case_name": name, "company": company, "domain": domain,
            "methods": meth, "summary": summary, "url": url,
            "record_id": rids[i] if i < len(rids) else "",
            "score": score,
        })
hits.sort(key=lambda x: x["score"], reverse=True)
for h in hits[:limit]:
    print(json.dumps(h, ensure_ascii=False))
'
}
