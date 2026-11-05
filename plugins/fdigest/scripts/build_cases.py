#!/usr/bin/env python3
"""客户案例 → 独立文档（含 MinerU OCR 出来的真实案例内容）。

案例页是整页扫描图，文本层为零。走 MinerU 的 OCR 通道（它支持图片输入，
且输出带版面结构的 markdown：标题层级、表格、段落），比让通用 vision
模型"描述这张图"更贴近文档本身的组织结构。

每节版式（用户三轮反馈后定案，改之前先看 references/ops.md §案例文档版式）：
  原图 → 蓝色高亮块（案例名居中加粗 + 成果无序列表，不用表格）
      → 引文与署名合成同一个 <blockquote>，署名 <p align="right">
      → 背景/影响等正文小节

两条易犯的错：
  1. 引言漂在高亮块前面 —— 高亮块必须先出。
  2. 署名单独成段漂在正文里 —— 必须并进前一个引用的 blockquote。
align 属性只在 --detail full 可见，simple 会丢掉，别用 simple 验证对齐。
"""
import argparse
import json
import os
import re

COLWIDTH_TOTAL = 822


def _strip_dollars(t):
    """去掉翻译遗留的 $...$ LaTeX 标记。"""
    s = t.replace('\\%', '%').replace('\\$', '$')
    return re.sub(r'\$(\d+[,.%]+)*\$', r'\1', s)


def esc(s):
    return _strip_dollars(str(s)).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


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
    """MinerU markdown → (title, preamble, metrics_list, sections_list)。

    把 md 分成：
      1. title — # 开头的第一行
      2. preamble — 标题之后、第一个 ## 之前的内容（引言、背景段落等）
      3. metrics — 成果/结果 节下的指标项
      4. sections — 其余 ## 节的 [(h_text, [(kind, line)])]

    metrics_list: [(num, desc)]，desc 已去尾脚注数字
    preamble: [(kind, text)] → kind ∈ 'quote'/'p'
    """
    blocks = [b.strip() for b in re.split(r'\n\s*\n', md.strip()) if b.strip()]
    title = ''
    preamble = []
    metrics = []
    sections = []
    phase = 'title'
    cur_h = ''
    cur_body = []
    metric_h = False  # current section is '成果' or '结果'

    def flush():
        nonlocal cur_h, cur_body, metric_h
        if not cur_h or not cur_body:
            cur_h, cur_body, metric_h = '', [], False
            return
        if metric_h:
            # 成果/结果 节 → 先合并连续的文本块
            merged_ps = []
            cur_texts = []
            for kind, b in cur_body:
                if kind == 'p':
                    cur_texts.append(b)
                else:
                    if cur_texts:
                        merged_ps.append(('p', '\n'.join(cur_texts)))
                        cur_texts = []
                    merged_ps.append((kind, b))
            if cur_texts:
                merged_ps.append(('p', '\n'.join(cur_texts)))
            cur_body = merged_ps
            # 提取指标
            for kind, b in cur_body:
                if kind == 'table':
                    for rm in re.finditer(r'<tr>(.*?)</tr>', b, re.S):
                        cells = [re.sub(r'<[^>]+>', '', c).strip()
                                 for c in re.findall(r'<td>(.*?)</td>', rm.group(1), re.S)]
                        if cells:
                            num = re.sub(r'\d+$', '', cells[0]).strip() if cells[0] else ''
                            desc = re.sub(r'\d+$', '', cells[1]).strip() if len(cells) > 1 else ''
                            if num:
                                metrics.append((num, desc))
                elif kind == 'p':
                    t = b.strip()
                    # 简单提取：数字开头行 / 数字结尾行
                    for line in t.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        # 数字开头（含逗号/百分比/符号），兼容「近 25,000」「约 1 周」
                        pre = ''
                        pm = re.match(r'^(约|高达|近)\s*([\d,+\-%↑↓]+)\s*(.*)', line)
                        if pm:
                            pre, num, desc = pm.group(1), pm.group(2), pm.group(3).strip()
                        else:
                            m = re.match(r'^([\d,+\-%↑↓]+)\s*(.*)', line)
                            if m:
                                num, desc = m.group(1), m.group(2).strip()
                            else:
                                num, desc = '', ''
                        if num:
                            desc = re.sub(r'^(名|位|个|家|人|种|项)\s*', '', desc)
                            metrics.append((pre + num, desc))
                        # 行末百分比/数字（如「提速 14%」）
                        elif re.search(r'([\d,.%]+)$', line) and not re.search(r'Firefox |Claude |Fable |Opus ', line):
                            m2 = re.search(r'(.+?)\s*([\d,.%]+)$', line)
                            if m2:
                                desc, num = m2.group(1).strip(), m2.group(2).strip()
                                metrics.append((num, desc))
                        else:
                            sections.append((cur_h, [('p', line)]))
        else:
            sections.append((cur_h, cur_body))
        cur_h, cur_body, metric_h = '', [], False

    for b in blocks:
        if b.startswith('# '):
            if not title:
                title = re.sub(r'^#+\s*', '', b).strip()
                phase = 'preamble'
            else:
                # 第二个 # 行 — 可能是引言被 OCR 成标题
                txt = re.sub(r'^#+\s*', '', b).strip()
                preamble.append(('quote', txt))
            continue
        if b.startswith('## '):
            flush()
            cur_h = re.sub(r'^##+\s*', '', b).strip()
            # 没有 # 标题时，第一个 ## 当标题
            if not title:
                title = cur_h
                phase = 'preamble'
                cur_h = ''
                continue
            metric_h = cur_h in ('成果', '结果')
            # 某些案例 OCR 把指标行写成了 ## 节标题（如 "## 约 1 周"）
            if not metric_h and re.search(r'^[\d,+\-%↑↓约高达近]+', cur_h):
                metrics.append((cur_h, ''))
                metric_h = True
                cur_h = ''
            phase = 'body'
            continue
        if b.startswith('### ') or b.startswith('#'):
            txt = re.sub(r'^#+\s*', '', b).strip()
            if phase == 'body' and cur_h:
                cur_body.append(('h3', txt))
            else:
                preamble.append(('p', txt))
            continue
        # 纯内容块
        if phase == 'preamble':
            if '<table>' in b:
                # 标题后面的首张表一定是指标表 → metrics
                for rm in re.finditer(r'<tr>(.*?)</tr>', b, re.S):
                    cells = [re.sub(r'<[^>]+>', '', c).strip()
                             for c in re.findall(r'<td>(.*?)</td>', rm.group(1), re.S)]
                    if cells:
                        num = cells[0] or ''
                        desc = (re.sub(r':?\d+$', '', cells[1]).strip()
                                if len(cells) > 1 else '')
                        if num:
                            metrics.append((num, desc))
            else:
                is_quote = bool(re.search(r'[「」\"”“]', b)) and len(b) > 30
                is_attribution = bool(re.search(r'(董事长|CEO|CTO|总裁|联合创始人|董事|主席|执行官)', b))
                # 形如 "成果" "Results" 的标题残词直接跳过
                if b.strip() in ('成果', 'Results', '结果'):
                    pass
                elif is_quote or is_attribution:
                    preamble.append(('quote', b))
                else:
                    preamble.append(('p', b))
        else:
            cur_body.append(('p' if '<table>' not in b else 'table', b))
    flush()
    return title, preamble, metrics, sections


ATTR_RE = re.compile(
    r'^[一-鿿\w.\s·]{2,30}[，,]\s*\S{2,40}(董事长|CEO|CTO|CIO|COO|总裁|创始人|'
    r'董事|主席|执行官|副总裁|官|合伙人|负责人)$')

# 职务关键词：署名行末尾必须落在这些词上（OCR 会把「联合创始人」这类复合词写全，
# 正则里列前缀太脆，改成「末尾命中关键词」即可）
ATTR_TAIL = ('董事长', '总裁', '创始人', '董事', '主席', '执行官', '副总裁',
             'CEO', 'CTO', 'CIO', 'COO', 'CFO', '官', '合伙人', '负责人', '经理',
             '主管', '总监', '总工程师', 'VP', 'SVP', 'EVP', 'MD', '总经理', '社长')

# 行末「公司名」作为署名（无逗号），仅限单行公司名
ATTR_SINGLE = ('Mercado Libre', 'Jane Street', 'PayPal', 'SAP', 'Travelers', 'Verizon',
               'Mozilla', 'DoorDash', 'AIG', 'BMS', 'Salesforce', 'Rakuten', 'IRC',
               'Shy Bird', 'KBF')


def _is_attr(t):
    """署名行判定：短、无引号、含「，」+ 职务末尾，或公司名单行。

    OCR 常把引文和署名拆成两段（有的还夹在正文中间），必须成对合并，
    否则署名会单独漂在正文里，看不出是谁说的。
    """
    t = t.strip()
    if len(t) > 60 or re.search(r'[「」""]', t):
        return False
    if '，' in t or ',' in t:
        return t.rstrip('。.').endswith(ATTR_TAIL)
    # 无逗号纯公司名（OCR 截断署名行，丢了逗号和职务）
    return t in ATTR_SINGLE


def _is_quote(t):
    t = t.strip()
    if len(t) < 20:
        return False
    return bool(re.search(r'[「」""…]', t))


def _pair_quotes(items):
    """[(kind,text)] → [(kind,text,attr)]，引文与紧随署名合成一项。

    两种合并：
      1. 带引号的段落 + 下一个署名行 → 一个引用块
      2. 无引号但后面紧跟署名的段落（OCR/译文常把引文改写成转述）→ 同样合成
    署名独占一行且前一块不是署名，说明这段就是那个人说的，必须配对。
    """
    out, i = [], 0
    while i < len(items):
        kind, t = items[i]
        if kind == 'p' and i + 1 < len(items) and _is_attr(items[i + 1][1]):
            out.append(('quote', t.strip(), items[i + 1][1].strip()))
            i += 2
            continue
        if _is_quote(t):
            attr = ''
            if i + 1 < len(items) and _is_attr(items[i + 1][1]):
                attr = items[i + 1][1].strip()
                i += 1
            out.append(('quote', t.strip(), attr))
        elif _is_attr(t):
            # 孤立署名（前面没有可配对的正文）→ 单独引用块，右对齐
            out.append(('quote', '', t.strip()))
        elif kind == 'h3':
            out.append(('h3', t, ''))
        elif kind == 'table':
            out.append(('table', t, ''))
        else:
            out.append(('p', t, ''))
        i += 1
    return out


def _render(items):
    """渲染 [(kind,text,attr)]。引用块内署名右对齐。"""
    o = []
    for kind, t, attr in items:
        if kind == 'quote':
            inner = f'<p>{esc(t)}</p>' if t else ''
            if attr:
                inner += f'<p align="right">{esc(attr)}</p>'
            o.append(f'<blockquote>{inner}</blockquote>')
        elif kind == 'h3':
            o.append(f'<h3>{esc(t)}</h3>')
        elif kind == 'table':
            tx = md_table_to_xml(t)
            if tx:
                o.append(tx)
        else:
            o.append(f'<p>{esc(re.sub(r"\s+", " ", t.strip()))}</p>')
    return o


def layout_check(xml):
    """案例版式断言 —— 把用户三轮反馈的规则变成可执行检查，不靠人眼。

    返回 {"errors": [...], "stats": {...}}。errors 非空说明版式违规。
    """
    errs = []
    # 每页一节切分
    parts = re.split(r'(?=<h2>第 \d+ 页)', xml)
    parts = [p for p in parts if re.match(r'^<h2>第 \d+ 页', p)]
    quote_n = attr_ok = callout_n = tbl_in_metric = 0
    for p in parts:
        pg = re.match(r'^<h2>第 (\d+) 页', p).group(1)
        # 1. 高亮块必须在第一个引用之前
        ci, qi = p.find('<callout'), p.find('<blockquote')
        if ci < 0:
            errs.append(f'p{pg} 无成果高亮块')
        else:
            callout_n += 1
            if qi >= 0 and qi < ci:
                errs.append(f'p{pg} 引言漂在高亮块之前')
        # 2. 引用块内的署名必须右对齐；块外的署名视为漂移
        for seg in re.findall(r'<blockquote>.*?</blockquote>', p, re.S):
            quote_n += 1
            inner = re.findall(r'<p[^>]*>([^<]{0,60})</p>', seg)
            tail = inner[-1].strip() if inner else ''
            if tail.endswith(ATTR_TAIL):
                attr_ok += 1
                if 'align="right"' not in seg:
                    errs.append(f'p{pg} 署名未右对齐：{tail[:20]}')
        # 3. 高亮块里不许有表格
        for seg in re.findall(r'<callout[^>]*>.*?</callout>', p, re.S):
            if '<table' in seg:
                tbl_in_metric += 1
                errs.append(f'p{pg} 成果用了表格（应为无序列表）')
    return {'errors': errs, 'stats': {'pages': len(parts), 'callout': callout_n,
                                      'quotes': quote_n, 'attr_right': attr_ok}}


def _preamble_to_impact(preamble, sections):
    """preamble 的引言/引用归入「影响」节开头。

    用户指出：前引不应该飘在高亮块前面，应放在「影响」节开头。
    搬移规则：从尾部往前找 (p+quote) 配对、独立 quote、或 (quote+p) 配对。
    """
    if not preamble:
        return preamble, sections
    movable, i = [], len(preamble) - 1
    while i >= 0:
        k, t = preamble[i]
        if k == 'p' and i > 0 and preamble[i-1][0] == 'quote':
            # p at i is attribution, quote at i-1 is text → 保持原序 (quote, p)
            movable.insert(0, preamble[i])     # p (attribution)
            movable.insert(0, preamble[i-1])   # quote (text)
            i -= 2
        elif k == 'quote' and i > 0 and preamble[i-1][0] == 'p':
            # quote at i is text, p at i-1 is attribution → 保持原序 (p, quote)
            movable.insert(0, preamble[i])     # quote
            movable.insert(0, preamble[i-1])   # p
            i -= 2
        elif k == 'quote':
            movable.insert(0, preamble[i])
            i -= 1
        else:
            break
    if not movable:
        return preamble, sections
    for si, (h, body) in enumerate(sections):
        if h == '影响':
            sections[si] = (h, movable + body); break
    return preamble[:i+1] if i >= 0 else [], sections


def _fill_orphan_metrics(metrics, sections):
    """成果指标有数字无说明时，从后续节逐一取说明。

    p224 模式：OCR 把指标行间的说明文字变成独立段落。
    在 metrics 内部，数字后的纯文本行自动作为该数字的描述。
    """
    if not metrics:
        return metrics, sections
    new_metrics = list(metrics)
    new_sections = list(sections)
    for mi, (num, desc) in enumerate(new_metrics):
        if desc:
            continue
        for si, (h, body) in enumerate(new_sections):
            if body and any(k == 'p' and len(b.strip()) > 10 for k, b in body):
                first_text = next(b.strip() for k, b in body if k == 'p' and len(b.strip()) > 10)
                new_metrics[mi] = (num, first_text)
                new_sections[si] = (h, body[1:])
                break
    return new_metrics, [s for s in new_sections if s[1] or s[0] in ('背景', '影响')]


def md_to_xml(md):
    """把案例 md 渲染成 DocxXML。

    顺序（用户定）：蓝色高亮块（案例名居中 + 成果指标列表）→ 摘要正文
    → 各小节。引文与署名合成一个引用块，署名右对齐。
    引言（如 p222 的 Andy Fang）归入「影响」节开头。
    """
    title, preamble, metrics, sections = parse_md(md)
    metrics, sections = _fill_orphan_metrics(metrics, sections)
    preamble, sections = _preamble_to_impact(preamble, sections)
    o = []

    # 高亮块：案例名居中加粗 + 成果列表。没指标时只放标题，不再重复 h2。
    if title or metrics:
        o.append('<callout emoji="📊" background-color="blue">')
        if title:
            o.append(f'<p align="center"><b>{esc(title)}</b></p>')
        if metrics:
            o.append('<ul>')
            for num, desc in metrics:
                num_e = esc(num)
                o.append(f'<li><p><b>{num_e}</b>{("　" + esc(desc)) if desc else ""}</p></li>')
            o.append('</ul>')
        o.append('</callout>')

    o.extend(_render(_pair_quotes(preamble)))

    for h, body in sections:
        if h:
            o.append(f'<h3>{esc(h)}</h3>')
        o.extend(_render(_pair_quotes(body)))
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
                      'layout': layout_check(xml),
                      'over_limit': cost > 5000}, ensure_ascii=False))


if __name__ == '__main__':
    main()
