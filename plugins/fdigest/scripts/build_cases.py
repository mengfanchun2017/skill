#!/usr/bin/env python3
"""客户案例 → 独立文档（含 MinerU OCR 出来的真实案例内容）。

案例页是整页扫描图，文本层为零。走 MinerU 的 OCR 通道（它支持图片输入，
且输出带版面结构的 markdown：标题层级、表格、段落），比让通用 vision
模型"描述这张图"更贴近文档本身的组织结构。

每节结构：原图 → 成果高亮块（蓝色底色+无序列表）→ 案例正文（含引用）。
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


def parse_md(md):
    """MinerU markdown → (title, metrics_lines, sections_list)。

    把 md 分成三个部分：
      1. 标题（# 开头第一行）
      2. 指标（标题之后、第一个 ## 之前的内容 — 可能是 table 或纯文本）
      3. 各小节（从 ## 开始往后拆）

    metrics_lines: [(kind, line)]，kind ∈ 'table_row'/'text'
    sections_list: [(h_text, [(kind, line)])]
    """
    blocks = [b.strip() for b in re.split(r'\n\s*\n', md.strip()) if b.strip()]
    title = ''
    metrics = []
    sections = []
    phase = 'title'
    cur_h = ''
    cur_body = []

    def flush():
        nonlocal cur_h, cur_body
        if cur_h and cur_body:
            sections.append((cur_h, cur_body))
        cur_h, cur_body = '', []

    for b in blocks:
        if b.startswith('# '):
            title = re.sub(r'^#+\s*', '', b).strip()
            phase = 'metrics'
        elif b.startswith('## '):
            flush()
            cur_h = re.sub(r'^##+\s*', '', b).strip()
            phase = 'body'
        elif b.startswith('#'):
            # non-first level headings — treat as sub-heading
            txt = re.sub(r'^#+\s*', '', b).strip()
            if phase == 'body':
                cur_body.append(('h3', txt))
            else:
                # a heading before any ## — unusual
                if title:
                    metrics.append(('text', b))
                else:
                    title = txt
                    phase = 'metrics'
        else:
            if phase == 'metrics':
                if '<table>' in b:
                    # 把表格行解析为指标
                    for rm in re.finditer(r'<tr>(.*?)</tr>', b, re.S):
                        cells = [re.sub(r'<[^>]+>', '', c).strip()
                                 for c in re.findall(r'<td>(.*?)</td>', rm.group(1), re.S)]
                        if cells:
                            metrics.append(('metric_row', cells))
                else:
                    metrics.append(('text', b))
            else:
                if '<table>' in b:
                    cur_body.append(('table', b))
                else:
                    cur_body.append(('p', b))
    flush()
    return title, metrics, sections


def md_to_xml(md):
    """把案例 md 渲染成 DocxXML。

    结构：蓝色高亮块（指标）→ 正文各小节。
    引号段落的句子 → blockquote（引用）。
    H3 仅在正文小节内使用。
    """
    title, metrics, sections = parse_md(md)
    o = []

    # 案例标题
    if title:
        o.append(f'<h2>{esc(title)}</h2>')

    # 指标 → 蓝色高亮块
    if metrics:
        o.append('<callout emoji="📊" background-color="blue">')
        o.append('<p><b>成果</b></p>')
        o.append('<ul>')
        for kind, data in metrics:
            if kind == 'metric_row':
                for cells in [data]:
                    num = esc(cells[0]) if len(cells) > 0 else ''
                    txt = esc(cells[1]) if len(cells) > 1 else ''
                    # 去掉末尾的数字（原文脚注标记，如 "业务线1" → "业务线"）
                    txt = re.sub(r'\d+$', '', txt).strip()
                    if num and txt:
                        o.append(f'<li><p><b>{num}</b>　{txt}</p></li>')
                    elif num:
                        o.append(f'<li><p><b>{num}</b></p></li>')
            elif kind == 'text':
                # 纯文本指标，如 "+32% … 性能提升"
                o.append(f'<li><p>{esc(data)}</p></li>')
        o.append('</ul>')
        o.append('</callout>')

    # 各小节
    for h, body in sections:
        o.append(f'<h3>{esc(h)}</h3>')
        for kind, b in body:
            if kind == 'h3':
                o.append(f'<h3>{esc(b)}</h3>')
            elif kind == 'table':
                tx = md_table_to_xml(b)
                if tx:
                    o.append(tx)
            elif kind == 'p':
                # 识别引文：整段被「」包裹，或"人名职务"结尾
                t = b.strip()
                is_quote = False
                if t.startswith('「') or t.startswith('"') or t.startswith('“'):
                    is_quote = True
                if not is_quote and re.search(r'[」\"”]\s*，?\s*[，。]\s*[一-鿿\w\s]+0?,?\s*$', t[-80:]) and '说' in t[-80:]:
                    is_quote = True  # 句末有「…」+ 人名 + "说"
                # 更精确：匹配「xxx。xxxx」 整段都是引用
                if '「' in t and '」' in t:
                    inner = t[t.index('「') + 1:t.index('」')]
                    if len(inner) > 20:
                        is_quote = True
                if is_quote:
                    o.append(f'<blockquote><p>{esc(t)}</p></blockquote>')
                else:
                    o.append(f'<p>{esc(re.sub(r"\s+", " ", t))}</p>')
    return '\n'.join(o)


def main():
    ap = argparse.ArgumentParser(description='客户案例 → 独立文档')
    ap.add_argument('slug')
    ap.add_argument('--workdir', default=os.path.expanduser('~/digest-work'))
    ap.add_argument('--title', default='客户案例')
    ap.add_argument('--images-dir', required=True)
    ap.add_argument('--ocr', default='', help='MinerU OCR 结果 json（build_cases_ocr 产出）')
    ap.add_argument('--ocr-zh', default='', help='OCR markdown 的中文译文 json（translate_cases 产出）')
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

    ocr, ocr_zh = {}, {}
    if args.ocr and os.path.exists(args.ocr):
        for fn, v in json.load(open(args.ocr)).items():
            ocr[v['page']] = v.get('md', '')
    if args.ocr_zh and os.path.exists(args.ocr_zh):
        for fn, v in json.load(open(args.ocr_zh)).items():
            ocr_zh[v['page']] = v.get('md', '')

    ordered = sorted(by_page)
    o = [f'<title>{esc(args.title)}</title>']
    o.append('<callout emoji="🗂️" background-color="light-gray">'
             '<p>本页收录原文中的客户案例。每页一张原图，图下结构：</p>'
             '<ul><li><p>蓝色高亮块：案例核心成果指标</p></li>'
             '<li><p>正文小节（背景→影响），引文以引用格式展示</p></li></ul>'
             f'<p>共 {len(ordered)} 页（第 {ordered[0]}-{ordered[-1]} 页）。'
             '原文件中这些页是整页扫描图，文字不在文本层，'
             '已用 MinerU 视觉 OCR 通道提取并译成中文。</p>'
             '<p>需要核对英文原文时，直接看原图。</p></callout>')

    # 清单
    o.append('<h1><span text-color="blue">案例清单</span></h1>')
    o.append('<table><colgroup><col width="90"/><col width="340"/><col width="392"/></colgroup>'
             '<thead><tr><th><p>原文页</p></th><th><p>案例</p></th><th><p>关键点</p></th></tr></thead><tbody>')
    for p in ordered:
        fn = by_page[p][0]['file']
        md = ocr_zh.get(p, '') or ocr.get(p, '')
        title = ''
        for line in md.split('\n'):
            if line.startswith('#'):
                title = re.sub(r'^#+\s*', '', line).strip()
                break
        # 关键点取案例指标数据：优先表格行，回落纯文本"成果"段
        pts = []
        for rm in re.finditer(r'<tr>(.*?)</tr>', md, re.S):
            cells = [re.sub(r'<[^>]+>', '', c).strip()
                     for c in re.findall(r'<td>(.*?)</td>', rm.group(1), re.S)]
            if len(cells) == 2 and cells[0]:
                pts.append(cells[0])
        if not pts:
            # 纯文本指标：找「## 成果/结果」后的数字行
            after = re.split(r'## 成果|## 结果', md, maxsplit=1)
            if len(after) > 1:
                for line in after[1].split('\n')[:15]:
                    s = line.strip()
                    if s.startswith(('+', '-', '高达', '近', '约')):
                        pts.append(s[:30])
                    m = re.match(r'^[\d,]+', s)
                    if m:
                        pts.append(m.group()[:15])
        o.append(f'<tr><td><p>{p}</p></td><td><p>{esc(title) or esc(fn)}</p></td>'
                 f'<td><p>{esc(" / ".join(x.strip() for x in pts[:3]))}</p></td></tr>')
    o.append('</tbody></table>')

    # 详情
    o.append('<h1><span text-color="blue">案例详情</span></h1>')
    for p in ordered:
        x = by_page[p][0]
        md = ocr.get(p, '')
        zh = ocr_zh.get(p, '')
        src = zh or md
        title = ''
        for line in src.split('\n'):
            if line.startswith('# '):
                title = re.sub(r'^#+\s*', '', line).strip()
                break
        head = f'第 {p} 页 · {title}' if title else f'第 {p} 页'
        o.append(f'<h2>{esc(head)}</h2>')
        pth = os.path.join(args.images_dir, x['file'])
        o.append(f'<img path="@{pth}" caption="第 {p} 页 · {esc(title) or esc(x["file"])}"/>')
        if zh.strip():
            o.append(md_to_xml(zh))
        elif md.strip():
            o.append(f'<callout emoji="⚠️" background-color="light-yellow">'
                     '<p>本页暂无中文译文，以下为 MinerU OCR 原文。</p></callout>')
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
