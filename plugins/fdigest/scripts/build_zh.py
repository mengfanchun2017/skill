#!/usr/bin/env python3
"""fdigest build-zh — 把 SEC 式定位 HTML 的抽取结果重建为结构化飞书 DocxXML。

与 render_zh.py（逐页文本流）的区别：这里按**版面坐标还原结构**——
标题按字号分层、段落按行距合并、表格按 <table> 原样还原。
产出是一份可读的在线中文文档，不是"每页的字"。

结构还原规则（均由实测分布标定）：
    - 行距：同段落内 11.4pt；≥20.4pt 为段落分界（gap 直方图的头两个峰）
    - 字号：≥18 章 / 14-17 节 / 12-13 小节 / <12 正文
    - 页眉页脚：y<40 或 y>700，直接丢弃
    - 页码 / "Table of Contents" 行：丢弃
    - 表格页：<table> 还原为真表格，对应的散行单元格丢弃

译文对齐：zh/*.json 缓存是「筛后行」的逐行译文。行筛选规则必须与 translate.py
完全一致，否则下标错位；这里复用同一函数（_filter_lines）。
"""
import argparse
import json
import os
import re
import sys

COLWIDTH_TOTAL = 822
HEADER_Y = 40.0          # 页眉上界
FOOTER_Y = 700.0         # 页脚下界
PARA_GAP = 20.0          # 段落分界行距（实测峰 11.4 / 20.4）
HEAD_SIZES = [(18, 1), (14, 2), (12, 3)]   # 字号阈值 → 标题级别


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def strip_manual_number(t):
    """去掉标题里的手动编号（飞书自动生成目录，手写编号会重复）。

    财报附注的 "2. 收入" 是原文编号，保留编号本身会让飞书目录出现
    "2 2. 收入" 这类重复；按 ffeishu 规范一律剥掉前缀。
    """
    return re.sub(r'^\s*(?:[一二三四五六七八九十]+[、.]|\d+(?:\.\d+)*[.、）)]?)\s*', '', t).strip()


def _filter_lines(lines):
    """与 translate.py 的行筛选保持逐字一致 —— 译文缓存按这个顺序对齐。"""
    out = [l['t'] for l in lines
           if not re.fullmatch(r'\d{1,3}', l['t']) and l['t'] != 'Table of Contents']
    return [x for x in out if len(x) > 20]


def _heading_level(sz):
    for thresh, lvl in HEAD_SIZES:
        if sz >= thresh:
            return lvl
    return None


def _is_bold_lead(l):
    """加粗引导行是不是小节标题。

    SEC 的 10pt 加粗短行（"Our Core Advantages"）不靠字号分层，但结构上就是
    H3。判据：加粗 + 短 + 不带句子标点 + 不是项目符号。带 "•" 的是列表项主体
    （"•Adoption of Claude. The advancing..."），不能当标题。
    """
    t = l['t'].strip()
    if not l['b'] or _heading_level(l['sz']):
        return False
    if t.startswith('•') or t.startswith('-'):
        return False
    if len(t) > 60 or t.endswith(('.', '。', ':', '：', ';', '；')):
        return False
    return len(t.split()) <= 8


def _is_standalone_heading(lines, i):
    """独立成行的小标题（不加粗版本）。

    这是此前标题丢失的根因：SEC 里有些小节标题是 10pt **不加粗**，
    比如 p63 "Internal Governance and Decision-Making"、p45 "Electrical
    Power and Fuel Constraints"。旧判据只认「≥12 加粗」和「10pt 加粗」，
    这一整档全部被当成正文段落吞掉，用户反复反馈的"标题丢失"就是它。

    判据不能只看"短"：正文里的断行短句（"efficient training methodologies;"）
    也短。关键是**前后都有段落分界的行距**（>PARA_GAP）——段落内部的断行
    行距只有 11.4pt，独立小标题前后都是 20.4pt。
    """
    l = lines[i]
    t = l['t'].strip()
    if _heading_level(l['sz']) or l['b']:
        return False                      # 已由字号/加粗判据覆盖
    if not (9.9 <= l['sz'] <= 11.9):
        return False
    if len(t) < 4 or len(t) > 70:
        return False
    if t.startswith(('•', '-', '(')) or re.search(r'[.。,，;；:：]$', t):
        return False
    if re.fullmatch(r'\(?Continued\)?|\(续\)', t, re.I):
        return False
    if re.match(r'^[a-z]', t):
        return False
    # 首字母大写或全大写；且后面紧跟正文（不是列表项）
    if not (t[0].isupper() or t.isupper()):
        return False
    words = t.split()
    if len(words) > 9:
        return False
    # 地址 / 编号行不是标题（"San Francisco, California 94104"）
    if re.search(r'\d{3,}', t) or re.search(r'\b(Suite|Street|Avenue|Road|Blvd)\b', t):
        return False
    # 前后行距都要是段落分界（标题自成一行）
    prev_gap = l['y'] - lines[i - 1]['y'] if i > 0 else 999
    next_gap = lines[i + 1]['y'] - l['y'] if i + 1 < len(lines) else 999
    if prev_gap < PARA_GAP * 0.85:
        return False                      # 紧贴上行 → 是段落内断行
    if next_gap < PARA_GAP * 0.85:
        return False                      # 紧贴下行 → 是段落内断行
    if words and t.isupper() and len(words) == 1:
        return False                      # 单词大写多为表头/装饰
    return True


def _is_furniture(l):
    """页眉页脚 / 页码 / 目录行 / 续页标记 —— 不属于正文。"""
    if l['y'] and (l['y'] < HEADER_Y or l['y'] > FOOTER_Y):
        return True
    t = l['t'].strip()
    if re.fullmatch(r'\d{1,3}', t) or t == 'Table of Contents':
        return True
    # 财报长表格跨 50 页，每页顶部都有 "(Continued)"。它既不是标题也不是正文，
    # 混进去会在目录里堆 51 个同名条目。
    if re.fullmatch(r'\(?Continued\)?|\(续\)', t, re.I):
        return True
    return False


FOOTNOTE_SZ = 8.2       # 正文 9.5pt，脚注 8.0pt（实测 499 行集中在 8.0）
FRONT_MATTER_END = 16   # p1-15 是封面/免责/目录/术语表，p16 起才是正文
GLOSSARY_START = 12     # p12 "Select Defined Terms"


def _is_footnote(l):
    """行尾的脚注（小字号 + 页码编号开头）。

    SEC 把脚注排在页面底部，字号 8pt，正文是 9.5pt。学习者需要能区分
    "这是正文的一句" 和 "这是对上面某个数字的注释"——所以渲染成引用块。
    """
    if l['sz'] > FOOTNOTE_SZ:
        return False
    t = l['t'].strip()
    # "1 See the section titled ..." / "2 IDC, The Economic Impact of AI ..."
    return bool(re.match(r'^\d{1,2}\s+\S', t))


def _inline_code(text):
    """把 (MCP)/(SDK)/(API) 这类缩写括号改成行内代码。

    原文用括号补全缩写（"通用模型上下文协议（MCP）"），正文里满屏括号很吵。
    改成 `<code>MCP</code>` 后既保留信息又更好扫读。
    """
    import re as _re
    return _re.sub(r'[（(]([A-Z][A-Z0-9\-]{1,7})[）)]', r'<code>\1</code>', text)


def build_blocks(page, zh_lines, table_rows):
    """一页 → 有序块列表。

    正文行按 x 分栏、按 y 排序；同栏内行距 < PARA_GAP 的行合并成一段。
    标题行单独成块。表格页优先输出真表格，其单元格文本不再作为正文重复。
    """
    lines = [l for l in page['lines'] if not _is_furniture(l)]
    # 单栏 SEC 文档按 y 排序即可。早期按 x 再 y（分栏思路）会把居中标题拆散：
    # 标题首行居中（x=140）、折行后靠左（x=72），按 x 排会让 "Transactions"
    # 排到 "Relationships and Related Person" 之前。同 y 才按 x（真左右分栏）。
    lines.sort(key=lambda l: (round(l['y'] / 4), l['x']))

    table_cells = set()
    blocks, i = [], 0
    while i < len(lines):
        l = lines[i]
        lvl = _heading_level(l['sz']) if l['b'] else None
        if lvl or _is_bold_lead(l) or _is_standalone_heading(lines, i):
            lvl = lvl or 3
            # SEC 会把长标题折成多行（"Management's Discussion and Analysis of" +
            # "Financial Condition and Results of Operations"），同字号同加粗且行距
            # 相邻的一律并回一个标题，否则飞书目录里会出现两个半截标题。
            txt, j = l['t'], i + 1
            while (j < len(lines) and lines[j]['sz'] == l['sz'] and lines[j]['b']
                   and (_heading_level(lines[j]['sz']) == lvl or not _heading_level(lines[j]['sz']))
                   and not _is_bold_lead(lines[j])
                   and abs(lines[j]['x'] - l['x']) < 90
                   and 0 < lines[j]['y'] - lines[j - 1]['y'] <= 26):
                txt += ' ' + lines[j]['t']
                j += 1
            blocks.append({'kind': 'h', 'level': lvl, 'text': txt})
            i = j
            continue
        # 表格单元格散行：该行文本是某个单元格 → 由表格还原，正文跳过
        if l['t'].strip() in table_cells:
            i += 1
            continue
        # 段落：同栏、行距连续的行合并
        para, j = [l], i + 1
        while j < len(lines):
            n = lines[j]
            if _heading_level(n['sz']) and n['b']:
                break
            if _is_standalone_heading(lines, j):
                break
            if n['t'].strip() in table_cells:
                break
            # 脚注单独成块：不和正文段落混在一起，否则读者分不清哪句是注释
            if _is_footnote(n) != _is_footnote(para[-1]):
                break
            prev = para[-1]
            if abs(n['x'] - prev['x']) > 8 or not (0 < n['y'] - prev['y'] < PARA_GAP):
                break
            para.append(n)
            j += 1
        text = ' '.join(x['t'] for x in para)
        kind = 'note' if _is_footnote(para[0]) else 'p'
        # 项目符号行（"•Rapid Revenue Growth. ..."）单独成块，后面拼列表时按块分组
        if text.lstrip().startswith(('•', '▪', '·')):
            kind = 'li'
        blocks.append({'kind': kind, 'text': text, 'nlines': len(para)})
        i = j
    return blocks


def align_zh(page_lines, zh):
    """把译文逐行贴回结构化块。

    译文缓存是筛后行的顺序列表；这里给每个筛后行编号，块按覆盖的行号
    取对应译文再拼接 —— 段内多行的译文用同样顺序黏连。
    """
    kept = [l for l in page_lines if not _is_furniture(l)]
    kept.sort(key=lambda l: (round(l['x'] / 8), l['y']))
    idx_of = {}
    k = 0
    for l in kept:
        if re.fullmatch(r'\d{1,3}', l['t'].strip()) or l['t'] == 'Table of Contents':
            continue
        if len(l['t']) <= 20:
            continue
        idx_of[id(l)] = k
        k += 1
    return idx_of


def block_cost(xml):
    """飞书真实块数（实测标定，不是标签数）。

    DOC_OPERATION_BLOCK_LIMIT 的 actual 值 = 1(标题) + <p> + <h> + <table>
    + 2×<td> + 2×<li>。表格每个单元格按 2 块算（cell + 内部 p），行/列组不计。
    实测 vol-344 用此式得 8,312，API 报 8,313。
    """
    return (1 + len(re.findall(r'<p\b', xml)) + len(re.findall(r'<h[1-3]\b', xml))
            + len(re.findall(r'<table\b', xml)) + 2 * len(re.findall(r'<t[hd]\b', xml))
            + 2 * len(re.findall(r'<li\b', xml)))


def split_by_cost(xml, limit=4500):
    """按顶层块累积块数切成若干段，每段 < limit。

    飞书 append 是累积计数：同一文档多次追加的总块数不能超 5000。
    单段超限时 API 直接拒，所以切分要按顶层块边界，不能拦腰断表格。
    """
    parts = re.split(r'(?=<(?:h1|h2|h3|p|table|ul|ol|callout|blockquote|img)\b)', xml)
    chunks, cur, cur_cost = [], [], 0
    for p in parts:
        if not p.strip():
            continue
        c = block_cost(p)
        if cur and cur_cost + c > limit:
            chunks.append(''.join(cur))
            cur, cur_cost = [p], c
        else:
            cur.append(p)
            cur_cost += c
    if cur:
        chunks.append(''.join(cur))
    return chunks


def image_xml(path, caption=''):
    """嵌真图。实测 <img path="@./xxx.jpg"> 会生成 block_type=image。

    path 必须相对 CLI 当前工作目录（lark-cli 的 allowlist：cwd / /tmp / ~/files）。
    """
    cap = f' caption="{esc(caption)}"' if caption else ''
    return f'<img path="@{path}"{cap}/>'


def table_xml(rows):
    """还原为飞书真表格：colgroup 宽度和 = 822，首列 30%，其余均分。"""
    # 传进来的可能是「行列表」也可能是单个字符串（调用方结构不一致时的兜底）
    if isinstance(rows, str):
        return ''
    rows = [r if isinstance(r, list) else [r] for r in rows]
    rows = [r for r in rows if r and any(str(c).strip() for c in r)]
    if not rows:
        return ''
    ncol = max(len(r) for r in rows)
    if ncol < 2:
        return ''
    first = round(COLWIDTH_TOTAL * 0.30)
    rest = round((COLWIDTH_TOTAL - first) / (ncol - 1))
    # 均分后补差：round 会让 n 列累加偏离 822（实测 4 列得 823），飞书要求严格相等
    widths = [first] + [rest] * (ncol - 1)
    widths[-1] += COLWIDTH_TOTAL - sum(widths)
    cols = ''.join(f'<col width="{w}"/>' for w in widths)
    out = [f'<table><colgroup>{cols}</colgroup>']
    for ri, r in enumerate(rows):
        padded = r + [''] * (ncol - len(r))
        cells = ''.join(
            f'<td>{("<b>" + esc(c) + "</b>") if ri == 0 else esc(c)}</td>'
            for c in padded
        )
        body = f'<tr>{cells}</tr>'
        out.append(f'<thead>{body}</thead>' if ri == 0 else f'<tbody>{body}</tbody>')
    out.append('</table>')
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser(description='按版面结构重建中文 DocxXML')
    ap.add_argument('slug')
    ap.add_argument('--workdir', default=os.path.expanduser('~/digest-work'))
    ap.add_argument('--title', default='全文中文翻译')
    ap.add_argument('--out', default=None)
    ap.add_argument('--max-blocks', type=int, default=3000)
    ap.add_argument('--vol', type=int, default=0, help='分卷号（0=不分卷）')
    ap.add_argument('--page-start', type=int, default=1)
    ap.add_argument('--page-end', type=int, default=0)
    ap.add_argument('--images-dir', default=None,
                    help='图片本地目录（相对 lark-cli cwd）；给了才嵌图')
    ap.add_argument('--split-cost', type=int, default=0,
                    help='按飞书块数切成多段（0=不切）。单次 append 上限 5000')
    ap.add_argument('--split-dir', default=None, help='多段输出目录')
    args = ap.parse_args()

    d = os.path.join(args.workdir, args.slug)
    pages = json.load(open(os.path.join(d, 'pages.json')))
    tables = json.load(open(os.path.join(d, 'tables.json')))

    tb_by_page = {}
    for t in tables:
        tb_by_page.setdefault(t['page'], []).append(t['rows'])

    # 图片按页归组，页内按 y 排序 —— 正文逐块渲染时按行距插到对应位置
    img_by_page = {}
    ipath = os.path.join(d, 'images.json')
    if args.images_dir and os.path.exists(ipath):
        for im in json.load(open(ipath)):
            img_by_page.setdefault(im['page'], []).append(im)
        for v in img_by_page.values():
            v.sort(key=lambda x: x.get('y', 0))

    # 译文真相源是 zh-blocks（块级），不是 zh（旧的逐行）。块级译文与 build_blocks
    # 的输出一一对应，直接按下标取用，不需要再对齐行。
    zdir = os.path.join(d, 'zh-blocks')
    zb_by_page = {}
    if os.path.isdir(zdir):
        for fn in os.listdir(zdir):
            if fn.endswith('.json'):
                z = json.load(open(os.path.join(zdir, fn)))
                zb_by_page[z['page']] = z

    out = [f'<title>{esc(args.title)}</title>']
    nblocks = 1
    nimages = 0
    missing, mismatched = 0, []
    for p in pages:
        n = p['page']
        if args.page_end and not (args.page_start <= n <= args.page_end):
            continue
        zrec = zb_by_page.get(n)
        blocks = build_blocks(p, [], [r for rs in tb_by_page.get(n, []) for r in rs])
        zblocks = (zrec or {}).get('blocks') or []
        if len(zblocks) != len(blocks):
            if blocks:
                mismatched.append(n)
            missing += 1

        # 页面图片按 y 插入：渲染每个块时，把 y 小于该块起始 y 的图先放出来。
        # 块没有记录 y，用「块的第一个文本行」的 y 反查。
        page_imgs = list(img_by_page.get(n, []))
        first_y = {}
        fl = [l for l in p['lines'] if not _is_furniture(l)]
        fl.sort(key=lambda l: (round(l['y'] / 4), l['x']))
        bi = 0
        for b in blocks:
            head = b['text'][:30]
            for cand in fl[bi:]:
                if cand['t'].startswith(head[:12]):
                    first_y[id(b)] = cand['y']
                    bi = fl.index(cand)
                    break

        li_buf = []       # 连续的项目符号行攒成一个 <ul>

        def flush_li():
            if li_buf:
                body = ''.join(f'<li>{_inline_code(esc(x))}</li>' for x in li_buf)
                out.append(f'<ul>{body}</ul>')
                li_buf.clear()

        for i, b in enumerate(blocks):
            by = first_y.get(id(b))
            if by is not None:
                while page_imgs and page_imgs[0].get('y', 0) <= by:
                    im = page_imgs.pop(0)
                    pth = os.path.join(args.images_dir, im['file'])
                    out.append(image_xml(pth, f"第 {im['page']} 页 · {im['file']}"))
                    nimages += 1
            zh = zblocks[i]['zh'] if i < len(zblocks) else ''
            txt = (zh or '').strip() or b['text']
            if not txt:
                continue
            if b['kind'] == 'h':
                flush_li()
                lvl = min(b['level'], 3)
                txt = strip_manual_number(txt)
                if not txt:
                    continue
                if lvl == 1:
                    out.append(f'<h1><span text-color="blue">{esc(txt)}</span></h1>')
                else:
                    out.append(f'<h{lvl}>{esc(txt)}</h{lvl}>')
            elif b['kind'] == 'li':
                li_buf.append(re.sub(r'^[•▪·]\s*', '', txt))
            elif b['kind'] == 'note':
                # 脚注渲染成引用块：学习者一眼能看出这是注释而非正文
                flush_li()
                out.append(f'<blockquote><p>{_inline_code(esc(txt))}</p></blockquote>')
            else:
                flush_li()
                out.append(f'<p>{_inline_code(esc(txt))}</p>')
        flush_li()

        # 页面尾部剩余的图（y 大于所有正文块）
        while page_imgs:
            im = page_imgs.pop(0)
            pth = os.path.join(args.images_dir, im['file'])
            out.append(image_xml(pth, f"第 {im['page']} 页 · {im['file']}"))
            nimages += 1

        # 表格：优先用块级译文里的 tables（与 tables.json 结构一致）
        ztables = (zrec or {}).get('tables') or []
        src_tables = tb_by_page.get(n, [])
        for ti, rows in enumerate(src_tables):
            tr = ztables[ti] if ti < len(ztables) and ztables[ti] else rows
            tx = table_xml(tr)
            if tx:
                out.append(tx)
        nblocks += len(blocks) + len(src_tables)

    xml = '\n'.join(out)
    cost = block_cost(xml)

    if args.split_cost and cost > args.split_cost:
        spdir = args.split_dir or os.path.join(d, 'zh-parts')
        os.makedirs(spdir, exist_ok=True)
        for f in os.listdir(spdir):
            if f.endswith('.xml'):
                os.remove(os.path.join(spdir, f))
        chunks = split_by_cost(xml, args.split_cost)
        paths = []
        for i, c in enumerate(chunks, 1):
            fp = os.path.join(spdir, f'part{i:02d}.xml')
            open(fp, 'w', encoding='utf-8').write(c)
            paths.append(fp)
        print(json.dumps({'parts': paths, 'pages': len(pages),
                          'feishu_blocks': cost, 'part_counts': [block_cost(c) for c in chunks],
                          'images': nimages, 'pages_missing_zh': missing,
                          'block_count_mismatch': mismatched[:10]}, ensure_ascii=False))
        return

    outp = args.out or os.path.join(d, 'zh-structured.xml')
    open(outp, 'w', encoding='utf-8').write(xml)
    print(json.dumps({'out': outp, 'pages': len(pages), 'blocks': nblocks,
                      'feishu_blocks': cost, 'images': nimages,
                      'over_5000': cost > 5000,
                      'pages_missing_zh': missing,
                      'block_count_mismatch': mismatched[:10]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
