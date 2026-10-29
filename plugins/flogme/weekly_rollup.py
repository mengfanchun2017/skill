#!/usr/bin/env python3
"""周末工作汇总 — 扫全部 session transcript，按 KR 聚合，每 KR 每周一条 worklog。

设计（2026-10-29 用户定稿）：
- 每周跑一次，不再每 session 一条（旧 SessionEnd hook 已于 2026-07-20 删除）
- 每个 KR 每周最多一条 worklog，多 session 合进同一条
- 多终端并发：先查本周该 KR 是否已有记录，有则追加说明而非新建
- 空 session（0 user 消息 + 0 commit + 0 编辑）跳过

用法：
  python3 weekly_rollup.py                 # 本周（周一起），预览
  python3 weekly_rollup.py --write         # 写入飞书
  python3 weekly_rollup.py --week 2026-W43 # 指定 ISO 周
  python3 weekly_rollup.py --since 2026-10-20 --write
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _conf():
    from _skillconf_boot import config_env
    return config_env.load_config() or {}


CONF = _conf()
BASE = CONF["bases"]["okr_v2"]["token"]
T = CONF["bases"]["okr_v2"]["tables"]
KR_ROUTE = CONF.get("kr_route") or {}
ENV = {
    **os.environ,
    "LARKSUITE_CLI_CONFIG_DIR": os.path.expanduser(CONF["lark_cli"]["config_dir"]),
    "PATH": os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", ""),
}

PROJECTS_DIR = Path.home() / ".claude" / "projects"

# 会话噪音：这些 cwd 不算「工作」
SKIP_CWD_PATTERNS = ("/tmp", "/mnt/c/Users", "/home/francis--claude-jobs")


def lark(*args):
    r = subprocess.run(["lark-cli", *args], capture_output=True, text=True,
                       env=ENV, cwd="/tmp")
    out = r.stderr or r.stdout
    lines = []
    for line in out.splitlines():
        s = line.strip()
        if not s or s.startswith("[lark-cli]") or s.startswith("Shell cwd was reset"):
            continue
        while "\x1b[" in s:
            i = s.index("\x1b[")
            j = s.index("m", i) + 1 if "m" in s[i:] else i + 4
            s = s[:i] + s[j:]
        lines.append(s)
    text = "\n".join(lines)
    if not text.strip():
        sys.exit(f"lark-cli 空输出 (rc={r.returncode})\n{r.stderr}\n{r.stdout}")
    return json.loads(text)


# ── transcript 解析（移植自 2026-07-20 删除的 session_end_aggregator.py，
#    该段逻辑本身没坏，坏的是它写入的字段名和调度方式） ──────────────

def _extract_commit_msg(cmd):
    m = re.search(r"<<-?['\"]?EOF['\"]?\s*\n(.+?)\n\s*EOF", cmd, re.DOTALL)
    if m:
        return m.group(1).strip().split("\n")[0][:200]
    m = re.search(r'git commit[^|]*-m\s+["\']([^"\']+)["\']', cmd)
    if m:
        return m.group(1)[:200]
    return None


def parse_transcript(path, since_ts=None, until_ts=None):
    """读 JSONL → {commits, edits, user_prompts, tokens, cwd, sid}。
    since/until 用于只统计指定时间窗内的活动。"""
    agg = {"input_tokens": 0, "output_tokens": 0}
    commits, edits, user_prompts = [], [], []
    cwd, ts_first = None, None

    try:
        fh = open(path, encoding="utf-8", errors="ignore")
    except OSError:
        return None

    with fh as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue

            ts = o.get("timestamp")
            if ts and ts_first is None:
                ts_first = ts
            if since_ts and ts and ts < since_ts:
                continue
            if until_ts and ts and ts > until_ts:
                continue

            if not cwd and o.get("cwd"):
                cwd = o["cwd"]

            t = o.get("type", "")
            if t == "assistant":
                m = o.get("message", {})
                usage = m.get("usage", {})
                for k in agg:
                    if k in usage:
                        agg[k] += usage[k]
                content = m.get("content", [])
                if isinstance(content, list):
                    for c in content:
                        if not isinstance(c, dict) or c.get("type") != "tool_use":
                            continue
                        n, inp = c.get("name", ""), c.get("input", {})
                        if n == "Bash":
                            cmd = inp.get("command", "")
                            if "git commit" in cmd:
                                msg = _extract_commit_msg(cmd)
                                if msg:
                                    commits.append(msg)
                        elif n in ("Write", "Edit", "MultiEdit"):
                            fp = inp.get("file_path", "")
                            if fp:
                                edits.append(fp)
            elif t == "user":
                m = o.get("message", {})
                c = m.get("content", "")
                if isinstance(c, str) and c.strip():
                    if c.startswith("<") or "Caveat:" in c[:20]:
                        continue
                    txt = c.strip().replace("\n", " ")
                    user_prompts.append(txt[:100])

    if not user_prompts and not commits and not edits:
        return None

    return {
        "commits": commits,
        "edits": sorted(set(edits)),
        "user_prompts": user_prompts,
        "tokens": agg,
        "cwd": cwd or "",
        "sid": Path(path).stem,
        "ts_first": ts_first,
    }


def week_bounds(week=None, since=None):
    """返回 (周一 00:00, 下周一 00:00, 标签)。"""
    if since:
        start = datetime.fromisoformat(since)
        end = start + timedelta(days=7)
        return start, end, f"{since}~{(end - timedelta(days=1)).date()}"
    if week:
        y, w = week.split("-W")
        start = datetime.fromisocalendar(int(y), int(w), 1)
    else:
        today = date.today()
        start = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    end = start + timedelta(days=7)
    iso = start.isocalendar()
    return start, end, f"{iso[0]}-W{iso[1]:02d}"


def kr_for_cwd(cwd):
    """cwd → KR record_id（按 kr_route 前缀匹配）"""
    home = os.path.expanduser("~")
    for name, kid in KR_ROUTE.items():
        if name == "_default" or not kid:
            continue
        prefix = os.path.join(home, "git", name)
        if cwd and cwd.startswith(prefix):
            return kid, name
    return KR_ROUTE.get("_default") or None, "_default"


def scan_sessions(start, end):
    """扫全部 transcript，按 (KR, 项目) 聚合本周活动。"""
    since_ts = start.isoformat()
    until_ts = end.isoformat()
    groups = defaultdict(lambda: {"sessions": [], "commits": [], "edits": set(),
                                 "prompts": [], "tokens": {"input_tokens": 0, "output_tokens": 0}})

    if not PROJECTS_DIR.is_dir():
        return groups

    for proj in PROJECTS_DIR.iterdir():
        if not proj.is_dir():
            continue
        for tp in proj.rglob("*.jsonl"):
            try:
                mtime = datetime.fromtimestamp(tp.stat().st_mtime)
            except OSError:
                continue
            # mtime 早于窗口 → 该 session 不可能有本周活动
            if mtime < start:
                continue
            parsed = parse_transcript(tp, since_ts, until_ts)
            if not parsed:
                continue
            cwd = parsed["cwd"]
            if any(p in cwd for p in SKIP_CWD_PATTERNS):
                continue
            kr_id, proj_name = kr_for_cwd(cwd)
            g = groups[(kr_id, proj_name)]
            g["sessions"].append(parsed["sid"][:8])
            g["commits"] += parsed["commits"]
            g["edits"] |= set(parsed["edits"])
            g["prompts"] += parsed["user_prompts"]
            for k in g["tokens"]:
                g["tokens"][k] += parsed["tokens"][k]

    return groups


def build_title(kr_title, proj_name, label):
    """标题：{项目} {周} 工作汇总"""
    return f"{proj_name} {label} 工作汇总"


def build_desc(groups_entry, kr_title, label):
    """说明：结构化摘要，多 session 合并。"""
    g = groups_entry
    parts = [f"周期：{label}", f"session 数：{len(g['sessions'])}"]

    if g["commits"]:
        parts.append("\n主要提交：")
        for c in list(dict.fromkeys(g["commits"]))[:12]:
            parts.append(f"  · {c}")

    if g["edits"]:
        by_dir = defaultdict(list)
        for e in g["edits"]:
            by_dir[os.path.dirname(e)].append(os.path.basename(e))
        parts.append("\n改动文件：")
        for d, fs in sorted(by_dir.items(), key=lambda x: -len(x[1]))[:6]:
            shown = "、".join(fs[:4]) + ("…" if len(fs) > 4 else "")
            parts.append(f"  · {d or '.'}：{len(fs)} 个（{shown}）")

    if g["prompts"]:
        parts.append("\n涉及任务：")
        for p in list(dict.fromkeys(g["prompts"]))[:8]:
            parts.append(f"  · {p}")

    parts.append(f"\n用量：输入 {g['tokens']['input_tokens']} / 输出 {g['tokens']['output_tokens']} tokens")
    return "\n".join(parts)


def find_existing(kr_id, date_str):
    """查本周该 KR 是否已有 worklog（多终端并发去重）。"""
    data = lark("base", "+record-list", "--base-token", BASE,
                "--table-id", T["Worklog"], "--as", "user",
                "--format", "json", "--limit", "200")
    fields = data["data"]["fields"]
    ids = data["data"]["record_id_list"]
    for row, rid in zip(data["data"]["data"], ids):
        d = dict(zip(fields, row))
        kr = d.get("关联KR")
        link = kr[0]["id"] if (kr and isinstance(kr, list) and kr) else None
        if link == kr_id and str(d.get("日期", "")).startswith(date_str):
            return rid, d
    return None, None


def kr_meta():
    """KR record_id → 标题"""
    data = lark("base", "+record-list", "--base-token", BASE,
                "--table-id", T["KR"], "--as", "user",
                "--format", "json", "--limit", "200")
    fields = data["data"]["fields"]
    out = {}
    for row, rid in zip(data["data"]["data"], data["record_id_list"]):
        d = dict(zip(fields, row))
        out[rid] = d.get("标题")
    return out


def write_worklog(title, kr_id, desc, date_str):
    from log_write import cmd_worklog  # noqa: F401  (复用其字段校验)
    payload = {"fields": ["标题", "成果类型", "关联KR", "日期", "说明"],
               "rows": [[title, "工具开发", [{"id": kr_id}] if kr_id else None,
                         date_str, desc]]}
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".json", dir="/tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(payload, f, ensure_ascii=False)
    try:
        out = lark("base", "+record-batch-create", "--base-token", BASE,
                   "--table-id", T["Worklog"], "--as", "user",
                   "--json", f"@{os.path.basename(path)}")
    finally:
        os.unlink(path)
    return out["data"]["record_id_list"][0]


def append_worklog(rid, old_desc, new_desc):
    payload = {"record_id_list": [rid], "patch": {"说明": old_desc + "\n\n---\n" + new_desc}}
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".json", dir="/tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(payload, f, ensure_ascii=False)
    try:
        lark("base", "+record-batch-update", "--base-token", BASE,
             "--table-id", T["Worklog"], "--as", "user",
             "--json", f"@{os.path.basename(path)}")
    finally:
        os.unlink(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", help="ISO 周，如 2026-W43")
    ap.add_argument("--since", help="起始日 YYYY-MM-DD（7 天窗口）")
    ap.add_argument("--write", action="store_true", help="写入飞书（默认预览）")
    args = ap.parse_args()

    start, end, label = week_bounds(args.week, args.since)
    print(f"窗口：{start.date()} ~ {(end - timedelta(days=1)).date()}  ({label})")

    groups = scan_sessions(start, end)
    if not groups:
        print("本周无有效 session 活动")
        return 0

    km = kr_meta()
    date_str = start.date().isoformat()
    total_new, total_app = 0, 0

    for (kr_id, proj_name), g in sorted(groups.items(),
                                        key=lambda x: -len(x[1]["sessions"])):
        kr_title = km.get(kr_id, "(未匹配 KR)")
        desc = build_desc(g, kr_title, label)
        title = build_title(kr_title, proj_name, label)
        print(f"\n{'='*60}")
        print(f"KR: {kr_title}")
        print(f"项目: {proj_name} | session: {len(g['sessions'])} | "
              f"commit: {len(g['commits'])} | 文件: {len(g['edits'])}")
        print(f"标题: {title}")

        rid, old = find_existing(kr_id, date_str)
        if rid:
            print(f"→ 已有本周记录 {rid}，追加说明")
            if args.write:
                append_worklog(rid, old.get("说明") or "", desc)
                total_app += 1
        else:
            print(f"→ 新建")
            if args.write:
                nid = write_worklog(title, kr_id, desc, date_str)
                print(f"   写入 {nid}")
                total_new += 1

    if args.write:
        print(f"\n完成：新建 {total_new} 条，追加 {total_app} 条")
    else:
        print(f"\n⚠ 预览模式。加 --write 写入飞书。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
