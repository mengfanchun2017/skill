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


def _is_furniture(l):
    """页眉页脚 / 页码 / 目录行 —— 不属于正文。"""
    if l['y'] and (l['y'] < HEADER_Y or l['y'] > FOOTER_Y):
        return True
    t = l['t'].strip()
    return bool(re.fullmatch(r'\d{1,3}', t) or t == 'Table of Contents')


def build_blocks(page, zh_lines, table_rows):
    """一页 → 有序块列表。

    正文行按 x 分栏、按 y 排序；同栏内行距 < PARA_GAP 的行合并成一段。
    标题行单独成块。表格页优先输出真表格，其单元格文本不再作为正文重复。
    """
    lines = [l for l in page['lines'] if not _is_furniture(l)]
    lines.sort(key=lambda l: (round(l['x'] / 8), l['y']))   # 左栏在上，再按纵向

    table_cells = set()
    blocks, i = [], 0
    while i < len(lines):
        l = lines[i]
        lvl = _heading_level(l['sz']) if l['b'] else None
        if lvl or _is_bold_lead(l):
            lvl = lvl or 3
            # SEC 会把长标题折成多行（"Management's Discussion and Analysis of" +
            # "Financial Condition and Results of Operations"），同字号同加粗且行距
            # 相邻的一律并回一个标题，否则飞书目录里会出现两个半截标题。
            txt, j = l['t'], i + 1
            while (j < len(lines) and lines[j]['sz'] == l['sz'] and lines[j]['b']
                   and (_heading_level(lines[j]['sz']) == lvl or not _heading_level(lines[j]['sz']))
                   and not _is_bold_lead(lines[j])
                   and abs(lines[j]['x'] - l['x']) < 8
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
            if n['t'].strip() in table_cells:
                break
            prev = para[-1]
            if abs(n['x'] - prev['x']) > 8 or not (0 < n['y'] - prev['y'] < PARA_GAP):
                break
            para.append(n)
            j += 1
        text = ' '.join(x['t'] for x in para)
        blocks.append({'kind': 'p', 'text': text, 'nlines': len(para)})
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


def table_xml(rows):
    """还原为飞书真表格：colgroup 宽度和 = 822，首列 30%，其余均分。"""
    rows = [r for r in rows if r]
    if not rows:
        return ''
    ncol = max(len(r) for r in rows)
    if ncol < 2:
        return ''
    first = round(COLWIDTH_TOTAL * 0.30)
    rest = round((COLWIDTH_TOTAL - first) / (ncol - 1))
    cols = ''.join(f'<col width="{first if i == 0 else rest}"/>' for i in range(ncol))
    out = [f'<table><colgroup>{cols}</colgroup>']
    for ri, r in enumerate(rows):
        cells = ''.join(
            f'<td>{("<b>" + esc(c) + "</b>") if ri == 0 else esc(c)}</td>'
            for c in (r + [''] * (ncol - len(r))) if c
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
    args = ap.parse_args()

    d = os.path.join(args.workdir, args.slug)
    pages = json.load(open(os.path.join(d, 'pages.json')))
    tables = json.load(open(os.path.join(d, 'tables.json')))

    tb_by_page = {}
    for t in tables:
        tb_by_page.setdefault(t['page'], []).append(t['rows'])

    zhdir = os.path.join(d, 'zh')
    zh_by_page = {}
    if os.path.isdir(zhdir):
        for fn in os.listdir(zhdir):
            if fn.endswith('.json'):
                z = json.load(open(os.path.join(zhdir, fn)))
                zh_by_page[z['page']] = z['zh']

    out = [f'<title>{esc(args.title)}</title>']
    blocks_total = 1
    missing = 0
    for p in pages:
        n = p['page']
        kept = _filter_lines(p['lines'])
        zh = zh_by_page.get(n, [])
        if len(zh) != len(kept):
            missing += 1
            zh = zh + [''] * (len(kept) - len(zh))
        # 筛后行 → 译文；再按同样规则把译文顺序贴到结构块
        counter = {'i': 0}

        def take(line_text):
            i = counter['i']
            counter['i'] += 1
            return zh[i] if i < len(zh) else ''

        rows_here = [r for rs in tb_by_page.get(n, []) for r in rs]
        blocks = build_blocks(p, zh, rows_here)
        # 逐块配译文：正文块按覆盖行数取，表格块不取
        for b in blocks:
            if b['kind'] == 'h' or b['kind'] == 'p':
                b['zh'] = ' '.join(take(b['text']) for _ in range(1))

        for b in blocks:
            txt = b.get('zh') or b['text']
            if not txt:
                continue
            if b['kind'] == 'h':
                lvl = min(b['level'], 3)
                if lvl == 1:
                    out.append(f'<h1><span text-color="blue">{esc(txt)}</span></h1>')
                else:
                    out.append(f'<h{lvl}>{esc(txt)}</h{lvl}>')
            elif b['kind'] == 'p':
                out.append(f'<p>{esc(txt)}</p>')
        for rows in tb_by_page.get(n, []):
            tx = table_xml(rows)
            if tx:
                out.append(tx)
        blocks_total += len(blocks)

    xml = '\n'.join(out)
    outp = args.out or os.path.join(d, 'zh-structured.xml')
    open(outp, 'w', encoding='utf-8').write(xml)
    print(json.dumps({'out': outp, 'pages': len(pages), 'blocks': blocks_total,
                      'zh_mismatch_pages': missing}, ensure_ascii=False))


if __name__ == '__main__':
    main()
