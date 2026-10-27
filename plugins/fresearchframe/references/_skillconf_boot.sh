#!/bin/bash
# _skillconf_boot.sh — 定位并 source 配置解析的【单一实现】。
#
# ⚠️ 本文件是**生成物**：由 ccconfig/bin/sync-plugin-env.sh 从
#    ffeishu/references/_skillconf_boot.sh 复制到每个 plugin 的 references/。
#    不要单独改某一个 plugin 里的副本 —— 改源文件后重跑 sync。
#
# 为何需要这个 stub：配置解析的完整实现（plugin_env.sh，~200 行）只放 ffeishu 一处，
# 但 `/plugin install` 只复制 plugin **自己**的目录 → 别的 plugin 装完后拿不到它。
# 实测：27 个 plugin 全装一遍，只有 ffeishu 有 plugin_env.sh，其余 26 个无解析器。
#
# 故每个 plugin 带这份 ~30 行 stub 找实现，实现仍只有一处。
# 查找顺序（覆盖 git clone 与 plugin 安装两种布局）：
#   1. 本 plugin 自己就是 ffeishu
#   2. 向上找兄弟目录 ffeishu/（git clone: plugins/<name>/ siblings）
#   3. cache 布局：<cache>/<market>/ffeishu/<version>/references/
#   4. ~/.claude/skills/ffeishu/（本地 symlink 布局）

_skillconf_boot() {
    local here
    here="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" 2>/dev/null && pwd)" || return 1
    local cand=""

    # 1. 自己就是 ffeishu（或在 ffeishu/references 下）
    if [[ -f "$here/plugin_env.sh" && "$(basename "$here")" == "references" ]] \
       && [[ "$(basename "$(dirname "$here")")" == "ffeishu" ]]; then
        cand="$here/plugin_env.sh"
    fi

    # 2. 兄弟目录（git clone 的 plugins/ 布局）
    if [[ -z "$cand" ]]; then
        local pdir; pdir="$(dirname "$here")"      # <plugin>/ 的父 = plugins/ 或 <market>/
        [[ -f "$pdir/ffeishu/references/plugin_env.sh" ]] && cand="$pdir/ffeishu/references/plugin_env.sh"
    fi

    # 3. cache 布局：<cache>/<market>/<plugin>/<version>/references
    #    → <cache>/<market>/ffeishu/<version>/references
    if [[ -z "$cand" ]]; then
        local ver_dir; ver_dir="$(dirname "$here")"           # <plugin>/<version>/
        local plugin_dir; plugin_dir="$(dirname "$ver_dir")"  # <plugin>/
        local market_dir; market_dir="$(dirname "$plugin_dir")"  # <market>/
        if [[ -d "$market_dir/ffeishu" ]]; then
            local fv
            fv="$(ls -d "$market_dir/ffeishu"/*/ 2>/dev/null | head -1)"
            [[ -n "$fv" && -f "${fv%/}/references/plugin_env.sh" ]] && cand="${fv%/}/references/plugin_env.sh"
        fi
    fi

    # 4. 本地 symlink 布局
    if [[ -z "$cand" && -f "$HOME/.claude/skills/ffeishu/references/plugin_env.sh" ]]; then
        cand="$HOME/.claude/skills/ffeishu/references/plugin_env.sh"
    fi

    # 5. 环境变量兜底（换布局/测试时用）
    if [[ -z "$cand" && -n "${SKILLCONF_IMPL:-}" && -f "$SKILLCONF_IMPL" ]]; then
        cand="$SKILLCONF_IMPL"
    fi

    [[ -n "$cand" ]] || return 1
    # shellcheck source=/dev/null
    source "$cand"
}

_skillconf_boot