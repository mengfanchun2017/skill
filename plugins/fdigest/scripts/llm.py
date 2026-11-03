#!/usr/bin/env python3
"""LLM 调用层 — 预设解析 + 协议自适应。fdigest 与 fpdf 共用这一份。

为什么单独抽出来：之前 fdigest/scripts/translate.py 和 fpdf/scripts/translate.py
各写了一份「读 ~/.cache/llm-merged.json → 拼 endpoint → POST」的实现，
协议判断还互相矛盾（fpdf 硬编码 Anthropic，fdigest 猜 base_url 后缀），
遇到 OpenAI 形态的内网网关时一边挂一边通。同一件事只该有一份代码。

真相源：~/.cache/llm-merged.json（init-llm.sh 合并 llm.json 的 key +
llmprivate.json 的 base_url/model 后的快照）。
"""
import fcntl
import json
import os
import random
import time
import urllib.error
import urllib.request

LLM_MERGED = os.path.expanduser('~/.cache/llm-merged.json')
LLM_CURRENT = os.path.expanduser('~/.claude/llm-current')
BRIDGE = 'http://127.0.0.1:8898'

# ---- 并发治理层（从 transliter/translate-doc.py 移植，两边共用一份）----
# 为什么用 flock 槽位而不是进程内信号量：每份报告是一个独立 python 进程，
# 彼此看不见，单靠进程内线程池约束不住总量（N 份报告 = N 个独立池，叠成 N 倍
# 打爆端点）。flock 随进程消亡自动释放，被 kill 的进程不会漏占槽位。
LLM_MAX_INFLIGHT = int(os.environ.get('LLM_MAX_INFLIGHT', '0'))   # 0 = 不限
SLOT_DIR = os.environ.get('SLOT_DIR',
                          os.path.expanduser('~/.cache/transliter/llm_slots'))
RETRY_CODES = {408, 429, 500, 502, 503, 504}
RETRY_N = int(os.environ.get('LLM_RETRY_N', '5'))
RETRY_BASE = float(os.environ.get('LLM_RETRY_BASE', '1.5'))
# 失败率超过此值才认为「这个模型不行」并整批重译。单个段落失败就重烧整轮
# 代价极高（实测 2564 段文档仅 1 段失败也白烧 45 万 prompt token）。
FALLBACK_FAIL_RATIO = float(os.environ.get('FALLBACK_FAIL_RATIO', '0.05'))

_retry_lock = None
RETRY_STATS = {'total': 0, 'http': {}, 'net': 0, 'empty': 0}


def acquire_slot():
    if LLM_MAX_INFLIGHT <= 0:
        return None
    os.makedirs(SLOT_DIR, exist_ok=True)
    n = LLM_MAX_INFLIGHT
    while True:
        start = random.randrange(n)   # 随机起点，避免所有线程都从 0 号槽撞起
        for k in range(n):
            path = os.path.join(SLOT_DIR, 's%05d' % ((start + k) % n))
            try:
                fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
            except OSError:
                continue
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd
            except OSError:
                os.close(fd)
        time.sleep(0.02 + random.uniform(0, 0.05))


def release_slot(fd):
    if fd is None:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def backoff(e, attempt):
    """优先尊重 Retry-After，否则指数退避加抖动。"""
    try:
        ra = e.headers.get('Retry-After')
    except Exception:
        ra = None
    if ra:
        try:
            return max(0.0, float(ra))
        except ValueError:
            pass
    return RETRY_BASE ** (attempt + 1) + random.uniform(0, 0.5)


def count_retry(kind, code=None):
    """调并发时唯一的依据就是 429 有多少。以前只写 stderr，一被 tail 就丢。"""
    import threading
    global _retry_lock
    if _retry_lock is None:
        _retry_lock = threading.Lock()
    with _retry_lock:
        RETRY_STATS['total'] += 1
        if code is not None:
            RETRY_STATS['http'][str(code)] = RETRY_STATS['http'].get(str(code), 0) + 1
        else:
            RETRY_STATS[kind] = RETRY_STATS.get(kind, 0) + 1


def load_preset(name=None):
    """取 preset 的 base_url / key / model / use_bridge。"""
    try:
        d = json.load(open(LLM_MERGED))
    except Exception:
        return None
    llms = d.get('llms') or {}
    if not name:
        name = d.get('current') or ''
        if not name:
            try:
                name = open(LLM_CURRENT).read().strip()
            except Exception:
                name = ''
    p = llms.get(name)
    if not isinstance(p, dict):
        return None
    key = p.get('key')
    if isinstance(key, dict):
        key = key.get('key') or next(
            (v for v in key.values() if isinstance(v, str)), '')
    return {'base_url': (p.get('base_url') or p.get('url') or '').rstrip('/'),
            'key': key, 'model': p.get('model'),
            'use_bridge': p.get('use_bridge', False), 'name': name}


def endpoint(cfg):
    """按网关形态选协议。

    两种形态实测：base_url 已带 /v1 的多是 OpenAI 兼容网关（只暴露
    /v1/chat/completions，POST /v1/v1/messages 直接 404）；其余走
    Anthropic Messages。走本地 bridge 时固定 Anthropic（bridge 只为
    Claude Code 暴露 /v1/messages）。
    """
    if cfg.get('use_bridge'):
        return f'{BRIDGE}/v1/messages', 'anthropic'
    base = cfg['base_url']
    if base.endswith('/v1'):
        return base + '/chat/completions', 'openai'
    return base + '/v1/messages', 'anthropic'


def call(cfg, text, max_tokens=8000, retries=None, temperature=0.2):
    """发一次请求，返回正文字符串。429/5xx 按 Retry-After 或指数退避重试。"""
    url, proto = endpoint(cfg)
    sys_prompt = None
    if isinstance(text, tuple):        # (system, user)
        sys_prompt, text = text

    if proto == 'openai':
        msgs = []
        if sys_prompt:
            msgs.append({'role': 'system', 'content': sys_prompt})
        msgs.append({'role': 'user', 'content': text})
        body = {'model': cfg['model'], 'messages': msgs,
                'max_tokens': max_tokens, 'temperature': temperature}
        hdrs = {'Content-Type': 'application/json'}
        if cfg.get('key'):
            hdrs['Authorization'] = f"Bearer {cfg['key']}"
    else:
        body = {'model': cfg['model'], 'max_tokens': max_tokens,
                'temperature': temperature,
                'thinking': {'type': 'disabled'},
                'messages': [{'role': 'user', 'content': text}]}
        if sys_prompt:
            body['system'] = sys_prompt
        hdrs = {'Content-Type': 'application/json',
                'anthropic-version': '2023-06-01'}
        if cfg.get('key') and not cfg.get('use_bridge'):
            hdrs['x-api-key'] = cfg['key']

    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=hdrs)
    last = None
    for attempt in range(RETRY_N if retries is None else max(retries, RETRY_N)):
        last_attempt = attempt == (RETRY_N if retries is None else max(retries, RETRY_N)) - 1
        wait = 0.0
        slot = acquire_slot()      # 跨进程在途闸：槽位抢不到就在这里等
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                d = json.loads(r.read())
            if proto == 'openai':
                ch = (d.get('choices') or [{}])[0]
                out = (ch.get('message') or {}).get('content') or ''
            else:
                out = ''.join(b.get('text', '') for b in d.get('content', [])
                              if b.get('type') == 'text')
            if out.strip():
                return out
            last = 'empty content'
            count_retry('empty')
        except urllib.error.HTTPError as e:
            last = f'HTTP {e.code}'
            if e.code not in RETRY_CODES or last_attempt:
                raise RuntimeError(f'LLM 调用失败: {last}')
            wait = backoff(e, attempt)
            count_retry('http', e.code)
        except Exception as e:
            last = str(e)
            if last_attempt:
                break
            wait = RETRY_BASE ** (attempt + 1) + random.uniform(0, 0.5)
            count_retry('net')
        finally:
            release_slot(slot)     # 退避期间让出槽位，别占着空转
        if wait:
            time.sleep(wait)
    raise RuntimeError(f'LLM 调用失败: {last}')
