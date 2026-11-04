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
    f="$(f_conf_file fcore.yaml 2>/dev/null)" || return 1
    [[ -f "$f" ]] && printf '%s\n' "$f"
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
best = None
for dom, spec in (d.get("domains") or {}).items():
    for t in spec.get("trigger") or []:
        if t and t in text:
            score = len(t) ** 2
            if best is None or score > best["score"]:
                best = {"domain": dom, "skill": spec.get("skill"),
                        "trigger": t, "score": score, "desc": spec.get("desc", "")}
for g, spec in (d.get("genres") or {}).items():
    for t in spec.get("trigger") or []:
        if t and t in text:
            score = len(t) ** 2 + 10   # 体裁比域更具体，同命中优先
            if best is None or score > best["score"]:
                best = {"domain": spec.get("parent", "write"), "genre": g,
                        "skill": spec.get("skill"), "orchestrator": spec.get("orchestrator"),
                        "spec": spec.get("spec"), "config": spec.get("config"),
                        "trigger": t, "score": score, "desc": spec.get("desc", "")}
if best is None:
    print(json.dumps({"domain": None, "hint": "无触发词命中，需模型判断或问用户"}))
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
