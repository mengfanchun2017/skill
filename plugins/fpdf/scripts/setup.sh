#!/usr/bin/env bash
# fpdf 依赖预检 + 安装 — 幂等，缺什么装什么。
#
# 依赖分五类（实测结论，非猜测）：
#   uv            解析/渲染脚本的运行器（PEP723 自管 py 依赖，不碰系统 Python）
#   poppler-utils PDF 命令行工具（pdftotext/pdfinfo/pdfimages/pdftoppm）— apt 装
#   lark-cli      飞书读写（docs +create/+fetch/+update、drive +export/+delete）
#   飞书授权       lark-cli auth（未授权任何飞书写操作都会失败）
#   MinerU token  Precision 档鉴权（存在 ccprivate/conf/mineru.json；Flash 档不需要）
#
# pymupdf/pdf2docx 等 python 库由 uv 按脚本头部 # /// script 自动拉，本脚本不管。
#
# 用法：
#   bash setup.sh            # 检查 + 缺啥装啥（装需 sudo 时提示）
#   bash setup.sh --check    # 只检查不安装（CI/只想看状态时用）
#   bash setup.sh --quiet    # 只输出结论行 + 退出码（供 run.sh 内嵌调用）

set -uo pipefail

CHECK_ONLY=0; QUIET=0
while [ $# -gt 0 ]; do
    case "$1" in
        --check) CHECK_ONLY=1 ;;
        --quiet) QUIET=1 ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "未知参数: $1" >&2; exit 2 ;;
    esac
    shift
done

ok()   { [ "$QUIET" = 1 ] || printf '  \033[32m✓\033[0m %s\n' "$*"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*" >&2; }
info() { [ "$QUIET" = 1 ] || printf '  \033[36m→\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*" >&2; }

MISSING=0

[ "$QUIET" = 1 ] || { echo "fpdf 依赖检查"; echo "─────────────"; }

# 能否免密 sudo（无 TTY 时交互 sudo 会挂，须先判）
_sudo_ok() {
    command -v sudo >/dev/null 2>&1 || return 1
    sudo -n true 2>/dev/null && return 0
    [ -t 0 ] || return 1          # 无 TTY 且不免密 → 交互 sudo 必挂
    return 0
}

# 需用户手动装时，给可**原样复制**的命令（提示勿手打：实测手输易混入中文顿号、
# 全角字符，apt 会报 "Unable to locate package poppler-utils、"，白跑一趟）
_poppler_manual_hint() {
    printf '\n' >&2
    printf '  \033[33m>>> 需要你自己执行这行（请整行复制，勿手打）\033[0m\n' >&2
    printf '\n      sudo apt-get install -y poppler-utils\n\n' >&2
    printf '  在本会话里可直接输入（! 前缀 = 直接跑，输出回到对话）：\n' >&2
    printf '      ! sudo apt-get install -y poppler-utils\n' >&2
    printf '\n  \033[36m注意\033[0m：包名是 poppler-utils，结尾不要带任何标点；\n' >&2
    printf '       若报 "Unable to locate package poppler-utils、"，\n' >&2
    printf '       多半是粘进了中文顿号「、」——删掉重跑即可。\n' >&2
    printf '\n  （不装也能跑：解析/渲染主路径走 pymupdf，不依赖 poppler）\n' >&2
}

# --- uv ---
if command -v uv >/dev/null 2>&1; then
    ok "uv $(uv --version 2>/dev/null | awk '{print $2}')"
else
    bad "uv 未安装"
    info "装 uv:  curl -LsSf https://astral.sh/uv/install.sh | sh"
    MISSING=$((MISSING+1))
fi

# --- poppler-utils（PDF 命令行工具；非必需但有则更快更省，尤其大文件抽文本/拆图）---
POPPLER_BINS="pdftotext pdfinfo pdfimages pdftoppm"
pop_missing=""
for b in $POPPLER_BINS; do command -v "$b" >/dev/null 2>&1 || pop_missing="$pop_missing $b"; done
if [ -z "$pop_missing" ]; then
    ok "poppler-utils（$POPPLER_BINS 齐备）"
elif [ "$CHECK_ONLY" = 1 ]; then
    warn "poppler-utils 缺:$pop_missing"
    MISSING=$((MISSING+1))
elif _sudo_ok; then
    info "poppler-utils 缺失（$pop_missing）→ 安装中..."
    if sudo apt-get install -y poppler-utils >/dev/null 2>&1; then
        ok "poppler-utils 已安装"
    else
        bad "poppler-utils 安装失败"
        _poppler_manual_hint
        MISSING=$((MISSING+1))
    fi
else
    # 需用户自己装 —— 提示必须可直接复制粘贴，别让人手打（易混入中文标点/全角字符）
    bad "poppler-utils 缺:$pop_missing（需 sudo 但当前环境不可用）"
    _poppler_manual_hint
    MISSING=$((MISSING+1))
fi

# --- lark-cli ---
if command -v lark-cli >/dev/null 2>&1 || [ -x "$HOME/.local/bin/lark-cli" ]; then
    ok "lark-cli $(lark-cli --version 2>/dev/null | awk '{print $NF}')"
else
    bad "lark-cli 未安装"
    info "装 lark-cli:  bash ~/git/ccconfig/init-option.sh larkcli"
    MISSING=$((MISSING+1))
fi

# --- 飞书授权 ---
MARKER="$HOME/.lark-cli-account"
if [ -f "$MARKER" ]; then
    CFG="$(grep '^configDir=' "$MARKER" | cut -d= -f2)"
    export LARKSUITE_CLI_CONFIG_DIR="$CFG"
    if lark-cli auth status --json 2>/dev/null \
        | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('identities',{}).get('user',{}).get('available') else 1)" 2>/dev/null; then
        ok "飞书授权（账号 $(grep '^name=' "$MARKER" | cut -d= -f2)）"
    else
        bad "飞书未授权（token 过期或缺）"
        info "授权:  bash ~/git/ccconfig/init-option.sh larkcli   （走扫码，一次性）"
        MISSING=$((MISSING+1))
    fi
else
    bad "未配置飞书账号 marker（$MARKER）"
    info "配置:  bash ~/git/ccconfig/init-option.sh larkcli"
    MISSING=$((MISSING+1))
fi

# --- MinerU token（Precision 档需要；Flash 不需要）---
CONF="${CCPRIVATE_HOME:-$HOME/git/ccprivate}/conf/mineru.json"
if [ -f "$CONF" ] && python3 -c "
import json,sys
t=json.load(open('$CONF')).get('token','')
sys.exit(0 if t and not any(m in t for m in ('请填入','请到','your key','placeholder','<your-')) else 1)
" 2>/dev/null; then
    ok "MinerU token（Precision 档可用）"
else
    warn "MinerU token 未配置 → 只能跑 flash 档（仅文本，无结构/无图，不能排版）"
    info "配置:  bash ~/git/ccconfig/init-option.sh mineru key"
fi

if [ "$QUIET" = 1 ]; then
    [ "$MISSING" -eq 0 ] && echo "deps-ok" || echo "deps-missing:$MISSING"
else
    echo "─────────────"
    if [ "$MISSING" -eq 0 ]; then
        echo "全部就绪"
    else
        echo "$MISSING 项待处理（见上方 → 提示）"
    fi
fi
exit "$MISSING"