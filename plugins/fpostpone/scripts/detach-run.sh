#!/usr/bin/env bash
# fpostpone --detach 模式：落一个 systemd user timer，到点无头跑命令。
# 关终端、关 Claude 会话都照跑（依赖 systemd --user + linger）。
#
# 用法:
#   detach-run.sh --at "2026-10-27 18:02:00" --cmd "/transliter /path/x.zip" [--name job1]
#   detach-run.sh --list
#   detach-run.sh --cancel job1
#
# 输出: ~/.cache/fpostpone/<name>/result.md（摘要）+ stdout.txt（完整输出）
set -euo pipefail

FP_HOME="${FP_HOME:-$HOME/.cache/fpostpone}"
UNIT_PREFIX="fpostpone"

die() { echo "错误: $*" >&2; exit 1; }

# systemd --user 需要 XDG_RUNTIME_DIR；从 shell 环境进来时可能没设
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

usage() {
    sed -n '2,14p' "$0" | sed 's/^# \?//'
    exit "${1:-0}"
}

sanitize_name() {
    echo "$1" | tr -c 'a-zA-Z0-9_-' '-' | cut -c1-40 | sed 's/-\+$//'
}

cmd_list() {
    systemctl --user list-timers --all --no-pager 2>/dev/null \
        | grep -E "${UNIT_PREFIX}-" || echo "（无 fpostpone 定时任务）"
}

cmd_cancel() {
    local name="$1" unit="${UNIT_PREFIX}-${1}"
    systemctl --user stop "${unit}.timer" 2>/dev/null || true
    systemctl --user reset-failed "${unit}.timer" 2>/dev/null || true
    systemctl --user reset-failed "${unit}.service" 2>/dev/null || true
    echo "已取消: $name"
}

run_job() {
    local at="" cmd="" name=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --at)   at="${2:-}"; shift 2 ;;
            --cmd)  cmd="${2:-}"; shift 2 ;;
            --name) name="${2:-}"; shift 2 ;;
            -h|--help) usage 0 ;;
            *) die "未知参数: $1" ;;
        esac
    done
    [ -n "$at" ]  || die "缺 --at"
    [ -n "$cmd" ] || die "缺 --cmd"
    [ -n "$name" ] || name="$(date +%Y%m%d-%H%M%S)"

    # systemd 要求 "YYYY-MM-DD HH:MM:SS"
    [[ "$at" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}$ ]] \
        || die "--at 格式须为 'YYYY-MM-DD HH:MM:SS'，收到: $at"

    local job_dir="$FP_HOME/$(sanitize_name "$name")"
    mkdir -p "$job_dir"

    local runner="$job_dir/runner.sh"
    cat > "$runner" <<RUNNER
#!/usr/bin/env bash
# fpostpone 自动生成 — 到点由 systemd 调用
exec > "$job_dir/stdout.txt" 2>&1
echo "START \$(date '+%F %T')"
echo "CMD: $cmd"
echo "---"
export PATH="\$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
cd "\$HOME"
# claude 认证走 ~/.claude/settings.json 的 env 块，不吃 shell 继承，故无需注入 key
claude -p "$cmd"
echo "---"
echo "CLAUDE_EXIT=\$?"
echo "END \$(date '+%F %T')"
RUNNER
    chmod +x "$runner"

    local unit="${UNIT_PREFIX}-$(sanitize_name "$name")"

    # TimeoutStartSec: oneshot 默认 90s，transliter 跑百篇要 1 小时+，必须放开
    systemd-run --user \
        --on-calendar="$at" \
        --unit="$unit" \
        --property=TimeoutStartSec=infinity \
        --property=Type=oneshot \
        /bin/bash "$runner" >/dev/null 2>&1 \
        || die "systemd-run 失败（检查时间是否为将来、unit 名是否重复）"

    echo "已排定 (detach 模式)"
    echo "  任务名:   $name"
    echo "  触发时间: $at"
    echo "  systemd:  ${unit}.timer"
    echo "  结果落盘: $job_dir/result.md"
    echo "  查看:     systemctl --user list-timers | grep ${UNIT_PREFIX}"
    echo "  取消:     bash $0 --cancel $name"
    notify_done_note "$name" "$at" "$job_dir"
}

# 提示用户通知通道（实际发送在 runner 到点后由 claude 自己调 lark-cli 完成）
notify_done_note() {
    local name="$1" at="$2" job_dir="$3"
    if [ -n "${FP_NO_NOTIFY:-}" ]; then return 0; fi
    echo ""
    echo "注: 到点跑完后要发飞书通知，请在命令里带上要求，例如"
    echo "    --cmd '/transliter ... 跑完用 lark-cli 发飞书私信给我'"
}

case "${1:-}" in
    --list)   cmd_list ;;
    --cancel) [ $# -ge 2 ] || die "--cancel 需要任务名"; cmd_cancel "$2" ;;
    -h|--help|"") usage 0 ;;
    *) run_job "$@" ;;
esac