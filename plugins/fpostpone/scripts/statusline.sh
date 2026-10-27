#!/usr/bin/env bash
# fpostpone statusLine —— 在 Claude Code 底栏常驻显示待执行的定时任务。
#
# 读影子表 ~/.cache/fpostpone/tasks.json 的 pending 项，渲染成一行。
# statusLine 每轮刷新，所以排完任务后立刻可见。
#
# 输出示例:
#   ⏳ 14:50 输出100内的质数（还有 6 分钟）
#   ⏳ 3 个待执行: 14:50 质数 · 明天9:02 transliter
#   （无待执行任务时不输出，保持底栏干净）
set -uo pipefail

FP_HOME="${FP_HOME:-$HOME/.cache/fpostpone}"
STORE="$FP_HOME/tasks.json"

[ -f "$STORE" ] || exit 0

python3 - "$STORE" <<'PY'
import json, sys
from datetime import datetime

store = sys.argv[1]
try:
    d = json.load(open(store))
except Exception:
    sys.exit(0)

pending = [t for t in d.get("tasks", []) if t.get("status") == "pending"]
if not pending:
    sys.exit(0)

now = datetime.now()


def parse_at(s):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def rel(dt):
    if dt is None:
        return ""
    sec = int((dt - now).total_seconds())
    if sec < 0:
        return "已到点"
    if sec < 3600:
        return f"还有 {sec // 60} 分钟"
    if sec < 86400:
        h, m = divmod(sec // 60, 60)
        return f"还有 {h}h{m}m" if m else f"还有 {h}h"
    return f"还有 {sec // 86400} 天"


def short(cmd, n=18):
    c = cmd.strip().replace("\n", " ")
    return c if len(c) <= n else c[: n - 1] + "…"


items = []
for t in sorted(pending, key=lambda x: parse_at(x.get("at", "")) or datetime.max):
    dt = parse_at(t.get("at", ""))
    items.append((dt, t))

if len(items) == 1:
    dt, t = items[0]
    stamp = dt.strftime("%H:%M") if dt and dt.date() == now.date() else (dt.strftime("%m-%d %H:%M") if dt else "?")
    print(f"⏳ {stamp} {short(t.get('cmd',''))}（{rel(dt)}）")
else:
    first_dt, first = items[0]
    stamp = first_dt.strftime("%H:%M") if first_dt and first_dt.date() == now.date() else (first_dt.strftime("%m-%d %H:%M") if first_dt else "?")
    print(f"⏳ {len(items)} 个待执行: {stamp} {short(first.get('cmd',''), 14)} · 最近{rel(first_dt)}")
PY