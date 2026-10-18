#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""fpdf 翻译层 — 结构包 → 译文映射 map.json。

为什么单独一步而不塞进 render.py：
    翻译要调 LLM，render 必须保持纯确定性（同输入同输出，可重跑可校验）。
    把 LLM 结果落到 map.json，render 只做查表替换 —— 重跑排版不再重烧 token。

LLM 后端复用 ~/.claude/llm-current（与 Claude 当前模型一致，零配置），
协议/密钥从 ccprivate/conf/llm.json 的 preset 读。fallback 依次尝试。

用法：
    translate.py <slug> --workdir DIR [--target zh|en] [--preset NAME] [--dry-run]
输出：<workdir>/<slug>.trans.json   {"__title__": "...", "段落原文": "段落译文", ...}
"""
import sys, os, json, argparse, urllib.request, urllib.error, re
from pathlib import Path

LLM_MERGED = os.path.expanduser("~/.cache/llm-merged.json")
LLM_CURRENT = os.path.expanduser("~/.claude/llm-current")
BRIDGE = "http://127.0.0.1:8898"


def load_preset(name):
    """取 preset 的 base_url/key/model。

    真相源是 init-llm.sh 产出的合并快照 ~/.cache/llm-merged.json —— 它已把三层
    （llm.json 的 key / llmprivate.json 的 base_url+model / 自定义）合好。
    直接读 ccprivate/conf/llm.json 只有 key，拿不到 base_url/model。
    """
    try:
        d = json.load(open(LLM_MERGED))
    except Exception:
        return None
    llms = d.get("llms") or {}
    if not name:
        name = d.get("current") or ""
    p = llms.get(name)
    if not isinstance(p, dict):
        return None
    key = p.get("key")
    if isinstance(key, dict):
        key = key.get("key") or next((v for v in key.values() if isinstance(v, str)), "")
    return {"base_url": p.get("base_url") or p.get("url"), "key": key,
            "model": p.get("model"), "use_bridge": p.get("use_bridge", False),
            "name": name}


def current_preset_name():
    try:
        return open(LLM_CURRENT).read().strip()
    except Exception:
        return ""


def call_llm(cfg, prompt, max_tokens=8000):
    """OpenAI 兼容 chat completions。

    use_bridge=True 的 preset 上游是内网 OpenAI-only 端点，本机 bridge(8898) 已按
    当前 preset 配好 upstream（claude 自己也走它）→ 直接打 bridge 即可，无需自己
    拼内网鉴权/host_header。
    """
    if cfg.get("use_bridge"):
        url = f"{BRIDGE}/v1/chat/completions"
        hdrs = {"Content-Type": "application/json"}
    else:
        url = cfg["base_url"].rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        hdrs = {"Content-Type": "application/json",
                "Authorization": f"Bearer {cfg['key']}"}
    body = json.dumps({
        "model": cfg["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }).encode()
    req = urllib.request.Request(url, data=body, headers=hdrs)
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"]


def collect_texts(content_list):
    out = []
    for e in content_list:
        if e.get("type") == "text" and e.get("text", "").strip():
            out.append(e["text"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--target", default="zh", choices=["zh", "en"])
    ap.add_argument("--preset", default=None, help="llm.json preset 名（默认用当前生效模型）")
    ap.add_argument("--batch-size", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    wd = Path(args.workdir)
    cl_path = wd / f"{args.slug}.content_list.json"
    if not cl_path.exists():
        print("ERROR: 无 content_list.json，无法翻译（flash 档不含结构）", file=sys.stderr)
        sys.exit(2)
    cl = json.loads(cl_path.read_text(encoding="utf-8"))
    texts = collect_texts(cl)
    meta = json.loads((wd / f"{args.slug}.meta.json").read_text(encoding="utf-8")) \
        if (wd / f"{args.slug}.meta.json").exists() else {}

    preset = args.preset or current_preset_name()
    cfg = load_preset(preset) if preset else None
    if not cfg or not cfg.get("base_url"):
        print(f"ERROR: 取不到 LLM 配置（preset={preset!r}, conf={LLM_MERGED}）。"
              f"指定 --preset 或检查 llm.json。", file=sys.stderr)
        sys.exit(3)

    print(f"[fpdf] 翻译 target={args.target} preset={preset} 段数={len(texts)}", file=sys.stderr)
    if args.dry_run:
        print(json.dumps({"preset": preset, "model": cfg["model"],
                          "segments": len(texts)}, ensure_ascii=False))
        return

    lang = {"zh": "中文", "en": "English"}[args.target]
    result = {}
    # 标题
    title = wd.name
    batches = [texts[i:i + args.batch_size] for i in range(0, len(texts), args.batch_size)]
    for bi, batch in enumerate(batches):
        numbered = "\n".join(f"<<<{j}>>>{t}" for j, t in enumerate(batch))
        prompt = (
            f"你是专业学术翻译。把下面用 <<<N>>> 编号的段落逐段翻译成{lang}。\n"
            f"要求：\n"
            f"1. 严格保持 <<<N>>> 编号和段落一一对应，输出格式与输入一致。\n"
            f"2. 不要合并、拆分或遗漏任何段落。\n"
            f"3. 保留原文的专有名词、缩写、公式、引用编号 [1] 等不译。\n"
            f"4. 只输出译文，不要任何解释或前后缀。\n\n{numbered}"
        )
        try:
            resp = call_llm(cfg, prompt)
        except Exception as e:
            print(f"ERROR: 批次 {bi} 调用失败: {type(e).__name__}: {str(e)[:300]}", file=sys.stderr)
            sys.exit(1)
        # 解析 <<<N>>>译文
        parts = re.split(r"<<<(\d+)>>>", resp)
        got = {}
        for k in range(1, len(parts), 2):
            try:
                got[int(parts[k])] = parts[k + 1].strip()
            except (IndexError, ValueError):
                pass
        for j, orig in enumerate(batch):
            result[orig] = got.get(j, "")
        print(f"[fpdf] 批次 {bi+1}/{len(batches)} 完成 ({len(got)}/{len(batch)} 段)", file=sys.stderr)

    result["__title__"] = title
    out_path = args.out or str(wd / f"{args.slug}.trans.json")
    Path(out_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    miss = sum(1 for v in result.values() if not v)
    print(f"[fpdf] 译文 → {out_path}（{len(result)-1} 段，{miss} 段空）", file=sys.stderr)
    print(json.dumps({"trans_map": out_path, "segments": len(result) - 1, "empty": miss},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()