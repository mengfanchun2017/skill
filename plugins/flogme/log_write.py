#!/usr/bin/env python3
"""
flogme 数据写入助手

子命令:
- worklog: 写 worklog
- reflect: 写 reflect（含批量关联 KR, 仅写入关联，不触发 KR 字段更新）
- kr-status: 改 KR.status (active / done / paused / cancelled)，只管生命周期

设计变化 (2026-06-12):
- 移除 KR_Progress 历史快照（表已废弃）
- 移除"每 worklog +5% / 每 reflect +10%"伪指标
- KR 状态改为手动管理（完成时主动跑 kr-status）
- 状态字段统一为 KR.状态 (3 选 1)，不再用 KR.进度 / KR.信心

用法示例:
  python3 log_write.py worklog --title "X" --kr recXXX --type "项目交付" --date 2026-06-12
  python3 log_write.py reflect --title "Q2 W3" --o recYYY --date 2026-06-12 --good "A" --improve "B" --learned "C" --next "D" --batch-kr recXXX recYYY
  python3 log_write.py kr-status --kr recXXX --status done
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path


import yaml

def _load_conf():
    """配置走单一实现（2026-10-27）：8 级链（官方两通道 + $CLAUDE_PLUGIN_DATA
    + ccprivate + 旧的 <skill>/config.yaml），不再只读 skill 根那一个文件。"""
    sys.path.insert(0, str(Path(__file__).resolve().parent / "references"))
    try:
        from _skillconf_boot import config_env as _ce
        load_config = _ce.load_config
        return load_config() or {}
    except Exception:
        pass
    c = Path(__file__).resolve().parent / "config.yaml"
    if c.exists():
        return yaml.safe_load(c.read_text()) or {}
    sys.exit("未找到配置：$CCPRIVATE_HOME/conf/<plugin>.yaml，"
             "或 claude plugin configure <plugin>@<market>")


CONF = _load_conf()
BASE = CONF["bases"]["okr_v2"]["token"]
T = CONF["bases"]["okr_v2"]["tables"]

ENV = {
    **os.environ,
    "LARKSUITE_CLI_CONFIG_DIR": os.path.expanduser(CONF["lark_cli"]["config_dir"]),
    "PATH": os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", ""),
    "HOME": os.environ.get("HOME", os.path.expanduser("~")),
}


def lark(*args, cwd=None):
    """调 lark-cli, 过滤日志行, 返回解析后 JSON。cwd 默认 /tmp (lark-cli --json @file 需相对路径)"""
    r = subprocess.run(["lark-cli", *args], capture_output=True, text=True, env=ENV, cwd=cwd or "/tmp")
    # lark-cli outputs JSON to stderr (not stdout)
    output = r.stderr or r.stdout
    # strip log lines (prefix tags) and terminal escape codes
    lines = []
    for l in output.splitlines():
        s = l.strip()
        if not s:
            continue
        if s.startswith("[lark-cli]") or s.startswith("Shell cwd was reset"):
            continue
        # remove terminal color escape sequences
        while "\x1b[" in s:
            i = s.index("\x1b[")
            j = s.index("m", i) + 1 if "m" in s[i:] else i + 4
            s = s[:i] + s[j:]
        lines.append(s)
    text = "\n".join(lines)
    if not text.strip():
        sys.stderr.write(f"lark-cli empty output (rc={r.returncode})\n---stderr---\n{r.stderr}\n---stdout---\n{r.stdout}\n")
        sys.exit(1)
    return json.loads(text)


def write_json_file(payload):
    """写 JSON 到 /tmp, 返回相对路径 (供 --json @file 用)"""
    fd, path = tempfile.mkstemp(suffix=".json", dir="/tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(payload, f, ensure_ascii=False)
    return path


def update_kr_field(kr_id, fields_dict):
    """更新 KR 单字段 (raw API: PUT /records/{id})"""
    payload = {"fields": fields_dict}
    lark("api", "PUT", f"/open-apis/bitable/v1/apps/{BASE}/tables/{T['KR']}/records/{kr_id}",
         "--data", json.dumps(payload), "--as", "user")


FIELD_CACHE = {}

# KR 状态字段真名。历史上改名过（KR.状态 → KR.status），写错名 API 不报错只静默丢弃。
KR_STATUS_FIELD = "KR.status"

# 逻辑字段名 → 候选真名（按顺序取第一个存在的）。
# 教训：Worklog 的 KR 链接列在 Base 里被改名成「所属KR」，脚本还按「关联KR」读写 →
# 写报 not_found、读 .get() 恒 None。读错名不报错，是静默失效（weekly_rollup 的去重
# 因此永不命中，每周重复新建）。写死字段名一律走本表。
FIELD_ALIASES = {
    "Worklog": {"关联KR": ["所属KR", "关联KR"]},
}


def field_name(table_key, logical):
    """逻辑字段名 → 该表里真实存在的字段名，找不到返回 None。"""
    names = table_fields(table_key)
    for cand in FIELD_ALIASES.get(table_key, {}).get(logical, [logical]):
        if cand in names:
            return cand
    return None


def table_fields(table_key):
    """取某表全部字段名（带缓存）。写之前用它校验，避免静默丢弃。"""
    if table_key in FIELD_CACHE:
        return FIELD_CACHE[table_key]
    data = lark("base", "+field-list", "--base-token", BASE,
                "--table-id", T[table_key], "--as", "user")
    names = {f["name"] for f in data["data"]["fields"]}
    FIELD_CACHE[table_key] = names
    return names


def verify_field(table_key, field_name):
    """字段不存在 → 报错退出，而不是让 API 静默吞掉。"""
    names = table_fields(table_key)
    if field_name not in names:
        sys.exit(f"字段不存在: {table_key}.{field_name}\n"
                 f"该表现有字段: {sorted(names)}\n"
                 f"（bitable API 对未知字段静默丢弃并返回成功，故此处硬拦）")


SELECT_CACHE = {}


def verify_select_value(table_key, field_name, value):
    """单选值必须在选项里，否则 API 报错或写入无效值。"""
    key = (table_key, field_name)
    if key not in SELECT_CACHE:
        data = lark("base", "+field-list", "--base-token", BASE,
                    "--table-id", T[table_key], "--as", "user")
        for f in data["data"]["fields"]:
            if f["name"] == field_name:
                SELECT_CACHE[key] = {o["name"] for o in (f.get("options") or [])}
                break
        else:
            SELECT_CACHE[key] = set()
    allowed = SELECT_CACHE[key]
    if allowed and value not in allowed:
        sys.exit(f"无效值: {table_key}.{field_name}={value!r}\n"
                 f"可选: {sorted(allowed)}")


def read_kr_field(kr_id, field_name):
    """读回校验写入是否真生效。"""
    data = lark("base", "+record-list", "--base-token", BASE,
                "--table-id", T["KR"], "--as", "user", "--format", "json",
                "--limit", "200")
    fields = data["data"]["fields"]
    ids = data["data"]["record_id_list"]
    for row, rid in zip(data["data"]["data"], ids):
        if rid == kr_id:
            return dict(zip(fields, row)).get(field_name)
    return None


def cmd_worklog(args):
    date_str = args.date or date.today().isoformat()

    # 「每条必须关联 KR」此前只是文档约定，脚本不校验 → 33 条裸记录。
    # 这里硬拦，除非显式 --allow-no-kr。
    if not args.kr and not getattr(args, "allow_no_kr", False):
        sys.exit("缺少 --kr：Worklog 规则要求每条关联一个 KR。\n"
                 "确实无法归类时用 --allow-no-kr 显式豁免。\n"
                 f"可用 KR: python3 {Path(__file__).name} kr-list")
    if args.type:
        verify_select_value("Worklog", "成果类型", args.type)
    kr_field = field_name("Worklog", "关联KR")
    if args.kr and not kr_field:
        verify_field("Worklog", "关联KR")  # 抛错列出真实字段

    fields = ["标题", "成果类型", kr_field, "日期", "说明"]
    row = [
        args.title,
        args.type or "工具开发",
        [{"id": args.kr}] if args.kr else None,
        date_str,
        args.note or "",
    ]
    payload = {"fields": fields, "rows": [row]}
    path = write_json_file(payload)
    try:
        out = lark("base", "+record-batch-create", "--base-token", BASE,
                   "--table-id", T["Worklog"], "--as", "user",
                   "--json", f"@{os.path.basename(path)}")
    finally:
        os.unlink(path)

    worklog_id = out["data"]["record_id_list"][0]
    print(json.dumps({"worklog_id": worklog_id}, ensure_ascii=False, indent=2))
    return 0


def cmd_reflect(args):
    date_str = args.date or date.today().isoformat()

    # 关联KR 之前只打印不落库（batch-kr 假成功），这里真正写入
    fields = ["标题", "周期类型", "关联O", "做得好", "待改进", "学到", "下阶段", "日期", "关联KR"]
    row = [
        args.title,
        args.period or "周",
        [{"id": args.o}] if args.o else None,
        args.good or "",
        args.improve or "",
        args.learned or "",
        args.next or "",
        date_str,
        [{"id": k} for k in args.batch_kr] if args.batch_kr else None,
    ]
    payload = {"fields": fields, "rows": [row]}
    path = write_json_file(payload)
    try:
        out = lark("base", "+record-batch-create", "--base-token", BASE,
                   "--table-id", T["Reflect"], "--as", "user",
                   "--json", f"@{os.path.basename(path)}")
    finally:
        os.unlink(path)

    reflect_id = out["data"]["record_id_list"][0]
    result = {"reflect_id": reflect_id, "linked_krs": args.batch_kr or []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_kr_status(args):
    """手动更新 KR.status (active / done / paused / cancelled)

    只管生命周期，不表达进展好坏——进展健康度在 KR.health（on_track/at_risk/
    off_track/n_a），由每月 audit 检查更新。旧选项 smooth/challenge 已废弃，
    它把「进展健康」混进了「生命周期」，选了一个就丢另一个。

    字段名是 KR.status（带点号），不是旧文档写的 KR.状态 —— 旧名不存在时
    bitable API 静默丢弃该键、仍返回成功，造成「假成功」。这里先校验字段存在。
    """
    verify_field("KR", KR_STATUS_FIELD)
    update_kr_field(args.kr, {KR_STATUS_FIELD: args.status})
    got = read_kr_field(args.kr, KR_STATUS_FIELD)
    ok = got == args.status or (isinstance(got, list) and args.status in got)
    print(json.dumps({"kr_id": args.kr, "status": args.status,
                      "verified": ok, "read_back": got}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def cmd_kr_list(args):
    """列出 KR（id + 标题 + 状态），供 worklog 关联时查 record_id。"""
    data = lark("base", "+record-list", "--base-token", BASE,
                "--table-id", T["KR"], "--as", "user", "--format", "json",
                "--limit", "200")
    fields = data["data"]["fields"]
    ids = data["data"]["record_id_list"]
    rows = []
    for row, rid in zip(data["data"]["data"], ids):
        d = dict(zip(fields, row))
        rows.append({
            "kr_id": rid,
            "标题": d.get("标题"),
            "KR.status": d.get(KR_STATUS_FIELD),
            "KR.domain": d.get("KR.domain"),
            "KR.para": d.get("KR.para"),
        })
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("worklog")
    w.add_argument("--title", required=True)
    w.add_argument("--kr", help="关联 KR record_id")
    w.add_argument("--type", help="成果类型")
    w.add_argument("--note", help="说明")
    # usage fields removed: token/msg counts now handled by maintain.sh token
    w.add_argument("--date", help="日期 YYYY-MM-DD")
    w.add_argument("--allow-no-kr", action="store_true",
                   help="显式豁免「必须关联 KR」规则")
    w.set_defaults(func=cmd_worklog)

    r = sub.add_parser("reflect")
    r.add_argument("--title", required=True)
    r.add_argument("--period", choices=["周", "月", "季度", "年"])
    r.add_argument("--o", help="关联 O record_id")
    r.add_argument("--good", help="做得好")
    r.add_argument("--improve", help="待改进")
    r.add_argument("--learned", help="学到")
    r.add_argument("--next", help="下阶段")
    r.add_argument("--batch-kr", nargs="*", help="批量关联的 KR record_id (本周涉及的)")
    r.add_argument("--date", help="日期 YYYY-MM-DD")
    r.set_defaults(func=cmd_reflect)

    k = sub.add_parser("kr-status")
    k.add_argument("--kr", required=True, help="KR record_id")
    k.add_argument("--status", required=True, help="取 KR.status 字段的选项值")
    k.set_defaults(func=cmd_kr_status)

    kl = sub.add_parser("kr-list", help="列出可用 KR（写 worklog 前查 record_id）")
    kl.set_defaults(func=cmd_kr_list)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
