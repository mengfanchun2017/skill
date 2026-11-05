#!/usr/bin/env python3
"""把 MinerU OCR 出的案例 markdown 译成中文。

复用 scripts/llm.py 的预设解析 + 协议自适应 + flock 并发闸 + 429 退避。
按块翻（标题/段落/表格分别处理），保留原始结构，翻译结果回写到同一 markdown
骨架里，由 build_cases.py 再转成 DocxXML。
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import call, load_preset  # noqa: E402

SYSTEM = (
    '你是专业财经与技术文档译者。把英文翻译成简体中文，要求：\n'
    '1. 忠实原意，不增删内容，不加工观点\n'
    '2. 保留机构名/产品名的常用中文译法（如 DoorDash、Claude、Anthropic 保持原名）\n'
    '3. 数字、百分比、金额原样保留\n'
    '4. 只输出译文，不要任何解释或前缀'
)


def split_blocks(md):
    """markdown → [(kind, raw)]，kind ∈ head/text/table/quote。

    块边界必须与原文一致：build_cases.py 的 _pair_quotes 靠「引文块 + 紧随的
    署名块」配对，如果这里把署名并进引文（或反过来跨块合并），下游就配不上，
    署名会漂成正文。所以翻译只做 1:1 块替换，不跨块重组。
    """
    out = []
    for b in re.split(r'\n\s*\n', md.strip()):
        b = b.strip()
        if not b:
            continue
        if b.startswith('#'):
            out.append(('head', b))
        elif '<table>' in b:
            out.append(('table', b))
        elif b.startswith('"') or b.startswith('“'):
            out.append(('quote', b))
        else:
            out.append(('text', re.sub(r'\s+', ' ', b)))
    return out


def tr_texts(cfg, texts):
    if not texts:
        return []
    numbered = '\n'.join(f'{i+1}. {t}' for i, t in enumerate(texts))
    res = call(cfg, (SYSTEM, numbered), max_tokens=8000)
    out = []
    for line in res.split('\n'):
        s = line.strip()
        if not s or re.fullmatch(r'-{3,}', s):
            continue
        out.append(re.sub(r'^\s*\d+[.、]\s*', '', s).strip())
    if len(out) < len(texts):
        out += [''] * (len(texts) - len(out))
    return out[:len(texts)]


def tr_table(cfg, tbl):
    """表格逐行翻单元格，纯数字行不动。"""
    rows = []
    for rm in re.finditer(r'<tr>(.*?)</tr>', tbl, re.S):
        cells = re.findall(r'<td>(.*?)</td>', rm.group(1), re.S)
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        if not cells:
            continue
        if any(re.search(r'[A-Za-z]{3,}', c) for c in cells):
            cells = tr_texts(cfg, cells)
        rows.append(cells)
    if not rows:
        return tbl
    body = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    return '<table>' + body + '</table>'


def main():
    src = sys.argv[1]
    out = sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    data = json.load(open(src))
    cfg = load_preset(os.environ.get('PRESET'))
    print('预设 %s / %s' % (cfg['name'], cfg['model']), file=sys.stderr)

    # 每页拆块，批量翻译
    pages = []
    for fn, v in sorted(data.items(), key=lambda x: x[1]['page']):
        pages.append((fn, v['page'], split_blocks(v.get('md', ''))))

    jobs = []       # (pi, bi, kind, text)
    for pi, (fn, pg, blocks) in enumerate(pages):
        for bi, (kind, raw) in enumerate(blocks):
            if kind in ('head', 'text', 'quote'):
                jobs.append((pi, bi, kind, raw))

    print('待翻 %d 块（另有表格逐行处理）' % len(jobs), file=sys.stderr)
    results = {}

    # 逐页落盘：整批跑完再写，中途被杀（session 重启实测丢过一整轮）
    # 就全白干。按页缓存后重跑只补没译的页。
    cache_dir = out + '.parts'
    os.makedirs(cache_dir, exist_ok=True)

    def save_page(pi):
        fn, pg, blocks = pages[pi]
        rebuilt = []
        for bi, (kind, raw) in enumerate(blocks):
            z = results.get((pi, bi), '')
            if kind == 'head':
                rebuilt.append('#' * len(re.match(r'^#+', raw).group(0)) + ' '
                               + (z or re.sub(r'^#+\s*', '', raw)))
            else:
                rebuilt.append(z or raw)
        json.dump({'page': pg, 'md': '\n\n'.join(rebuilt)},
                  open(os.path.join(cache_dir, fn + '.json'), 'w'), ensure_ascii=False)

    for pi in range(len(pages)):
        fp = os.path.join(cache_dir, pages[pi][0] + '.json')
        if os.path.exists(fp):
            try:
                json.load(open(fp))
                continue          # 已译完的页直接跳过
            except Exception:
                pass

    todo_pages = [pi for pi in range(len(pages))
                  if not os.path.exists(os.path.join(cache_dir, pages[pi][0] + '.json'))]
    print('待译页 %d/%d（其余已缓存）' % (len(todo_pages), len(pages)), file=sys.stderr)

    def work_page(pi):
        fn, pg, blocks = pages[pi]
        texts, kinds, idxs = [], [], []
        for bi, (kind, raw) in enumerate(blocks):
            if kind == 'table':
                continue
            idxs.append(bi); kinds.append(kind)
            if kind == 'head':
                texts.append(re.sub(r'^#+\s*', '', raw))
            else:
                texts.append(re.sub(r'^["“]|["”]$', '', raw))
        zh = tr_texts(cfg, texts) if texts else []
        for bi, z in zip(idxs, zh):
            results[(pi, bi)] = z
        for bi, (kind, raw) in enumerate(blocks):
            if kind == 'table':
                try:
                    results[(pi, bi)] = tr_table(cfg, raw)
                except Exception as e:
                    print('table fail p%d: %s' % (pg, e), file=sys.stderr)
                    results[(pi, bi)] = raw
        save_page(pi)
        print('  p%d 完成（%d 块）' % (pg, len(blocks)), file=sys.stderr)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work_page, todo_pages))

    # 汇总所有分片（已缓存的页也从分片读）
    outdata = {}
    for pi, (fn, pg, blocks) in enumerate(pages):
        fp = os.path.join(cache_dir, fn + '.json')
        if os.path.exists(fp):
            outdata[fn] = json.load(open(fp))
        else:
            save_page(pi)
            outdata[fn] = json.load(open(fp))

    json.dump(outdata, open(out, 'w'), ensure_ascii=False, indent=1)
    miss = sum(1 for (pi, bi), v in results.items() if not v)
    print(json.dumps({'ok': True, 'pages': len(pages), 'blocks': len(jobs),
                      'empty': miss, 'out': out,
                      'chars': sum(len(v['md']) for v in outdata.values())},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
