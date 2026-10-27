#!/usr/bin/env python3
"""fllmpack — LLM 预设配置导出/导入。key 不进包，接收方自己填。

导出物自包含：presets.json + README.md + 本脚本副本，收件方无需装 skill 即可导入。
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

HOME = Path.home()
CCCONFIG = Path(os.environ.get("CCCONFIG_ROOT", HOME / "git/ccconfig"))

# "ccprivate 在哪"收敛到单一实现（2026-10-27）；此前这里用 .get("CCPRIVATE_HOME", ...)
# 只认一个变量名，而 CCDIR/别的 skill 还认 CCPRIVATE_DIR → 三套名字并存。
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ffeishu", "references"))
try:
    from config_env import ccprivate_root as _ccprivate_root
    CCPRIVATE = _ccprivate_root()
except Exception:
    CCPRIVATE = Path(os.environ.get("CCPRIVATE_HOME")
                     or os.environ.get("CCPRIVATE_DIR")
                     or HOME / "git/ccprivate")

NORMAL_FILE = CCCONFIG / "conf/llmnormal.json"
PRIVATE_FILE = CCPRIVATE / "conf/llmprivate.json"
KEYS_FILE = CCPRIVATE / "conf/llm.json"
CURRENT_FILE = HOME / ".claude/llm-current"

# 字段名精确匹配 + 后缀匹配（避免 max_context_tokens 这类含 "token" 的良性字段被误剥）
SECRET_EXACT = {"key", "apikey", "api_key", "token", "secret", "password", "passwd"}
SECRET_SUFFIX = ("_key", "_token", "_secret", "_password", "_apikey")
SAFE_FIELDS = {"max_context_tokens"}


def is_secret_field(name: str) -> bool:
    k = name.lower()
    if k in SAFE_FIELDS:
        return False
    return k in SECRET_EXACT or k.endswith(SECRET_SUFFIX)
IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
HOST_RE = re.compile(r"^(https?://)([^/]+)")


def default_out_dir() -> Path:
    env = os.environ.get("FLLMPACK_OUT")
    if env:
        return Path(env).expanduser()
    if Path("/mnt/c").is_dir():
        return Path("/mnt/c/claudepack")
    return HOME / "claudepack"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"读取失败 {path}: {e}")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def collect_defs() -> dict:
    """合并内置(llmnormal)+自定义(llmprivate)预设定义。两者均不含 key。"""
    out: dict = {}
    for path, tag in ((NORMAL_FILE, "builtin"), (PRIVATE_FILE, "custom")):
        for name, d in load_json(path).get("llms", {}).items():
            if not isinstance(d, dict):
                continue
            cur = out.setdefault(name, {})
            cur.update(d)
            cur["_src"] = tag
    return out


def load_keys() -> dict:
    return {n: v for n, v in load_json(KEYS_FILE).get("llms", {}).items() if isinstance(v, dict)}


def current_preset() -> str:
    if CURRENT_FILE.exists():
        return CURRENT_FILE.read_text(encoding="utf-8").strip()
    return ""


def sanitize(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if is_secret_field(k):
            out[k] = "<your-key>"
        elif isinstance(v, str) and k in ("base_url", "url"):
            v = HOST_RE.sub(lambda m: m.group(1) + "<your-llm-host>", v)
            out[k] = IP_RE.sub("<your-llm-ip>", v)
        elif k == "host_header":
            out[k] = "<your-llm-host>"
        else:
            out[k] = v
    return out


def strip_secrets(d: dict) -> dict:
    return {k: v for k, v in d.items() if not is_secret_field(k)}


README_TMPL = """# LLM 预设配置包

导出时间：{exported}
预设数量：{count}（{names}）

**本包不含任何 API key**，导入后请填自己的 key。

## 导入（两种方式）

### 一、装了 fllmpack skill（ccconfig 用户）
```bash
python3 ~/.claude/skills/fllmpack/llmpack.py import presets.json
```

### 二、没装 skill（本包自带脚本，推荐）
```bash
python3 fllmpack.py import presets.json
```

导入会：把预设写入本机 `ccprivate/conf/llmprivate.json`（自动备份），
并在 `ccprivate/conf/llm.json` 里为每个预设建一条空 key 记录。

## 填 key
导入时脚本会交互式询问；若跳过，事后补：
```bash
bash ~/git/ccconfig/lib/init-llm.sh add     # 或 edit <预设名>
```
或直接编辑 `~/git/ccprivate/conf/llm.json`。

## 切换使用
```bash
bash ~/git/ccconfig/lib/init-llm.sh list
bash ~/git/ccconfig/lib/init-llm.sh <预设名>
```
切完**重启 Claude Code session**（env 在启动时读入）。
"""


def readme_text(meta: dict, names: list) -> str:
    return README_TMPL.format(exported=meta["exported"], count=len(names), names=", ".join(names))


def cmd_export(args) -> None:
    defs = collect_defs()
    if not defs:
        sys.exit(f"未找到预设定义。检查路径：\n  {NORMAL_FILE}\n  {PRIVATE_FILE}")
    names = args.preset or sorted(defs)
    missing = [n for n in names if n not in defs]
    if missing:
        sys.exit(f"未知预设：{', '.join(missing)}")

    pack = {}
    for n in names:
        d = strip_secrets(dict(defs[n]))
        d.pop("_src", None)
        if args.sanitize:
            d = sanitize(d)
        pack[n] = d

    meta = {
        "tool": "fllmpack",
        "version": 1,
        "exported": datetime.now().astimezone().isoformat(timespec="seconds"),
        "note": "仅含预设定义，不含任何 API key。导入方自行填 key。",
        "sanitized": bool(args.sanitize),
        "source_current": current_preset() if current_preset() in pack else "",
    }

    out_dir = Path(args.out).expanduser() if args.out else default_out_dir()
    if args.dry_run:
        print(f"[dry-run] 输出目录：{out_dir}")
        print(f"[dry-run] 预设：{', '.join(names)}")
        return

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    packdir = out_dir / f"llm-pack-{ts}"
    packdir.mkdir(parents=True, exist_ok=False)
    (packdir / "presets.json").write_text(
        json.dumps({"_meta": meta, "llms": pack}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    (packdir / "README.md").write_text(readme_text(meta, names), encoding="utf-8")
    shutil.copy2(Path(__file__).resolve(), packdir / "fllmpack.py")

    tarball = out_dir / f"llm-pack-{ts}.tar.gz"
    with tarfile.open(tarball, "w:gz") as t:
        t.add(packdir, arcname=packdir.name)

    print(f"导出完成：{len(names)} 个预设，不含 key")
    for n in names:
        print(f"  - {n}")
    print(f"\n目录：{packdir}")
    print(f"压缩包：{tarball}")
    print(f"\n发给同事：{'（已脱敏内网地址）' if args.sanitize else tarball.name}")


def resolve_pack_file(p: Path) -> Path:
    if p.is_dir():
        return p / "presets.json"
    if p.name.endswith(".tar.gz") or p.suffix in (".tgz", ".gz"):
        tmp = Path(tempfile.mkdtemp(prefix="fllmpack-"))
        with tarfile.open(p, "r:gz") as t:
            t.extractall(tmp)
        for f in tmp.rglob("presets.json"):
            return f
        sys.exit(f"压缩包里没找到 presets.json：{p}")
    return p


def cmd_import(args) -> None:
    src = Path(args.file).expanduser()
    if not src.exists():
        sys.exit(f"文件不存在：{src}")
    pack_file = resolve_pack_file(src)
    pack = load_json(pack_file)
    llms = pack.get("llms", {})
    if not llms:
        sys.exit("包里没有预设（llms 为空）")

    names = args.preset or sorted(llms)
    unknown = [n for n in names if n not in llms]
    if unknown:
        sys.exit(f"包里没有这些预设：{', '.join(unknown)}")

    insecure = CCPRIVATE.exists()
    target = PRIVATE_FILE if insecure else HOME / ".claude/fllmpack/presets.json"

    existing = load_json(target).get("llms", {})
    added, overwritten, skipped = [], [], []
    for n in names:
        d = strip_secrets(dict(llms[n]))
        d.pop("_src", None)
        if n in existing:
            (overwritten if args.overwrite else skipped).append(n)
            if not args.overwrite:
                continue
        else:
            added.append(n)
        existing[n] = d

    imported = added + overwritten
    if args.dry_run:
        print(f"[dry-run] 目标：{target}")
        print(f"[dry-run] 新增：{added or '无'}")
        print(f"[dry-run] 覆盖：{overwritten or '无'}")
        print(f"[dry-run] 跳过（已存在，加 --overwrite 覆盖）：{skipped or '无'}")
        return

    if not imported:
        print(f"没有可导入的预设（全部已存在）：{', '.join(skipped)}")
        return

    if target.exists() and target == PRIVATE_FILE:
        shutil.copy2(target, target.with_suffix(".json.bak"))
        print(f"已备份：{target.with_suffix('.json.bak')}")

    write_json(target, {"llms": existing})
    print(f"预设已写入：{target}")
    for n in added:
        print(f"  + {n}")
    for n in overwritten:
        print(f"  ~ {n}（覆盖）")
    if skipped:
        print(f"  跳过：{', '.join(skipped)}")

    if target == PRIVATE_FILE:
        keys = load_json(KEYS_FILE).get("llms", {})
        for n in imported:
            entry = keys.setdefault(n, {})
            entry.setdefault("key", "")
        write_json(KEYS_FILE, {"llms": keys})
        print(f"已在 {KEYS_FILE} 为 {len(imported)} 个预设建空 key 记录")
    else:
        print(f"⚠ 未找到 ccprivate，预设写到 {target}。"
              "若要接入 ccconfig 的 LLM 菜单，请把内容手工并入 llmprivate.json / llm.json。")

    if not args.no_key_prompt and sys.stdin.isatty():
        print("\n填 key（直接回车跳过）：")
        filled = {}
        for n in imported:
            k = getpass.getpass(f"  {n} key: ").strip()
            if k:
                filled[n] = k
        if filled and target == PRIVATE_FILE:
            keys = load_json(KEYS_FILE).get("llms", {})
            for n, k in filled.items():
                keys.setdefault(n, {})["key"] = k
            write_json(KEYS_FILE, {"llms": keys})
            print(f"已写入 {len(filled)} 个 key")

    if args.set_current and args.set_current in imported:
        CURRENT_FILE.parent.mkdir(parents=True, exist_ok=True)
        CURRENT_FILE.write_text(args.set_current + "\n", encoding="utf-8")
        print(f"当前预设已设为：{args.set_current}")

    print("\n下一步：")
    print("  bash ~/git/ccconfig/lib/init-llm.sh list        # 看预设")
    print("  bash ~/git/ccconfig/lib/init-llm.sh <预设名>     # 切换（需填好 key）")
    print("  切换后重启 Claude Code session")


def cmd_list(args) -> None:
    defs = collect_defs()
    keys = load_keys()
    cur = current_preset()
    if not defs:
        sys.exit(f"未找到预设定义：{NORMAL_FILE} / {PRIVATE_FILE}")
    print(f"{'':2} {'预设':<18} {'来源':<8} {'key':<5} base_url")
    for n in sorted(defs):
        d = defs[n]
        mark = "*" if n == cur else " "
        has = "✓" if keys.get(n, {}).get("key") else "-"
        print(f"{mark:2} {n:<18} {d.get('_src',''):<8} {has:<5} {d.get('base_url','')}")
    print("\n* = 当前预设")


def cmd_status(args) -> None:
    print(f"ccconfig    : {CCCONFIG}  {'✓' if CCCONFIG.exists() else '✗ 缺失'}")
    print(f"ccprivate   : {CCPRIVATE}  {'✓' if CCPRIVATE.exists() else '✗ 缺失'}")
    print(f"内置预设    : {NORMAL_FILE}  {'✓' if NORMAL_FILE.exists() else '✗'}")
    print(f"自定义预设  : {PRIVATE_FILE}  {'✓' if PRIVATE_FILE.exists() else '✗'}")
    print(f"key 文件    : {KEYS_FILE}  {'✓' if KEYS_FILE.exists() else '✗'}")
    print(f"当前预设    : {current_preset() or '(未设置)'}")
    print(f"默认输出目录: {default_out_dir()}")
    defs = collect_defs()
    keys = load_keys()
    print(f"预设总数    : {len(defs)}（已配 key {sum(1 for n in defs if keys.get(n,{}).get('key'))}）")


def main() -> None:
    ap = argparse.ArgumentParser(prog="fllmpack", description="LLM 预设配置导出/导入（key 不导出）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("export", help="导出预设定义（无 key）")
    e.add_argument("--out", help="输出目录（默认 C:\\claudepack → /mnt/c/claudepack）")
    e.add_argument("--preset", action="append", help="只导出指定预设，可重复")
    e.add_argument("--sanitize", action="store_true", help="额外脱敏内网 base_url/IP（给公司外的人）")
    e.add_argument("--dry-run", action="store_true")
    e.set_defaults(func=cmd_export)

    i = sub.add_parser("import", help="导入预设包")
    i.add_argument("file", help="presets.json / llm-pack-*.tar.gz / 解压后的目录")
    i.add_argument("--preset", action="append", help="只导入指定预设，可重复")
    i.add_argument("--overwrite", action="store_true", help="覆盖同名已有预设（默认跳过）")
    i.add_argument("--set-current", metavar="NAME", help="导入后设为当前预设")
    i.add_argument("--no-key-prompt", action="store_true", help="不交互询问 key")
    i.add_argument("--dry-run", action="store_true")
    i.set_defaults(func=cmd_import)

    l = sub.add_parser("list", help="列出预设及 key 状态")
    l.set_defaults(func=cmd_list)

    s = sub.add_parser("status", help="显示路径与配置状态")
    s.set_defaults(func=cmd_status)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()