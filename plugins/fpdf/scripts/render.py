#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""fpdf 渲染层 — 结构包 → 飞书 DocxXML。

契约：读 parse.py 产出的 <slug>.md / .content_list.json / .layout.json / images/，
输出一个完整 DocxXML 到 stdout（调用方用 lark-cli docs +create --doc-format xml 上传）。

设计原则：
    - 不重新实现解析。版式信息全部来自 content_list 的 bbox 与类型字段。
    - 表格用标准 HTML <table><colgroup><thead><tr><th>（实测唯一保留列宽的写法；
      ffeishu 旧文档里的 <lark-table rows=...> 会被渲染器丢弃列宽和多行）。
    - 分栏只在「两栏且左右栏都有实质内容」时用 <grid>；论文类双栏本来就不该
      在移动阅读的文档里保留左右并排（会挤成一团团），故默认还原为顺序流，
      仅当 --columns grid 显式要求时才输出 <grid>。

用法：
    render.py <slug> --workdir DIR [--mode original|translated] [--columns flow|grid]
    render.py <slug> --workdir DIR --translate-map map.json   # 译文替换
"""
import sys, os, json, argparse, html, re
from pathlib import Path

COLWIDTH_TOTAL = 822   # 飞书文档正文可用宽度（实测）


def esc(t):
    """转义文本，但保留 <sup>/<sub> 为飞书上标语法。

    MinerU 对论文的角标会输出 <sup>1,2</sup>（作者单位）和 <sub>…</sub>（化学式）。
    直接 html.escape 会把它变成可见的 &lt;sup&gt; 字面量（用户实测"大量 <sup>1,2</sup>
    裸露"）。飞书 DocxXML 没有 sup/sub 标签，上标走 <latex>^{...}</latex> ——
    实测 lark-cli 收到 <sup>1</sup> 也会自动转成 <latex>{}^{1}</latex>，但
    经 esc 转义后就没有这个转换机会了，故在这里先还原成 latex。
    """
    s = str(t)
    # <sup>x</sup> → <latex>^{x}</latex>；<sub>x</sub> → <latex>_{x}</latex>
    s = re.sub(r"<sup>(.*?)</sup>", r"<latex>^{\1}</latex>", s, flags=re.S | re.I)
    s = re.sub(r"<sub>(.*?)</sub>", r"<latex>_{\1}</latex>", s, flags=re.S | re.I)
    # 只转义剩余文本：先占位已生成的 <latex> 段，避免它的尖括号被转义
    parts = re.split(r"(<latex>.*?</latex>)", s, flags=re.S)
    out = []
    for i, p in enumerate(parts):
        out.append(p if i % 2 else html.escape(p, quote=False))
    return "".join(out)


def read_pkg(workdir, slug):
    wd = Path(workdir)
    md = (wd / f"{slug}.md")
    cl = (wd / f"{slug}.content_list.json")
    ly = (wd / f"{slug}.layout.json")
    data = {
        "markdown": md.read_text(encoding="utf-8") if md.exists() else "",
        "content_list": json.loads(cl.read_text(encoding="utf-8")) if cl.exists() else [],
        "layout": json.loads(ly.read_text(encoding="utf-8")) if ly.exists() else {},
        "images_dir": wd / "images",
    }
    return data


def widths_for(n):
    """n 列均分 822，余数摊到前几列。"""
    base = COLWIDTH_TOTAL // n
    rem = COLWIDTH_TOTAL - base * n
    return [base + (1 if i < rem else 0) for i in range(n)]


def table_xml(table_body, caption=None):
    """MinerU 的 table_body 是 <table><tr><td> 结构 → 规范化为带 thead/colgroup 的飞书表格。"""
    if not table_body:
        return ""
    # 行
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table_body, re.S | re.I)
    grid = []
    for r in rows:
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S | re.I)
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        if cells:
            grid.append(cells)
    if not grid:
        return ""
    ncol = max(len(r) for r in grid)
    ws = widths_for(ncol)
    out = ["<p></p>"]
    if caption:
        out.append(f'<p align="center"><b>{esc(" ".join(caption))}</b></p>')
    cg = "".join(f'<col width="{w}"/>' for w in ws)
    out.append(f"<table><colgroup>{cg}</colgroup><thead><tr>")
    head = grid[0] + [""] * (ncol - len(grid[0]))
    for c in head:
        out.append(f'<th background-color="light-gray"><p>{esc(c)}</p></th>')
    out.append("</tr></thead><tbody>")
    for r in grid[1:]:
        r = r + [""] * (ncol - len(r))
        out.append("<tr>" + "".join(f"<td><p>{esc(c)}</p></td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def image_xml(item, images_dir, rel_prefix="images"):
    p = item.get("img_path")
    if not p:
        return ""
    local = Path(images_dir).parent / p
    if not local.exists():
        return ""
    caps = item.get("image_caption") or item.get("chart_caption") or []
    cap = f' caption="{esc(" ".join(caps))}"' if caps else ""
    return f'<img path="@./{rel_prefix}/{Path(p).name}"{cap}/>'


def render_flow(content_list, images_dir, translate=None):
    """顺序流：按 content_list 顺序输出块，跳过 header/footer/page_number。"""
    out = [f"<title>{esc(translate('__title__') if translate else '__title__')}</title>"]
    skip = {"header", "footer", "page_number"}
    for e in content_list:
        t = e.get("type")
        if t in skip:
            continue
        if t == "text":
            lvl = e.get("text_level")
            txt = (translate(e.get("text", "")) if translate else e.get("text", ""))
            if not txt.strip():
                continue
            if lvl and 1 <= lvl <= 3:
                out.append(f"<h{lvl}>{esc(txt)}</h{lvl}>")
            else:
                out.append(f"<p>{esc(txt)}</p>")
        elif t == "equation":
            out.append(f'<p align="center"><code>{esc(e.get("text",""))}</code></p>')
        elif t == "table":
            out.append(table_xml(e.get("table_body"), e.get("table_caption")))
        elif t in ("image", "chart"):
            out.append(image_xml(e, images_dir))
            caps = e.get("image_caption") or e.get("chart_caption") or []
            if caps:
                out.append(f'<p align="center">{esc(" ".join(caps))}</p>')
        elif t == "ref_text":
            continue   # 参考文献归入正文时保留，见 --keep-refs
    return "\n".join(x for x in out if x)


def render_grid_columns(content_list, images_dir, layout, translate=None):
    """按 bbox 把每页条目分左右栏，用 <grid> 输出。仅适合短内容对照。"""
    out = []
    cols_per_page = {int(k): v for k, v in (layout.get("columns_per_page") or {}).items()}
    pages = {}
    for e in content_list:
        pages.setdefault(e.get("page_idx", 0), []).append(e)
    for pg in sorted(pages):
        items = pages[pg]
        if cols_per_page.get(pg, 1) < 2:
            out.append(render_flow(items, images_dir, translate=translate).replace("<title>__title__</title>", ""))
            continue
        mid = sum(e["bbox"][0] + e["bbox"][2] for e in items
                  if e.get("bbox")) / max(1, len([e for e in items if e.get("bbox")]))
        left = [e for e in items if e.get("bbox") and e["bbox"][0] < mid]
        right = [e for e in items if e.get("bbox") and e["bbox"][0] >= mid]
        lx = render_flow(left, images_dir, translate=translate).replace("<title>__title__</title>", "")
        rx = render_flow(right, images_dir, translate=translate).replace("<title>__title__</title>", "")
        out.append(f'<grid><column width-ratio="0.5">{lx}</column>'
                   f'<column width-ratio="0.5">{rx}</column></grid>')
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--title", default=None, help="文档标题（默认用 slug）")
    ap.add_argument("--columns", default="flow", choices=["flow", "grid"],
                    help="flow=顺序流(默认,推荐) / grid=按原版式左右分栏")
    ap.add_argument("--translate-map", default=None,
                    help="JSON 文件: {原文段落: 译文}；命中则替换")
    ap.add_argument("--out", default=None, help="输出 XML 路径（默认 stdout）")
    args = ap.parse_args()

    pkg = read_pkg(args.workdir, args.slug)
    tmap = {}
    if args.translate_map and os.path.isfile(args.translate_map):
        tmap = json.load(open(args.translate_map, encoding="utf-8"))

    def translate(s):
        return tmap.get(s, s)

    cl = pkg["content_list"]
    if not cl:
        print("ERROR: 无 content_list.json（该文档用了 flash 档，不带结构）。"
              "要排版请用 precision 档重新解析。", file=sys.stderr)
        sys.exit(2)

    title = args.title or tmap.get("__title__") or args.slug
    if args.columns == "grid":
        body = render_grid_columns(cl, pkg["images_dir"], pkg["layout"], translate)
    else:
        body = render_flow(cl, pkg["images_dir"], translate=translate)

    # 标题：flow/grid 统一替换 <title> 占位（render_flow 里 __title__ 会被 translate 映射）
    body = re.sub(r"<title>.*?</title>", f"<title>{esc(title)}</title>", body, count=1)
    xml = body if "<title>" in body else f"<title>{esc(title)}</title>\n{body}"
    if args.out:
        Path(args.out).write_text(xml, encoding="utf-8")
        print(f"[fpdf] rendered → {args.out} ({len(xml)} chars)", file=sys.stderr)
    else:
        print(xml)


if __name__ == "__main__":
    main()