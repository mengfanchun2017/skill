#!/usr/bin/env bash
# fpostpone 任务登记表 —— 记录定时任务全生命周期，供 statusLine / list 展示。
#
# session-only 的 CronCreate 任务没有任何用户可见文件（不写 scheduled_tasks.json），
# 用户在终端里查不到。这里在 ~/.cache/fpostpone/tasks.json 留一份影子记录：
# 排定 → 开始 → 完成，全程留痕，**完成后不自动删除**（用户要知道做过什么）。
# 真伪仍以 CronList 为准（那边跑完自删；这里是历史账本）。
#
# 状态机: pending → running → finished
#
# 用法:
#   tasks.sh add   --id <id> --cron "<cron>" --at "<human>" --cmd "<命令>"
#   tasks.sh start --id <id>          # 任务真正开始执行时调用（记实际开始时间）
#   tasks.sh done  --id <id>          # 任务干完时调用（记实际结束时间）
#   tasks.sh list [--pending-only]
#   tasks.sh drop  --id <id>          # 删除某条记录（用户不想留了）
#   tasks.sh prune [--keep N]         # 只保留最近 N 条已完成（默认 50）
set -euo pipefail

FP_HOME="${FP_HOME:-$HOME/.cache/fpostpone}"
STORE="$FP_HOME/tasks.json"

ensure_store() {
    mkdir -p "$FP_HOME"
    [ -f "$STORE" ] || echo '{"tasks": []}' > "$STORE"
}

# 定位目标记录：--id X（可含前缀模糊匹配）或 --at "<排定时间>"（稳定键，排任务前就已知）。
# 输出 "id<TAB>at" 供后续按任一字段更新；找不到则输出空。
locate() {
    local id="" at=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --id) id="${2:-}"; shift 2 ;;
            --at) at="${2:-}"; shift 2 ;;
            *)    [ -z "$id" ] && id="${1:-}"; shift ;;
        esac
    done
    [ -n "$id$at" ] || { echo "需要 --id 或 --at" >&2; exit 1; }
    python3 - "$STORE" "$id" "$at" <<'PY'
import json, sys
store, wid, wat = sys.argv[1:4]
try:
    d = json.load(open(store))
except Exception:
    d = {"tasks": []}
for t in d.get("tasks", []):
    if t.get("status") == "finished":
        continue
    if wid and (t.get("id") == wid or str(t.get("id", "")).startswith(wid)):
        print(t.get("id"), t.get("at", ""), sep="\t")
        sys.exit(0)
    if wat and t.get("at") == wat:
        print(t.get("id"), t.get("at", ""), sep="\t")
        sys.exit(0)
# 模糊匹配失败时：若 wat 给了，按 at 兜底（可能是已完成记录）
if wat:
    for t in d.get("tasks", []):
        if t.get("at") == wat:
            print(t.get("id"), t.get("at", ""), sep="\t")
            sys.exit(0)
sys.exit(1)
PY
}

# 按 id 或 at 更新一条记录的字段。参数: <id> <at> <key> <value> [key value ...]
update_fields() {
    local tid="$1" tat="$2"; shift 2
    ensure_store
    python3 - "$STORE" "$tid" "$tat" "$@" <<'PY'
import json, sys
store, tid, tat = sys.argv[1:4]
pairs = sys.argv[4:]
d = json.load(open(store))
hit = None
for t in d.get("tasks", []):
    if tid and (t.get("id") == tid or str(t.get("id", "")).startswith(tid)):
        hit = t
        break
    if tat and t.get("at") == tat:
        hit = t
        break
if hit is not None:
    for i in range(0, len(pairs) - 1, 2):
        hit[pairs[i]] = pairs[i + 1]
json.dump(d, open(store, "w"), ensure_ascii=False, indent=1)
PY
}

cmd_add() {
    local id="" cron="" at="" cmd="" kind="session" recurring="false"
    local session="${CLAUDE_CODE_SESSION_ID:-}"
    while [ $# -gt 0 ]; do
        case "$1" in
            --id)        id="${2:-}"; shift 2 ;;
            --cron)      cron="${2:-}"; shift 2 ;;
            --at)        at="${2:-}"; shift 2 ;;
            --cmd)       cmd="${2:-}"; shift 2 ;;
            --kind)      kind="${2:-}"; shift 2 ;;
            --session)   session="${2:-}"; shift 2 ;;
            --recurring) recurring="${2:-}"; shift 2 ;;
            *) echo "未知参数: $1" >&2; exit 1 ;;
        esac
    done
    [ -n "$id" ] || { echo "--id 必填" >&2; exit 1; }

    ensure_store
    python3 - "$STORE" "$id" "$cron" "$at" "$cmd" "$kind" "$recurring" "$session" <<'PY'
import json, sys
from datetime import datetime
store, tid, cron, at, cmd, kind, recurring, session = sys.argv[1:9]
d = json.load(open(store))
d["tasks"] = [t for t in d.get("tasks", []) if t.get("id") != tid]
d["tasks"].append({
    "id": tid, "cron": cron, "at": at, "cmd": cmd,
    "kind": kind, "recurring": recurring == "true",
    # session 归属：CronCreate 是 session-only，任务只在该 session 进程里活着。
    # 记下来供 statusLine 过滤 —— 否则别的 session 也提示，误导用户。
    "session": session,
    "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "pending",
})
json.dump(d, open(store, "w"), ensure_ascii=False, indent=1)
PY
    echo "已登记: $id  $at  $cmd"
}

cmd_start() {
    local loc; loc="$(locate "$@")" || { echo "找不到任务（--id/--at 都没匹配上）" >&2; exit 1; }
    local tid="${loc%%$'\t'*}" tat="${loc##*$'\t'}"
    update_fields "$tid" "$tat" started "$(date '+%Y-%m-%d %H:%M:%S')" status running
    echo "已开始: $tid"
}

cmd_done() {
    local loc; loc="$(locate "$@")" || { echo "找不到任务（--id/--at 都没匹配上）" >&2; exit 1; }
    local tid="${loc%%$'\t'*}" tat="${loc##*$'\t'}"
    local now; now="$(date '+%Y-%m-%d %H:%M:%S')"
    # 没调过 start 就 done（任务被跳过 start）→ 用排定时间兜底，别让区间留空
    update_fields "$tid" "$tat" status finished finished "$now"
    python3 - "$STORE" "$tid" "$tat" <<'PY'
import json, sys
store, tid, tat = sys.argv[1:4]
d = json.load(open(store))
for t in d.get("tasks", []):
    if (tid and t.get("id") == tid) or (tat and t.get("at") == tat):
        t.setdefault("started", t.get("at"))
json.dump(d, open(store, "w"), ensure_ascii=False, indent=1)
PY
    echo "已完成: $tid"
}

cmd_drop() {
    local loc; loc="$(locate "$@")" || { echo "找不到任务" >&2; exit 1; }
    local tid="${loc%%$'\t'*}"
    ensure_store
    python3 - "$STORE" "$tid" <<'PY'
import json, sys
store, tid = sys.argv[1:3]
d = json.load(open(store))
d["tasks"] = [t for t in d.get("tasks", []) if t.get("id") != tid]
json.dump(d, open(store, "w"), ensure_ascii=False, indent=1)
PY
    echo "已删除记录: $tid"
}

cmd_prune() {
    local keep=50
    while [ $# -gt 0 ]; do
        case "$1" in
            --keep) keep="${2:-50}"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_store
    python3 - "$STORE" "$keep" <<'PY'
import json, sys
store, keep = sys.argv[1], int(sys.argv[2])
d = json.load(open(store))
tasks = d.get("tasks", [])
unfinished = [t for t in tasks if t.get("status") != "finished"]
finished = [t for t in tasks if t.get("status") == "finished"]
d["tasks"] = unfinished + finished[-keep:]
json.dump(d, open(store, "w"), ensure_ascii=False, indent=1)
print(f"保留 {len(unfinished)} 未完成 + 最近 {min(len(finished), keep)} 已完成")
PY
}

cmd_list() {
    ensure_store
    python3 - "$STORE" "$@" <<'PY'
import json, sys
from datetime import datetime

store = sys.argv[1]
pending_only = "--pending-only" in sys.argv
d = json.load(open(store))
tasks = d.get("tasks", [])
if pending_only:
    tasks = [t for t in tasks if t.get("status") in ("pending", "running")]
if not tasks:
    print("（无定时任务）")
    sys.exit(0)

MARK = {"pending": "⏳", "running": "▶", "finished": "✓"}


def hm(s):
    """'2026-10-27 14:59:41' → '14:59'；已是 HH:MM 就原样。"""
    if not s:
        return "?"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return s


for t in tasks:
    st = t.get("status", "pending")
    mark = MARK.get(st, "⏳")
    line = f"{mark} {t['id']}  {t.get('at','?')}  {t.get('cmd','')}"
    if st == "finished":
        line += f"   已完成 {hm(t.get('started'))}-{hm(t.get('finished'))}"
    elif st == "running":
        line += "   执行中"
    else:
        line += "   等执行"
    print(line)
PY
}

case "${1:-list}" in
    add)   shift; cmd_add "$@" ;;
    start) shift; cmd_start "$@" ;;
    done)  shift; cmd_done "$@" ;;
    drop)  shift; cmd_drop "$@" ;;
    prune) shift; cmd_prune "$@" ;;
    list)  shift; cmd_list "$@" ;;
    -h|--help) sed -n '2,18p' "$0" | sed 's/^# \?//' ;;
    *) echo "未知命令: $1" >&2; exit 1 ;;
esac