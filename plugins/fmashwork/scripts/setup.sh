#!/bin/bash
# fmashwork 依赖安装脚本 — 自动建 venv + 装包，不污染系统 Python
#
# 用法:
#   bash <fmashwork_skill>/scripts/setup.sh
#
# 幂等：重复运行只补装缺失依赖，不重复下载。
#
# 为什么需要 venv（PEP-668）:
#   新版 Ubuntu/Debian 的 Python 被 apt 管理，直接 `pip install` 报
#   externally-managed-environment。venv 隔离依赖，卸载即删目录。
#   系统用自己的包，skill 用自己的包，互不干扰。

set -euo pipefail

VENV_DIR="${FMASHWORK_VENV:-$HOME/.fmashwork-venv}"
PY_PREFIX="python3"

# ensurepip 缺失（PEP-668 精简 Python 不带）：自动 apt 装，省掉手动一步
if ! "$PY_PREFIX" -c "import ensurepip" >/dev/null 2>&1; then
    minor="$("$PY_PREFIX" -c 'import sys; print(sys.version_info.minor)')"
    echo "→ 缺 venv 组件，自动安装 python3.${minor}-venv ..."
    sudo apt-get install -y "python3.${minor}-venv" || {
        echo "❌ 自动安装失败，需手动执行:"
        echo "    sudo apt-get install python3.${minor}-venv"
        echo "装完重新运行本脚本即可。"
        exit 1
    }
    echo "→ venv 组件已装"
fi

# 幂等建 venv
if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "→ 创建 venv: $VENV_DIR"
    "$PY_PREFIX" -m venv "$VENV_DIR"
else
    echo "→ venv 已存在: $VENV_DIR"
fi

PIP="$VENV_DIR/bin/pip"
PY="$VENV_DIR/bin/python"

# 幂等逐装
# 循环逐个装而非一句话，缺失才装，减少重复检查/网络
# import 名 ≠ pip 名：pyyaml 导入是 yaml，需显式映射
for pkg in trimesh pymeshfix numpy pyyaml; do
    case "$pkg" in pyyaml) mod=yaml ;; *) mod="$pkg" ;; esac
    if "$PY" -c "import $mod" >/dev/null 2>&1; then
        echo "  ✓ $pkg 已装"
    else
        echo "→ 安装 $pkg"
        "$PIP" install -q "$pkg"
    fi
done

# 完成提示
echo
echo "✅ 依赖就绪。用 venv 的 Python 运行工具："
echo
echo "    $PY ~/.claude/skills/fmashwork/scripts/fmashwork.py check-env"
echo
echo "（fmashwork skill 会优先自动用这个 venv，无需手动切换）"