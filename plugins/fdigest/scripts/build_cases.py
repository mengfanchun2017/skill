#!/usr/bin/env python3
"""把整页扫描的客户案例抽成独立文档。

为什么单独拆出来：案例页是整页图片，文字不在文本层——混在全文中文版里
读者只会看到一堆图，既不能检索也不能引用。单独成文后，每页一图 + 中文解读
（解读位置留给后续视觉识别填入），才是可用的案例库。

用户定过：案例文档「每用户一页保留，真实的案例分析中文放在每个图下面」。
本脚本只负责排版骨架与图像，解读文本由调用方补。
"""
import argparse
import json
import os
import re

COLWIDTH_TOTAL = 822


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


CASE_NAME = re.compile(r'casestudy[-_]?(.+?)\d*[a-z]?\.jpg$', re.I)


def guess_company(filename):
    """从文件名推公司名（casestudy-doordash1c.jpg → DoorDash）。

    文件名不全覆盖（a2026-10x25xcasestudyxaccea.jpg 只给了 acce）。
    推不出来就留空，由视觉识别阶段补 —— 不要瞎猜。
    """
    m = CASE_NAME.search(filename)
    if not m:
        return ''
    raw = m.group(1).strip('-x_')
    if len(raw) < 4:
        return ''
    return raw.replace('x', ' ').title()


def main():
    ap = argparse.ArgumentParser(description='客户案例 → 独立文档骨架')
    ap.add_argument('slug')
    ap.add_argument('--workdir', default=os.path.expanduser('~/digest-work'))
    ap.add_argument('--title', default='客户案例')
    ap.add_argument('--images-dir', required=True, help='图片目录（相对 lark-cli cwd）')
    ap.add_argument('--page-start', type=int, default=0)
    ap.add_argument('--page-end', type=int, default=0)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    d = os.path.join(args.workdir, args.slug)
    imgs = json.load(open(os.path.join(d, 'images.json')))

    # 整页扫描 + 连续排布的才是案例（扉页也是整页扫描，但孤立）
    scans = [x for x in imgs if x.get('full_page_scan')]
    pages = sorted({x['page'] for x in scans})
    # 找最长的连续页段（案例通常连续排 20 页）
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
    case_pages = runs[0] if runs else []
    if args.page_start or args.page_end:
        lo = args.page_start or 0
        hi = args.page_end or 10 ** 6
        case_pages = [p for p in case_pages if lo <= p <= hi]

    seen, by_page = set(), {}
    for x in imgs:
        if x['page'] in case_pages and x['file'] not in seen:
            seen.add(x['file'])
            by_page.setdefault(x['page'], []).append(x)

    o = [f'<title>{esc(args.title)}</title>']
    o.append('<callout emoji="🗂️" background-color="light-gray">'
             '<p>本页收录原文中的客户案例，每页一张原图，图下留中文解读位置。</p>'
             f'<p>共 {len(case_pages)} 页（第 {case_pages[0]}-{case_pages[-1]} 页），'
             '原文件中这些页是整页扫描图，文字不在文本层，无法用检索命中。</p></callout>')

    o.append('<h1><span text-color="blue">案例清单</span></h1>')
    names = []
    for p in case_pages:
        for x in by_page.get(p, []):
            co = guess_company(x['file'])
            names.append((p, co, x['file']))
    o.append('<table><colgroup><col width="120"/><col width="240"/><col width="462"/></colgroup>'
             '<thead><tr><th><p>原文页</p></th><th><p>客户</p></th><th><p>图示</p></th></tr></thead><tbody>')
    for p, co, fn in names:
        o.append(f'<tr><td><p>{p}</p></td><td><p>{esc(co) or "待识别"}</p></td><td><p>{esc(fn)}</p></td></tr>')
    o.append('</tbody></table>')

    o.append('<h1><span text-color="blue">案例详情</span></h1>')
    o.append('<callout emoji="⚠️" background-color="light-red">'
             '<p>以下每页的图下方留了解读位置。客户名与案例细节需视觉识别后填入，'
             '本版未做识别，不臆测内容。</p></callout>')

    for p in case_pages:
        for x in by_page.get(p, []):
            co = guess_company(x['file'])
            head = f'第 {p} 页 · {co}' if co else f'第 {p} 页'
            o.append(f'<h2>{esc(head)}</h2>')
            pth = os.path.join(args.images_dir, x['file'])
            o.append(f'<img path="@{pth}" caption="第 {p} 页 · {esc(co) or esc(x[chr(39)+"file"+chr(39)]) if False else esc(x["file"])}"/>')
            o.append('<p><b>案例解读</b>：<i>待视觉识别补充</i></p>')

    xml = '\n'.join(o)
    open(args.out, 'w', encoding='utf-8').write(xml)
    cost = (1 + len(re.findall(r'<p\b', xml)) + len(re.findall(r'<h[1-3]\b', xml))
            + len(re.findall(r'<table\b', xml)) + 2 * len(re.findall(r'<t[hd]\b', xml)))
    print(json.dumps({'out': args.out, 'cases': len(case_pages),
                      'images': len(names), 'feishu_blocks': cost,
                      'pages': case_pages[:3] + ['...'] + case_pages[-2:] if case_pages else []},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
