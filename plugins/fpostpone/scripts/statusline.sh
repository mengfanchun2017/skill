#!/usr/bin/env bash
# fpostpone statusLine —— 底栏常驻显示定时任务（待执行的 + 最近完成的）。
#
# 读影子表 ~/.cache/fpostpone/tasks.json。statusLine 每轮刷新，排完即见。
#
# 输出形态（单行）:
#   ⏳ 15:20 计算30以内质数（还有 2 分钟）
#   ⏳ 2 个待执行: 15:20 xxx · 16:40 yyy
#   ✓ 15:20 计算30以内质数 已完成 15:20-15:34        ← 无待执行时显示最近完成的
#   （空表时不输出，保持底栏干净）
set -uo pipefail

FP_HOME="${FP_HOME:-$HOME/.cache/fpostpone}"
STORE="$FP_HOME/tasks.json"
SHOW_FINISHED="${FP_STATUSLINE_SHOW_FINISHED:-3}"   # 无待执行时最多回显几条已完成

[ -f "$STORE" ] || exit 0

python3 - "$STORE" "$SHOW_FINISHED" <<'PY'
import json, sys
from datetime import datetime

store, show_finished = sys.argv[1], int(sys.argv[2])
try:
    d = json.load(open(store))
except Exception:
    sys.exit(0)

tasks = d.get("tasks", [])
if not tasks:
    sys.exit(0)

now = datetime.now()


def parse(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
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
    if sec < 60:
        return "即将执行"
    if sec < 3600:
        return f"还有 {sec // 60} 分钟"
    if sec < 86400:
        h, m = divmod(sec // 60, 60)
        return f"还有 {h}小时{m}分" if m else f"还有 {h} 小时"
    return f"还有 {sec // 86400} 天"


def short(cmd, n=18):
    c = (cmd or "").strip().replace("\n", " ")
    return c if len(c) <= n else c[: n - 1] + "…"


def clock(dt):
    return dt.strftime("%H:%M") if dt else "?"


pending = sorted(
    (t for t in tasks if t.get("status") in ("pending", "running")),
    key=lambda x: parse(x.get("at", "")) or datetime.max,
)
finished = sorted(
    (t for t in tasks if t.get("status") == "finished"),
    key=lambda x: parse(x.get("finished", "")) or datetime.min,
    reverse=True,
)

parts = []

# 1) 待执行 / 执行中（优先显示——用户最关心接下来会自动发生什么）
for t in pending[:2]:
    dt = parse(t.get("at", ""))
    stamp = clock(dt) if dt and dt.date() == now.date() else (
        dt.strftime("%m-%d %H:%M") if dt else "?")
    if t.get("status") == "running":
        parts.append(f"▶ {stamp} {short(t.get('cmd',''), 14)}（执行中）")
    else:
        parts.append(f"⏳ {stamp} {short(t.get('cmd',''), 14)}（{rel(dt)}）")
extra = len(pending) - len(parts)
if extra > 0:
    parts.append(f"+{extra} 个待执行")

# 2) 无待执行时回显最近的已完成（不消除——用户要知道做过什么）
if not pending and finished:
    for t in finished[:show_finished]:
        sd, fd = parse(t.get("started", "")), parse(t.get("finished", ""))
        rng = f"{clock(sd)}-{clock(fd)}" if sd and fd else clock(fd)
        parts.append(f"✓ {clock(parse(t.get('at','')))} {short(t.get('cmd',''), 16)} 已完成 {rng}")

if parts:
    print("  ".join(parts))
PY