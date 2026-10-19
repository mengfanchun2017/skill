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


def call_llm(cfg, prompt, max_tokens=None):
    """走 Anthropic Messages 协议。

    实测本机 bridge(8898) 只暴露 /v1/messages（Anthropic 格式），POST
    /v1/chat/completions 返回 404 —— bridge 把内网 OpenAI 上游转成 Anthropic 给
    Claude 用，不反向暴露 OpenAI 面。所以这里也说 Anthropic 格式。

    思考预算：上游 DeepSeek 是推理模型，thinking 先占 max_tokens 预算，
    8000 时整批 30 段全被 thinking 吃光、stop_reason=max_tokens、正文 0 字符。
    与 transliter 对齐（translate-config.sh: MAX_TOKENS=100000 + LLM_THINKING=disabled）：
    预算给到 100000 + 显式传 thinking.disabled。注意本机 bridge 只对
    enabled/adaptive 做转发（openai_bridge.py 的 thinking 分支），disabled 落到
    bridge 里被忽略、不会传给上游网关 —— 所以真正兜底是「换非推理模型 + 拆批重试」。
    """
    if max_tokens is None:
        max_tokens = int(os.environ.get("FPDF_MAX_TOKENS", "100000"))
    url = f"{BRIDGE}/v1/messages" if cfg.get("use_bridge") else \
        cfg["base_url"].rstrip("/") + "/v1/messages"
    body = json.dumps({
        "model": cfg["model"],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    hdrs = {"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
    if not cfg.get("use_bridge"):
        hdrs["x-api-key"] = cfg["key"]
    req = urllib.request.Request(url, data=body, headers=hdrs)
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.loads(r.read())
    parts = [b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"]
    return "".join(parts)


def collect_texts(content_list):
    out = []
    for e in content_list:
        if e.get("type") == "text" and e.get("text", "").strip():
            out.append(e["text"])
    return out


def collect_texts_v2(pages):
    """从 content_list_v2 收集待译文本。

    v2 的文本藏在 fragment 数组里（paragraph_content / title_content / list_items），
    行内公式是支持 equation_inline 片段 —— 翻译只取 text 片段的 content，公式原样保留
    （render 时按同一 fragment 顺序重拼，译文 map 的 key 就是这些 text 片段）。
    """
    keys = ("paragraph_content", "title_content", "list_items",
            "page_header_content", "page_footer_content")
    out = []

    def walk(frags):
        for f in frags or []:
            if isinstance(f, dict) and f.get("type") == "text":
                c = (f.get("content") or "").strip()
                if c:
                    out.append(f["content"])

    for pg in pages:
        for e in pg:
            c = e.get("content") or {}
            for k in keys:
                v = c.get(k)
                if k == "list_items" and isinstance(v, list):
                    for it in v:
                        walk(it.get("item_content"))
                elif isinstance(v, list):
                    walk(v)
            for capk in ("image_caption", "chart_caption", "table_caption", "table_footnote"):
                for x in (c.get(capk) or []):
                    if isinstance(x, dict) and x.get("type") == "text" and (x.get("content") or "").strip():
                        out.append(x["content"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--target", default="zh", choices=["zh", "en"])
    ap.add_argument("--preset", default=None, help="llm.json preset 名（默认用当前生效模型）")
    ap.add_argument("--batch-size", type=int, default=30)
    ap.add_argument("--source", default="auto", choices=["auto", "v1", "v2"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    wd = Path(args.workdir)
    cl_path = wd / f"{args.slug}.content_list.json"
    v2_path = wd / f"{args.slug}.content_list_v2.json"
    v2 = json.loads(v2_path.read_text(encoding="utf-8")) if v2_path.exists() else []
    v1 = json.loads(cl_path.read_text(encoding="utf-8")) if cl_path.exists() else []
    use_v2 = args.source == "v2" or (args.source == "auto" and v2)
    if not v1 and not v2:
        print("ERROR: 无 content_list(.json/_v2.json)，无法翻译（flash 档不含结构）", file=sys.stderr)
        sys.exit(2)
    texts = collect_texts_v2(v2) if use_v2 else collect_texts(v1)
    print(f"[fpdf] 译文源={'v2' if use_v2 else 'v1'} 待译片段={len(texts)}", file=sys.stderr)
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
    # 模型兜底链：当前 preset（可能是推理模型，思考会吃满预算）失效时切到非推理模型。
    # 实测 officeds41flash(deepseek-v4.1-flash) 30 段整批 thinking 吃光 8000 预算、
    # 正文 0 字符；而 deepseek-v4-flash 是同一网关的非推理版（reasoning_tokens=0），
    # 同样 30 段 mt=8000 稳定出 29-30 段。默认链 = 当前 preset → 非推理副本。
    candidates = [cfg]
    for alt in (os.environ.get("FPDF_FALLBACK_PRESETS", "officedsflash,homedsflash,deepseek41flash")
                .split(",")):
        alt = alt.strip()
        if alt and alt != preset:
            c = load_preset(alt)
            if c and c.get("base_url"):
                candidates.append(c)
    cur = {"cfg": cfg}

    def build_prompt(batch):
        numbered = "\n".join(f"<<<{j}>>>{t}" for j, t in enumerate(batch))
        return (
            f"你是专业学术翻译。把下面用 <<<N>>> 编号的段落逐段翻译成{lang}。\n"
            f"要求：\n"
            f"1. 严格保持 <<<N>>> 编号和段落一一对应，输出格式与输入一致。\n"
            f"2. 不要合并、拆分或遗漏任何段落。\n"
            f"3. 保留原文的专有名词、缩写、公式、引用编号 [1] 等不译。\n"
            f"4. 只输出译文，不要任何解释或前后缀。\n\n{numbered}"
        )

    def _parse(resp):
        parts = re.split(r"<<<(\d+)>>>", resp)
        got = {}
        for k in range(1, len(parts), 2):
            try:
                got[int(parts[k])] = parts[k + 1].strip()
            except (IndexError, ValueError):
                pass
        return got

    def translate_batch(batch, depth=0):
        """返回 {段落: 译文}。输出缺失过半视为预算被 thinking 吃光 → 拆半递归；
        仍全空则整条链换下一个模型重试该批。

        实测 max_tokens 给到 32k 时推理模型能出全 30 段，但耗时和 token 都翻倍，
        且模型档位会变 —— 所以拆半 + 换非推理模型比单纯加大预算更省。
        """
        pad = "  " * depth
        last = {}
        for idx, c in enumerate(candidates):
            try:
                resp = call_llm(c, build_prompt(batch))
            except Exception as e:
                print(f"{pad}[fpdf] {c['name']} 调用失败: {type(e).__name__}: {str(e)[:160]}",
                      file=sys.stderr)
                continue
            got = _parse(resp)
            if len(got) > len(last):
                last = got
            print(f"{pad}[fpdf] {c['name']}: {len(batch)} 段 → {len(got)} 段译文", file=sys.stderr)
            if len(got) >= len(batch) / 2:
                cur["cfg"] = c
                return {orig: got.get(j, "") for j, orig in enumerate(batch)}
            if idx + 1 < len(candidates):
                print(f"{pad}[fpdf] 输出缺失过半（疑 thinking 吃光预算），换下一个模型",
                      file=sys.stderr)
        # 全链都没拿到一半：拆半继续（batch==1 时接受最后一次的产出）
        if len(batch) > 1:
            print(f"{pad}[fpdf] 所有模型均缺失，拆半重试", file=sys.stderr)
            half = (len(batch) + 1) // 2
            out = translate_batch(batch[:half], depth + 1)
            out.update(translate_batch(batch[half:], depth + 1))
            return out
        return {orig: last.get(0, "") for orig in batch}

    for bi, batch in enumerate(
            [texts[i:i + args.batch_size] for i in range(0, len(texts), args.batch_size)]):
        print(f"[fpdf] 批次 {bi+1}/{(len(texts)+args.batch_size-1)//args.batch_size}", file=sys.stderr)
        result.update(translate_batch(batch))

    result["__title__"] = meta.get("title") or wd.name
    out_path = args.out or str(wd / f"{args.slug}.trans.json")
    Path(out_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    miss = sum(1 for k, v in result.items() if k != "__title__" and not v)
    print(f"[fpdf] 译文 → {out_path}（{len(result)-1} 段，{miss} 段空）", file=sys.stderr)
    print(json.dumps({"trans_map": out_path, "segments": len(result) - 1, "empty": miss},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()