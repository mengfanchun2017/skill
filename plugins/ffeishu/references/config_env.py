#!/usr/bin/env python3
"""config_env.py — plugin_env.sh 的 Python 孪生实现。

优先级与 plugin_env.sh **完全一致**（改一处必须同时改另一处；
tests/test-plugin-env-parity.sh 会断言两者对同一输入给出同样结果）：

  1. 环境变量 SKILLCONF_<KEY>
  2. ${CLAUDE_PLUGIN_DATA}/config.json
  3. settings.json      -> pluginConfigs["<name>@<mkt>"].options.<key>
  4. .credentials.json  -> pluginSecrets["<name>@<mkt>"].<key>
  5. $CCPRIVATE_HOME/conf/<name>.yaml
  6. $CCPRIVATE_HOME/skill/<name>.yaml
  7. ~/.claude/skill-config/<name>.yaml
  8. <plugin 目录>/config.yaml

用法：
    from config_env import get, require, plugin_name, diag
    v = get("tenant_domain")
    v = get("tenant_domain", "默认值")
    require("app_secret")          # 缺失时打印引导并 SystemExit(1)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

__all__ = ["get", "require", "plugin_name", "plugin_dir", "ccprivate_root",
           "diag", "source_of", "load_config"]

_CLAUDE_DIR = Path.home() / ".claude"


def _dir_from_path(p) -> Path:
    """<plugin>/references|scripts/xxx → <plugin>"""
    d = Path(p).resolve().parent
    if d.name in ("references", "scripts"):
        return d.parent
    return d


def _caller_plugin_dir() -> Path | None:
    """从调用栈里找到**第一个不在本文件所在 plugin 内**的帧所属的 plugin 根。

    ⚠️ 不能用 __file__：本模块住在 ffeishu 下，被 fpdf/fworch-case import 后
    __file__ 仍指向 ffeishu → 给别的 skill 取配置会读成 ffeishu 的。实测踩过。
    """
    own = Path(__file__).resolve()
    own_dir = own.parent
    here = own_dir
    if here.name in ("references", "scripts"):
        here = here.parent          # 本模块所属 plugin 根
    frame = sys._getframe(1)
    while frame:
        f = frame.f_globals.get("__file__")
        if f:
            fp = Path(f).resolve()
            try:
                fp.relative_to(here)
            except ValueError:
                # 该帧的代码不在本 plugin 内 → 它就是调用方
                return _dir_from_path(fp)
        frame = frame.f_back
    return None


def plugin_dir() -> Path | None:
    """定位本 plugin 根目录。

    CLAUDE_PLUGIN_ROOT 在 hook/MCP/LSP 进程里存在，但【Bash 工具与普通 python
    进程里不存在】——故必须能从调用方路径反推，否则装机后脚本不知道自己是谁。
    """
    # 1. 显式指定（跨 plugin 取值时用）
    if os.environ.get("SKILLCONF_PLUGIN_DIR"):
        p = Path(os.environ["SKILLCONF_PLUGIN_DIR"])
        if p.is_dir():
            return p
    # 2. 官方变量
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env and Path(env).is_dir():
        return Path(env)
    # 3. 从调用栈反推
    c = _caller_plugin_dir()
    if c and c.is_dir():
        return c
    # 4. 兜底：本模块所在目录（被直接当脚本用时）
    return _dir_from_path(__file__)


def _lookup_installed_name(root: Path) -> str | None:
    """反查 installed_plugins.json，把安装目录映射回 plugin 名。

    ⚠️ /plugin install 用户的 CLAUDE_PLUGIN_ROOT 是**带版本号**的 cache 目录
    （.../cache/<market>/<plugin>/<version>/），直接取 basename 会得到 "0.1.0"
    → 去查 "0.1.0@market" 的配置永远查不到。实测踩过。
    """
    reg = _CLAUDE_DIR / "plugins" / "installed_plugins.json"
    try:
        d = json.loads(reg.read_text())
    except Exception:
        return None
    want = os.path.realpath(root)
    for key, arr in (d.get("plugins") or {}).items():
        name = key.split("@", 1)[0]
        for rec in (arr if isinstance(arr, list) else [arr]):
            p = rec.get("installPath") if isinstance(rec, dict) else None
            if p and os.path.realpath(p) == want:
                return name
    # 命中不到（版本目录已被替换）→ 按 cache 布局推断 <market>/<plugin>/<version>
    parts = Path(want).parts
    if "cache" in parts:
        i = len(parts) - 1 - parts[::-1].index("cache")
        if len(parts) > i + 2:
            return parts[i + 2]
    return None


def plugin_name() -> str:
    # 显式名优先（跨 plugin 取值，如 fpdf 要读 ffeishu 的配置）
    if os.environ.get("SKILLCONF_PLUGIN_NAME"):
        return os.environ["SKILLCONF_PLUGIN_NAME"]
    d = plugin_dir()
    if not d:
        return "<plugin>"
    n = _lookup_installed_name(d)
    return n or d.name


def ccprivate_root() -> Path:
    base = os.environ.get("CCPRIVATE_HOME") or os.environ.get("CCPRIVATE_DIR")
    return Path(base) if base else Path.home() / "git" / "ccprivate"


def _yaml_load(path: Path):
    try:
        import yaml  # type: ignore
        with open(path) as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _json_load(path: Path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _dig(node, dotted: str):
    if node is None:
        return None
    for k in dotted.split("."):
        if isinstance(node, dict) and k in node:
            node = node[k]
        else:
            return None
    return node


def _official(section: str, fname: str, name: str):
    """取 pluginConfigs / pluginSecrets 里属于本 plugin 的 dict。

    key 形如 "<plugin>@<market>"；market 名用户可自定义，故不硬编码，
    按 '@' 前缀扫描匹配（--plugin-dir 场景下也接受裸 plugin 名）。
    """
    d = _json_load(_CLAUDE_DIR / fname) or {}
    sec = d.get(section) or {}
    for k in sec:
        if k == name or k.split("@", 1)[0] == name:
            return sec[k]
    return None


def _candidates(key: str):
    """产出 (源描述, 取值函数) 序列，顺序即优先级。"""
    name = plugin_name()
    pdir = plugin_dir()

    # 3/4 官方两个 JSON
    pc = _official("pluginConfigs", "settings.json", name)
    if isinstance(pc, dict):
        opts = pc.get("options", pc)
        yield "settings.pluginConfigs", lambda o=opts: _dig(o, key)
    ps = _official("pluginSecrets", ".credentials.json", name)
    if isinstance(ps, dict):
        yield "credentials.pluginSecrets", lambda o=ps: _dig(o, key)

    # 5/6 私有仓（新位置 → 旧位置）
    root = ccprivate_root()
    for sub in ("conf", "skill"):
        for ext in ("yaml", "yml", "json"):
            p = root / sub / f"{name}.{ext}"
            if not p.is_file():
                continue
            loader = _json_load if ext == "json" else _yaml_load
            yield f"ccprivate/{sub}/{name}.{ext}", lambda p=p, l=loader: _dig(l(p), key)

    # 7 旧用户级路径
    p = _CLAUDE_DIR / "skill-config" / f"{name}.yaml"
    if p.is_file():
        yield "skill-config", lambda p=p: _dig(_yaml_load(p), key)

    # 8 plugin 内旧 symlink
    if pdir:
        p = pdir / "config.yaml"
        if p.is_file():
            yield "plugin/config.yaml", lambda p=p: _dig(_yaml_load(p), key)


def _resolve(key: str):
    """返回 (值, 源描述)；未命中返回 (None, None)。"""
    # 1 显式环境变量覆盖
    envkey = "SKILLCONF_" + key.upper().replace("-", "_")
    if os.environ.get(envkey):
        return os.environ[envkey], f"env:{envkey}"

    # 2 CLAUDE_PLUGIN_DATA（官方持久目录，跨升级保留）
    name = plugin_name()
    for base in (os.environ.get("CLAUDE_PLUGIN_DATA"),
                 str(_CLAUDE_DIR / "plugins" / "data" / name)):
        if not base:
            continue
        for fname, loader in (("config.json", _json_load), ("config.yaml", _yaml_load)):
            p = Path(base) / fname
            if p.is_file():
                v = _dig(loader(p), key)
                if v not in (None, ""):
                    return v, "plugin-data"

    for tag, fn in _candidates(key):
        try:
            v = fn()
        except Exception:
            v = None
        if v not in (None, ""):
            return v, tag
    return None, None


def get(key: str, default=None):
    """取值。缺失且有 default → 返回 default；否则返回 None。"""
    v, _ = _resolve(key)
    if v in (None, ""):
        return default
    return v


def load_config(name: str | None = None) -> dict:
    """加载**整份** plugin 配置 dict（嵌套结构保留）。

    用途：脚本需要 CONF["lark_cli"]["config_dir"] 这种子结构，而不只是单键。
    按优先级找**第一个可读**的源，返回其完整 dict；找不到返回 {}。

    官方两个 JSON（pluginConfigs/pluginSecrets）会被合并进结果 —— 它们只有
    平铺的 options，但用户可能把子结构整个塞进一个键里，故原样并入。
    """
    n = name or plugin_name()
    merged: dict = {}

    # 低优先级先并入，高优先级覆盖（顺序与 _resolve 相反）
    root = ccprivate_root()
    low = [
        _CLAUDE_DIR / "skill-config" / f"{n}.yaml",
        root / "skill" / f"{n}.yaml",
        root / "conf" / f"{n}.yaml",
        root / "conf" / f"{n}.json",
    ]
    # 目标 plugin 自己的 config.yaml（按名字在 skill 仓库里找，**不能**用 __file__ ——
    # 本模块住在 ffeishu 下，用 __file__ 会把 ffeishu 的配置并进任何 plugin 的结果）。
    for base in (Path(os.environ["SKILLCONF_PLUGIN_DIR"]) if os.environ.get("SKILLCONF_PLUGIN_DIR") else None,
                 _CLAUDE_DIR / "skills" / n,
                 _dir_from_path(__file__).parent / n):
        if base and (base / "config.yaml").is_file():
            low.insert(0, base / "config.yaml")
            break
    for p in low:
        if p and Path(p).is_file():
            d = _json_load(p) if str(p).endswith(".json") else _yaml_load(p)
            if isinstance(d, dict):
                merged.update(d)

    # 官方通道覆盖
    ps = _official("pluginSecrets", ".credentials.json", n)
    if isinstance(ps, dict):
        merged.update(ps)
    pc = _official("pluginConfigs", "settings.json", n)
    if isinstance(pc, dict):
        opts = pc.get("options", pc)
        if isinstance(opts, dict):
            merged.update(opts)

    # CLAUDE_PLUGIN_DATA 最高
    for base in (os.environ.get("CLAUDE_PLUGIN_DATA"),
                 str(_CLAUDE_DIR / "plugins" / "data" / n)):
        if not base:
            continue
        for fname, loader in (("config.yaml", _yaml_load), ("config.json", _json_load)):
            p = Path(base) / fname
            if p.is_file():
                d = loader(p)
                if isinstance(d, dict):
                    merged.update(d)
    return merged


def source_of(key: str):
    """值来自哪个源（诊断用）；未命中返回 None。"""
    v, tag = _resolve(key)
    return tag if v not in (None, "") else None


def require(key: str):
    """缺失时打印"缺哪个键、去哪填"并 SystemExit(1)。"""
    v, _ = _resolve(key)
    if v not in (None, ""):
        return v
    name = plugin_name()
    print(
        f"[skillconf] 缺少配置项: {key}  (plugin: {name})\n"
        f"  三选一：\n"
        f"    a) claude plugin configure {name}@<market>     # 弹窗填（推荐）\n"
        f'    b) 写入 $CLAUDE_PLUGIN_DATA/config.json : {{"{key}": "..."}}\n'
        f"    c) 写入 {ccprivate_root()}/conf/{name}.yaml :\n"
        f"         {key}: <值>",
        file=sys.stderr,
    )
    raise SystemExit(1)


def diag(keys=None):
    """打印各源概况 + 指定键的来源（值脱敏）。"""
    name = plugin_name()
    root = ccprivate_root()
    print(f"plugin: {name}")
    print(f"  dir:    {plugin_dir()}")
    print(f"  ccpriv: {root}")
    found = []
    for tag, fn in _candidates("__nonexistent__"):
        pass
    # 逐键报告
    for k in (keys or []):
        v, tag = _resolve(k)
        if v in (None, ""):
            print(f"  {k} = (缺失)")
        else:
            s = str(v)
            shown = s if len(s) <= 12 else s[:6] + "…" + s[-2:]
            print(f"  {k} = {shown}   <- {tag}")
    return found


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "diag":
        diag(args[1:])
    elif args and args[0] == "get":
        v = get(args[1], args[2] if len(args) > 2 else None)
        print(v if v is not None else "")
        sys.exit(0 if v is not None else 1)
    else:
        print(__doc__)