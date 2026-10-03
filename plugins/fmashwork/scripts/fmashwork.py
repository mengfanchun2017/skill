#!/usr/bin/env python3
"""fmashwork — AI 图生 3D → 拓竹打印 工具脚本

子命令:
  check-env        检查 Python / trimesh / pymeshfix / numpy / shared_dir / config
  validate <file>  校验水密 / 体积 / 面数 / 流形
  repair <in> <out>  pymeshfix 修孔洞
  convert <in> <out> [--format fmt]  格式互转 glb/stl/obj/3mf
  info <file>      网格元信息
  pipeline <in>    validate + (repair 如需) + convert 一次性串完

设计原则:
  - 单文件 + argparse,无外部依赖除 trimesh/pymeshfix/numpy
  - 所有路径支持 WSL (/mnt/c/...) 和 Linux 原生
  - 输出 JSON 友好（方便 Claude 解析）

用法示例:
  python3 fmashwork.py check-env
  python3 fmashwork.py validate model.glb
  python3 fmashwork.py repair model.glb model_fixed.stl
  python3 fmashwork.py convert model.glb model.stl
  python3 fmashwork.py info model.3mf
  python3 fmashwork.py pipeline model.glb --output-dir ./out
"""

import argparse
import json
import os
import shlex
import sys
from pathlib import Path

# 优先从 skill 根目录读 config.yaml（symlink → ccprivate/skill/fmashwork.yaml）
SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SKILL_DIR / "config.yaml"

# 自动切入 venv（if 已由 setup.sh 建好）：隔离依赖不污染系统 python。
# 判据用 sys.prefix != sys.base_prefix——venv 的 bin/python 是指向系统 python 的 symlink，realpath 相同判不出。
_FMASHWORK_VENV = os.environ.get(
    "FMASHWORK_VENV", f"{Path.home()}/.fmashwork-venv/bin/python"
)


def _switch_to_venv() -> bool:
    """非 venv 且 venv 已建 → exec 进去，返回是否已切换；避免重复切换递归。"""
    if hasattr(sys, "base_prefix") and sys.prefix != sys.base_prefix:
        return False
    if os.path.exists(_FMASHWORK_VENV):
        os.execv(_FMASHWORK_VENV, [_FMASHWORK_VENV, *sys.argv])  # noqa: S606
    return False


def load_config():
    """加载个人配置；不存在则返回空 dict（独立用户用 config.yaml.example 自行复制）。"""
    if not CONFIG_PATH.exists():
        return {}
    try:
        import yaml

        with CONFIG_PATH.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        print(
            "  ⚠️  PyYAML 未装,无法读 config.yaml（独立用户请 `pip install pyyaml`）",
            file=sys.stderr,
        )
        return {}
    except Exception as e:
        print(f"  ⚠️  config.yaml 解析失败: {e}", file=sys.stderr)
        return {}


# -------- Phase 1: 环境检查 --------
_switch_to_venv()


def cmd_check_env(args):
    """检查 Python + 关键库 + shared_dir + config 可达性。"""
    import importlib

    print("== fmashwork 环境检查 ==\n")
    ok = True

    # Python
    v = sys.version_info
    py_ok = v >= (3, 9)
    print(f"  Python: {v.major}.{v.minor}.{v.micro} {'✅' if py_ok else '❌ 需要 3.9+'}")
    ok = ok and py_ok

    # 关键库
    libs = ["trimesh", "pymeshfix", "numpy"]
    missing = []
    for label in libs:
        try:
            m = importlib.import_module(label)
            ver = getattr(m, "__version__", "?")
            print(f"  {label}: {ver} ✅")
        except ImportError:
            print(f"  {label}: ❌ 未装")
            missing.append(label)
            ok = False

    if missing:
        # 缺依赖 → 自动跑 setup.sh 装（幂等）。唯一人工步骤是 ensurepip 缺失时那条 sudo。
        print(f"  ⚠️ 缺 {'/'.join(missing)}，自动执行 scripts/setup.sh 安装...\n")
        setup = SKILL_DIR / "scripts" / "setup.sh"
        rc = os.system(f"bash {shlex.quote(str(setup))}")
        if rc != 0:
            minor = sys.version_info.minor
            print(f"\n  ❌ setup.sh 未能自动完成。若提示缺 python3.{minor}-venv，请先执行：")
            print(f"     sudo apt-get install python3.{minor}-venv")
            print("  然后重跑本命令。")
            sys.exit(1)
        # 装完：切 venv 重跑一次 check-env 做真校验（setup 可能只装了系统 python，或装漏）
        _switch_to_venv()
        os.execv(sys.executable, [sys.executable, *sys.argv])

    # 配置
    cfg = load_config()
    if cfg:
        print(f"  config.yaml: ✅ 已加载 ({CONFIG_PATH})")
    else:
        print(f"  config.yaml: ⚠️  未找到/为空 ({CONFIG_PATH})")
        print("    → ccconfig 用户: 写 ccprivate/skill/fmashwork.yaml")
        print("    → 独立用户: cp config.yaml.example config.yaml")

    # shared_dir
    sd = cfg.get("shared_dir") if isinstance(cfg, dict) else None
    if sd:
        sd_path = Path(os.path.expanduser(sd))
        if sd_path.exists():
            print(f"  shared_dir: ✅ {sd}")
        else:
            print(f"  shared_dir: ⚠️  {sd} 路径不存在")
            print(f"    → mkdir -p {sd}")
    else:
        print("  shared_dir: ⚠️  未配置（ccprivate/skill/fmashwork.yaml 设 shared_dir）")

    # channels
    if cfg.get("channels"):
        for name, url in cfg["channels"].items():
            print(f"  channel[{name}]: {url}")

    print(f"\n{'✅ 环境就绪' if ok else '❌ 有缺失项,见上'}")
    sys.exit(0 if ok else 1)


# -------- Phase 3: 校验 --------


def cmd_validate(args):
    """校验网格：水密 / 体积 / 面数 / 流形。"""
    import trimesh

    path = Path(args.file)
    if not path.exists():
        print(f"❌ 文件不存在: {path}", file=sys.stderr)
        sys.exit(1)

    mesh = trimesh.load_mesh(path, force="mesh")
    report = {
        "file": str(path),
        "format": path.suffix.lstrip("."),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "is_watertight": bool(mesh.is_watertight),
        "is_winding_consistent": bool(mesh.is_winding_consistent),
        "volume_mm3": float(mesh.volume) if mesh.is_watertight else None,
        "bounds_mm": (
            [float(x) for x in mesh.bounds[0]] + [float(x) for x in mesh.bounds[1]]
        ),
        "euler_number": int(mesh.euler_number),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.exit_code:
        sys.exit(0 if report["is_watertight"] else 2)


# -------- Phase 4: 修复 --------


def cmd_repair(args):
    """pymeshfix 修孔洞。"""
    import pymeshfix
    import trimesh

    inp, outp = Path(args.input), Path(args.output)
    if not inp.exists():
        print(f"❌ 输入不存在: {inp}", file=sys.stderr)
        sys.exit(1)

    print(f"  loading: {inp}")
    mesh = trimesh.load_mesh(inp, force="mesh")

    print("  repairing with pymeshfix...")
    mf = pymeshfix.MeshFix(mesh.vertices, mesh.faces)
    mf.repair(verbose=True)

    fixed = trimesh.Trimesh(vertices=mf.v, faces=mf.f)
    outp.parent.mkdir(parents=True, exist_ok=True)
    fixed.export(outp)
    print(f"  ✅ 已修复: {outp}")
    print(f"     水密: {fixed.is_watertight} | 顶点数: {len(fixed.vertices)} | 面数: {len(fixed.faces)}")


# -------- Phase 5: 转换 --------


def cmd_convert(args):
    """格式互转 glb/stl/obj/3mf。"""
    import trimesh

    inp, outp = Path(args.input), Path(args.output)
    if not inp.exists():
        print(f"❌ 输入不存在: {inp}", file=sys.stderr)
        sys.exit(1)

    fmt = args.format or outp.suffix.lstrip(".")
    outp.parent.mkdir(parents=True, exist_ok=True)

    mesh = trimesh.load_mesh(inp, force="mesh")
    mesh.export(outp, file_type=fmt)
    print(f"  ✅ {inp.name} → {outp.name} (format={fmt})")
    print(f"     大小: {outp.stat().st_size / 1024:.1f} KB")


# -------- Phase info --------


def cmd_info(args):
    """网格元信息（轻量）。"""
    import trimesh

    p = Path(args.file)
    if not p.exists():
        print(f"❌ 文件不存在: {p}", file=sys.stderr)
        sys.exit(1)
    mesh = trimesh.load_mesh(p, force="mesh")
    print(json.dumps({
        "file": str(p),
        "format": p.suffix.lstrip("."),
        "size_kb": round(p.stat().st_size / 1024, 1),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "is_watertight": bool(mesh.is_watertight),
    }, indent=2, ensure_ascii=False))


# -------- Pipeline: 一次性串完 --------


def cmd_pipeline(args):
    """validate → (repair 如需) → convert 串行。"""
    import trimesh

    inp = Path(args.input)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_format = args.format or "stl"

    print(f"== pipeline: {inp.name} → {out_dir} ({out_format}) ==\n")

    # Step 1: validate
    print("[1/3] validate")
    mesh = trimesh.load_mesh(inp, force="mesh")
    is_wt = bool(mesh.is_watertight)
    print(f"  水密: {is_wt} | 面数: {len(mesh.faces)}")

    # Step 2: repair if needed
    if not is_wt and not args.skip_repair:
        print("\n[2/3] repair (非水密,触发 pymeshfix)")
        import pymeshfix

        mf = pymeshfix.MeshFix(mesh.vertices, mesh.faces)
        mf.repair(verbose=False)
        mesh = trimesh.Trimesh(vertices=mf.v, faces=mf.f)
        print(f"  修复后水密: {mesh.is_watertight} | 面数: {len(mesh.faces)}")
    else:
        print("\n[2/3] repair (跳过:已水密 或 --skip-repair)")

    # Step 3: convert
    out_path = out_dir / f"{inp.stem}.{out_format}"
    print(f"\n[3/3] convert → {out_path}")
    mesh.export(out_path, file_type=out_format)
    print(f"  ✅ 完成: {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


# -------- main --------


def main():
    p = argparse.ArgumentParser(
        prog="fmashwork",
        description="AI 图生 3D → 拓竹打印 工具脚本",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("check-env", help="环境检查")
    sp.set_defaults(func=cmd_check_env)

    sp = sub.add_parser("validate", help="校验网格")
    sp.add_argument("file")
    sp.add_argument("--exit-code", action="store_true", help="非水密返回非零退出码")
    sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("repair", help="pymeshfix 修孔洞")
    sp.add_argument("input")
    sp.add_argument("output")
    sp.set_defaults(func=cmd_repair)

    sp = sub.add_parser("convert", help="格式互转")
    sp.add_argument("input")
    sp.add_argument("output")
    sp.add_argument("--format", help="目标格式 (默认按输出文件后缀)")
    sp.set_defaults(func=cmd_convert)

    sp = sub.add_parser("info", help="网格元信息")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_info)

    sp = sub.add_parser("pipeline", help="validate + repair? + convert 一条龙")
    sp.add_argument("input")
    sp.add_argument("--output-dir", default="./out", help="输出目录 (默认 ./out)")
    sp.add_argument("--format", default="stl", help="目标格式 (默认 stl)")
    sp.add_argument("--skip-repair", action="store_true", help="跳过修复步骤")
    sp.set_defaults(func=cmd_pipeline)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
