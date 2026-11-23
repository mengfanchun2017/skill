#!/bin/bash
# _boot.sh — 定位并 source fcore 的唯一实现。
#
# ⚠️ 本文件是**生成物**：由 ccconfig/bin/sync-plugin-env.sh 从
#    fcore/references/_boot.sh 复制到每个 plugin 的 references/。
#    不要改某一份副本 —— 改源文件后重跑 sync。
#
# 为何需要：`/plugin install` 只复制 plugin **自己**的目录，别的 plugin 拿不到 fcore。
# 查找顺序（覆盖 git clone 与 plugin 安装两种布局）：
#   1. 自己就是 fcore
#   2. 兄弟目录（git clone 布局：plugins/<name>/ → 上跳两层到 plugins/）
#   3. cache 布局：<cache>/<market>/fcore/<version>/lib/
#   4. ~/.claude/skills/fcore/lib/（本地 symlink 布局）
#   5. F_CORE_LIB 环境变量（测试/特殊布局）

_fcore_boot() {
    local here
    here="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" 2>/dev/null && pwd)" || return 1
    local lib=""

    # 1. 自己就是 fcore
    if [[ -f "$here/../lib/path.sh" && "$(basename "$(dirname "$here")")" == "fcore" ]]; then
        lib="$(cd "$here/../lib" && pwd)"
    fi
    # 2. 兄弟目录（plugin clone 布局）
    if [[ -z "$lib" ]]; then
        local pdir; pdir="$(dirname "$(dirname "$here")")"
        [[ -f "$pdir/fcore/lib/path.sh" ]] && lib="$pdir/fcore/lib"
    fi
    # 3. cache 布局
    if [[ -z "$lib" ]]; then
        local market_dir; market_dir="$(dirname "$(dirname "$(dirname "$here")")")"
        if [[ -d "$market_dir/fcore" ]]; then
            local fv; fv="$(ls -d "$market_dir/fcore"/*/ 2>/dev/null | head -1)"
            [[ -n "$fv" && -f "${fv%/}/lib/path.sh" ]] && lib="${fv%/}/lib"
        fi
    fi
    # 4. 本地 symlink 布局
    if [[ -z "$lib" && -f "$HOME/.claude/skills/fcore/lib/path.sh" ]]; then
        lib="$HOME/.claude/skills/fcore/lib"
    fi
    # 5. 环境变量
    if [[ -z "$lib" && -n "${F_CORE_LIB:-}" && -f "$F_CORE_LIB/path.sh" ]]; then
        lib="$F_CORE_LIB"
    fi

    [[ -n "$lib" ]] || return 1
    F_CORE_LIB="$lib"
    export F_CORE_LIB
    # shellcheck source=/dev/null
    source "$lib/path.sh"
    # shellcheck source=/dev/null
    [[ -f "$lib/lark.sh" ]]    && source "$lib/lark.sh"
    # shellcheck source=/dev/null
    [[ -f "$lib/genre.sh" ]]   && source "$lib/genre.sh"
    # shellcheck source=/dev/null
    [[ -f "$lib/fmt.sh" ]]     && source "$lib/fmt.sh"
    return 0
}

_fcore_boot
