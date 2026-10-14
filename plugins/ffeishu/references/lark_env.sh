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
