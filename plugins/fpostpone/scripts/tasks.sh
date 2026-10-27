#!/usr/bin/env bash
# fpostpone 任务登记表 —— 让用户可以随时查看「还有哪些定时任务在等」。
#
# session-only 的 CronCreate 任务没有任何用户可见文件（不写 scheduled_tasks.json），
# 用户在终端里查不到。这里在 ~/.cache/fpostpone/tasks.json 留一份影子记录，
# 供 /fpostpone list 和「有任务在等」提醒使用。
# 影子表只增记录；真伪以 CronList 为准（任务跑完自删，这里保留历史）。
#
# 用法:
#   tasks.sh add --id <id> --cron "<cron>" --at "<human>" --cmd "<命令>"
#   tasks.sh list [--pending-only]
#   tasks.sh done --id <id>
#   tasks.sh clear-finished
set -euo pipefail

FP_HOME="${FP_HOME:-$HOME/.cache/fpostpone}"
STORE="$FP_HOME/tasks.json"

ensure_store() {
    mkdir -p "$FP_HOME"
    [ -f "$STORE" ] || echo '{"tasks": []}' > "$STORE"
}

cmd_add() {
    local id="" cron="" at="" cmd="" kind="session" recurring="false"
    while [ $# -gt 0 ]; do
        case "$1" in
            --id)        id="${2:-}"; shift 2 ;;
            --cron)      cron="${2:-}"; shift 2 ;;
            --at)        at="${2:-}"; shift 2 ;;
            --cmd)       cmd="${2:-}"; shift 2 ;;
            --kind)      kind="${2:-}"; shift 2 ;;
            --recurring) recurring="${2:-}"; shift 2 ;;
            *) echo "未知参数: $1" >&2; exit 1 ;;
        esac
    done
    [ -n "$id" ] || { echo "--id 必填" >&2; exit 1; }

    ensure_store
    python3 - "$STORE" "$id" "$cron" "$at" "$cmd" "$kind" "$recurring" <<'PY'
import json, sys
from datetime import datetime
store, tid, cron, at, cmd, kind, recurring = sys.argv[1:8]
d = json.load(open(store))
d["tasks"] = [t for t in d.get("tasks", []) if t.get("id") != tid]
d["tasks"].append({
    "id": tid, "cron": cron, "at": at, "cmd": cmd,
    "kind": kind, "recurring": recurring == "true",
    "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "pending",
})
json.dump(d, open(store, "w"), ensure_ascii=False, indent=1)
PY
    echo "已登记: $id  $at  $cmd"
}

cmd_done() {
    local id="$1"
    ensure_store
    python3 - "$STORE" "$id" <<'PY'
import json, sys
from datetime import datetime
store, tid = sys.argv[1:3]
d = json.load(open(store))
for t in d.get("tasks", []):
    if t.get("id") == tid:
        t["status"] = "finished"
        t["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
json.dump(d, open(store, "w"), ensure_ascii=False, indent=1)
PY
    echo "已标记完成: $id"
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
    tasks = [t for t in tasks if t.get("status") == "pending"]
if not tasks:
    print("（无定时任务）")
    sys.exit(0)
now = datetime.now()
for t in tasks:
    mark = "✓" if t.get("status") == "finished" else "⏳"
    line = f"{mark} {t['id']}  {t['at']}  {t['cmd']}"
    if t.get("status") == "pending":
        line += "   [等执行]"
    print(line)
PY
}

cmd_clear() {
    ensure_store
    python3 - "$STORE" <<'PY'
import json, sys
store = sys.argv[1]
d = json.load(open(store))
d["tasks"] = [t for t in d.get("tasks", []) if t.get("status") != "finished"]
json.dump(d, open(store, "w"), ensure_ascii=False, indent=1)
print("已清理已完成记录")
PY
}

case "${1:-list}" in
    add)   shift; cmd_add "$@" ;;
    list)  shift; cmd_list "$@" ;;
    done)  [ $# -ge 2 ] || { echo "--id 必填" >&2; exit 1; }; cmd_done "$2" ;;
    clear-finished) cmd_clear ;;
    -h|--help)
        sed -n '2,12p' "$0" | sed 's/^# \?//'
        ;;
    *) echo "未知命令: $1" >&2; exit 1 ;;
esac