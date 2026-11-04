#!/bin/bash
# fcore/lib/genre.sh — 技能派发注册表匹配
#
# 取代 fworch 的单一职责（读体裁注册表 → 判体裁 → 派发）。注册表在私有仓
# ccprivate/conf/fcore.yaml（真值），公开仓只放 .example 模板。
#
# 设计要点：注册表**只有一份**。此前触发词存在三处（~/CLAUDE.md、
# registry.yaml、每个 SKILL.md 的 description），实测已漂移 ——
# ~/CLAUDE.md 曾写「写报告 → fresearchframe」而实际该派 fworch-report。

f_registry_file() {
    local f
    # 1. 用户/私有仓配置（f_conf_file 已按 ccprivate → 用户数据目录 顺序找）
    if f="$(f_conf_file fcore.yaml 2>/dev/null)" && [[ -f "$f" ]]; then
        printf '%s\n' "$f"; return 0
    fi
    # 2. plugin 自带的用户 config.yaml（官方通道写到 plugin 目录时）
    if f="$(f_plugin_dir 2>/dev/null)" && [[ -f "$f/config.yaml" ]]; then
        printf '%s\n' "$f/config.yaml"; return 0
    fi
    # 3. 内置默认（模板级，无真值）—— 保证独立用户也能派发
    if [[ -n "${F_CORE_LIB:-}" && -f "$F_CORE_LIB/../references/fcore.default.yaml" ]]; then
        printf '%s\n' "$F_CORE_LIB/../references/fcore.default.yaml"; return 0
    fi
    if [[ -f "$_ROOT/references/fcore.default.yaml" ]]; then
        printf '%s\n' "$_ROOT/references/fcore.default.yaml"; return 0
    fi
    return 1
}

# f_genre_match <需求文本> — 输出 JSON: {domain, skill, orchestrator, spec, config, score}
# 匹配规则：触发词命中数 × 词长权重；全不命中时给 domain=null 让调用方自己判断。
f_genre_match() {
    local text="$1" reg
    reg="$(f_registry_file)" || { echo '{"error":"no_registry"}'; return 1; }
    python3 - "$reg" "$text" <<'PYEOF'
import json, sys
try:
    import yaml
except ImportError:
    print(json.dumps({"error": "no_yaml"})); sys.exit(1)
path, text = sys.argv[1], sys.argv[2]
d = yaml.safe_load(open(path)) or {}

def hits(triggers, text):
    """返回命中的触发词。两级匹配：
    ① 完整短语出现过 → 高分（长词加权）
    ② 触发词拆成词元，命中比例高 → 低分兜底
    "PDF排到飞书" 不含 "PDF转飞书"，但含 "PDF"+"飞书" → 靠词元兜底命中。"""
    best = (0, None)
    for t in triggers or []:
        if not t:
            continue
        if t in text:
            s = len(t) ** 2
            if s > best[0]:
                best = (s, t)
    if best[0]:
        return best
    # 词元兜底：把触发词与文本都切成 2 字以上的中文块 + 英文词
    import re
    def toks(s):
        return set(re.findall(r"[A-Za-z]+|[一-鿿]{2,}", s.lower()))
    tt = toks(text)
    for t in triggers or []:
        if not t:
            continue
        st = toks(t)
        if not st:
            continue
        inter = st & tt
        ratio = len(inter) / len(st)
        if ratio >= 0.5:
            s = int(ratio * len(t) ** 2 * 0.6)   # 打折：词元匹配不如整短语可靠
            if s > best[0]:
                best = (s, t)
    return best

best = None
for dom, spec in (d.get("domains") or {}).items():
    s, t = hits(spec.get("trigger"), text)
    if s and (best is None or s > best["score"]):
        best = {"domain": dom, "skill": spec.get("skill"),
                "trigger": t, "score": s, "desc": spec.get("desc", "")}
for g, spec in (d.get("genres") or {}).items():
    s, t = hits(spec.get("trigger"), text)
    if s:
        s += 10   # 体裁比域更具体，同命中优先
        if best is None or s > best["score"]:
            best = {"domain": spec.get("parent", "write"), "genre": g,
                    "skill": spec.get("skill"), "orchestrator": spec.get("orchestrator"),
                    "spec": spec.get("spec"), "config": spec.get("config"),
                    "trigger": t, "score": s, "desc": spec.get("desc", "")}
if best is None:
    print(json.dumps({"domain": None, "hint": "无触发词命中，需模型判断或问用户"}, ensure_ascii=False))
else:
    print(json.dumps(best, ensure_ascii=False))
PYEOF
}

# f_genre_list — 列出所有域与体裁（供 /fhub 展示菜单）
f_genre_list() {
    local reg
    reg="$(f_registry_file)" || { echo '{"error":"no_registry"}'; return 1; }
    python3 - "$reg" <<'PYEOF'
import json, sys, yaml
d = yaml.safe_load(open(sys.argv[1])) or {}
out = {"domains": [], "genres": []}
for k, v in (d.get("domains") or {}).items():
    out["domains"].append({"domain": k, "skill": v.get("skill"),
                           "desc": v.get("desc", ""), "trigger": v.get("trigger") or []})
for k, v in (d.get("genres") or {}).items():
    out["genres"].append({"genre": k, "parent": v.get("parent"),
                          "orchestrator": v.get("orchestrator"), "spec": v.get("spec"),
                          "desc": v.get("desc", ""), "trigger": v.get("trigger") or []})
print(json.dumps(out, ensure_ascii=False, indent=2))
PYEOF
}

export -f f_registry_file f_genre_match f_genre_list 2>/dev/null || true
