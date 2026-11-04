#!/usr/bin/env python3
"""客户案例 → 独立文档（含 MinerU OCR 出来的真实案例内容）。

案例页是整页扫描图，文本层为零。走 MinerU 的 OCR 通道（它支持图片输入，
且输出带版面结构的 markdown：标题层级、表格、段落），比让通用 vision
模型"描述这张图"更贴近文档本身的组织结构。

用户定过：每页一图保留，真实的中文分析放在每个图下面。所以每节结构是
图 → 中文（--ocr-zh 译好的）→ 英文 OCR 原文（原文核对用）。
只有英文没有中文时退化成原文，不静默丢内容。
"""
import argparse
import json
import os
import re

COLWIDTH_TOTAL = 822


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def md_table_to_xml(rows_md):
    """MinerU 的 <table><tr><td> → 飞书 DocxXML（colgroup 和必须 = 822）。"""
    rows = []
    for rm in re.finditer(r'<tr>(.*?)</tr>', rows_md, re.S):
        cells = [re.sub(r'<[^>]+>', '', c).strip()
                 for c in re.findall(r'<td>(.*?)</td>', rm.group(1), re.S)]
        if cells:
            rows.append(cells)
    if not rows:
        return ''
    ncol = max(len(r) for r in rows)
    if ncol < 2:
        return ''
    first = round(COLWIDTH_TOTAL * 0.22)
    rest = round((COLWIDTH_TOTAL - first) / (ncol - 1))
    widths = [first] + [rest] * (ncol - 1)
    widths[-1] += COLWIDTH_TOTAL - sum(widths)
    cols = ''.join(f'<col width="{w}"/>' for w in widths)
    out = [f'<table><colgroup>{cols}</colgroup><tbody>']
    for r in rows:
        padded = r + [''] * (ncol - len(r))
        out.append('<tr>' + ''.join(f'<td><p>{esc(c)}</p></td>' for c in padded) + '</tr>')
    out.append('</tbody></table>')
    return ''.join(out)


def md_to_xml(md, base_level=3):
    """MinerU markdown → DocxXML 片段。

    # → h3 / ## → h3（案例内小节，挂在「案例详情」h1 下）
    正文段落 → p，表格 → 真表格，引用行（引号开头）→ blockquote
    """
    out = []
    for block in re.split(r'\n\s*\n', md.strip()):
        b = block.strip()
        if not b:
            continue
        if b.startswith('#'):
            txt = re.sub(r'^#+\s*', '', b).strip()
            if txt:
                out.append(f'<h3>{esc(txt)}</h3>')
            continue
        if '<table>' in b:
            tx = md_table_to_xml(b)
            if tx:
                out.append(tx)
            continue
        if b.startswith('"') or b.startswith('“'):
            out.append(f'<blockquote><p>{esc(b)}</p></blockquote>')
            continue
        out.append(f'<p>{esc(re.sub(r"\s+", " ", b))}</p>')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description='客户案例 → 独立文档')
    ap.add_argument('slug')
    ap.add_argument('--workdir', default=os.path.expanduser('~/digest-work'))
    ap.add_argument('--title', default='客户案例')
    ap.add_argument('--images-dir', required=True)
    ap.add_argument('--ocr', default='', help='MinerU OCR 结果 json（build_cases_ocr 产出）')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    d = os.path.join(args.workdir, args.slug)
    imgs = json.load(open(os.path.join(d, 'images.json')))

    scans = [x for x in imgs if x.get('full_page_scan')]
    pages = sorted({x['page'] for x in scans})
    runs, cur = [], [pages[0]] if pages else []
    for a, b in zip(pages, pages[1:]):
        if b == a + 1:
            cur.append(b)
        else:
            runs.append(cur)
            cur = [b]
    if cur:
        runs.append(cur)
    runs.sort(key=len, reverse=True)
    case_pages = set(runs[0]) if runs else set()

    seen, by_page = set(), {}
    for x in imgs:
        if x['page'] in case_pages and x['file'] not in seen:
            seen.add(x['file'])
            by_page.setdefault(x['page'], []).append(x)

    ocr = {}
    if args.ocr and os.path.exists(args.ocr):
        for fn, v in json.load(open(args.ocr)).items():
            ocr[v['page']] = v.get('md', '')

    ordered = sorted(by_page)
    o = [f'<title>{esc(args.title)}</title>']
    o.append('<callout emoji="🗂️" background-color="light-gray">'
             '<p>本页收录原文中的客户案例。每页一张原图，图下是 OCR 提取的案例正文。</p>'
             f'<p>共 {len(ordered)} 页（第 {ordered[0]}-{ordered[-1]} 页）。'
             '原文件中这些页是整页扫描图，文字不在文本层，'
             '已用 MinerU 视觉 OCR 通道提取。</p></callout>')

    # 清单
    o.append('<h1><span text-color="blue">案例清单</span></h1>')
    o.append('<table><colgroup><col width="90"/><col width="340"/><col width="392"/></colgroup>'
             '<thead><tr><th><p>原文页</p></th><th><p>案例</p></th><th><p>关键点</p></th></tr></thead><tbody>')
    for p in ordered:
        fn = by_page[p][0]['file']
        md = ocr.get(p, '')
        title = ''
        for line in md.split('\n'):
            if line.startswith('#'):
                title = re.sub(r'^#+\s*', '', line).strip()
                break
        o.append(f'<tr><td><p>{p}</p></td><td><p>{esc(title) or esc(fn)}</p></td>'
                 f'<td><p>{esc(fn)}</p></td></tr>')
    o.append('</tbody></table>')

    # 详情
    o.append('<h1><span text-color="blue">案例详情</span></h1>')
    for p in ordered:
        x = by_page[p][0]
        md = ocr.get(p, '')
        title = ''
        for line in md.split('\n'):
            if line.startswith('#'):
                title = re.sub(r'^#+\s*', '', line).strip()
                break
        head = f'第 {p} 页 · {title}' if title else f'第 {p} 页'
        o.append(f'<h2>{esc(head)}</h2>')
        pth = os.path.join(args.images_dir, x['file'])
        o.append(f'<img path="@{pth}" caption="第 {p} 页 · {esc(title) or esc(x["file"])}"/>')
        if md.strip():
            o.append(md_to_xml(md))
        else:
            o.append('<callout emoji="⚠️" background-color="light-red">'
                     '<p>本页 OCR 未提取到文字，需人工查看原图。</p></callout>')

    xml = '\n'.join(o)
    open(args.out, 'w', encoding='utf-8').write(xml)
    cost = (1 + len(re.findall(r'<p\b', xml)) + len(re.findall(r'<h[1-3]\b', xml))
            + len(re.findall(r'<table\b', xml)) + 2 * len(re.findall(r'<t[hd]\b', xml)))
    print(json.dumps({'out': args.out, 'cases': len(ordered),
                      'images': len(seen), 'feishu_blocks': cost,
                      'with_ocr': sum(1 for p in ordered if ocr.get(p, '').strip()),
                      'ocr_chars': sum(len(ocr.get(p, '')) for p in ordered),
                      'over_limit': cost > 5000}, ensure_ascii=False))


if __name__ == '__main__':
    main()
