#!/usr/bin/env python3
"""DocxXML -> 打印友好 HTML（供 chromium 转 PDF）

- 保留标题层级（H1 蓝、H2/H3 黑）
- 表格 -> 真 <table>；列表 -> 嵌套 <ul>/<ol>
- 画板 -> 引用已导出的 jpg
- 生成目录（TOC）+ 分页
"""
import json, os, re, html
from xml.etree import ElementTree as ET

OUT = os.environ.get('BUILD_DIR', './pdfbuild')
BOARDS = os.path.join(OUT, 'boards')
BOOK_TITLE = os.environ.get('BOOK_TITLE', '文档合订本')
_ap = os.path.join(OUT, 'anchors.json')
ANCHORS = json.load(open(_ap, encoding='utf-8')) if os.path.exists(_ap) else {}
SLUG = {}


def slug_of(title):
    if title not in SLUG:
        SLUG[title] = 'sec' + str(len(SLUG) + 1)
    return SLUG[title]

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
* { box-sizing: border-box; }
body { font-family: "Noto Sans CJK SC","Noto Sans SC","Microsoft YaHei",sans-serif;
       font-size: 10.5pt; line-height: 1.65; color: #1f2329; margin: 0; }
h1 { font-size: 17pt; color: #245BDB; margin: 26pt 0 10pt; page-break-after: avoid;
     border-bottom: 1.5pt solid #d6e0f5; padding-bottom: 4pt; }
h2 { font-size: 13pt; color: #1f2329; margin: 18pt 0 7pt; page-break-after: avoid; }
h3 { font-size: 11.5pt; color: #1f2329; margin: 13pt 0 5pt; page-break-after: avoid; }
p { margin: 6pt 0; }
ul, ol { margin: 6pt 0 6pt 6pt; padding-left: 18pt; }
li { margin: 3pt 0; }
li > ul, li > ol { margin: 3pt 0 3pt 4pt; }
blockquote { margin: 9pt 0; padding: 7pt 11pt; background: #f5f7fb;
             border-left: 3pt solid #245BDB; color: #3a4048; }
blockquote p { margin: 0; }
a { color: #245BDB; text-decoration: none; word-break: break-all; }
table { border-collapse: collapse; width: 100%; margin: 9pt 0; font-size: 9.8pt;
        page-break-inside: avoid; }
th, td { border: 0.6pt solid #cfd6e4; padding: 5pt 7pt; vertical-align: top; text-align: left; }
th { background: #eef1f6; font-weight: 600; }
td p, th p { margin: 0; }
img.board { display: block; max-width: 100%; margin: 10pt auto; page-break-inside: avoid; }
code { font-family: "DejaVu Sans Mono",monospace; background: #f2f3f5;
       padding: 0.5pt 2.5pt; border-radius: 2pt; font-size: 9.5pt; }
pre { background: #f5f7fa; padding: 8pt; border-radius: 3pt; overflow-x: auto;
      font-size: 9pt; page-break-inside: avoid; }
/* 封面 */
.cover { height: 250mm; display: flex; flex-direction: column; justify-content: center;
         text-align: center; page-break-after: always; }
.cover h1 { border: none; font-size: 30pt; margin: 0 0 8pt; }
.cover .sub { font-size: 13pt; color: #5a6472; margin-bottom: 26pt; }
.cover .meta { font-size: 10.5pt; color: #6b7280; line-height: 2; }
.cover .box { display: inline-block; text-align: left; background: #f5f7fb;
              padding: 14pt 22pt; border-radius: 5pt; margin-top: 20pt; font-size: 10.5pt; }
/* 目录 */
.toc { page-break-after: always; }
.toc h1 { margin-top: 0; }
.toc .grp { font-weight: 600; color: #245BDB; margin: 12pt 0 4pt; font-size: 11pt; }
.toc ol { list-style: none; padding-left: 0; margin: 0; }
.toc li { margin: 2.5pt 0; font-size: 10.5pt; }
.toc .pg { color: #8a929e; }
/* 章节 */
.mk { font-size: 1pt; color: #ffffff; }
.doc { page-break-before: always; }
.doc > h1:first-child { margin-top: 0; }
.doc-tag { display: inline-block; font-size: 8.5pt; color: #245BDB; background: #eaf0fd;
           padding: 1pt 6pt; border-radius: 8pt; margin-bottom: 4pt; }
"""


def esc(t):
    return html.escape(t or '', quote=False)


def render_inline(el):
    """递归渲染行内内容"""
    out = []
    if el.text:
        out.append(esc(el.text))
    for ch in el:
        tag = ch.tag
        inner = render_inline(ch)
        if tag == 'b':
            out.append(f'<b>{inner}</b>')
        elif tag == 'em':
            out.append(f'<i>{inner}</i>')
        elif tag == 'code':
            out.append(f'<code>{inner}</code>')
        elif tag == 'a':
            href = ch.get('href', '')
            mk = re.search(r'/wiki/([A-Za-z0-9]+)', href or '')
            tok = mk.group(1) if mk else None
            if tok and tok in ANCHORS:
                sec = slug_of(ANCHORS[tok])
                out.append(f'<a class="in" href="#{sec}">{inner}</a>')
            else:
                out.append(f'<a href="{esc(href)}">{inner}</a>')
        elif tag == 'span':
            out.append(inner)
        elif tag == 'br':
            out.append('<br/>')
        else:
            out.append(inner)
        if ch.tail:
            out.append(esc(ch.tail))
    return ''.join(out)


def render_table(el, board_map):
    cols = el.find('colgroup')
    widths = [c.get('width') for c in cols] if cols is not None else []
    total = sum(int(w) for w in widths if w and w.isdigit()) or 1
    out = ['<table>']
    if widths:
        out.append('<colgroup>' + ''.join(
            f'<col style="width:{int(w)/total*100:.2f}%"/>' for w in widths if w and w.isdigit()) + '</colgroup>')
    thead = el.find('thead')
    if thead is not None:
        out.append('<thead>')
        for tr in thead.findall('tr'):
            out.append('<tr>' + ''.join(
                f'<th>{render_block_inner(td, board_map)}</th>' for td in tr) + '</tr>')
        out.append('</thead>')
    tbody = el.find('tbody')
    if tbody is not None:
        out.append('<tbody>')
        for tr in tbody.findall('tr'):
            cells = []
            for td in tr:
                cs = td.get('colspan')
                attr = f' colspan="{cs}"' if cs else ''
                cells.append(f'<td{attr}>{render_block_inner(td, board_map)}</td>')
            out.append('<tr>' + ''.join(cells) + '</tr>')
        out.append('</tbody>')
    out.append('</table>')
    return ''.join(out)


def render_block_inner(el, board_map):
    """单元格内的块（通常是 <p>）"""
    parts = []
    ps = el.findall('p')
    if ps:
        for p in ps:
            parts.append(render_inline(p))
        if not parts and el.text:
            parts.append(esc(el.text))
    else:
        parts.append(render_inline(el))
    return '<br/>'.join(x for x in parts if x)


def render_list(el, ordered, board_map):
    tag = 'ol' if ordered else 'ul'
    out = [f'<{tag}>']
    for li in el.findall('li'):
        # li 里直接文本 + 嵌套列表
        txt = render_inline(li)
        subs = ''
        for ch in li:
            if ch.tag in ('ul', 'ol'):
                inner = ch
                subs += render_list(inner, ch.tag == 'ol', board_map)
        # 清掉已渲染的子列表文本残留
        out.append(f'<li>{txt}{subs}</li>')
    out.append(f'</{tag}>')
    return ''.join(out)


def render_doc(content, board_map):
    root = ET.fromstring('<root>' + content + '</root>')
    out = []
    for el in root:
        tag = el.tag
        if tag == 'title':
            continue
        if tag == 'h1':
            out.append(f'<h1>{render_inline(el)}</h1>')
        elif tag in ('h2', 'h3'):
            out.append(f'<{tag}>{render_inline(el)}</{tag}>')
        elif tag == 'p':
            out.append(f'<p>{render_inline(el)}</p>')
        elif tag == 'blockquote':
            out.append(f'<blockquote><p>{render_block_inner(el, board_map)}</p></blockquote>')
        elif tag == 'ul':
            out.append(render_list(el, False, board_map))
        elif tag == 'ol':
            out.append(render_list(el, True, board_map))
        elif tag == 'table':
            out.append(render_table(el, board_map))
        elif tag == 'whiteboard':
            tok = el.get('token')
            p = os.path.join(BOARDS, (tok or '') + '.jpg')
            if tok and os.path.exists(p):
                out.append(f'<img class="board" src="file://{p}"/>')
        elif tag == 'pre':
            out.append(f'<pre>{esc("".join(el.itertext()))}</pre>')
    return '\n'.join(out)


def label(kind, title):
    if kind == 'root':
        return '导航'
    if kind == 'overview':
        return '总览'
    if re.match(r'wharton-business-analytics-week\d+-update$', title):
        return '单元'
    return '案例'


def main():
    docs = json.load(open(os.path.join(OUT, 'docs.json'), encoding='utf-8'))
    # 分类
    for d in docs:
        t = d['title']
        if d['kind'] == 'root':
            continue
        if t.startswith('BADTI '):
            d['kind'] = 'overview'
        elif re.match(r'wharton-business-analytics-week\d+-update$', t):
            d['kind'] = 'week'
        else:
            d['kind'] = 'case'

    # 预注册 slug（与渲染顺序一致，保证锚点稳定）
    for d in docs:
        slug_of(d['title'])

    try:
        SECP = json.load(open(os.path.join(OUT, 'secpages.json'), encoding='utf-8'))
    except Exception:
        SECP = {}

    body, toc = [], []
    toc.append('<div class="toc"><h1>目录</h1>')
    groups = [('导航与总览', [d for d in docs if d['kind'] in ('root', 'overview')]),
              ('课程单元', [d for d in docs if d['kind'] == 'week']),
              ('案例精读', [d for d in docs if d['kind'] == 'case'])]

    CN = {'week4-chevron-refineries': 'Chevron 炼油厂生产计划优化', 'week4-zara': 'Zara 全球配送网络重构', 'week5-kroger': 'Kroger 药房库存仿真优化', 'week5-intel': 'Intel 资本投资决策优化', 'week6-internal-markets': 'JR Keller：内部市场与人力配置', 'week6-paying-more': 'Matthew Bidwell：外招与内部流动', 'week8-phytopharm': 'Phytopharm 研发估值与许可谈判', 'week8-polio': '脊灰根除与集成分析模型', 'week8-bank-one': 'Bank One 信用卡额度与定价管理'}

    WEEKS = {1: '描述性分析：获取洞察', 2: '描述性分析：描述与预测未来事件', 3: '预测分析：用数据做预测', 4: '预测与规范性分析：应用与工具箱', 5: '预测分析：决策工具', 6: '预测分析：预测员工绩效', 7: '规范性分析：提供改变行为的建议', 8: '规范性分析：确定最优结果', 9: '商业分析综合应用'}

    def pretty(t):
        m = re.match(r'wharton-business-analytics-week(\d+)-update$', t)
        if m:
            w = int(m.group(1))
            return f'Week {w}　{WEEKS.get(w, "")}'.rstrip('　')
        m = re.match(r'wharton-business-analytics-(.+)-update$', t)
        if m and m.group(1) in CN:
            return CN[m.group(1)]
        return t

    for gname, items in groups:
        if not items:
            continue
        toc.append(f'<div class="grp">{gname}</div><ol>')
        for d in items:
            pg = SECP.get(slug_of(d['title']), '')
        pgtxt = f'<span class="pg">{pg}</span>' if pg else f'<span class="pg">{label(d["kind"], d["title"])}</span>'
        toc.append(f'<li><a class="in" href="#{slug_of(d["title"])}">{esc(pretty(d["title"]))}</a>{pgtxt}</li>')
        toc.append('</ol>')
    toc.append('</div>')

    for d in docs:
        html_body = render_doc(d['content'], {})
        tag = '' if d['kind'] == 'root' else f'<div class="doc-tag">{label(d["kind"], d["title"])}</div>'
        marker = f'<span class="mk">{slug_of(d["title"])}</span>'
        body.append(f'<div class="doc" id="{slug_of(d["title"])}">{marker}{tag}{html_body}</div>')

    cover = f"""<div class="cover">
      <h1>{BOOK_TITLE}</h1>
      <div class="sub">文档合订本</div>
      <div class="meta">
        <div class="box">
          <b>内容构成</b><br/>
          3 篇总览：课程总结 / 课程结构 / 知识点列表<br/>
          9 篇课程单元：Week 1 – Week 9 中文精读<br/>
          9 篇案例精读：Chevron / Zara / Kroger / Intel / Bank One 等<br/>
          <br/>
          <b>来源</b>　Wharton 商学院 · Emeritus 课程<br/>
          <b>更新</b>　中文精读 + 2024—2026 演进补写<br/>
          <b>用途</b>　上过课的同学复习使用
        </div>
      </div>
    </div>"""

    html_doc = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"/>
<title>Wharton 商业分析复习课程</title><style>{CSS}</style></head>
<body>{cover}{''.join(toc)}{''.join(body)}</body></html>"""
    p = os.path.join(OUT, 'book.html')
    open(p, 'w', encoding='utf-8').write(html_doc)
    print('wrote', p, len(html_doc), 'chars |', len(docs), 'docs')


if __name__ == '__main__':
    main()