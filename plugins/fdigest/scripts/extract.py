#!/usr/bin/env python3
"""fdigest extract — 把一份源文档（HTML/PDF）抽成结构化中间产物。

产出（都落在 ~/digest-work/<slug>/，仓库外，避免 auto-sync 推公开库）：
    pages.json   逐页行结构 {page, lines:[{t,sz,b}]}
    heads.json   标题候选 {page,size,text}
    tables.json  表格 {page, rows[[cell]]}
    text.txt     全文本（供检索切块）
    manifest.json 元数据 + 源哈希

设计要点：HTML 走文本层直抽（零 OCR 成本）；扫描页只在 manifest 里标记，
交给 vision 通道单独处理，不无脑 OCR。
"""
import argparse
import hashlib
import html as H
import json
import os
import re
import sys

PAGE_SPLIT = re.compile(r'<div style="--justify:justify;--position:absolute;[^"]*height:792pt[^"]*"')
LINE_RE = re.compile(r'<div style="font-size:[^"]*"[^>]*>(.*?)</div>', re.S)
FONT_RE = re.compile(r'<font style="([^"]*)"[^>]*>([^<]*)</font>')
IMG_RE = re.compile(r'<img([^>]*)>')


def strip_tags(s):
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def extract_html(src):
    raw = open(src, encoding='utf-8', errors='ignore').read()
    pages_src = PAGE_SPLIT.split(raw)[1:]
    pages, tables, headings, images = [], [], [], []

    for idx, p in enumerate(pages_src, 1):
        lines = []
        for lm in LINE_RE.finditer(p):
            inner = lm.group(1)
            fonts = FONT_RE.findall(inner)
            if fonts:
                txt, maxsz, bold = '', 0.0, False
                for st, ft in fonts:
                    txt += H.unescape(re.sub(r'<[^>]+>', '', ft))
                    ms = re.search(r'font-size:(\d+(?:\.\d+)?)pt', st)
                    if ms:
                        maxsz = max(maxsz, float(ms.group(1)))
                    if 'font-weight:bold' in st:
                        bold = True
           else:
                txt, maxsz, bold = strip_tags(inner), 0.0, False
            txt = re.sub(r'\s+', ' ', txt).strip()
            if not txt:
                continue
            # 行内片段被 SEC 拆成多个 font 标签，需按位置拼接而非空格分隔
            lines.append({'t': txt, 'sz': maxsz, 'b': bold})
            if maxsz >= 12 and bold:
                headings.append({'page': idx, 'size': maxsz, 'text': txt})

        for tm in re.finditer(r'<table.*?</table>', p, re.S):
            rows = []
            for rm in re.finditer(r'<tr.*?</tr>', tm.group(0), re.S):
                cells = [strip_tags(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rm.group(0), re.S)]
                cells = [c for c in cells if c]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append({'page': idx, 'rows': rows})

        for im in IMG_RE.finditer(p):
            a = im.group(1)
            src_m = re.search(r'src="([^"]+)"', a)
            st_m = re.search(r'height:([\d.]+)pt;width:([\d.]+)pt', a)
            if not src_m:
                continue
            h_pt = float(st_m.group(1)) if st_m else 0.0
            w_pt = float(st_m.group(2)) if st_m else 0.0
            images.append({
                'page': idx, 'file': src_m.group(1),
                'height_pt': h_pt, 'width_pt': w_pt,
                # 整页扫描图判据：高≈792pt 且宽≈612pt
                'full_page_scan': h_pt >= 780 and w_pt >= 600,
            })

        pages.append({'page': idx, 'lines': lines})

    return raw, pages, headings, tables, images


def merge_headings(headings):
    """把同一页同一字号的碎片合并成完整标题（SEC 常把一句话拆成多个 font 标签）。"""
    out = []
    for h in headings:
        if out and out[-1]['page'] == h['page'] and out[-1]['size'] == h['size']:
            out[-1]['text'] = (out[-1]['text'] + ' ' + h['text']).strip()
        else:
            out.append(dict(h))
    return [h for h in out if len(h['text']) > 1]


def build_page_text(pages):
    return [{'page': p['page'], 'text': ' '.join(l['t'] for l in p['lines'])} for p in pages]


def main():
    ap = argparse.ArgumentParser(description='抽取源文档为结构化中间产物')
    ap.add_argument('source', help='本地文件路径（.htm/.html）')
    ap.add_argument('--workdir', required=True, help='产出目录（仓库外）')
    ap.add_argument('--slug', default=None)
    ap.add_argument('--source-url', default='', help='原始 URL，写进 manifest')
    args = ap.parse_args()

    if not os.path.exists(args.source):
        sys.exit(f'源文件不存在: {args.source}')
    slug = args.slug or re.sub(r'[^\w.-]+', '-', os.path.splitext(os.path.basename(args.source))[0])
    outdir = os.path.join(args.workdir, slug)
    os.makedirs(outdir, exist_ok=True)

    raw = open(args.source, 'rb').read()
    sha = hashlib.sha256(raw).hexdigest()

    if not args.source.lower().endswith(('.htm', '.html')):
        sys.exit('当前只支持 HTML；PDF 走 MinerU（fpdf scripts/parse.py）产出结构包后复用同一索引')

    _, pages, headings, tables, images = extract_html(args.source)
    heads = merge_headings(headings)
    page_text = build_page_text(pages)

    def dump(name, obj):
        with open(os.path.join(outdir, name), 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)

    dump('pages.json', pages)
    dump('heads.json', heads)
    dump('tables.json', tables)
    dump('page_text.json', page_text)
    images.sort(key=lambda x: x['page'])
    dump('images.json', images)

    full = '\n'.join(f"[p{t['page']}] {t['text']}" for t in page_text if t['text'].strip())
    with open(os.path.join(outdir, 'text.txt'), 'w', encoding='utf-8') as f:
        f.write(full)

    scans = [i for i in images if i['full_page_scan']]
    manifest = {
        'slug': slug,
        'source_file': os.path.abspath(args.source),
        'source_url': args.source_url,
        'sha256': sha,
        'size_bytes': len(raw),
        'pages': len(pages),
        'headings': len(heads),
        'tables': len(tables),
        'images': len(images),
        'full_page_scans': len(scans),
        'scan_pages': [i['page'] for i in scans],
        'chars': len(full),
        'workdir': outdir,
    }
    dump('manifest.json', manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
