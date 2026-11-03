#!/usr/bin/env python3
"""下载并压缩原文图片，放到 lark-cli 可读目录。

为什么需要这一步：lark-cli 的 <img path="@./x.jpg"> 走路径 allowlist
（cwd / /tmp / ~/files），放别处静默失败；且 SEC 原图动辄 7MB 一张，
142MB 直接上传极慢。实测压到 1600px / quality85 后 142MB → 10MB，
飞书里看不出差别（正文宽度只有约 800px）。

为什么必须记录 y 坐标：图片在外层布局 div 上有 top，不记就不知道
图该插在正文哪一段之后，只能全堆页尾。
"""
import argparse
import json
import os
import sys
import urllib.request

UA = 'Mozilla/5.0 (research contact@example.com)'


def fetch(url, dst, timeout=60):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    if not data:
        raise RuntimeError('empty response')
    with open(dst, 'wb') as f:
        f.write(data)


def main():
    ap = argparse.ArgumentParser(description='下载并压缩原文图片')
    ap.add_argument('slug')
    ap.add_argument('--workdir', default=os.path.expanduser('~/digest-work'))
    ap.add_argument('--out', default=None,
                    help='输出目录（必须在 lark-cli allowlist 内），默认 ~/files/fdigest/<slug>-images')
    ap.add_argument('--max-px', type=int, default=1600)
    ap.add_argument('--quality', type=int, default=85)
    ap.add_argument('--no-resize', action='store_true')
    ap.add_argument('--source-url', default='',
                    help='源文档 URL；manifest 里缺 source_url 时用它补')
    args = ap.parse_args()

    d = os.path.join(args.workdir, args.slug)
    man = {}
    for name in ('manifest.json',):
        try:
            man = json.load(open(os.path.join(d, name)))
        except Exception:
            pass
    try:
        imgs = json.load(open(os.path.join(d, 'images.json')))
    except Exception:
        print(json.dumps({'error': 'no images.json', 'dir': d}))
        return

    out = os.path.expanduser(args.out or f'~/files/fdigest/{args.slug}-images')
    os.makedirs(out, exist_ok=True)

    # SEC 的 src 是相对文件名，基址 = 源文档 URL 去掉末段。
    # manifest 里没有 source_url 时（早期 extract 调用没传），退到 manifest
    # 的 source_file 同目录找同名图片；再不行才报错。
    src_url = man.get('source_url') or ''
    base = src_url.rsplit('/', 1)[0] + '/' if '/' in src_url else ''
    local_dir = os.path.dirname(man.get('source_file') or '')

    seen, downloaded, already, failed = set(), 0, 0, []
    for im in imgs:
        fn = im['file']
        if fn in seen:
            continue
        seen.add(fn)
        fp = os.path.join(out, fn)
        if os.path.exists(fp) and os.path.getsize(fp) > 0:
            already += 1
            continue
        # 本地已有原图（源文件同目录）优先，省一次下载
        local = os.path.join(local_dir, fn) if local_dir else ''
        if local and os.path.exists(local):
            try:
                import shutil
                shutil.copy2(local, fp)
                downloaded += 1
                continue
            except Exception:
                pass
        if not base:
            failed.append({'file': fn, 'why': 'no source_url in manifest'})
            continue
        try:
            fetch(base + fn, fp)
            downloaded += 1
        except Exception as e:
            failed.append({'file': fn, 'why': str(e)[:70]})
        # SEC 限速 10 req/s，保守到 ~8/s
        import time
        time.sleep(0.12)

    resized = 0
    if not args.no_resize:
        try:
            from PIL import Image
        except ImportError:
            print(json.dumps({'error': 'pillow_missing',
                              'hint': 'uv run --with pillow python3 prepare_images.py ...'}))
            return
        for fn in list(seen):
            fp = os.path.join(out, fn)
            if not os.path.exists(fp):
                continue
            try:
                im = Image.open(fp)
                if max(im.size) <= args.max_px:
                    continue
                im.thumbnail((args.max_px, args.max_px), Image.LANCZOS)
                im.convert('RGB').save(fp, 'JPEG', quality=args.quality, optimize=True)
                resized += 1
            except Exception:
                pass      # 损坏的图留着，让下游如实报缺

    total = sum(os.path.getsize(os.path.join(out, f))
                for f in os.listdir(out) if os.path.isfile(os.path.join(out, f)))
    print(json.dumps({
        'out': out, 'unique': len(seen), 'downloaded': downloaded,
        'already': already, 'resized': resized,
        'failed_n': len(failed), 'failed': failed[:8],
        'size_mb': round(total / 1024 / 1024, 1),
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
