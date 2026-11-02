#!/usr/bin/env python3
"""fdigest search — 在已索引的文档库里做段落级检索。

输出每条命中带完整坐标：slug + 页码 + 章节路径 + 原文片段 + 飞书链接。
这是「降低阅读负载」的核心：不把整份文档塞进上下文，只取命中段。
"""
import argparse
import json
import os
import sqlite3
import re
import sys

DEFAULT_DB = os.path.expanduser('~/digest-work/index.db')


def fts_query(q):
    """FTS5 语法保护：把用户输入按词包成短语，避免特殊字符炸查询。"""
    terms = [t for t in q.replace('"', ' ').split() if t]
    if not terms:
        return None
    return ' OR '.join(f'"{t}"' for t in terms)


def main():
    ap = argparse.ArgumentParser(description='段落级检索')
    ap.add_argument('query', nargs='+')
    ap.add_argument('--db', default=DEFAULT_DB)
    ap.add_argument('--slug', default=None, help='限定在某份文档内检索')
    ap.add_argument('--limit', type=int, default=8)
    ap.add_argument('--context', type=int, default=280, help='片段截断长度')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--lang', choices=['auto', 'en', 'zh'], default='auto',
                    help='检索语言：auto 按查询字符自动判断')
    args = ap.parse_args()

    if not os.path.exists(args.db):
        sys.exit(f'索引不存在: {args.db}（先跑 index.py 建索引）')

    q = ' '.join(args.query)
    fq = fts_query(q)
    if not fq:
        sys.exit('查询为空')

    conn = sqlite3.connect(args.db)
    has_zh = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='zh_chunks'").fetchone()
    lang = args.lang
    if lang == 'auto':
        lang = 'zh' if re.search(r'[\u4e00-\u9fff]', q) else 'en'

    if lang == 'zh' and has_zh and len(q) >= 3:
        # trigram 分词：按整串匹配中文子串；<3 字时 trigram 无法命中，走 LIKE 兜底
        sql = '''SELECT z.slug, z.page, '' AS chapter, '' AS section,
                        snippet(zh_chunks, 2, '《', '》', '…', 40) AS snip,
                        d.title, d.feishu_url
                 FROM zh_chunks z LEFT JOIN docs d ON d.slug=z.slug
                 WHERE zh_chunks MATCH ?'''
        fq = '"' + q.replace('"', '') + '"'
    elif lang == 'zh' and has_zh:
        sql = '''SELECT z.slug, z.page, '' AS chapter, '' AS section,
                        substr(z.text,1,200) AS snip,
                        d.title, d.feishu_url
                 FROM zh_chunks z LEFT JOIN docs d ON d.slug=z.slug
                 WHERE z.text LIKE ?'''
        fq = '%' + q + '%'
    else:
        sql = '''SELECT c.slug, c.page, c.chapter, c.section,
                        snippet(chunks, 4, '《', '》', '…', 40) AS snip,
                        d.title, d.feishu_url
                 FROM chunks c LEFT JOIN docs d ON d.slug=c.slug
                 WHERE chunks MATCH ?'''
    params = [fq]
    if args.slug:
        sql += (' AND z.slug=?' if lang == 'zh' and has_zh else ' AND c.slug=?')
        params.append(args.slug)
    sql += ' ORDER BY rank LIMIT ?'
    params.append(args.limit)

    rows = conn.execute(sql, params).fetchall()
    out = []
    for slug, page, chap, sect, snip, title, url in rows:
        out.append({
            'slug': slug, 'page': page, 'chapter': chap, 'section': sect,
            'snippet': snip, 'title': title, 'feishu_url': url,
            'cite': f'{title} · 第 {page} 页 · {chap}' + (f' > {sect}' if sect else ''),
        })

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        if not out:
            print(f'无命中: {q}')
        for i, r in enumerate(out, 1):
            print(f"{i}. {r['cite']}")
            print(f"   {r['snippet']}")
            print(f"   链接: {r['feishu_url'] or '(未归档到飞书)'}")
    conn.close()


if __name__ == '__main__':
    main()
