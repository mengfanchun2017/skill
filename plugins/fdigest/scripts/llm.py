#!/usr/bin/env python3
"""LLM 调用层 — 预设解析 + 协议自适应。fdigest 与 fpdf 共用这一份。

为什么单独抽出来：之前 fdigest/scripts/translate.py 和 fpdf/scripts/translate.py
各写了一份「读 ~/.cache/llm-merged.json → 拼 endpoint → POST」的实现，
协议判断还互相矛盾（fpdf 硬编码 Anthropic，fdigest 猜 base_url 后缀），
遇到 OpenAI 形态的内网网关时一边挂一边通。同一件事只该有一份代码。

真相源：~/.cache/llm-merged.json（init-llm.sh 合并 llm.json 的 key +
llmprivate.json 的 base_url/model 后的快照）。
"""
import json
import os
import time
import urllib.request

LLM_MERGED = os.path.expanduser('~/.cache/llm-merged.json')
LLM_CURRENT = os.path.expanduser('~/.claude/llm-current')
BRIDGE = 'http://127.0.0.1:8898'


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


def call(cfg, text, max_tokens=8000, retries=3, temperature=0.2):
    """发一次请求，返回正文字符串。空内容/超时/5xx 会重试。"""
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
    for attempt in range(retries):
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
        except Exception as e:
            last = str(e)
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f'LLM 调用失败: {last}')
