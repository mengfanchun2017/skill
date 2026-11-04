#!/usr/bin/env python3
"""用 MinerU 批量 OCR 客户案例页（整页扫描图）。

为什么走 MinerU 而不是 vision 模型：
  MinerU 的 OCR 通道就是视觉通道，但输出的是带版面结构的 markdown
  （标题层级、表格、段落），比让通用 vision 模型"描述这张图"更贴近
  文档本身的组织结构。而且本机已配 token，不用新授权。

踩坑（实测 2026-11-04）：预签名上传 URL 用**空 Content-Type** 签名，
  任何带 Content-Type 的客户端（requests/urllib/curl）都会 403
  SignatureDoesNotMatch。PUT 必须显式发空 Content-Type。
  见 opendatalab/MinerU issue #5393。
"""
import json
import os
import sys
import time
import urllib.request
import zipfile

def load_conf():
    """读 mineru 配置：优先 skill-config，回落 ccprivate。真实 token 不进公开库。"""
    cands = [
        os.path.expanduser('~/.claude/skill-config/mineru.json'),
        os.path.expanduser('~/git/ccprivate/conf/mineru.json'),
    ]
    for c in cands:
        if os.path.exists(c):
            return json.load(open(c))
    raise SystemExit('未找到 mineru 配置，请填 ~/.claude/skill-config/mineru.json'
                     '（api_base + token）')


def api(cfg, path, body=None, method='GET'):
    url = cfg['api_base'] + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + cfg['token'],
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def upload(url, path):
    data = open(path, 'rb').read()
    # Content-Type 必须为空字符串 —— 见文件头踩坑说明
    req = urllib.request.Request(url, data=data, method='PUT',
                                 headers={'Content-Type': ''})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.status


def main():
    slug = sys.argv[1]
    imgs_dir = sys.argv[2]
    out_md = sys.argv[3]
    workdir = os.environ.get('FDIGEST_WORKDIR') or os.path.expanduser('~/digest-work')
    d = os.path.join(workdir, slug)
    imgs = json.load(open(os.path.join(d, 'images.json')))

    # 案例页 = 整页扫描图里连续排布的那一段
    scans = [x for x in imgs if x.get('full_page_scan')]
    pages = sorted({x['page'] for x in scans})
    runs, cur = [], [pages[0]] if pages else []
    for a, b in zip(pages, pages[1:]):
        if b == a + 1:
            cur.append(b)
        else:
            runs.append(cur); cur = [b]
    if cur:
        runs.append(cur)
    runs.sort(key=len, reverse=True)
    case_pages = set(runs[0]) if runs else set()

    seen, todo = set(), []
    for x in imgs:
        if x['page'] in case_pages and x['file'] not in seen:
            seen.add(x['file'])
            todo.append(x)
    todo.sort(key=lambda y: y['page'])

    cfg = load_conf()
    names = [x['file'] for x in todo]
    r = api(cfg, '/file-urls/batch', {
        'enable_formula': True, 'enable_table': True, 'language': 'en',
        'model_version': 'vlm',
        'files': [{'name': n, 'is_ocr': True} for n in names],
    }, 'POST')
    if r.get('code') != 0:
        print(json.dumps({'error': 'url_batch', 'msg': r.get('msg')}))
        return
    batch = r['data']['batch_id']
    urls = r['data']['file_urls']
    print('batch=%s files=%d' % (batch, len(urls)), file=sys.stderr)

    up_ok = 0
    for x, u in zip(todo, urls):
        fp = os.path.join(os.path.abspath(os.path.expanduser(imgs_dir)), x['file'])
        try:
            if upload(u, fp) == 200:
                up_ok += 1
        except Exception as e:
            print('upload fail %s: %s' % (x['file'], e), file=sys.stderr)
    print('uploaded=%d/%d' % (up_ok, len(todo)), file=sys.stderr)

    res = None
    for i in range(60):
        time.sleep(10)
        d2 = api(cfg, '/extract-results/batch/' + batch)
        items = (d2.get('data') or {}).get('extract_result') or []
        done = [x for x in items if x.get('state') == 'done']
        print('poll%d done=%d/%d' % (i + 1, len(done), len(todo)), file=sys.stderr)
        if len(done) == len(todo):
            res = done
            break
        if any(x.get('state') == 'failed' for x in items):
            print('有失败项', file=sys.stderr)

    if not res:
        print(json.dumps({'error': 'timeout', 'batch': batch}))
        return

    zipdir = os.environ.get('TMPDIR', '/tmp') + '/fdigest_mu'
    os.makedirs(zipdir, exist_ok=True)
    out = {}
    for item in res:
        fn = item['file_name']
        pg = next((x['page'] for x in todo if x['file'] == fn), 0)
        zp = os.path.join(zipdir, fn + '.zip')
        urllib.request.urlretrieve(item['full_zip_url'], zp)
        try:
            with zipfile.ZipFile(zp) as z:
                md = next((n for n in z.namelist() if n.endswith('full.md')), None)
                out[fn] = {'page': pg, 'md': z.read(md).decode('utf-8') if md else ''}
        except Exception as e:
            out[fn] = {'page': pg, 'md': '', 'err': str(e)[:80]}

    json.dump(out, open(out_md, 'w'), ensure_ascii=False, indent=1)
    got = sum(1 for v in out.values() if v.get('md', '').strip())
    print(json.dumps({'ok': True, 'pages': len(todo), 'with_text': got,
                      'out': out_md,
                      'chars': sum(len(v.get('md', '')) for v in out.values())},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
