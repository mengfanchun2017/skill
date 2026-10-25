#!/usr/bin/env python3
"""Markdown -> 飞书 DocxXML 转换器（标题配色 + 列表化排版 + 自动结构白板）

把一份 Markdown 稿转成可直接喂给 `lark-cli docs +create/+update --doc-format xml` 的 DocxXML。

用法:
    python3 md2docxxml.py <input.md> <out_name> [--root=<画板根节点名>] [--board=key=file.mmd ...]

产出:
    <脚本同目录>/gen/<out_name>.xml   （含 <title>，可 `cat xml | lark-cli ... --content -` 直接喂）

排版规则（2026-10-25 定案）:
    - 标题：H1 = 蓝色文字**无底色**；H2/H3 = 默认黑色。标题本身不加 <b>（渲染器自带加粗）
    - 正文：**不撒黑体**。<p> 里的 `**...**` 一律降级为纯文本，避免"吵闹"
    - 表格选型（按内容而非一律用表）:
        · 2 列          -> 无序列表（定义式：`<li>术语：说明</li>`）
        · 首列是步骤号  -> 有序列表
        · 3–4 列        -> 真表格（表头 light-gray）
        · ≥5 列         -> 嵌套无序列表（首列为主项，其余列为子项）—— 手机竖屏下宽表必崩
    - 列表：支持两级嵌套（按缩进）；`<li>` 允许短术语前导加粗（`<b>术语</b>：说明`），
      仅限 <= 12 字且紧跟 `：` / `-` 的术语，其余不加粗
    - 白板：从 H1/H2 大纲自动生成结构 mindmap，插在首个 H1 之前

踩过的坑（务必保留）:
    - colgroup 列宽之和必须 = 822
    - **Markdown 表格分隔行有 `|-|-|` 与 `|------|` 两种**，正则必须容忍单横线，
      否则分隔行被当数据 -> 整表错位（2026-10-25 实际踩到）
    - mermaid mindmap 缩进只可靠支持两级；节点文本禁引号/斜杠，过长会溢出（截断 ~14 字）
"""
import re, sys, os, html

TOTAL = 822
TERM_BOLD_MAX = 12


# ---------------- inline ----------------

def inline(t, term_only=False):
    """markdown 行内 -> DocxXML 行内

    排版原则：**正文不撒黑体**（"很吵闹"）。`**x**` 默认一律降级为纯文本；
    仅当 `term_only=True`（列表项）时，**行首那个 <=12 字且紧跟冒号/破折号的短术语**保留加粗。

    例：`**优点**：成本低` -> `<b>优点</b>：成本低`（保留）
        `**你有多大可能把这款产品推荐给朋友？**` -> 纯文本（过长，丢弃加粗）
        `这里是**重点**说明` -> 纯文本（不在行首，丢弃加粗）
    """
    t = html.escape(t, quote=False)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)

    m = re.match(r'^\*\*([^*]{1,%d})\*\*\s*(?=[：:—\-])' % TERM_BOLD_MAX, t) if term_only else None
    if m:
        t = f'<b>{m.group(1)}</b>' + t[m.end():]
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)   # 其余全降级
    t = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    return t


def strip_num(text):
    """剥掉手动标题编号（顿号式）——飞书自动生成目录，手写编号会重复"""
    CN = '一二三四五六七八九十'
    pat = re.compile(
        r'^\s*(?:'
        r'[' + CN + r']{1,3}[、.．)）]\s*'
        r'|[(（][' + CN + r'\d]{1,3}[)）]\s*'
        r'|\d+(?:\.\d+)*[、.．)）]\s*'
        r'|第[' + CN + r'\d]{1,3}[章节部分]\s*'
        r')'
    )
    prev = None
    while prev != text:
        prev = text
        text = pat.sub('', text, count=1)
    return text.strip()


def heading(level, text):
    text = strip_num(text)
    inner = inline(text)
    if level == 1:
        return f'<h1><span text-color="blue">{inner}</span></h1>'
    return f'<h{level}>{inner}</h{level}>'


# ---------------- 表格选型 ----------------

def _cells(row):
    r = row.strip()
    if r.startswith('|'):
        r = r[1:]
    if r.endswith('|'):
        r = r[:-1]
    return [c.strip() for c in r.split('|')]


def _is_sep(row):
    """分隔行判定：`|-|-|` `|---|---|` `|:---:|---|` 都算（容忍单横线）"""
    cs = _cells(row)
    if not cs:
        return False
    return all(re.fullmatch(r':?-+:?', c) for c in cs)


def _widths(n):
    if n <= 1:
        return [TOTAL]
    w0 = int(TOTAL * 0.30) if n == 2 else int(TOTAL * 0.26)
    rest = TOTAL - w0
    per = rest // (n - 1)
    return [w0] + [per] * (n - 2) + [rest - per * (n - 2)]


def render_table(rows):
    """把 markdown 表格按内容选最合适的形态渲染"""
    cells = [_cells(r) for r in rows]
    body = [c for c in cells if not _is_sep(r'|' + '|'.join(c) + '|')]
    if not body:
        return ''
    n = max(len(r) for r in body)
    body = [r + [''] * (n - len(r)) for r in body]
    head, data = body[0], body[1:]
    if not data:
        return ''

    # 单列 -> 列表
    if n == 1:
        return '<ul>' + ''.join(f'<li>{inline(r[0], term_only=True)}</li>' for r in data) + '</ul>'

    # 首列是步骤号（Step 0..N / 1..N / 第N步）-> 有序列表
    seqish = all(re.fullmatch(r'(?:Step\s*\d+|\d+|[第]?[一二三四五六七八九十\d]+[步阶段])',
                              r[0].strip(), re.I) for r in data)
    if seqish and n <= 3:
        items = []
        for r in data:
            if n == 2:
                items.append(inline(r[1], term_only=True))
            else:
                items.append(f"{inline(r[1], term_only=True)}：{'；'.join(inline(x) for x in r[2:] if x)}")
        return '<ol>' + ''.join(f'<li>{x}</li>' for x in items) + '</ol>'

    # 2 列 -> 定义式无序列表（手机上最易读）
    if n == 2:
        items = []
        for r in data:
            k, v = r[0].strip(), r[1].strip()
            if not k and not v:
                continue
            kb = f'<b>{inline(k)}</b>' if len(k) <= TERM_BOLD_MAX else inline(k)
            items.append(f'{kb}：{inline(v)}' if v else kb)
        return '<ul>' + ''.join(f'<li>{x}</li>' for x in items) + '</ul>'

    # ≥5 列 -> 嵌套列表（首列主项，其余列子项）
    if n >= 5:
        out = []
        for r in data:
            main = r[0].strip()
            mb = f'<b>{inline(main)}</b>' if len(main) <= TERM_BOLD_MAX else inline(main)
            subs = ''.join(f'<li>{inline(h)}：{inline(v)}</li>'
                           for h, v in zip(head[1:], r[1:]) if (h or v).strip() and v.strip())
            out.append(f'<li>{mb}{("<ul>" + subs + "</ul>") if subs else ""}</li>')
        return '<ul>' + ''.join(out) + '</ul>'

    # 3–4 列 -> 真表格
    w = _widths(n)
    o = ['<table><colgroup>' + ''.join(f'<col width="{x}"/>' for x in w) + '</colgroup>']
    o.append('<thead><tr>' + ''.join(
        f'<th background-color="light-gray"><p>{inline(h)}</p></th>' for h in head) + '</tr></thead><tbody>')
    for r in data:
        o.append('<tr>' + ''.join(f'<td><p>{inline(c)}</p></td>' for c in r) + '</tr>')
    o.append('</tbody></table>')
    return ''.join(o)


# ---------------- 列表（支持两级嵌套） ----------------

def render_list(lines, ordered):
    """lines: [(indent, text)]；按缩进做两级嵌套"""
    if not lines:
        return ''
    base = min(i for i, _ in lines)
    out, i = [], 0
    tag = 'ol' if ordered else 'ul'
    while i < len(lines):
        ind, txt = lines[i]
        if ind > base:                      # 防御：孤立子项 -> 提为同级
            out.append(f'<li>{inline(txt, term_only=True)}</li>')
            i += 1
            continue
        subs = []
        j = i + 1
        while j < len(lines) and lines[j][0] > base:
            subs.append(lines[j][1])
            j += 1
        item = inline(txt, term_only=True)
        if subs:
            item += '<ul>' + ''.join(f'<li>{inline(s, term_only=True)}</li>' for s in subs) + '</ul>'
        out.append(f'<li>{item}</li>')
        i = j
    return f'<{tag}>' + ''.join(out) + f'</{tag}>'


# ---------------- 白板 ----------------

def build_mindmap(h1_items, root):
    def clean(t):
        t = strip_num(t)
        t = re.sub(r'[（(].*?[)）]', '', t)
        t = t.replace('：', '').replace(':', '').strip()
        t = re.sub(r'["\'`/\\]', '', t)
        if len(t) > 14:
            t = t[:14].rstrip('，,、。；;的了和与及 ')
        return t or '—'

    lines = ['mindmap', '  root((' + clean(root) + '))']
    for h1, subs in h1_items:
        lines.append('    ' + clean(h1))
        for s in subs[:6]:
            lines.append('      ' + clean(s))
    return '\n'.join(lines)


def collect_outline(md):
    out, cur, first = [], None, True
    for ln in md.split('\n'):
        m = re.match(r'^(#{1,6})\s+(.*)$', ln)
        if not m:
            continue
        lvl, txt = len(m.group(1)), m.group(2).strip()
        if lvl == 1:
            if first:
                first = False
                continue
            if cur:
                out.append(cur)
            cur = (txt, [])
        elif lvl == 2 and cur:
            cur[1].append(txt)
    if cur:
        out.append(cur)
    return out


def inject_board(md):
    lines = md.split('\n')
    seen = 0
    for i, ln in enumerate(lines):
        if re.match(r'^#\s+', ln):
            seen += 1
            if seen == 1:
                lines.insert(i, '<!--whiteboard:autostruct-->')
                break
    return '\n'.join(lines)


# ---------------- 主转换 ----------------

def convert(md, boards=None):
    boards = boards or {}
    lines = md.split('\n')
    out, i, first_h1 = [], 0, True

    def para_break(nx):
        return (not nx.strip()) or re.match(r'^#{1,6}\s', nx) or nx.strip().startswith('|') \
            or nx.startswith('>') or re.match(r'^\s*[-*+]\s+', nx) \
            or re.match(r'^\s*\d+[.)]\s+', nx) or nx.startswith('```') \
            or re.match(r'^<!--\s*whiteboard', nx)

    while i < len(lines):
        s = lines[i].rstrip()

        if s.startswith('```'):
            blk = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                blk.append(lines[i]); i += 1
            i += 1
            out.append('<pre><code>' + html.escape('\n'.join(blk)) + '</code></pre>')
            continue

        m = re.match(r'^<!--\s*whiteboard:([^\s]+)\s*-->', s)
        if m:
            key = m.group(1)
            if key in boards:
                out.append('<whiteboard type="mermaid">\n' + boards[key].strip() + '\n</whiteboard>')
            i += 1
            continue

        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            lvl, txt = len(m.group(1)), m.group(2).strip()
            if lvl == 1 and first_h1:
                first_h1 = False
                i += 1
                continue
            out.append(heading(min(lvl, 3), txt))
            i += 1
            continue

        if s.strip().startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(lines[i]); i += 1
            t = render_table(rows)
            if t:
                out.append(t)
            continue

        if s.startswith('>'):
            buf = []
            while i < len(lines) and lines[i].startswith('>'):
                buf.append(lines[i].lstrip('>').strip()); i += 1
            out.append(f'<blockquote><p>{inline(" ".join(x for x in buf if x))}</p></blockquote>')
            continue

        mo = re.match(r'^(\s*)\d+[.)]\s+(.*)$', s)
        mu = re.match(r'^(\s*)[-*+]\s+(.*)$', s)
        if mo or mu:
            ordered = bool(mo)
            items = []
            while i < len(lines):
                mm = re.match(r'^(\s*)\d+[.)]\s+(.*)$', lines[i]) if ordered \
                    else re.match(r'^(\s*)[-*+]\s+(.*)$', lines[i])
                if not mm:
                    break
                items.append((len(mm.group(1)), mm.group(2).strip()))
                i += 1
            out.append(render_list(items, ordered))
            continue

        if not s.strip():
            i += 1
            continue

        buf = [s.strip()]
        i += 1
        while i < len(lines) and not para_break(lines[i]):
            buf.append(lines[i].strip()); i += 1
        out.append('<p>' + inline(' '.join(buf)) + '</p>')

    return '\n'.join(out)


def load_boards(args):
    boards = {}
    for a in args:
        if a.startswith('--board='):
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
    outline = collect_outline(md)
    if outline and 'autostruct' not in boards:
        boards['autostruct'] = build_mindmap(outline, root)
        md = inject_board(md)
    xml = convert(md, boards)
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gen')
    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, name + '.xml')
    open(p, 'w', encoding='utf-8').write('<title>' + name + '</title>\n' + xml)
    print('wrote', p, len(xml), 'chars')