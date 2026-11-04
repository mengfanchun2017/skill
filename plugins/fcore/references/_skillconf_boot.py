#!/usr/bin/env python3
"""_skillconf_boot.py — 定位并 import 配置解析的【单一实现】config_env。

⚠️ 本文件是**生成物**：由 ccconfig/bin/sync-plugin-env.sh 从
   ffeishu/references/_skillconf_boot.py 复制到每个 plugin 的 references/。
   不要单独改某个 plugin 里的副本 —— 改源文件后重跑 sync。

对应 _skillconf_boot.sh 的 Python 版。查找顺序相同（见该文件注释）。

用法：
    from _skillconf_boot import config_env
    v = config_env.get("tenant_domain")
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

__all__ = ["load", "config_env"]


def _here() -> Path:
    return Path(__file__).resolve().parent


def _find_impl() -> Path | None:
    here = _here()

    # 1. 自己就是 ffeishu
    if here.name == "references" and here.parent.name == "ffeishu":
        p = here / "config_env.py"
        if p.is_file():
            return p

    # 2. 兄弟目录（git clone 布局：plugins/<name>/references）
    for base in (here.parent.parent, here.parent):
        p = base / "ffeishu" / "references" / "config_env.py"
        if p.is_file():
            return p

    # 3. cache 布局：<cache>/<market>/<plugin>/<version>/references
    version_dir = here.parent            # <plugin>/<version>/
    plugin_dir = version_dir.parent      # <plugin>/
    market_dir = plugin_dir.parent       # <market>/
    if market_dir.is_dir():
        for fv in sorted(market_dir.glob("ffeishu/*/references/config_env.py")):
            return fv

    # 4. 本地 symlink 布局
    p = Path.home() / ".claude" / "skills" / "ffeishu" / "references" / "config_env.py"
    if p.is_file():
        return p

    # 5. 环境变量兜底
    env = os.environ.get("SKILLCONF_IMPL")
    if env and Path(env).is_file():
        return Path(env)
    return None


def load():
    """import 并返回单一实现模块。"""
    p = _find_impl()
    if p is None:
        return None
    spec = importlib.util.spec_from_file_location("_skillconf_config_env", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_skillconf_config_env"] = mod
    spec.loader.exec_module(mod)
    return mod


config_env = load()