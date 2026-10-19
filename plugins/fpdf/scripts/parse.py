#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["mineru-open-sdk", "pymupdf", "pyyaml"]
# ///
"""fpdf 解析层 — PDF → 结构包（markdown + content_list + 图片）。

为什么独立于 fworch-case/references/mineru_parse.py：
    那个脚本是「素材转 markdown」取向（stdout 出 md，用途=喂给课程化流水线）。
    本脚本是「版式还原」取向：必须拿到 content_list 的 bbox 坐标，才能重建
    分栏/表格结构 → 交给飞书 XML 排版。两者输出契约不同，故不复用。

档位（实测差异，非猜测）：
    Flash（免费，无 token）  → 只有 markdown 纯文本，content_list=None，无图片
    Precision（token）       → markdown + content_list（带 bbox/table_body/caption）+ 图片
    ⇒ 要结构必须 Precision。--tier flash 仅供「只要纯文本、省额度」时降级。

产物布局（--outdir 下）：
    <slug>.md                 正文 markdown
    <slug>.content_list.json  结构化条目（type/bbox/page_idx/table_body/...）
    <slug>.layout.json        版式推断结果（分栏列数 per page，供排版层读）
    images/                   image/chart 类条目的图片文件
    <slug>.meta.json          来源、档位、页数、解析时间

用法：
    parse.py <pdf路径> --outdir DIR [--tier precision|flash] [--slug NAME]
    parse.py <pdf路径> --outdir DIR --dry-run    # 只打档位判定，不调 API
"""
import sys, os, json, time, argparse, re, hashlib
from pathlib import Path

CONF_CANDIDATES = [
    lambda: os.environ.get("MINERU_CONF"),
    lambda: (os.environ.get("CCPRIVATE_HOME") or os.environ.get("CCPRIVATE_DIR") or "") and
            os.path.join(os.environ.get("CCPRIVATE_HOME") or os.environ.get("CCPRIVATE_DIR"), "conf", "mineru.json"),
    lambda: os.path.expanduser("~/git/ccprivate/conf/mineru.json"),
]


def load_token():
    for cand in CONF_CANDIDATES:
        p = cand()
        if p and os.path.isfile(p):
            try:
                t = json.load(open(p)).get("token", "")
                if t and not any(m in t for m in ("请填入", "请到", "your key", "placeholder", "<your-")):
                    return t
            except Exception:
                pass
    return ""


def pdf_meta(path):
    try:
        import pymupdf
        d = pymupdf.open(path)
        n, w, h = d.page_count, [], []
        for p in d:
            r = p.rect
            w.append(round(r.width)); h.append(round(r.height))
        d.close()
        return {"pages": n, "widths": w, "heights": h}
    except Exception:
        return {"pages": None, "widths": [], "heights": []}


def detect_columns(content_list, page_w):
    """按 bbox 左边界聚类推断分栏数。

    判据：同一页里正文文本框的左边界若聚成 2+ 个明显分离的簇（间距 > 页面宽 25%），
    视为多栏。header/footer/page_number 不参与（它们横跨全宽会污染判断）。
    """
    if not page_w:
        return {}
    body = [e for e in content_list
            if e.get("type") in ("text", "table", "image", "chart", "equation")
            and isinstance(e.get("bbox"), (list, tuple)) and len(e["bbox"]) == 4]
    if not body:
        return {}
    # bbox 坐标系与 PDF 点不一致（实测 MinerU 用更宽的内部坐标，x 可超出页面点宽）
    # → 页面有效宽度取 bbox 自身的右边界，不拿 pymupdf 的页面宽度去比。
    page_w = max(e["bbox"][2] for e in body) or page_w
    cols = {}
    for e in body:
        pg = e.get("page_idx", 0)
        x0 = e["bbox"][0]
        cols.setdefault(pg, []).append(x0)
    out = {}
    for pg, xs in cols.items():
        if len(xs) < 3:
            out[pg] = 1
            continue
        xs = sorted(xs)
        gap = page_w * 0.25
        # 先按左边界切簇，再按簇内条目数过滤：居中标题/页眉这类孤立元素
        # 会自成一簇，不过滤就虚报栏数（实测单栏标题页被切成 4 簇）。
        sizes, cur_size = [], 1
        for a, b in zip(xs, xs[1:]):
            if b - a > gap:
                sizes.append(cur_size)
                cur_size = 1
            else:
                cur_size += 1
        sizes.append(cur_size)
        min_size = max(3, len(xs) * 0.15)
        out[pg] = max(1, sum(1 for s in sizes if s >= min_size))
    return out


def slugify(path):
    s = Path(path).stem
    s = re.sub(r"[^\w一-鿿-]+", "-", s).strip("-")
    return s or "document"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="本地 PDF 路径")
    ap.add_argument("--outdir", required=True, help="结构包输出目录")
    ap.add_argument("--tier", default="precision", choices=["precision", "flash"],
                    help="precision(默认,带结构) / flash(免费,仅文本)")
    ap.add_argument("--slug", default=None, help="产物命名 slug（默认取文件名）")
    ap.add_argument("--model", default="vlm", help="precision 模型 vlm/pipeline")
    ap.add_argument("--dry-run", action="store_true", help="只打档位判定，不调 API")
    args = ap.parse_args()

    if not os.path.isfile(args.source):
        print(f"ERROR: 文件不存在: {args.source}", file=sys.stderr); sys.exit(2)

    slug = args.slug or slugify(args.source)
    meta = pdf_meta(args.source)
    token = load_token()
    tier = args.tier
    if tier == "precision" and not token:
        print("ERROR: precision 档需要 MinerU token，未在 ccprivate/conf/mineru.json 找到。\n"
              "  降级: --tier flash（仅文本无结构）；或先配置 token: bash ccconfig/init-option.sh mineru key",
              file=sys.stderr)
        sys.exit(3)

    size_mb = os.path.getsize(args.source) / 1e6
    print(f"[fpdf] tier={tier} pages={meta['pages']} size={size_mb:.1f}MB slug={slug}", file=sys.stderr)

    if args.dry_run:
        print(json.dumps({"tier": tier, "pages": meta["pages"], "size_mb": round(size_mb, 2),
                          "has_token": bool(token), "slug": slug}, ensure_ascii=False))
        return

    from mineru import MinerU
    client = MinerU(token) if tier == "precision" else MinerU()
    t0 = time.time()
    try:
        if tier == "precision":
            # table/formula 显式开启：实测 vlm 默认已带表格与公式识别，但显式传
            # 保证行为确定（options 只在显式设置时才发给服务端）。
            result = client.extract(args.source, model=args.model, timeout=600,
                                    formula=True, table=True)
        else:
            result = client.flash_extract(args.source, timeout=300)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)[:500]}", file=sys.stderr)
        sys.exit(1)

    if result.state != "done":
        print(f"ERROR: 解析未完成 state={result.state} err={result.err_code} {result.error}", file=sys.stderr)
        sys.exit(1)

    outdir = Path(args.outdir)
    (outdir / "images").mkdir(parents=True, exist_ok=True)
    md = result.markdown or ""
    (outdir / f"{slug}.md").write_text(md, encoding="utf-8")

    cl = result.content_list or []
    if cl:
        (outdir / f"{slug}.content_list.json").write_text(
            json.dumps(cl, ensure_ascii=False, indent=2), encoding="utf-8")

    # 图片：SDK Image dataclass（.data/.name），文件名取自其 path
    saved = []
    for i, img in enumerate(getattr(result, "images", None) or []):
        data = getattr(img, "data", img)
        if not isinstance(data, (bytes, bytearray)):
            continue
        name = Path(getattr(img, "path", None) or getattr(img, "name", f"img_{i:03d}.png")).name
        (outdir / "images" / name).write_bytes(data)
        saved.append(name)

    # 全量产物：zip 里还有 content_list_v2（含 equation_inline）、layout.json
    # （行级 span + 置信度）、full.html（MathML 公式）。SDK 的 ExtractResult 只暴露
    # v1 markdown/content_list/图片三样 —— 不 save_all 就永远拿不到 v2 与版面树，
    # 行内公式只能以 $...$ 裸文留在正文里（实测 55 号 4 处、88 号 54 处）。
    v2_path = outdir / f"{slug}.content_list_v2.json"
    html_path = outdir / f"{slug}.html"
    blocks_path = outdir / f"{slug}.blocks.json"
    n_v2 = 0
    try:
        if getattr(result, "_zip_bytes", None):
            import zipfile, io as _io
            with zipfile.ZipFile(_io.BytesIO(result._zip_bytes)) as zf:
                for n in zf.namelist():
                    base = Path(n).name
                    if base.endswith("_content_list_v2.json") and n_v2 == 0:
                        data = json.loads(zf.read(n))
                        v2_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
                        n_v2 = sum(len(pg) for pg in data) if isinstance(data, list) else 0
                    elif base == "layout.json":
                        blocks_path.write_text(zf.read(n).decode("utf-8"), encoding="utf-8")
                    elif base.endswith(".html"):
                        html_path.write_text(zf.read(n).decode("utf-8"), encoding="utf-8")
            if not n_v2:
                v2_path.unlink(missing_ok=True)
    except Exception as e:
        print(f"[fpdf] 警告：全量产物提取失败（{type(e).__name__}: {str(e)[:120]}），"
              f"回落到 v1 content_list", file=sys.stderr)

    # 原始图：MinerU 会把一页里的一张 figure（含 A/B/C/D 子图）**切成多块**
    # 低清截图（实测 55 号 pg4 一张 5185x5094 的图被切成 4 块 617x429 的 28KB 缩略图），
    # 拼接关系丢失、分辨率掉 8 倍。PDF 里每张 figure 本身就是一张完整嵌入图，
    # 直接抽原图并按版面 bbox 建立「图块 → 原图」映射，渲染时每张原图只出一次。
    orig_map = {}          # 原图文件名 → 覆盖的 MinerU 图块数
    orig_path = outdir / f"{slug}.figure_map.json"
    try:
        import pymupdf
        doc = pymupdf.open(args.source)
        # MinerU 版面树的 bbox 与 PDF 同坐标系（实测 page_size=[595,779] 与 PDF 一致），
        # 但 content_list_v2 的 bbox 被放大过 —— 映射一律用版面树坐标。
        blocks = json.loads(blocks_path.read_text(encoding="utf-8")).get("pdf_info") \
            if blocks_path.exists() else []
        figures = []       # {page, pdf_bbox, file, size, keys:[(v2 block 坐标)]}
        for pgi, pg in enumerate(doc):
            page_figs, seen_hash = [], {}
            for x in pg.get_images(full=True):
                xr = x[0]
                info = doc.extract_image(xr)
                w, h = info["width"], info["height"]
                # 过滤装饰件：小图标（<800 宽）和极扁横条（标题下划线、表格框线，
                # 实测 88 号 pg6 有 1456x30 这种）都不是 figure
                if w < 800 or h < 200 or w / max(1, h) > 12:
                    continue
                rects = pg.get_image_rects(xr)
                if not rects:
                    continue
                # 同图多 xref（PDF 里重复嵌入，实测 88 号 pg2 内容完全相同的两张
                # 1358x286 各有 2 个 xref）→ 按内容哈希去重，只留第一个
                key = (w, h, hashlib.md5(info["image"]).hexdigest())
                if key in seen_hash:
                    continue
                r = rects[0]
                fn = f"fig_p{pgi}_x{xr}_{w}x{h}.{info['ext']}"
                (outdir / "images" / fn).write_bytes(info["image"])
                seen_hash[key] = fn
                page_figs.append({"xref": xr, "file": fn,
                                  "bbox": [round(r.x0), round(r.y0), round(r.x1), round(r.y1)],
                                  "size": f"{w}x{h}"})
            # 版面树该页的图块（用于确认覆盖关系）
            if pgi < len(blocks):
                mb = [b for b in (blocks[pgi].get("para_blocks") or [])
                      if b.get("type") in ("image", "chart") and b.get("bbox")]
                for f in page_figs:
                    fb = f["bbox"]
                    f["blocks"] = sum(
                        1 for b in mb
                        if (min(fb[2], b["bbox"][2]) - max(fb[0], b["bbox"][0])) > 0
                        and (min(fb[3], b["bbox"][3]) - max(fb[1], b["bbox"][1])) > 0)
            figures.extend(page_figs)
        doc.close()
        if figures:
            orig_map = {f["file"]: f for f in figures}
            orig_path.write_text(json.dumps(figures, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    except Exception as e:
        print(f"[fpdf] 警告：原图提取失败（{type(e).__name__}: {str(e)[:120]}），"
              f"用 MinerU 裁切图", file=sys.stderr)

    # 版式推断：用 MinerU 版面树的页宽（更贴合其 bbox 坐标系），回落 pymupdf
    widths = meta["widths"] or [0]
    page_w = max(set(widths), key=widths.count) if widths else 0
    if blocks_path.exists():
        try:
            pi = json.loads(blocks_path.read_text(encoding="utf-8")).get("pdf_info") or []
            sizes = [p.get("page_size", [0, 0])[0] for p in pi if p.get("page_size")]
            if sizes:
                page_w = max(set(sizes), key=sizes.count)
        except Exception:
            pass
    cols = detect_columns(cl, page_w) if cl else {}

    from collections import Counter
    types = dict(Counter(e.get("type") for e in cl)) if cl else {}
    (outdir / f"{slug}.meta.json").write_text(json.dumps({
        "source": os.path.abspath(args.source), "slug": slug, "tier": tier,
        "pages": meta["pages"], "size_mb": round(size_mb, 2),
        "chars": len(md), "items": len(cl), "images": len(saved),
        "item_types": types, "parse_seconds": round(time.time() - t0, 1),
        "parsed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "has_v2": bool(n_v2), "v2_items": n_v2,
        "has_html": html_path.exists(), "has_blocks": blocks_path.exists(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[fpdf] done tier={tier} chars={len(md)} items={len(cl)} v2={n_v2} "
          f"images={len(saved)} cols_pages={sum(1 for v in cols.values() if v > 1)}/{len(cols)} "
          f"{time.time() - t0:.0f}s", file=sys.stderr)
    print(json.dumps({"slug": slug, "outdir": str(outdir), "items": len(cl), "v2_items": n_v2,
                      "images": len(saved), "multi_col_pages":
                      sorted(p for p, v in cols.items() if v > 1)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()