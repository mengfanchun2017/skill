#!/usr/bin/env python3
"""fdigest translate — 分段翻译正文，结果按段缓存（可续跑、不重烧 token）。

按页切段送翻，翻译结果落 <workdir>/<slug>/zh/<page>.json，
每页一个文件 → 中断后重跑只补缺页，已翻的不重烧。

LLM 后端复用 Claude 当前生效预设（~/.cache/llm-merged.json 的 current），
协议走 Anthropic Messages。可用 --preset 指定。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

LLM_MERGED = os.path.expanduser('~/.cache/llm-merged.json')

SYSTEM = ('你是专业金融文件翻译。把给定英文段落译成中文，要求：'
          '① 数字、百分比、货币金额原样保留，不改写不换算；'
          '② 专有名词保留英文原名（如 Anthropic、Claude、AWS Trainium、Claude Code）；'
          '③ 不增删内容，不加解释，不合并段落；'
          '④ 逐段输出，每段一行，段间用单独一行 ---  分隔，顺序与原文一致；'
          '⑤ 只输出译文，不要任何前言后记。')


def load_preset(name=None):
    p = LLM_MERGED
    if not os.path.exists(p):
        sys.exit(f'找不到 {p}，先跑 ccconfig 的 lib/init-llm.sh 生成合并配置')
    d = json.load(open(p))
    llms = d.get('llms') or {}
    key = name or d.get('current') or ''
    cfg = llms.get(key)
    if not isinstance(cfg, dict):
        sys.exit(f'预设不存在: {key}')
    k = cfg.get('key')
    if isinstance(k, dict):
        k = k.get('key') or next((v for v in k.values() if isinstance(v, str)), '')
    return {'name': key, 'base_url': (cfg.get('base_url') or '').rstrip('/'),
            'key': k, 'model': cfg.get('model')}


def endpoint(cfg):
    """两种网关形态：base_url 已带 /v1 → OpenAI chat/completions；否则 Anthropic messages。"""
    base = cfg['base_url']
    if base.endswith('/v1'):
        return base + '/chat/completions', 'openai'
    return base + '/v1/messages', 'anthropic'


def call(cfg, text, max_tokens=8000, retries=3):
    url, proto = endpoint(cfg)
    if proto == 'openai':
        body = json.dumps({
            'model': cfg['model'], 'max_tokens': max_tokens,
            'messages': [{'role': 'system', 'content': SYSTEM},
                         {'role': 'user', 'content': text}],
        }).encode()
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + cfg['key']}
    else:
        body = json.dumps({
            'model': cfg['model'], 'max_tokens': max_tokens, 'system': SYSTEM,
            'messages': [{'role': 'user', 'content': text}],
        }).encode()
        headers = {'Content-Type': 'application/json',
                   'x-api-key': cfg['key'], 'anthropic-version': '2023-06-01'}
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read())
            if proto == 'openai':
                out = (d.get('choices') or [{}])[0].get('message', {}).get('content') or ''
            else:
                blocks = d.get('content') or []
                out = ''.join(b.get('text', '') for b in blocks if b.get('type') == 'text')
            if out.strip():
                return out
            # 空内容 → 已知网关故障，重试
            sys.stderr.write(f'  空内容，重试 {attempt+1}/{retries}\n')
        except urllib.error.HTTPError as e:
            sys.stderr.write(f'  HTTP {e.code}: {e.read()[:200]}\n')
        except Exception as e:
            sys.stderr.write(f'  {type(e).__name__}: {e}\n')
        time.sleep(2 * (attempt + 1))
    return None


def para_batches(lines, max_chars=5000):
    buf, size = [], 0
    for l in lines:
        if size + len(l) > max_chars and buf:
            yield buf
            buf, size = [], 0
        buf.append(l)
        size += len(l) + 1
    if buf:
        yield buf


def main():
    ap = argparse.ArgumentParser(description='分段翻译，按页缓存可续跑')
    ap.add_argument('slug')
    ap.add_argument('--workdir', default=os.path.expanduser('~/digest-work'))
    ap.add_argument('--preset', default=None)
    ap.add_argument('--start', type=int, default=1)
    ap.add_argument('--end', type=int, default=None)
    ap.add_argument('--force', action='store_true', help='忽略缓存重翻')
    args = ap.parse_args()

    d = os.path.join(args.workdir, args.slug)
    man = json.load(open(os.path.join(d, 'manifest.json')))
    pages = json.load(open(os.path.join(d, 'pages.json')))
    outdir = os.path.join(d, 'zh')
    os.makedirs(outdir, exist_ok=True)

    cfg = load_preset(args.preset)
    print(f"预设 {cfg['name']} / 模型 {cfg['model']}", file=sys.stderr)

    end = args.end or man['pages']
    done = skipped = failed = 0
    for p in pages:
        n = p['page']
        if n < args.start or n > end:
            continue
        out = os.path.join(outdir, f'{n:04d}.json')
        if os.path.exists(out) and not args.force:
            skipped += 1
            continue
        lines = [l['t'] for l in p['lines']
                 if not re.fullmatch(r'\d{1,3}', l['t']) and l['t'] != 'Table of Contents']
        lines = [l for l in lines if len(l) > 20]
        if not lines:
            json.dump({'page': n, 'src': [], 'zh': []}, open(out, 'w'), ensure_ascii=False)
            skipped += 1
            continue
        zh = []
        for batch in para_batches(lines):
            res = call(cfg, '\n'.join(batch))
            if res is None:
                failed += 1
                print(f'  第 {n} 页翻译失败，跳过（重跑会补）', file=sys.stderr)
                zh = None
                break
            zh.extend(x.strip() for x in res.split('\n---\n') if x.strip())
        if zh is None:
            continue
        json.dump({'page': n, 'src': lines, 'zh': zh}, open(out, 'w'), ensure_ascii=False)
        done += 1
        if done % 10 == 0:
            print(f'  已翻 {done} 页（当前 p{n}）', file=sys.stderr)

    print(json.dumps({'slug': args.slug, 'translated': done,
                      'cached': skipped, 'failed': failed}, ensure_ascii=False))


if __name__ == '__main__':
    main()
