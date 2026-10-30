#!/usr/bin/env python3
"""Worklog 归档 — 把旧年份记录搬到 Worklog_Archive，主表只留当年。

为什么要归档：主表 244 条跨 2024-2026，日常浏览/去重查询都要翻 3 页。
归档后主表只留当年，每周汇总的 find_existing 查询也更快更准。

用法：
  python3 archive_worklogs.py --before 2026-01-01              # 预览
  python3 archive_worklogs.py --before 2026-01-01 --write      # 执行
  python3 archive_worklogs.py --before 2026-01-01 --write --keep-kr-link
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "references"))


def _conf():
    from _skillconf_boot import config_env
    return config_env.load_config() or {}


CONF = _conf()
BASE = CONF["bases"]["okr_v2"]["token"]
T = CONF["bases"]["okr_v2"]["tables"]
ARCHIVE_TABLE = "tbld4zKDq0mrtd2H"  # Worklog_Archive
ENV = {
    **os.environ,
    "LARKSUITE_CLI_CONFIG_DIR": os.path.expanduser(CONF["lark_cli"]["config_dir"]),
    "PATH": os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", ""),
}


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
        sys.exit(f"lark-cli 空输出 (rc={r.returncode})")
    return json.loads(text)


def fetch_all(table):
    out, fields, off = [], None, 0
    while True:
        d = lark("base", "+record-list", "--base-token", BASE,
                 "--table-id", table, "--as", "user", "--format", "json",
                 "--limit", "200", "--offset", str(off))["data"]
        fields = d["fields"]
        for row, rid in zip(d["data"], d["record_id_list"]):
            rec = dict(zip(fields, row))
            # Worklog 的 KR 链接列在 Base 里叫「所属KR」（历史改名），归一成下游读的名字
            if "关联KR" not in rec and "所属KR" in rec:
                rec["关联KR"] = rec["所属KR"]
            rec["_rid"] = rid
            out.append(rec)
        if not d.get("has_more"):
            break
        off += len(d["data"])
    return out


def kr_titles():
    data = lark("base", "+record-list", "--base-token", BASE,
                "--table-id", T["KR"], "--as", "user", "--format", "json",
                "--limit", "200")["data"]
    f = data["fields"]
    return {rid: dict(zip(f, r)).get("标题")
            for r, rid in zip(data["data"], data["record_id_list"])}


def batch_create(rows):
    """rows: list of field→value dict，用 Worklog_Archive 的字段顺序。"""
    if not rows:
        return []
    fields = ["标题", "日期", "说明", "成果类型", "原关联KR", "归档周"]
    payload = {"fields": fields,
               "rows": [[r.get(k) for k in fields] for r in rows]}
    fd, path = tempfile.mkstemp(suffix=".json", dir="/tmp")
    with os.fdopen(fd, "w") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    try:
        out = lark("base", "+record-batch-create", "--base-token", BASE,
                   "--table-id", ARCHIVE_TABLE, "--as", "user",
                   "--json", f"@{os.path.basename(path)}")
    finally:
        os.unlink(path)
    return out["data"]["record_id_list"]


def delete_records(rids):
    n = 0
    for rid in rids:
        lark("api", "DELETE",
             f"/open-apis/bitable/v1/apps/{BASE}/tables/{T['Worklog']}/records/{rid}",
             "--as", "user")
        n += 1
    return n


def iso_week(date_str):
    from datetime import date
    try:
        y, m, dd = (int(x) for x in str(date_str)[:10].split("-"))
        c = date(y, m, dd).isocalendar()
        return f"{c[0]}-W{c[1]:02d}"
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True, help="早于该日期（YYYY-MM-DD）的记录归档")
    ap.add_argument("--write", action="store_true", help="真执行（默认预览）")
    args = ap.parse_args()

    recs = fetch_all(T["Worklog"])
    krt = kr_titles()
    targets = [r for r in recs if str(r.get("日期") or "")[:10] < args.before]

    print(f"主表共 {len(recs)} 条，待归档 {len(targets)} 条（早于 {args.before}）")
    if not targets:
        return 0

    from collections import Counter
    print("按年份:", dict(sorted(Counter(str(r.get("日期"))[:4] for r in targets).items())))

    rows = []
    for r in targets:
        kr = r.get("关联KR")
        kr_id = kr[0]["id"] if (kr and isinstance(kr, list) and kr) else ""
        rows.append({
            "标题": r.get("标题") or "",
            "日期": r.get("日期"),
            "说明": r.get("说明") or "",
            "成果类型": (r.get("成果类型") or [None])[0]
                        if isinstance(r.get("成果类型"), list)
                        else r.get("成果类型"),
            "原关联KR": f"{krt.get(kr_id, '')}|{kr_id}" if kr_id else "",
            "归档周": iso_week(r.get("日期")),
        })

    if not args.write:
        print("\n样例（前 3 条）:")
        for x in rows[:3]:
            print(f"  · {x['标题'][:50]} | {str(x['日期'])[:10]} | {x['成果类型']}")
        print("\n⚠ 预览模式。加 --write 执行归档。")
        return 0

    ids = batch_create(rows)
    print(f"✓ 写入归档表 {len(ids)} 条")
    if len(ids) != len(rows):
        sys.exit(f"归档写入不完整（{len(ids)}/{len(rows)}），中止删除。")

    n = delete_records([r["_rid"] for r in targets])
    print(f"✓ 从主表删除 {n} 条")

    left = fetch_all(T["Worklog"])
    print(f"✓ 主表剩余 {len(left)} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
