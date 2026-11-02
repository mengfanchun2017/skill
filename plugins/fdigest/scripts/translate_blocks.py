#!/usr/bin/env python3
"""fdigest translate-blocks — 按结构块翻译（标题/段落/表格），供 build_zh 拼装。

与 translate.py（逐行）的区别：这里翻的是**已还原结构的块**，不是碎行。
输出 <workdir>/<slug>/zh-blocks/NNNN.json = {page, items:[{kind,level,zh}]}，
块级缓存可续跑；表格按行翻，键为 (page, table_idx, row_idx)。

为��么不用逐行译文：行级译文拼回段落会得到"译文按行断开"的碎片，而且
标题与正文的行会被切开。块级是唯一能让中文文档读起来像原文的粒度。
"""
import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_zh import build_blocks  # noqa: E402
from llm import call, load_preset  # noqa: E402  公共 LLM 层，与 fpdf 共用

SYSTEM = (
    '你是金融文件的专业译者。把英文译成简体中文。规则：'
    '① 术语按中国证监会/投行惯例（"prospectus"=招股说明书，"GAAP"=美国公认会计原则，'
    '"Run-Rate Revenue"=年化收入，"NRR"=净收入留存率，公司名保留英文）；'
    '② 数字、金额、百分比、日期、页码、注册号一律原样保留，不改写不换算；'
    '③ 输入按 1. 2. 3. 编号，输出必须保持同样编号，编号后直接接译文；'
    '④ 只输出译文行，不要任何前言后记，不要分隔线；'
    '⑤ 表格单元格逐格翻译，保持逗号和括号内的数字不动。'
)

BATCH_CHARS = 4000


def batches(items, max_chars=BATCH_CHARS):
    """打包成翻译批次，返回 (batch_items, text, index_map)。"""
    buf, size = [], 0
    for it in items:
        n = len(it['text']) + 12
        if size + n > max_chars and buf:
            yield buf
            buf, size = [], 0
        buf.append(it)
        size += n
    if buf:
        yield buf


def main():
    ap = argparse.ArgumentParser(description='结构块翻译')
    ap.add_argument('slug')
    ap.add_argument('--workdir', default=os.path.expanduser('~/digest-work'))
    ap.add_argument('--preset', default=None)
    ap.add_argument('--workers', type=int, default=10)
    ap.add_argument('--start', type=int, default=1)
    ap.add_argument('--end', type=int, default=None)
    ap.add_argument('--only-text', action='store_true', help='只翻正文块，跳过表格')
    args = ap.parse_args()

    d = os.path.join(args.workdir, args.slug)
    pages = json.load(open(os.path.join(d, 'pages.json')))
    tables = json.load(open(os.path.join(d, 'tables.json')))
    tb = {}
    for t in tables:
        tb.setdefault(t['page'], []).append(t['rows'])

    outdir = os.path.join(d, 'zh-blocks')
    os.makedirs(outdir, exist_ok=True)
    cfg = load_preset(args.preset)
    print(f"预设 {cfg['name']} / {cfg['model']}", file=sys.stderr)

    end = args.end or len(pages)
    todo = []
    for p in pages:
        n = p['page']
        if not (args.start <= n <= end):
            continue
        out = os.path.join(outdir, f'{n:04d}.json')
        if os.path.exists(out):
            continue
        blocks = build_blocks(p, [], [r for rs in tb.get(n, []) for r in rs])
        if not blocks and n not in tb:
            json.dump({'page': n, 'blocks': [], 'tables': []}, open(out, 'w'), ensure_ascii=False)
            continue
        # rows 保持三层：表格列表 → 行 → 单元格（不能拍平，否则每行变成一个独立表格）
        todo.append((n, blocks, tb.get(n, []), out))

    print(f'待翻 {len(todo)} 页', file=sys.stderr)
    done, failed = 0, 0
    lock = threading.Lock()

    def tr_many(texts):
        """一次请求翻一批，返回与输入等长的译文列表。"""
        if not texts:
            return []
        numbered = '\n'.join(f'{i+1}. {t}' for i, t in enumerate(texts))
        res = call(cfg, (SYSTEM, numbered), max_tokens=8000)
        out = []
        for line in res.split('\n'):
            if not line.strip():
                continue
            if re.fullmatch(r'\s*-{3,}\s*', line):
                continue
            out.append(re.sub(r'^\s*\d+[.、]\s*', '', line).strip())
        # 行数与输入不符时按顺序截断/补齐，不整体丢弃（否则整页重来）
        if len(out) < len(texts):
            out += [''] * (len(texts) - len(out))
        return out[:len(texts)]

    def work(item):
        nonlocal done, failed
        n, blocks, rows, out = item
        try:
            texts = [b['text'] for b in blocks]
            zhs = []
            for batch in batches([{'text': t, 'kind': blocks[i]['kind']}
                                  for i, t in enumerate(texts)]):
                zhs.extend(tr_many([x['text'] for x in batch]))
            # 表格：每张表逐行逐格翻。rows 是 [表格][行][单元格] 三层，必须原样保留，
            # 拍平会让每行变成一个独立表格（曾导致 158 张表变成几百张单行表，渲染全丢）。
            tzh = []
            for tbl in rows:
                out_rows = []
                for r in tbl:
                    cells = [str(c) for c in r]
                    if any(re.search(r'[A-Za-z]{3,}', c) for c in cells):
                        out_rows.append(tr_many(cells))
                    else:
                        out_rows.append(cells)   # 纯数字行不翻
                tzh.append(out_rows)
            json.dump({'page': n,
                       'blocks': [{'kind': b['kind'], 'level': b.get('level'), 'zh': z}
                                  for b, z in zip(blocks, zhs)],
                       'tables': tzh},
                      open(out, 'w'), ensure_ascii=False)
            with lock:
                done += 1
                if done % 20 == 0:
                    print(f'  已完成 {done}/{len(todo)}', file=sys.stderr)
        except Exception as e:
            with lock:
                failed += 1
            print(f'  p{n} 失败: {e}', file=sys.stderr)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, todo))

    print(json.dumps({'pages_done': done, 'failed': failed,
                      'outdir': outdir}, ensure_ascii=False))


if __name__ == '__main__':
    main()
