#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["mineru-open-sdk", "pymupdf"]
# ///
"""MinerU 解析封装 — fworch-case 材料预处理用。

输入: 本地文件路径 或 URL (PDF/图片/Office/HTML)
输出: markdown 到 stdout; 图片存 --outdir (默认取文件同目录/../images 或当前目录)

自动分级:
  - ≤20 页 且 ≤10MB  → Flash API (免费, 无 token)
  - 否则            → Precision API (token, vlm 模型)
判断依据: mineru.json 的 flash_page_limit / flash_size_limit_mb; PDF 页数用 pymupdf 数。

依赖由 uv 自管（不再依赖系统 python 的 mineru 包，系统 Python 重建后就坏）:
  uv run mineru_parse.py <file_or_url> [--outdir DIR] [--model vlm|pipeline] [--force-precision]
  直接 `python3 mineru_parse.py` 也行（uv script shebang 自动拉依赖）。
"""
import sys, os, json, argparse, tempfile

# 单一实现（配置路径解析）：ffeishu 是 hub，所有 skill 的 config 工具层放它下面
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from _skillconf_boot import config_env as _ce
    _ccprivate_root = _ce.ccprivate_root
except Exception:
    def _ccprivate_root():
        from pathlib import Path
        base = os.environ.get("CCPRIVATE_HOME") or os.environ.get("CCPRIVATE_DIR")
        return Path(base) if base else Path.home() / "git" / "ccprivate"

# 配置路径解析已收敛到单一实现 config_env.py（2026-10-27）。
# 此前这里自维护 "MINERU_CONF > $CCPRIVATE_HOME/conf > $CCPRIVATE_DIR/conf > ~/git/ccprivate/conf"
# 一条回退链，与 fpdf/parse.py、fllmpack 等各自一份 —— "ccprivate 在哪"有多处实现。
def _conf_path():
    env = os.environ.get("MINERU_CONF")
    if env:
        return os.path.expanduser(env)
    # 借单一实现的路径解析（官方通道 + 私有仓，顺序统一）
    for rel in ("conf/mineru.json",):
        p = _skillconf_file(rel)
        if p:
            return p
    return os.path.expanduser(str(_ccprivate_root() / "conf" / "mineru.json"))


def _skillconf_file(rel):
    try:
        return str(_ccprivate_root() / rel) if (_ccprivate_root() / rel).is_file() else None
    except Exception:
        return None


CONF = _conf_path()


def load_conf():
    try:
        with open(CONF) as f:
            return json.load(f)
    except Exception:
        # 无 conf → 降级纯 Flash（免费档），不中断
        return {}


def pdf_pages(path):
    try:
        import pymupdf
        d = pymupdf.open(path)
        n = d.page_count
        d.close()
        return n
    except Exception:
        return None


def file_size_mb(path):
    try:
        return os.path.getsize(path) / 1e6
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="本地文件路径或 URL")
    ap.add_argument("--outdir", default=None, help="图片/资源输出目录")
    ap.add_argument("--model", default=None, help="precision 模型: vlm(默认)/pipeline")
    ap.add_argument("--force-precision", action="store_true", help="强制走 precision (复杂文档)")
    args = ap.parse_args()

    conf = load_conf()
    token = conf.get("token", "")
    flash_limit = conf.get("flash_page_limit", 20)
    size_limit = conf.get("flash_size_limit_mb", 10)

    is_url = args.source.startswith(("http://", "https://"))
    pages = None if is_url else pdf_pages(args.source)
    size_mb = None if is_url else file_size_mb(args.source)

    # 网页 URL (非文件扩展名) → precision + MinerU-HTML；Flash 不支持网页
    is_webpage = False
    if is_url:
        path = args.source.split("?")[0].split("#")[0]
        ext = os.path.splitext(path)[1].lower()
        is_webpage = ext not in (".pdf", ".png", ".jpg", ".jpeg", ".webp", ".docx", ".pptx", ".xlsx")

    use_flash = not args.force_precision and not is_webpage
    if pages is not None and pages > flash_limit:
        use_flash = False
    if size_mb is not None and size_mb > size_limit:
        use_flash = False

    local = not is_url
    if local:
        for p in (args.source, os.path.abspath(args.source)):
            if os.path.exists(p):
                args.source = os.path.abspath(p)
                break
        if not os.path.exists(args.source):
            print(f"ERROR: file not found: {args.source}", file=sys.stderr)
            sys.exit(2)

    if not use_flash and not token:
        print("ERROR: 该材料需 Precision 档（>20页/网页/强制），但未配置 MinerU token。"
              f"\n  配置: bash ccconfig/init-option.sh mineru key  （conf: {CONF}）", file=sys.stderr)
        sys.exit(3)

    from mineru import MinerU
    client = MinerU(token) if (token and not use_flash) else MinerU()
    # 网页 → MinerU-HTML model (vlm/pipeline 不能处理 html)；文件/PDF → 用户指定或 vlm
    model = "MinerU-HTML" if is_webpage else (args.model or "vlm")

    try:
        if is_webpage:
            result = client.extract(args.source, model="MinerU-HTML", timeout=300)
        elif use_flash:
            result = client.flash_extract(args.source, timeout=180)
        else:
            result = client.extract(args.source, model=model, timeout=300)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)[:500]}", file=sys.stderr)
        sys.exit(1)

    md = result.markdown or ""
    print(md)

    # 图片资源：SDK 返回 Image dataclass（.data/.name/.path），老版本可能是裸 bytes
    images = getattr(result, "images", None) or []
    if images and args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
        for i, img in enumerate(images):
            name = getattr(img, "path", None) or getattr(img, "name", None)
            ext = os.path.splitext(name)[1].lstrip(".") if name else "png"
            data = getattr(img, "data", img)
            if not isinstance(data, (bytes, bytearray)):
                print(f"WARN: 跳过未知图片格式 {type(img)}", file=sys.stderr)
                continue
            with open(os.path.join(args.outdir, f"img_{i:03d}.{ext}"), "wb") as f:
                f.write(data)

    # debug 信息到 stderr
    print(f"[mineru] mode={'flash' if use_flash else 'precision'} "
          f"pages={pages} size_mb={size_mb} chars={len(md)}", file=sys.stderr)


if __name__ == "__main__":
    main()