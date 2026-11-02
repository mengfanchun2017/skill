#!/usr/bin/env python3
"""fdigest index — 把结构包建成可检索的段落级索引（SQLite FTS5）。

索引是派生物：正文真相源在飞书，索引丢了可从飞书重建。
库放仓库外（默认 ~/digest-work/index.db），绝不落 ~/git/。

切块策略：按段落切，但保留 page + 章节路径（chapter > section），
这样检索命中后能精确回指「哪份文件 · 第几页 · 哪个章节」。
"""
import argparse
import json
import os
import re
import sqlite3
import sys

DEFAULT_DB = os.path.expanduser('~/digest-work/index.db')
MIN_CHUNK = 120       # 太短的碎片（页眉页脚、页码）不建块
MAX_CHUNK = 1800      # 超长段落二次切分，避免单块塞满上下文


def init_db(conn):
    conn.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS docs (
        slug TEXT PRIMARY KEY,
        title TEXT,
        source_url TEXT,
        source_file TEXT,
        sha256 TEXT,
        pages INTEGER,
        chars INTEGER,
        feishu_url TEXT,
        archived_at TEXT,
        disclosed_at TEXT,
        subject TEXT,
        doc_kind TEXT
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
        slug UNINDEXED,
        page UNINDEXED,
        chapter,
        section,
        text,
        tokenize = 'unicode61'
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS zh_chunks USING fts5(
        slug UNINDEXED,
        page UNINDEXED,
        chapter,
        section,
        text,
        tokenize = 'trigram'
    );
    CREATE TABLE IF NOT EXISTS figs (
        slug TEXT, page INTEGER, file TEXT, kind TEXT, caption TEXT
    );
    ''')
    conn.commit()


def chapter_path(heads, page):
    """返回 page 所在章节路径：最近的 20pt 章 + 最近的 12pt 节。"""
    chap = sect = ''
    for h in heads:
        if h['page'] > page:
            break
        if h['size'] >= 20:
            chap, sect = h['text'], ''
        elif h['size'] >= 12:
            sect = h['text']
    return chap, sect


def split_long(text):
    if len(text) <= MAX_CHUNK:
        return [text]
    out, buf = [], ''
    for sent in re.split(r'(?<=[.!?。！？])\s+', text):
        if len(buf) + len(sent) > MAX_CHUNK and buf:
            out.append(buf.strip())
            buf = ''
        buf += sent + ' '
    if buf.strip():
        out.append(buf.strip())
    return out


def index_doc(conn, workdir, slug, meta=None):
    d = os.path.join(workdir, slug)
    man = json.load(open(os.path.join(d, 'manifest.json')))
    heads = json.load(open(os.path.join(d, 'heads.json')))
    pages = json.load(open(os.path.join(d, 'pages.json')))
    meta = meta or {}

    conn.execute('DELETE FROM chunks WHERE slug=?', (slug,))
    conn.execute('DELETE FROM figs WHERE slug=?', (slug,))

    n = 0
    for p in pages:
        # 按行聚合段落：连续正文行拼成一段，遇到标题或缩进断开时切
        paras, buf = [], []
        for l in p['lines']:
            t = l['t']
            is_head = l['sz'] >= 12 and l['b']
            looks_footer = bool(re.fullmatch(r'\d{1,3}', t)) or t == 'Table of Contents'
            if is_head or looks_footer:
                if buf:
                    paras.append(' '.join(buf))
                    buf = []
                continue
            buf.append(t)
        if buf:
            paras.append(' '.join(buf))

        chap, sect = chapter_path(heads, p['page'])
        for para in paras:
            para = para.strip()
            if len(para) < MIN_CHUNK:
                continue
            for piece in split_long(para):
                conn.execute(
                    'INSERT INTO chunks (slug,page,chapter,section,text) VALUES (?,?,?,?,?)',
                    (slug, p['page'], chap, sect, piece))
                n += 1

    # 中文索引：从 zh-blocks 取块级译文，按页 + 章节路径入库。
    # 中文必须用 trigram（unicode61 对中文不分词）；不足 3 字由 search.py 走 LIKE。
    zhdir = os.path.join(d, 'zh-blocks')
    if os.path.isdir(zhdir):
        conn.execute('DELETE FROM zh_chunks WHERE slug=?', (slug,))
        zh_n = 0
        for fn in sorted(os.listdir(zhdir)):
            if not fn.endswith('.json'):
                continue
            z = json.load(open(os.path.join(zhdir, fn)))
            pg = z.get('page')
            chap, sect = chapter_path(heads, pg)
            for b in z.get('blocks') or []:
                t = (b.get('zh') or '').strip()
                if len(t) < MIN_CHUNK // 4:      # 中文信息密度高，阈值放宽
                    continue
                for piece in split_long(t):
                    conn.execute(
                        'INSERT INTO zh_chunks (slug,page,chapter,section,text) VALUES (?,?,?,?,?)',
                        (slug, pg, chap, sect, piece))
                    zh_n += 1
        print(f'  中文块 {zh_n}', file=sys.stderr)

    conn.execute('''INSERT OR REPLACE INTO docs
        (slug,title,source_url,source_file,sha256,pages,chars,feishu_url,archived_at,disclosed_at,subject,doc_kind)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', (
        slug, meta.get('title', slug), man.get('source_url', ''),
        man.get('source_file', ''), man.get('sha256', ''),
        man.get('pages', 0), man.get('chars', 0),
        meta.get('feishu_url', ''), meta.get('archived_at', ''),
        meta.get('disclosed_at', ''), meta.get('subject', ''),
        meta.get('doc_kind', '')))
    conn.commit()
    return n


def main():
    ap = argparse.ArgumentParser(description='建段落级检索索引')
    ap.add_argument('slug', nargs='?', help='要索引的文档 slug；省略则重建全部')
    ap.add_argument('--workdir', default=os.path.expanduser('~/digest-work'))
    ap.add_argument('--db', default=DEFAULT_DB)
    ap.add_argument('--meta', default=None, help='JSON 字符串，文档元数据（title/feishu_url 等）')
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.db), exist_ok=True)
    conn = sqlite3.connect(args.db)
    init_db(conn)

    meta = json.loads(args.meta) if args.meta else {}
    if args.slug:
        n = index_doc(conn, args.workdir, args.slug, meta)
        total = conn.execute('SELECT count(*) FROM chunks').fetchone()[0]
        print(json.dumps({'slug': args.slug, 'chunks': n, 'total_chunks': total}, ensure_ascii=False))
    else:
        total = 0
        for name in sorted(os.listdir(args.workdir)):
            if os.path.exists(os.path.join(args.workdir, name, 'manifest.json')):
                total += index_doc(conn, args.workdir, name)
        print(json.dumps({'rebuilt': True, 'total_chunks': total}, ensure_ascii=False))
    conn.close()


if __name__ == '__main__':
    main()
