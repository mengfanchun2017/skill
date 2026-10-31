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
sys.path.insert(0, str(HERE / "references"))


def _conf():
    from _skillconf_boot import config_env
    return config_env.load_config() or {}


CONF = _conf()
BASE = CONF["bases"]["okr_v2"]["token"]
T = CONF["bases"]["okr_v2"]["tables"]
KR_ROUTE = CONF.get("kr_route") or {}
KR_KEYWORD = CONF.get("kr_keyword") or []  # [{"keywords":["..."], "kr":"rec...", "repos":["ccconfig"]}, ...]
ENV = {
    **os.environ,
    "LARKSUITE_CLI_CONFIG_DIR": os.path.expanduser(CONF["lark_cli"]["config_dir"]),
    "PATH": os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", ""),
}

PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Worklog 的 KR 链接列在 Base 里叫「所属KR」（历史改名，旧名「关联KR」）。
# 读错名不报错、`.get()` 恒 None → find_existing 永不命中 → 每周重复新建。
# 别写死，运行时查真名。
_KR_FIELD_CACHE = []


def _kr_field():
    if _KR_FIELD_CACHE:
        return _KR_FIELD_CACHE[0]
    data = lark("base", "+field-list", "--base-token", BASE,
                "--table-id", T["Worklog"], "--as", "user")
    names = {f["name"] for f in data["data"]["fields"]}
    for cand in ("所属KR", "关联KR"):
        if cand in names:
            _KR_FIELD_CACHE.append(cand)
            return cand
    sys.exit(f"Worklog 表没有 KR 链接字段，现有: {sorted(names)}")


# 会话噪音：这些 cwd 不算「工作」
SKIP_CWD_PATTERNS = ("/tmp", "/mnt/c/Users", "--claude-jobs-")
SKIP_EDIT_PATTERNS = ("/tmp/", "--claude-jobs-", "/.claude/jobs/")


def git_commits_since(proj_name, start, end):
    """从 git log 直接拉提交。

    ⚠️ 不能靠 transcript 里的 `git commit` 命令：~/git/ 下的仓库由 auto-sync
    monitor 独占提交权，session 从不自己 commit，transcript 里根本没有 commit 命令
    （实测上周 19 个 session，commit 命中 0）。真提交只在 git log 里。
    """
    repo = Path.home() / "git" / proj_name
    if not (repo / ".git").exists():
        return []
    r = subprocess.run(
        ["git", "-C", str(repo), "log",
         f"--since={start.isoformat()}", f"--until={end.isoformat()}",
         "--pretty=format:%s", "--no-merges"],
        capture_output=True, text=True)
    if r.returncode != 0:
        return []
    out = []
    for line in r.stdout.splitlines():
        s = line.strip()
        if not s:
            continue
        # auto-sync 的提交通常是 "Auto-sync: <repo> N 文件"，语义为零，只记数量
        if s.startswith("Auto-sync:"):
            continue
        out.append(s[:150])
    return out


def git_commit_count(proj_name, start, end):
    """auto-sync 独占提交权，提交信息无语义，但数量能反映活跃度。"""
    repo = Path.home() / "git" / proj_name
    if not (repo / ".git").exists():
        return 0
    r = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--count",
         f"--since={start.isoformat()}", f"--until={end.isoformat()}", "HEAD"],
        capture_output=True, text=True)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return 0


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
    """从 `git commit -m ...` 里取真实提交信息。

    ⚠️ 只在 `git commit` 之后的片段里找 heredoc。裸匹配全文 `<<EOF...EOF`
    会命中同一条命令里**前面**的其它 heredoc（`cat > x.sh <<'EOF'`），
    取到 `#!/bin/bash` 之类的垃圾当提交信息（实测混进汇总结论）。
    """
    i = cmd.find("git commit")
    if i < 0:
        return None
    tail = cmd[i:]
    # 两种写法取**位置最靠前**的那个：同一条命令里常有多段 heredoc
    # （`git commit -m x` 后面再 `cat > run.sh <<EOF`），先按顺序匹配就会
    # 抓到后面那段的首行（`#!/bin/bash`）当提交信息。
    cands = []
    m = re.search(r"<<-?['\"]?(\w+)['\"]?\s*\n(.+?)\n\s*\1", tail, re.DOTALL)
    if m:
        line = m.group(2).strip().split("\n")[0][:200]
        if not line.startswith("$("):
            cands.append((m.start(), line))
    m = re.search(r'-m\s+["\']([^"\'\n]+)["\']', tail)
    if m:
        v = m.group(1).strip()
        if v and not v.startswith("$(") and "<<" not in v:
            cands.append((m.start(), v[:200]))
    if not cands:
        return None
    return min(cands, key=lambda x: x[0])[1]


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
        iso = start.isocalendar()
        return start, end, f"{iso[0]}-W{iso[1]:02d}"
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
    """cwd → KR record_id（按 kr_route 前缀匹配）。

    kr_route 没配的 ~/git/<repo> 会落到 _default，而用户定稿「没有 KR 就不更新」
    → 这些活动会整块丢弃。所以未命中时按「AI 辅助编程工作流」这个 KR 兜底
    （~/git 下的开发工作本质都属于它），而不是静默丢掉。
    """
    home = os.path.expanduser("~")
    for name, kid in KR_ROUTE.items():
        if name == "_default" or not kid:
            continue
        prefix = os.path.join(home, "git", name)
        if cwd and cwd.startswith(prefix):
            return kid, name

    # 非 ~/git 下的 cwd 不是开发工作 → 不记录
    gitroot = os.path.join(home, "git") + os.sep
    if not (cwd or "").startswith(gitroot):
        return None, ""

    default = KR_ROUTE.get("_default")
    if default:
        # 从 cwd 反推仓库名当项目标签
        rel = (cwd or "")[len(gitroot):].split(os.sep)[0]
        return default, rel or "_default"
    return None, ""


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

    # 补真提交（transcript 里没有，见 git_commits_since 注释）
    for (kr_id, proj_name), g in groups.items():
        g["commits"] += git_commits_since(proj_name, start, end)
        g["commit_count"] = git_commit_count(proj_name, start, end)

    return groups


def build_title(kr_title, proj_name, label):
    """标题：{项目} {ISO周} 工作汇总。

    ⚠️ 周五与周一必须产出**同一标题**，否则 find_existing 按日期找到记录后
    标题却对不上，看起来像两条（且不利于阅读）。
    """
    tag = label.replace("-mid", "")
    return f"{proj_name} {tag} 工作汇总"


def build_desc(groups_entry, kr_title, label):
    """说明：结构化摘要，多 session 合并。"""
    g = groups_entry
    parts = [f"周期：{label}", f"session 数：{len(g['sessions'])}"]

    if g.get("commit_count"):
        parts.append(f"\n提交数：{g['commit_count']} 个")
    if g["commits"]:
        parts.append("\n主要提交：")
        for c in list(dict.fromkeys(g["commits"]))[:12]:
            parts.append(f"  · {c}")

    if g["edits"]:
        by_dir = defaultdict(list)
        for e in g["edits"]:
            # /tmp 与作业目录是临时文件，不算工作产出
            if any(p in e for p in SKIP_EDIT_PATTERNS):
                continue
            by_dir[os.path.dirname(e)].append(os.path.basename(e))
        if by_dir:
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
    """查本周该 KR 是否已有 worklog（多终端并发去重）。

    ⚠️ 必须翻页：Worklog 已超 200 条，只查第一页会漏掉新记录，
    第二次运行会重复新建（实测踩过）。
    """
    off = 0
    while True:
        data = lark("base", "+record-list", "--base-token", BASE,
                    "--table-id", T["Worklog"], "--as", "user",
                    "--format", "json", "--limit", "200", "--offset", str(off))
        dd = data["data"]
        fields = dd["fields"]
        kr_col = _kr_field()
        for row, rid in zip(dd["data"], dd["record_id_list"]):
            d = dict(zip(fields, row))
            kr = d.get(kr_col)
            link = kr[0]["id"] if (kr and isinstance(kr, list) and kr) else None
            if link == kr_id and str(d.get("日期", "")).startswith(date_str):
                return rid, d
        if not dd.get("has_more"):
            return None, None
        off += len(dd["data"])


def kr_meta():
    """KR record_id → 标题"""
    data = lark("base", "+record-list", "--base-token", BASE,
                "--table-id", T["KR"], "--as", "user",
                "--format", "json", "--limit", "200")
    fields = data["data"]["fields"]
    out = {}
    for row, rid in zip(data["data"]["data"], data["data"]["record_id_list"]):
        d = dict(zip(fields, row))
        out[rid] = d.get("标题")
    return out


def write_worklog(title, kr_id, desc, date_str):
    from log_write import cmd_worklog  # noqa: F401  (复用其字段校验)
    payload = {"fields": ["标题", "成果类型", _kr_field(), "日期", "说明"],
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
    """同周重跑 = 用最新内容覆盖，不累加。

    ⚠️ 原先是 `old + "---" + new`，周五写一遍、周一再写一遍 → 完全相同的内容
    重复两段。每周的记录应当反映该周最终状态，重跑就是刷新。
    """
    payload = {"record_id_list": [rid], "patch": {"说明": new_desc}}
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


def _emit(groups, label, anchor, do_write):
    """把聚合结果落地：每 KR 一条，已有则追加。周一/周五两条路径共用。

    anchor = 该周周一，**固定不变**。周五和周一的扫描窗口起点不同，
    但记录日期必须锚到同一个周一，否则 find_existing 找不到周五写的那条，
    会重复新建（实测踩过）。
    """
    if not groups:
        print("该窗口无有效 session 活动")
        return 0

    km = kr_meta()
    date_str = (anchor.date().isoformat() if isinstance(anchor, datetime)
                 else anchor.isoformat())
    total_new, total_app = 0, 0

    for (kr_id, proj_name), g in sorted(groups.items(),
                                        key=lambda x: -len(x[1]["sessions"])):
        # 用户定稿：「没有 KR 就不更新」——未匹配到 KR 的活动不记录
        if not kr_id:
            print(f"\n跳过非工作目录活动（{len(g['sessions'])} session，无 KR 归属）")
            continue
        kr_title = km.get(kr_id, "(KR 已删除)")
        desc = build_desc(g, kr_title, label)
        title = build_title(kr_title, proj_name, label)
        print(f"\n{'='*60}")
        print(f"KR: {kr_title}")
        print(f"项目: {proj_name} | session: {len(g['sessions'])} | "
              f"提交: {g.get('commit_count', 0)} | 文件: {len(g['edits'])}")
        print(f"标题: {title}")

        rid, old = find_existing(kr_id, date_str)
        if rid:
            print(f"→ 已有本周记录 {rid}，追加说明")
            if do_write:
                append_worklog(rid, old.get("说明") or "", desc)
                total_app += 1
        else:
            print(f"→ 新建")
            if do_write:
                nid = write_worklog(title, kr_id, desc, date_str)
                print(f"   写入 {nid}")
                total_new += 1

    if do_write:
        print(f"\n完成：新建 {total_new} 条，追加 {total_app} 条")
    else:
        print(f"\n⚠ 预览模式。加 --write 写入飞书。")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", help="ISO 周，如 2026-W43")
    ap.add_argument("--since", help="起始日 YYYY-MM-DD（7 天窗口）")
    ap.add_argument("--last-week", action="store_true",
                    help="上一个完整周（周一 00:01 定时跑用）")
    ap.add_argument("--this-week", action="store_true",
                    help="本周至今（周五 00:01 定时跑用）")
    ap.add_argument("--write", action="store_true", help="写入飞书（默认预览）")
    args = ap.parse_args()

    if args.last_week:
        # 周一整周重扫（幂等）：周五写的是「本周一~本周五」，本周一跑时
        # 这一周已完整，重扫得到**完整一周**（含周末尾巴），覆盖周五那版。
        # append_worklog 已是覆盖语义，重跑不会累加，故整周重扫是安全的。
        this_monday = date.today() - timedelta(days=date.today().weekday())
        last_monday = this_monday - timedelta(days=7)
        start_full = datetime.combine(last_monday, datetime.min.time())
        end_full = datetime.combine(this_monday, datetime.min.time())
        _, _, lbl = week_bounds(None, last_monday.isoformat())
        print(f"窗口：{start_full.date()} ~ {(end_full - timedelta(days=1)).date()}  ({lbl} 完整一周，覆盖周五版本)")
        return _emit(scan_sessions(start_full, end_full), lbl, last_monday, args.write)

    start, end, label = week_bounds(args.week, args.since)
    if args.this_week:
        # 周五跑：本周一到现在，截掉未来
        end = datetime.now()
        label = label + "-mid"
    print(f"窗口：{start.date()} ~ {end.date()}  ({label})")

    groups = scan_sessions(start, end)
    return _emit(groups, label, start, args.write)


if __name__ == "__main__":
    sys.exit(main())
