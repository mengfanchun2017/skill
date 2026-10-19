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


_SUP_OR_SUB = re.compile(r"<(sup|sub)>(.*?)</\1>", re.S | re.I)


def _is_script_content(x):
    """判断 sup/sub 的内容是不是真角标。

    MinerU 有两类 sup：真角标（作者单位 "1,2"、"a"、"†"）和误判 —— 图注整段
    被逐词包成上标（实测 <sup>Figure</sup> <sup>1.</sup> <sup>Suppression</sup>
    <sup>of</sup> …）。后者按 latex 渲染会让整行缩成上标，必须还原成普通文本。
    判据：短（≤8 字符）、不含空格、且不是英文单词（真角标是数字/符号/单字母）。
    """
    x = x.strip()
    if not x or len(x) > 8 or " " in x:
        return False
    return not re.fullmatch(r"[A-Za-z]{2,}\.?", x)


def _false_positive_run(text):
    """整段被逐词包成 sup 的情况（图注误判）→ 返回 True。

    单看一个 <sup>of</sup> 和真角标难分；但 MinerU 的误判是**连成一串**的
    （图注每个词一个 sup，实测 88 号有 226 个）。一段里出现 ≥3 个 sup 且多数
    内容是英文单词，就是整段误判 —— 此时全部还原成普通文本，一个都不当角标。
    """
    found = _SUP_OR_SUB.findall(text)
    if len(found) < 3:
        return False
    words = sum(1 for _, c in found if re.fullmatch(r"[A-Za-z]{2,}\.?", c.strip()))
    return words >= len(found) * 0.5


def esc(t):
    """转义文本，但把真角标 <sup>/<sub> 还原为飞书上标语法。

    飞书 DocxXML 没有 sup/sub 标签，上标走 <latex>^{...}</latex>（实测 lark-cli
    收到 <sup>1</sup> 也会自动转成 <latex>{}^{1}</latex>）。原先直接 html.escape
    会把它变成可见的 &lt;sup&gt;1&lt;/sup&gt; 字面量（用户实测"大量 sup 裸露"）。
    """
    s = str(t)
    bad_run = _false_positive_run(s)
    s = _SUP_OR_SUB.sub(
        lambda m: (f"<latex>^{{{m.group(2)}}}</latex>" if m.group(1).lower() == "sup"
                   else f"<latex>_{{{m.group(2)}}}</latex>")
        if not bad_run and _is_script_content(m.group(2)) else m.group(2),
        s)
    # 只转义剩余文本：占位已生成的 <latex> 段，避免它的尖括号被转义
    parts = re.split(r"(<latex>.*?</latex>)", s, flags=re.S)
    return "".join(p if i % 2 else html.escape(p, quote=False) for i, p in enumerate(parts))


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


def _inline_v2(fragments, translate=None):
    """把 v2 的内联片段数组渲染成飞书行内 XML。

    v2 的段落是 fragment 列表：text / equation_inline / 其它。行内公式必须
    转成 <latex>，否则会以 "$2 5 ^ { \\circ } \\mathrm { C }$" 裸文出现
    （v1 content_list 完全没有 equation 条目 —— 实测 55 号 4 处、88 号 54 处）。
    """
    out = []
    for f in fragments or []:
        if not isinstance(f, dict):
            continue
        ft = f.get("type")
        c = f.get("content", "")
        if ft == "equation_inline":
            body = c.strip()
            if body.startswith("$") and body.endswith("$"):
                body = body[1:-1].strip()
            out.append(f"<latex>{body}</latex>")
        else:
            txt = translate(c) if translate else c
            out.append(esc(txt))
    return "".join(out)


_V2_TEXT_KEYS = {
    "paragraph": "paragraph_content", "title": "title_content",
    "page_header": "page_header_content", "page_footer": "page_footer_content",
    "page_number": "page_number_content", "aside_text": "aside_text_content",
}


def render_v2(pages, images_dir, translate=None, keep_refs=False, rel_prefix="images"):
    """用 content_list_v2 渲染（含行内公式、list、图片/表格）。

    v2 按页组织成块列表，天然带版面顺序；公式作为 equation_inline 片段保留，
    参考文献是 list(reference_list) 而不是散落的 ref_text。
    """
    out = [f"<title>{esc(translate('__title__') if translate else '__title__')}</title>"]
    seen_levels = set()

    def block_xml(e, in_grid=False):
        t = e.get("type")
        c = e.get("content") or {}
        if t in ("page_header", "page_footer", "page_number"):
            return ""
        if t in _V2_TEXT_KEYS:
            frags = c.get(_V2_TEXT_KEYS[t]) or []
            html = _inline_v2(frags, translate)
            if not html.strip():
                return ""
            if t == "title":
                lvl = c.get("level") or 2
                txt_plain = re.sub(r"<[^>]+>", "", html)
                lvl = _heading_level({"text_level": lvl, "text": txt_plain}, seen_levels) or 2
                return f"<h{lvl}>{html}</h{lvl}>"
            return f"<p>{html}</p>"
        if t == "list":
            items = c.get("list_items") or []
            is_ref = c.get("list_type") == "reference_list"
            if is_ref and not keep_refs:
                return ""
            lis = []
            for it in items:
                inner = _inline_v2(it.get("item_content") or [], translate)
                if inner.strip():
                    lis.append(f"<li>{inner}</li>")
            if not lis:
                return ""
            return "<ol>" + "".join(lis) + "</ol>" if is_ref else "<ul>" + "".join(lis) + "</ul>"
        if t == "table":
            caps = [x.get("content", "") for x in (c.get("table_caption") or [])]
            body = table_xml(c.get("html"), caps)
            return body
        if t in ("image", "chart"):
            src = (c.get("image_source") or {}).get("path")
            if not src:
                return ""
            local = Path(images_dir).parent / src
            if not local.exists():
                return ""
            caps = [x.get("content", "") for x in (c.get("image_caption")
                                                   or c.get("chart_caption") or [])]
            cap = f' caption="{esc(" ".join(caps))}"' if caps else ""
            img = f'<img path="@./{rel_prefix}/{Path(src).name}"{cap}/>'
            return img
        return ""

    for pg in pages:
        body_blocks = [e for e in pg if e.get("type") not in
                       ("page_header", "page_footer", "page_number")]
        for e in body_blocks:
            x = block_xml(e)
            if x:
                out.append(x)
    return "\n".join(x for x in out if x)


def render_v2_grid(pages, images_dir, translate=None, keep_refs=False, rel_prefix="images"):
    """v2 + 按页左右分栏（用 bbox 左边界中位数分界）。"""
    out = []
    for pg in pages:
        body = [e for e in pg if e.get("type") in
                ("paragraph", "title", "table", "image", "chart", "list") and e.get("bbox")]
        if len(body) < 3:
            out.append(render_v2([pg], images_dir, translate, keep_refs, rel_prefix)
                       .replace("<title>__title__</title>", ""))
            continue
        x0s = sorted(e["bbox"][0] for e in body)
        mid = x0s[len(x0s) // 2]
        left = [e for e in pg if not e.get("bbox") or e["bbox"][0] < mid]
        right = [e for e in pg if e.get("bbox") and e["bbox"][0] >= mid]
        if not left or not right:
            out.append(render_v2([pg], images_dir, translate, keep_refs, rel_prefix)
                       .replace("<title>__title__</title>", ""))
            continue
        lx = render_v2([left], images_dir, translate, keep_refs, rel_prefix) \
            .replace("<title>__title__</title>", "")
        rx = render_v2([right], images_dir, translate, keep_refs, rel_prefix) \
            .replace("<title>__title__</title>", "")
        out.append(f'<grid><column width-ratio="0.5">{lx}</column>'
                   f'<column width-ratio="0.5">{rx}</column></grid>')
    return "\n".join(x for x in out if x)


def _heading_level(item, seen_levels):
    """修正 MinerU 的标题层级。

    MinerU 把论文里所有小标题都标成 text_level=2（实测 88 号 17 个 h2 里
    "4.1. Microorganisms…" 这类子节应为 h3），且不跳级约束要求 h1 → h2 → h3
    连续出现。用编号模式（"2.1." 是二级、"1." 是一级）和首次出现层级推断。
    """
    lvl = item.get("text_level")
    if not lvl:
        return None
    txt = (item.get("text") or "").strip()
    if lvl == 1:
        seen_levels.add(1)
        return 1
    # 编号形态：X.Y.Z. / X.Y. / X. 决定相对深度
    m = re.match(r"^(\d+(?:\.\d+)*)\.?\s", txt)
    if m:
        depth = m.group(1).count(".") + 1
        return min(1 + depth, 4)
    seen_levels.add(2)
    return 2


def render_flow(content_list, images_dir, translate=None, keep_refs=False):
    """顺序流：按 content_list 顺序输出块，跳过 header/footer/page_number。

    keep_refs=True 时保留 ref_text（参考文献）——默认关掉是为了不让长长的
    文献表淹没正文；但用户要"原文结构完整"时它就是文档的一部分。
    """
    out = [f"<title>{esc(translate('__title__') if translate else '__title__')}</title>"]
    skip = {"header", "footer", "page_number"}
    seen_levels = set()
    for e in content_list:
        t = e.get("type")
        if t in skip:
            continue
        if t == "text":
            lvl = _heading_level(e, seen_levels)
            txt = (translate(e.get("text", "")) if translate else e.get("text", ""))
            if not txt.strip():
                continue
            if lvl and 1 <= lvl <= 4:
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
            if not keep_refs:
                continue
            txt = (translate(e.get("text", "")) if translate else e.get("text", ""))
            if txt.strip():
                out.append(f"<p>{esc(txt)}</p>")
    return "\n".join(x for x in out if x)


def render_grid_columns(content_list, images_dir, layout, translate=None, keep_refs=False):
    """按 bbox 把每页条目分左右栏，用 <grid> 输出。

    分栏线取**正文条目** bbox 的中位分界，不是全体均值：页眉页脚横跨全宽
    （实测 x0=70、x1=926 而正文只有 x0=68..504 / 502..929），把它们的中心算进
    均值会把分界线推到页面之外，判成"全部左栏"、右栏空 grid。
    """
    out = []
    cols_per_page = {int(k): v for k, v in (layout.get("columns_per_page") or {}).items()}
    pages = {}
    for e in content_list:
        pages.setdefault(e.get("page_idx", 0), []).append(e)
    for pg in sorted(pages):
        items = pages[pg]
        flow = lambda sub: render_flow(sub, images_dir, translate=translate,
                                       keep_refs=keep_refs).replace("<title>__title__</title>", "")
        # 只拿正文块定分栏线（去 header/footer/page_number）
        body = [e for e in items
                if e.get("type") in ("text", "table", "image", "chart", "equation")
                and e.get("bbox")]
        if cols_per_page.get(pg, 1) < 2 or len(body) < 2:
            out.append(flow(items))
            continue
        # 用左边界的中位数分界：左栏 x0 聚在 ~68，右栏 ~502
        x0s = sorted(e["bbox"][0] for e in body)
        mid = x0s[len(x0s) // 2]
        left = [e for e in items if e.get("bbox") and e["bbox"][0] < mid]
        right = [e for e in items if e.get("bbox") and e["bbox"][0] >= mid]
        if not left or not right:
            out.append(flow(items))
            continue
        out.append(f'<grid><column width-ratio="0.5">{flow(left)}</column>'
                   f'<column width-ratio="0.5">{flow(right)}</column></grid>')
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
    ap.add_argument("--keep-refs", action="store_true",
                    help="保留参考文献段（默认丢弃，避免长文献表淹没正文）")
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
        body = render_flow(cl, pkg["images_dir"], translate=translate,
                           keep_refs=args.keep_refs)

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