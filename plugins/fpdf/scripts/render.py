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
    cl2 = (wd / f"{slug}.content_list_v2.json")
    ly = (wd / f"{slug}.layout.json")
    blk = (wd / f"{slug}.blocks.json")
    fm = (wd / f"{slug}.figure_map.json")
    data = {
        "markdown": md.read_text(encoding="utf-8") if md.exists() else "",
        "content_list": json.loads(cl.read_text(encoding="utf-8")) if cl.exists() else [],
        "content_list_v2": json.loads(cl2.read_text(encoding="utf-8")) if cl2.exists() else [],
        "layout": json.loads(ly.read_text(encoding="utf-8")) if ly.exists() else {},
        "blocks": json.loads(blk.read_text(encoding="utf-8")) if blk.exists() else {},
        "figure_map": json.loads(fm.read_text(encoding="utf-8")) if fm.exists() else [],
        "images_dir": wd / "images",
    }
    return data


def _ov(a, b):
    dx = min(a[2], b[2]) - max(a[0], b[0])
    dy = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, dx) * max(0.0, dy)


def build_figure_resolver_v2(pages, blocks, figure_map):
    """按**出现顺序**建立「v2 图块 → PDF 原图」映射（推荐路径）。

    为什么不按 bbox 匹配：content_list_v2 的 bbox 与 blocks.json 换算比例不一致
    （实测 x 倍 1.68、y 倍 1.34，非等比），拿 v2 bbox 去比 PDF 矩形必然错配。
    但**同一页里两者的图块顺序一致**（都按版面序），所以按序号配对即可 ——
    实测 55 号 pg3 的 3 个 v2 图块 ↔ blocks 3 个图块 ↔ 1 张 PDF 原图。
    """
    if not figure_map or not blocks:
        return (lambda pgi, idx: None), {}

    by_page = {}
    for f in figure_map:
        pg = int(re.search(r"fig_p(\d+)_", f["file"]).group(1))
        by_page.setdefault(pg, []).append(f)
    # blocks 每页图块（同坐标系）→ 用重叠面积判归属
    blk_page = {}
    for pgi, p in enumerate(blocks.get("pdf_info") or []):
        blk_page[pgi] = [b["bbox"] for b in (p.get("para_blocks") or [])
                         if b.get("type") in ("image", "chart") and b.get("bbox")]

    mapping, emitted = {}, set()

    def resolve(pgi, idx):
        """v2 第 idx 个图块（该页内序号）→ 原图文件名 / ""（已输出）/ None（回落）。"""
        figs = by_page.get(pgi) or []
        bl = blk_page.get(pgi) or []
        if not figs or idx >= len(bl):
            return None
        bbox = bl[idx]
        best, best_ov = None, 0.0
        for f in figs:
            ov = _ov(bbox, f["bbox"])
            if ov > best_ov:
                best, best_ov = f, ov
        area = max(1.0, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
        if not best or best_ov / area < 0.5:
            return None
        if best["file"] in emitted:
            return ""          # 同一张原图已输出 → 合并碎片
        emitted.add(best["file"])
        return best["file"]

    return resolve, mapping


def build_figure_resolver(pages, blocks, figure_map):
    """构造「MinerU 图块 → PDF 原图」的解析器，并把碎片合并成整图。

    MinerU 会把一页里的一张 figure（含 A/B/C/D 子图）切成多块低清截图 ——
    实测 55 号 pg3 的 5099x3390 大图被切成 3 块 617x429 缩略图，拼接关系丢失。
    做法：用**重叠面积占比**把每个图块归到覆盖它最多的原图（不依赖坐标系换算，
    因为 content_list_v2 与 blocks.json 的 bbox 比例不一致）；同一张原图下的多个
    块只输出一次（位置取覆盖它的块的第一个出现处）。

    返回 (resolver, state)：resolver(block) → 原图文件名或 None；
    state 记录每个图块是否已被 emit（避免同图重复输出）。
    """
    if not figure_map or not blocks:
        return (lambda pgi, bbox: None), {"emitted": set()}
    # 版面树按页收集图块 bbox（与 PDF 同坐标系）
    per_page = {}
    for pgi, p in enumerate(blocks.get("pdf_info") or []):
        per_page[pgi] = [b["bbox"] for b in (p.get("para_blocks") or [])
                         if b.get("type") in ("image", "chart") and b.get("bbox")]
    by_page = {}
    for f in figure_map:
        pg = int(re.search(r"fig_p(\d+)_", f["file"]).group(1))
        by_page.setdefault(pg, []).append(f)

    emitted = set()

    def resolve(pgi, bbox):
        cands = by_page.get(pgi) or []
        best, best_ov = None, 0.0
        for f in cands:
            ov = _ov(bbox, f["bbox"])
            if ov > best_ov:
                best, best_ov = f, ov
        if not best:
            return None
        area = max(1.0, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
        if best_ov / area < 0.5:      # 覆盖不足一半 → 不是这张图
            return None
        if best["file"] in emitted:    # 同图已出过 → 跳过（合并碎片）
            return ""
        emitted.add(best["file"])
        return best["file"]

    return resolve, {"emitted": emitted}


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


# 论文首页的元信息标签（PDF 里用 Bold/BdIt 字体排的）→ 渲染时补 <b>
_FRONT_LABELS = ("OPEN ACCESS", "Edited by:", "Reviewed by:", "*Correspondence:",
                 "Specialty section:", "Received:", "Accepted:", "Published:",
                 "Citation:", "Keywords:")


def _bold_labels(html, labels=_FRONT_LABELS):
    """给正文里的元信息标签加粗。

    PDF 用 HelveticaNeue-Bd/BdIt 把 "Edited by:"、"Received:" 这类标签排成粗体，
    MinerU 的 content_list 丢掉了字体信息 → 渲染出来全是细体。这里按标签名补
    <b>。先处理长标签避免 "Received:" 与 "Accepted:" 的前缀互相干扰。
    """
    for lab in sorted(labels, key=len, reverse=True):
        if lab == "OPEN ACCESS":
            html = re.sub(r"(?<![\w>])(OPEN\s+ACCESS)(?![\w<])", r"<b>\1</b>", html)
        elif lab.startswith("*Correspondence"):
            html = html.replace("*Correspondence:", "<b>*Correspondence:</b>")
        else:
            html = html.replace(lab, f"<b>{lab}</b>")
    return html


def _group_lists(blocks):
    """把切碎的 list 块按「同一栏 + 相邻」归组，返回 {id(首块): [块...]}。

    参考文献在 v2 里是逐条一个 list 块（55 号 69 条 = 69 块）。双栏页里左右栏
    条目在数组里交错（实测 pg8 左栏 A–D 在前、右栏 D–F 在后，被正文块隔开），
    因此分组键是 (栏, 邻接)：同栏且中间只隔 0–2 个非 list 块视为同一引用区。
    """
    groups, order = {}, []
    cur, cur_key = [], None
    gap = 0
    for e in blocks:
        if e.get("type") == "list":
            b = e.get("bbox") or [0, 0, 0, 0]
            # 栏判定：一栏半页宽为界；没有 bbox 时归同一组
            key = None if not e.get("bbox") else (0 if b[0] < 300 else 1)
            if cur and (gap <= 2 and (key is None or cur_key is None or key == cur_key)):
                cur.append(e)
            else:
                if cur:
                    groups[id(cur[0])] = cur
                    order.append(id(cur[0]))
                cur, cur_key = [e], key
            gap = 0
        else:
            gap += 1
    if cur:
        groups[id(cur[0])] = cur
    return groups


def _list_block_xml(blocks, translate=None, keep_refs=False):
    """把一组 list 块合成一个 <ol>/<ul>。"""
    items, numbered = [], False
    for e in blocks:
        c = e.get("content") or {}
        if c.get("list_type") == "reference_list" and not keep_refs:
            return ""
        for it in (c.get("list_items") or []):
            inner = _inline_v2(it.get("item_content") or [], translate)
            if re.match(r"^\s*\d+[.)]\s", inner):
                numbered = True
            items.append(inner)
    if not items:
        return ""
    lis = []
    for inner in items:
        t = re.sub(r"^\s*\d+[.)]\s+", "", inner) if numbered else inner
        if t.strip():
            lis.append(f"<li>{t}</li>")
    if not lis:
        return ""
    # 来源自带编号（88 号式）→ <ol> 自动编号；无编号（55 号式）→ <ul> 保留悬挂缩进
    tag = "ol" if numbered else "ul"
    return f"<{tag}>" + "".join(lis) + f"</{tag}>"


def render_v2(pages, images_dir, translate=None, keep_refs=False, rel_prefix="images",
              fig_resolve=None, front_matter=True):
    """用 content_list_v2 渲染（含行内公式、list、图片/表格）。

    v2 按页组织成块列表，天然带版面顺序；公式作为 equation_inline 片段保留，
    参考文献是 list(reference_list) 而不是散落的 ref_text。

    fig_resolve(page_idx, bbox) 由 build_figure_resolver 提供：返回 PDF 原图文件名
    （碎片合并后每张只出一次）、""（同图已出过）或 None（用 MinerU 裁切图）。
    front_matter=True 时把首页「论文信息区」渲染成引用块，并在正文（INTRODUCTION）
    前插一条分隔线 —— 用户要求：作者/OPEN ACCESS 等信息做引用，正文前加横线区分。
    """
    out = [f"<title>{esc(translate('__title__') if translate else '__title__')}</title>"]
    seen_levels = set()
    fm = {"in_front": bool(front_matter), "closed": not front_matter}

    def _is_body_start(e):
        """正文起点：首页第一个 level<=2 的 title（INTRODUCTION / 1. Introduction）。"""
        if e.get("type") != "title":
            return False
        c = e.get("content") or {}
        t = "".join(x.get("content", "") for x in (c.get("title_content") or [])
                    if isinstance(x, dict)).strip()
        return bool(re.match(r"^(?:\d+\.?\s*)?(INTRODUCTION|Introduction)\b", t))

    def block_xml(e, pgi, figidx):
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
            numbered = any(re.match(r"^\s*\d+[.)]\s", _inline_v2(
                it.get("item_content") or [], None)) for it in items)
            lis = []
            for it in items:
                inner = _inline_v2(it.get("item_content") or [], translate)
                # 条目自带编号（"1. Jiang..."）时交给 <ol> 统一编号，去掉原文前缀
                # 以免 "1. 1. Jiang"；源自带编号则保留（不加 <ol>，见下）
                if numbered:
                    inner = re.sub(r"^\s*\d+[.)]\s+", "", inner)
                if inner.strip():
                    lis.append(f"<li>{inner}</li>")
            if not lis:
                return ""
            # 原文本来就带编号的（88 号 style）用 <ol> 自动编号；55 号式无编号文献
            # 用 <ul> 保留悬挂缩进观感 —— 否则飞书会给原本无编号的文献强加 "1."
            tag = "ol" if numbered else "ul"
            return f"<{tag}>" + "".join(lis) + f"</{tag}>"
        if t == "table":
            caps = [x.get("content", "") for x in (c.get("table_caption") or [])]
            body = table_xml(c.get("html"), caps)
            return body
        if t in ("image", "chart"):
            src = None
            if fig_resolve:
                r = fig_resolve(pgi, figidx[0])
                figidx[0] += 1
                if r == "":
                    return ""          # 同张原图已输出过（碎片合并）
                src = r
            if not src:
                src = (c.get("image_source") or {}).get("path")
            if not src:
                return ""
            local = Path(images_dir).parent / src
            if not local.exists():
                return ""
            caps = [x.get("content", "") for x in (c.get("image_caption")
                                                   or c.get("chart_caption") or [])]
            cap = f' caption="{esc(" ".join(caps))}"' if caps else ""
            return f'<img path="@./{rel_prefix}/{Path(src).name}"{cap}/>'
        return ""

    for pgi, pg in enumerate(pages):
        body_blocks = [e for e in pg if e.get("type") not in
                       ("page_header", "page_footer", "page_number")]
        # 参考文献的 list 块是「每条一段」切碎的（实测 55 号 69 条 = 69 个 list 块），
        # 而且双栏页里左右栏的条目在数组里交错 —— 直接逐块输出会散成 69 个列表。
        # 合并策略：同一个引用块（相邻 ≤2 块的间隙 + 同一栏 x0）的 list 归成一组。
        groups = _group_lists(body_blocks)
        for e in body_blocks:
            # 正文起点：关掉引用块、插分隔线（论文信息区 → 正文 的分界）
            if fm["in_front"] and _is_body_start(e) and not fm["closed"]:
                fm["closed"] = True
                fm["in_front"] = False
                out.append("</blockquote>")
                out.append("<hr/>")
            if e.get("type") == "list" and id(e) in groups:
                g = groups.pop(id(e))
                x = _list_block_xml(g, translate, keep_refs)
            else:
                x = block_xml(e, pgi)
            if not x:
                continue
            if fm["in_front"] and e.get("type") == "paragraph":
                # 首页信息区各段 → 引用块内逐段；标签加粗
                if not fm.get("opened"):
                    out.append("<blockquote>")
                    fm["opened"] = True
                out.append(_bold_labels(x) if x.startswith("<p>") else x)
            else:
                out.append(x)
    # 文档无 INTRODUCTION 标题时，别留未闭合的引用块
    if fm["in_front"] and fm.get("opened"):
        out.append("</blockquote>")
    return "\n".join(x for x in out if x)


def render_v2_grid(pages, images_dir, translate=None, keep_refs=False, rel_prefix="images",
                   fig_resolve=None):
    """v2 + 按页左右分栏。只对**真双栏页**分栏，单栏页（标题页/跨栏图页）走顺序流。

    判据不是"有条目在中间"，而是看 x0 是否显著双峰：真双栏页的正文左边界聚成
    两簇（实测 ~68 与 ~502），单栏页（首页/末页）x0 连续铺满。用「左右两簇各自
    至少 2 条，且簇间距 > 页宽 25%」判定，避免把单栏标题页误切两半。
    """
    out = []
    for pgi, pg in enumerate(pages):
        body = [e for e in pg if e.get("type") in
                ("paragraph", "title", "table", "image", "chart", "list") and e.get("bbox")]
        flat = lambda p: render_v2([p], images_dir, translate, keep_refs, rel_prefix,
                                   fig_resolve) \
            .replace("<title>__title__</title>", "")
        if len(body) < 4:
            out.append(flat(pg))
            continue
        x0s = sorted(e["bbox"][0] for e in body)
        page_w = max((e["bbox"][2] for e in body), default=0)
        mid = x0s[len(x0s) // 2]
        left = [e for e in body if e["bbox"][0] < mid]
        right = [e for e in body if e["bbox"][0] >= mid]
        # 双栏须两簇都够厚且分离明显
        if len(left) < 2 or len(right) < 2 or (
                min(e["bbox"][0] for e in right) -
                max(e["bbox"][0] for e in left)) < page_w * 0.25:
            out.append(flat(pg))
            continue
        # 页眉页脚按页保留在 grid 之外（它们横跨全宽，塞进 column 会误导）
        chrome = [e for e in pg if e.get("type") in ("page_header", "page_footer")]
        out.append(f'<grid><column width-ratio="0.5">{flat(left)}</column>'
                   f'<column width-ratio="0.5">{flat(right)}</column></grid>')
        if chrome:
            continue
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
    ap.add_argument("--source", default="auto", choices=["auto", "v1", "v2"],
                    help="结构来源：auto=有 v2 用 v2（含行内公式）否则 v1")
    ap.add_argument("--out", default=None, help="输出 XML 路径（默认 stdout）")
    args = ap.parse_args()

    pkg = read_pkg(args.workdir, args.slug)
    tmap = {}
    if args.translate_map and os.path.isfile(args.translate_map):
        tmap = json.load(open(args.translate_map, encoding="utf-8"))

    def translate(s):
        return tmap.get(s, s)

    cl = pkg["content_list"]
    v2 = pkg["content_list_v2"]
    use_v2 = args.source == "v2" or (args.source == "auto" and v2)
    if not cl and not v2:
        print("ERROR: 无 content_list(.json/_v2.json)（该文档用了 flash 档，不带结构）。"
              "要排版请用 precision 档重新解析。", file=sys.stderr)
        sys.exit(2)

    title = args.title or tmap.get("__title__") or args.slug
    # 原图解析器：把一页里被 MinerU 切碎的多个图块合并回 PDF 的那张完整大图
    fig_resolve, _ = build_figure_resolver(v2, pkg["blocks"], pkg["figure_map"])
    if use_v2:
        fn = render_v2_grid if args.columns == "grid" else render_v2
        body = fn(v2, pkg["images_dir"], translate=translate, keep_refs=args.keep_refs,
                  fig_resolve=fig_resolve)
    elif args.columns == "grid":
        body = render_grid_columns(cl, pkg["images_dir"], pkg["layout"], translate,
                                   keep_refs=args.keep_refs)
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