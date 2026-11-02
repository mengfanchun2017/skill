#!/usr/bin/env python3
"""fdigest render-zh — 把逐页译文拼成可上传的飞书 DocxXML。

中文译文 + 原文页码锚点。飞书单文档块数有上限，超长文档按 --max-blocks 分卷，
输出多个 xml 文件（卷1、卷2…），由调用方分别创建再挂到同一父节点下。
"""
import argparse
import json
import os
import re
import sys

MAX_BLOCKS_DEFAULT = 4000     # 单卷块数上限，保守取值避免触发飞书限制


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def is_heading(line, heads_by_page, page):
    """译文行是否对应原文标题：靠原文侧标定的标题文本位置判断。"""
    return None


def main():
    ap = argparse.ArgumentParser(description='拼装译文 DocxXML')
    ap.add_argument('slug')
    ap.add_argument('--workdir', default=os.path.expanduser('~/digest-work'))
    ap.add_argument('--max-blocks', type=int, default=MAX_BLOCKS_DEFAULT)
    ap.add_argument('--title', default='全文中文翻译')
    args = ap.parse_args()

    d = os.path.join(args.workdir, args.slug)
    zhdir = os.path.join(d, 'zh')
    if not os.path.isdir(zhdir):
        sys.exit(f'没有译文目录: {zhdir}')
    pages = json.load(open(os.path.join(d, 'pages.json')))
    heads = json.load(open(os.path.join(d, 'heads.json')))

    # 标题判定：原文该页中字号>=12 且加粗的行，按其文本在 src 行里的下标定位
    headmap = {}
    for p in pages:
        idx = set()
        for i, l in enumerate(p['lines']):
            if l['sz'] >= 12 and l['b']:
                idx.add(i)
        headmap[p['page']] = idx
    # 译文与原文的段落索引已对齐（translate.py 逐段编号），但 translate 过滤掉了短行，
    # 这里用 zh 文件的 src 列表反查原文行号更稳
    srcidx = {}
    for p in pages:
        srcidx[p['page']] = {t: i for i, (t, l) in enumerate(
            [(l['t'], l) for l in p['lines']])}

    blocks = [f'<title>{esc(args.title)}</title>',
              '<callout emoji="📖" background-color="light-gray">'
              '<p>本页是 S-1 招股说明书全文中文翻译，按原文页码顺序逐页对应，页首标注原文页码以便复核。'
              '专有名词与数字保留原文形态，不做换算。</p></callout>']
    vol, vols = 1, []
    count = 0

    for f in sorted(os.listdir(zhdir)):
        if not f.endswith('.json'):
            continue
        data = json.load(open(os.path.join(zhdir, f)))
        pg = data['page']
        srcs, zhs = data.get('src') or [], data.get('zh') or []
        if not zhs:
            continue
        if count >= args.max_blocks:
            vols.append((vol, blocks))
            vol += 1
            blocks = [f'<title>{esc(args.title)}（续 {vol}）</title>']
            count = 0

        # 找该页的标题行（原文 12pt+ 加粗）
        head_pos = set()
        if pg in headmap:
            for t, i in srcidx.get(pg, {}).items():
                if i in headmap[pg]:
                    head_pos.add(t)

        blocks.append(f'<h2><span text-color="blue">原文第 {pg} 页</span></h2>')
        count += 1
        for src_line, zh_line in zip(srcs, zhs):
            zh_line = zh_line.strip()
            if not zh_line:
                continue
            if src_line in head_pos:
                blocks.append(f'<h3>{esc(zh_line)}</h3>')
            else:
                blocks.append(f'<p>{esc(zh_line)}</p>')
            count += 1
        # 译文比原文短的段落（LLM 合并）单独补
        if len(zhs) > len(srcs):
            for extra in zhs[len(srcs):]:
                if extra.strip():
                    blocks.append(f'<p>{esc(extra.strip())}</p>')
                    count += 1

    vols.append((vol, blocks))

    outdir = os.path.join(d, 'xml')
    os.makedirs(outdir, exist_ok=True)
    paths = []
    for v, bl in vols:
        p = os.path.join(outdir, f'zh-{v}.xml')
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(bl))
        paths.append((v, p, len(bl)))

    print(json.dumps({'volumes': [{'vol': v, 'path': p, 'blocks': n} for v, p, n in paths]},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
