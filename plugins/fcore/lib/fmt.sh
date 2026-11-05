#!/bin/bash
# fcore/lib/fmt.sh — 飞书文档格式断言（机械可判的部分）
#
# write-checklist 里的规则很多能机械判定。这里只收**确定可判**的，
# 剩下靠人看的不硬凑。规则真相源仍是 ffeishu/references/write-checklist.md，
# 本文件是它的可执行子集 —— 两者不一致时以 write-checklist 为准并回来改这里。

F_FMT_VIOLATIONS=0
_f_fmt_bad() { F_FMT_VIOLATIONS=$((F_FMT_VIOLATIONS + 1)); echo "  ❌ $1"; }

# f_fmt_check_xml <file> — 校验 DocxXML/markdown 混排的飞书内容
f_fmt_check_xml() {
    local f="$1"
    [[ -f "$f" ]] || { echo "[fcore] 文件不存在: $f" >&2; return 2; }
    F_FMT_VIOLATIONS=0
    echo "格式自检: $f"

    # H1 必须是蓝字无底色（用户两轮反馈定过的规则，别再自作主张换方案）
    if grep -qE '<h1[^>]*background-color' "$f"; then
        _f_fmt_bad "H1 用了 background-color（应为蓝字无底色）"
    fi
    local h1; h1=$(grep -c '<h1' "$f" || true)
    local h1blue; h1blue=$(grep -cE '<h1><span text-color="blue">' "$f" || true)
    [[ "$h1" -gt 0 && "$h1blue" -eq 0 ]] && _f_fmt_bad "H1 未用 <span text-color=\"blue\"> 包裹（共 $h1 处 H1）"

    # H2 及以下不染色
    grep -qE '<h[2-6][^>]*text-color|<h[2-6]><span[^>]*text-color' "$f" \
        && _f_fmt_bad "H2-H6 被染了色（应为默认黑）"

    # 禁止 H4+
    grep -qE '<h[4-6]' "$f" && _f_fmt_bad "出现 H4+ 标题（只允许 H1-H3）"

    # 禁止分割线（用户明确要求）
    grep -qE '<hr/?>|^---$' "$f" && _f_fmt_bad "出现分割线（<hr/> 或 ---）"

    # 表格必须有 colgroup width=822
    local tables no_cg
    tables=$(grep -c '<lark-table\|<table' "$f" || true)
    no_cg=$(grep -c '<table' "$f" || true)
    if [[ "$tables" -gt 0 ]] && ! grep -q '<colgroup' "$f"; then
        _f_fmt_bad "有表格但缺 <colgroup>（飞书表格必须 XML + colgroup width=822）"
    fi
    # 判据是**每个 colgroup 的宽度和**等于 822，不是某个 col 写了 822。
    # 旧判据 grep 字面 'width="822"' 会把「两列 411+411」「三列 90+340+392」
    # 这类完全合法的表全判失败（实测误报 141 张表）。
    local cg
    while IFS= read -r cg; do
        local sum
        sum=$(printf '%s' "$cg" | grep -oE 'width="[0-9]+"' | grep -oE '[0-9]+' \
              | awk '{s+=$1} END{print s+0}')
        [[ "$sum" -ne 822 ]] && _f_fmt_bad "colgroup 宽度和 = $sum（应为 822）"
    done < <(python3 - "$f" <<'PY'
import re, sys
x = open(sys.argv[1], encoding='utf-8').read()
for m in re.finditer(r'<colgroup[^>]*>(.*?)</colgroup>', x, re.S):
    print(m.group(1))
PY
)

    # 手动编号（飞书自动生成目录，禁止手写编号）
    grep -qE '^#+ *([一二三四五六七八九十]+、|[0-9]+\.[0-9]* *|[（(][0-9]+[)）] *)' "$f" \
        && _f_fmt_bad "标题含手动编号（一、/ 1.1 / (1)）"

    if [[ "$F_FMT_VIOLATIONS" -eq 0 ]]; then
        echo "  ✅ 无问题"
        return 0
    fi
    echo "  共 $F_FMT_VIOLATIONS 项，规则真相源: ffeishu/references/write-checklist.md"
    return 1
}

# f_fmt_check_md <file> — 校验纯 markdown 报告（fstander-report 交付前门禁的可执行子集）
f_fmt_check_md() {
    local f="$1"
    [[ -f "$f" ]] || { echo "[fcore] 文件不存在: $f" >&2; return 2; }
    F_FMT_VIOLATIONS=0
    echo "报告自检: $f"

    grep -qE '^---$' "$f" && _f_fmt_bad "出现 --- 分割线（用户要求不用分割线）"
    grep -qE '<hr/?>' "$f" && _f_fmt_bad "出现 <hr/>"

    # 表格分隔行必须是 |---|---| 双横线。单横线 |-|-| 会被判定正则漏掉当数据行
    grep -qE '^\|[[:space:]]*-[[:space:]]*\|' "$f" \
        && _f_fmt_bad "表格分隔行用了单横线 |-|-|，必须 |---|（否则当数据行渲染错乱）"

    # 正文句末引用：有数字断言但全篇无 [n] 引用
    local nums cites
    nums=$(grep -cE '[0-9]+(\.[0-9]+)?[%％]|[0-9]{4}年|亿元|万美元' "$f" || true)
    cites=$(grep -cE '\[[0-9]+\]' "$f" || true)
    [[ "$nums" -gt 5 && "$cites" -eq 0 ]] && _f_fmt_bad "正文有 $nums 处数据但无 [n] 句末引用（凡数据必有引用）"

    # 文献 ≥15 条（仅当有参考文献段时检查）
    if grep -qE '^#+ *参考(文献|资料)' "$f"; then
        local refs
        refs=$(sed -n '/^#+ *参考\(文献\|资料\)/,$p' "$f" | grep -cE '^\s*(\[[0-9]+\]|[0-9]+\.) ' || true)
        [[ "$refs" -lt 15 ]] && _f_fmt_bad "参考文献仅 $refs 条（要求 ≥15）"
    fi

    if [[ "$F_FMT_VIOLATIONS" -eq 0 ]]; then
        echo "  ✅ 无问题"
        return 0
    fi
    echo "  共 $F_FMT_VIOLATIONS 项，规则真相源: fstander-report"
    return 1
}

export -f f_fmt_check_xml f_fmt_check_md 2>/dev/null || true
