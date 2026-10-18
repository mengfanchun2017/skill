#!/usr/bin/env bash
# fpdf 依赖预检 + 安装 — 幂等，缺什么装什么。
#
# 依赖分三类（实测结论，非猜测）：
#   uv           解析/渲染脚本的运行器（PEP723 自管 py 依赖，不碰系统 Python）
#   lark-cli     飞书读写（docs +create/+fetch/+update、drive +export/+delete）
#   MinerU token Precision 档鉴权（存在 ccprivate/conf/mineru.json；Flash 档不需要）
#
# pymupdf/pdf2docx 等 python 库由 uv 按脚本头部 # /// script 自动拉，本脚本不管。

set -uo pipefail

ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*"; }
info() { printf '  \033[36m→\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }

MISSING=0

echo "fpdf 依赖检查"
echo "─────────────"

# --- uv ---
if command -v uv >/dev/null 2>&1; then
    ok "uv $(uv --version 2>/dev/null | awk '{print $2}')"
else
    bad "uv 未安装"
    info "装 uv:  curl -LsSf https://astral.sh/uv/install.sh | sh"
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

echo "─────────────"
if [ "$MISSING" -eq 0 ]; then
    echo "全部就绪"
else
    echo "$MISSING 项待处理（见上方 → 提示）"
fi
exit "$MISSING"