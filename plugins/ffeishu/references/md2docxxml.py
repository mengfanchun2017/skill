#!/usr/bin/env python3
"""Markdown -> 飞书 DocxXML 转换器（手机竖屏 + 三级标题配色 + 自动结构白板）

把一份 Markdown 稿转成可直接喂给 `lark-cli docs +create/+update --doc-format xml` 的 DocxXML。

用法:
    python3 md2docxxml.py <input.md> <out_name> [--root=<画板根节点名>] [--board=key=file.mmd ...]

产出:
    <脚本同目录>/gen/<out_name>.xml   （含 <title>，可 `cat xml | lark-cli ... --content -` 直接喂）

能力:
    - 标题三级配色：H1 蓝底白字 / H2 蓝字 / H3 灰字（飞书只认 7 个基础色相，详见 write-checklist §2）
    - 自动剥离手动标题编号（`一、` `1.2` `(1)` `第N章`）——飞书自动生成目录，手写编号会重复
    - 手机竖屏表格：列数 > 3 时转为「分组竖排」两列表（跨列蓝底标题 + 表头/值对）
    - 自动结构 mindmap：从 H1/H2 大纲生成白板，插在首个 H1 之前
    - Markdown 内联：**粗体** / *斜体* / `代码` / [链接](url)
    - 显式白板：稿中写 `<!--whiteboard:key-->`，配合 `--board=key=file.mmd` 注入

设计约束（实飞书踩过的）:
    - colgroup 列宽之和必须 = 822
    - mermaid mindmap 缩进只可靠支持两级；节点文本禁引号/斜杠，过长会溢出（自动截断 ~14 字）
"""
import re, sys, os, json, html

# 手机竖屏：目标列宽总和 822，但每列不超过 ~280（约 12 个中文字）
MAXCOL = 280
TOTAL = 822


def esc(t):
    t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    t = t.replace('**', '\x00B\x00')  # protect marker
    return t


def inline(t):
    """markdown inline -> DocxXML inline"""
    t = html.escape(t, quote=False)
    # links
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    # bold
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    # italic
    t = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', t)
    # code
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    return t


CN_NUM = '一二三四五六七八九十'
NUM_PREFIX = re.compile(
    r'^\s*(?:'
    r'[' + CN_NUM + r']{1,3}[、.．)）]\s*'          # 一、二. 三）
    r'|[(（][' + CN_NUM + r'\d]{1,3}[)）]\s*'       # (1) （二）
    r'|\d+(?:\.\d+)*[、.．)）]\s*'                   # 1. 1.1 1)
    r'|第[' + CN_NUM + r'\d]{1,3}[章节部分]\s*'      # 第1章
    r')'
)


def strip_num(text):
    """剥掉手动标题编号（顿号式）——飞书自动生成目录，手写编号会重复"""
    prev = None
    while prev != text:
        prev = text
        text = NUM_PREFIX.sub('', text, count=1)
    return text.strip()


def heading_xml(level, text, doc_title=None):
    text = strip_num(text)
    inner = inline(text)
    if level == 1:
        return f'<h1><span background-color="blue"><b>{inner}</b></span></h1>'
    if level == 2:
        return f'<h2><span text-color="blue"><b>{inner}</b></span></h2>'
    return f'<h3><span text-color="gray"><b>{inner}</b></span></h3>'


def col_widths(n):
    """手机竖屏列宽：总和 822；首列约 30%，其余均分"""
    if n <= 1:
        return [TOTAL]
    w0 = int(TOTAL * 0.30) if n == 2 else int(TOTAL * 0.26)
    rest = TOTAL - w0
    per = rest // (n - 1)
    w = [w0] + [per] * (n - 2) + [rest - per * (n - 2)]
    return w


def _split_row(r):
    r = r.strip()
    if r.startswith('|'): r = r[1:]
    if r.endswith('|'): r = r[:-1]
    return [c.strip() for c in r.split('|')]


def parse_md_table(rows, maxcol=3):
    """Markdown 表 -> DocxXML。

    手机竖屏优化：列数 <= maxcol 时保持横向表；> maxcol 时转为
    「分组竖排」两张列表（每行原始记录 = 一个跨列小节 + 字段/值对）。
    """
    cells = [_split_row(r) for r in rows]
    body = [c for c in cells if not all(re.fullmatch(r':?-{2,}:?', x or '-') for x in c)]
    if not body:
        return ''
    ncol = max(len(r) for r in body)
    body = [r + [''] * (ncol - len(r)) for r in body]
    head, data = body[0], body[1:]

    if ncol > maxcol:
        return _vertical_table(head, data)

    widths = col_widths(ncol)
    out = ['<table><colgroup>' + ''.join(f'<col width="{w}"/>' for w in widths) + '</colgroup>']
    out.append('<thead><tr>' + ''.join(
        f'<th background-color="light-gray"><p>{inline(c)}</p></th>' for c in head) + '</tr></thead>')
    out.append('<tbody>')
    for r in data:
        out.append('<tr>' + ''.join(f'<td><p>{inline(c)}</p></td>' for c in r) + '</tr>')
    out.append('</tbody></table>')
    return ''.join(out)


def _vertical_table(head, data):
    """宽表 -> 手机竖屏分组布局：每条记录一个跨列标题 + 字段/值两列"""
    w = [240, TOTAL - 240]
    out = ['<table><colgroup>' + ''.join(f'<col width="{x}"/>' for x in w) + '</colgroup><tbody>']
    for r in data:
        label = r[0] or '—'
        out.append(f'<tr><td colspan="2" background-color="light-blue"><p><b>{inline(label)}</b></p></td></tr>')
        for h, v in zip(head[1:], r[1:]):
            if not (h or v).strip():
                continue
            out.append(f'<tr><td><p>{inline(h)}</p></td><td><p>{inline(v)}</p></td></tr>')
    out.append('</tbody></table>')
    return ''.join(out)


def build_mindmap(h1_items, leaf_items):
    """从 H1/H2 结构生成 mermaid mindmap（飞书画板）。

    飞书 mindmap 只支持两层节点缩进可靠渲染，故 H1 -> H2 两级。
    """
    def clean(t):
        t = strip_num(t)
        t = re.sub(r'[（(].*?[)）]', '', t)
        t = t.replace('：', '').replace(':', '').strip()
        # mermaid 标签内引号/斜杠会破坏语法
        t = re.sub(r'["\'`/\\]', '', t)
        if len(t) > 14:
            t = t[:14].rstrip('，,、。；;的了和与及 ')
        return t or '—'

    lines = ['mindmap', '  root((' + clean(leaf_items) + '))']
    for h1, subs in h1_items:
        lines.append('    ' + clean(h1))
        for s in subs[:6]:
            lines.append('      ' + clean(s))
    return '\n'.join(lines)


def collect_outline(md):
    """收集 H1（跳过首个标题）与每个 H1 下的 H2"""
    out = []
    cur = None
    for ln in md.split('\n'):
        m = re.match(r'^(#{1,6})\s+(.*)$', ln)
        if not m: continue
        lvl, txt = len(m.group(1)), m.group(2).strip()
        if lvl == 1:
            if not out and cur is None and not out:
                cur = None  # 首行标题（文档名）跳过
                out.append(None)  # sentinel
                continue
            if cur is not None:
                out.append(cur)
            cur = (txt, [])
        elif lvl == 2 and cur is not None:
            cur[1].append(txt)
    if cur is not None:
        out.append(cur)
    return [x for x in out if x]


def inject_board(md, board_text, before_h1_idx=1):
    """在指定第 n 个 H1 前插入 <!--whiteboard:key--> 标记"""
    lines = md.split('\n')
    seen = 0
    for i, ln in enumerate(lines):
        if re.match(r'^#\s+', ln):
            seen += 1
            if seen == before_h1_idx:
                lines.insert(i, '<!--whiteboard:autostruct-->')
                break
    return '\n'.join(lines)


def convert(md, boards=None, drop_title_h1=True, maxcol=3):
    lines = md.split('\n')
    out = []
    i = 0
    boards = boards or {}
    first_h1_seen = False

    while i < len(lines):
        ln = lines[i]
        s = ln.rstrip()

        # fenced code
        if s.startswith('```'):
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                block.append(lines[i]); i += 1
            i += 1
            out.append('<pre><code>' + html.escape('\n'.join(block)) + '</code></pre>')
            continue

        # whiteboard marker
        m = re.match(r'^<!--\s*whiteboard:([^\s]+)\s*-->', s)
        if m:
            key = m.group(1)
            if key in boards:
                out.append('<whiteboard type="mermaid">\n' + boards[key].strip() + '\n</whiteboard>')
            i += 1
            continue

        # heading
        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            lvl = len(m.group(1))
            txt = m.group(2).strip()
            if lvl == 1 and drop_title_h1 and not first_h1_seen:
                first_h1_seen = True
                i += 1
                continue
            lvl = min(lvl, 3)
            out.append(heading_xml(lvl, txt))
            i += 1
            continue

        # table
        if s.strip().startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(lines[i]); i += 1
            out.append(parse_md_table(rows, maxcol))
            continue

        # blockquote
        if s.startswith('>'):
            buf = []
            while i < len(lines) and lines[i].startswith('>'):
                buf.append(lines[i].lstrip('>').strip()); i += 1
            txt = ' '.join(x for x in buf if x)
            out.append(f'<blockquote><p>{inline(txt)}</p></blockquote>')
            continue

        # ordered list
        if re.match(r'^\s*\d+[.)]\s+', s):
            items = []
            while i < len(lines) and re.match(r'^\s*\d+[.)]\s+', lines[i]):
                items.append(re.sub(r'^\s*\d+[.)]\s+', '', lines[i]).strip()); i += 1
            out.append('<ol>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ol>')
            continue

        # unordered list
        if re.match(r'^\s*[-*+]\s+', s):
            items = []
            while i < len(lines) and re.match(r'^\s*[-*+]\s+', lines[i]):
                items.append(re.sub(r'^\s*[-*+]\s+', '', lines[i]).strip()); i += 1
            out.append('<ul>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ul>')
            continue

        # blank
        if not s.strip():
            i += 1
            continue

        # paragraph (join continuation lines)
        buf = [s.strip()]
        i += 1
        while i < len(lines):
            nx = lines[i]
            if not nx.strip(): break
            if re.match(r'^(#{1,6})\s', nx) or nx.strip().startswith('|') \
               or nx.startswith('>') or re.match(r'^\s*[-*+]\s+', nx) \
               or re.match(r'^\s*\d+[.)]\s+', nx) or nx.startswith('```') \
               or re.match(r'^<!--\s*whiteboard', nx):
                break
            buf.append(nx.strip()); i += 1
        out.append('<p>' + inline(' '.join(buf)) + '</p>')

    return '\n'.join(out)


def load_boards(args):
    boards = {}
    for a in args:
        if a.startswith('--board'):
            _, name, path = a.split('=', 2)
            boards[name] = open(path, encoding='utf-8').read()
    return boards


if __name__ == '__main__':
    src, name = sys.argv[1], sys.argv[2]
    rest = sys.argv[3:]
    root = name
    for a in list(rest):
        if a.startswith('--root='):
            root = a.split('=', 1)[1]; rest.remove(a)
    boards = load_boards(rest)
    md = open(src, encoding='utf-8').read()
    # 自动结构图：从 H1/H2 大纲生成 mindmap，插在第一个 H1 之前
    outline = collect_outline(md)
    if outline and 'autostruct' not in boards:
        boards['autostruct'] = build_mindmap(outline, root)
        md = inject_board(md, 'autostruct')
    xml = convert(md, boards)
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gen')
    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, name + '.xml')
    open(p, 'w', encoding='utf-8').write('<title>' + name + '</title>\n' + xml)
    print('wrote', p, len(xml), 'chars')