#!/bin/bash
# fcore/lib/lark.sh — lark-cli 包装（账号前缀 + auth 预检 + 输出净化 + 固定参数模板）
#
# 取代此前 5 处各自实现的 auth 预检（其中 3 处 grep 写成 '"ok":true' 导致
# lark-cli 输出 `"ok": true` 时永不匹配 → 认证明明正常也恒报 AUTH_FAILED），
# 以及 2 份已分叉的 lark_env.sh。

# --- 账号目录：由 marker 决定（lark-switch.sh 维护），不写死 ---
# 无 marker 时**不设**该变量，让 lark-cli 用自己的默认目录（写死 $HOME/.lark-cli
# 会让没建过该目录的用户直接 not_configured）。
f_lark_init() {
    local marker="$HOME/.lark-cli-account"
    if [[ -f "$marker" ]]; then
        local d
        d="$(grep '^configDir=' "$marker" | cut -d= -f2)"
        [[ -n "$d" ]] && export LARKSUITE_CLI_CONFIG_DIR="$d"
    fi
    case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac
}

f_lark_bin() { command -v lark-cli 2>/dev/null; }

# f_lark_auth_check — 返回 0=可用，1=未装，2=未配置/过期
# ⚠️ lark-cli 输出是 `"ok": true`（冒号后有空格）。必须用 '"ok": *true'。
f_lark_auth_check() {
    f_lark_init
    f_lark_bin >/dev/null || return 1
    lark-cli drive +search --query test --page-size 1 --as user 2>&1 \
        | sed '/^\[lark-cli\]/d' | grep -qE '"ok": *true' && return 0
    return 2
}

# f_lark_need_auth — 预检并打印可执行指引；不可用时返回非零（调用方据此降级）
f_lark_need_auth() {
    local rc=0
    f_lark_auth_check || rc=$?
    case "$rc" in
        0) return 0 ;;
        1) echo "[fcore] lark-cli 未安装：npm install -g @larksuite/cli" >&2; return 1 ;;
        *)
            echo "[fcore] lark-cli 未配置或授权过期。修复：" >&2
            echo "  lark-cli auth login --scope \"docx:document:create,docx:document:readonly,drive:drive:readonly\" --no-wait --json" >&2
            echo "  lark-cli auth qrcode \"<verification_url>\" --output ./feishu-auth-qr.png" >&2
            return 2 ;;
    esac
}

# f_lark <cmd...> — 透传 lark-cli，剥离日志行，保留退出码
f_lark() {
    f_lark_init
    local out rc
    out="$("$@" 2>&1)"; rc=$?
    printf '%s\n' "$out" | sed '/^\[lark-cli\]/d'
    return $rc
}

# 简写：所有 f_lark_* 都自动带 --as user 与账号前缀
f_lark_doc_get()  { f_lark lark-cli docs +fetch  --api-version v2 --doc "$1" --detail "${2:-full}" --as user; }
f_lark_doc_ids()  { f_lark lark-cli docs +fetch  --api-version v2 --doc "$1" --detail with-ids --as user; }
f_lark_doc_create() {  # <parent-token> <title> [content-file|-]
    local parent="$1" title="$2" src="${3:--}"
    f_lark_init
    if [[ "$src" == "-" ]]; then
        f_lark lark-cli docs +create --api-version v2 --parent-token "$parent" --as user \
            --title "$title" --doc-format markdown --content -
    else
        f_lark lark-cli docs +create --api-version v2 --parent-token "$parent" --as user \
            --title "$title" --doc-format markdown --content "$(cat "$src")"
    fi
}

# f_lark_upload <本地文件> — 上传到 Drive，输出 file_token
f_lark_upload() {
    f_lark_init
    f_lark lark-cli drive +upload --file "$1" --as user
}

# f_lark_search <关键词> [数量]
f_lark_search() {
    f_lark_init
    f_lark lark-cli drive +search --query "$1" --page-size "${2:-10}" --as user
}

export -f f_lark_init f_lark_bin f_lark_auth_check f_lark_need_auth f_lark \
          f_lark_doc_get f_lark_doc_ids f_lark_doc_create f_lark_upload f_lark_search 2>/dev/null || true
