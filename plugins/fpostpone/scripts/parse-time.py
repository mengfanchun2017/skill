#!/usr/bin/env python3
"""中文时间表达式 → cron 表达式 + 绝对时间。

用法: parse-time.py "<表达式>" [--now "YYYY-MM-DD HH:MM:SS"]
输出: JSON {ok, cron, at, human, warn?} 或 {ok:false, error, hint}

支持: 18点 / 18:30 / 明天9点 / 后天14点 / +2h / +30m / 3天后 / 今晚8点 /
      周三9点 / 下周一10点 / 13:07 / 2026-10-28 09:15
"""
import json
import re
import sys
from datetime import datetime, timedelta

WEEKDAYS = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}

CN_HOUR = re.compile(r"^(?P<h>[01]?\d|2[0-3])\s*[点時时](?:(?P<m>[0-5]?\d)\s*分?)?$")
CN_HALF = re.compile(r"^(?P<h>[01]?\d|2[0-3])\s*点半$")
COLON = re.compile(r"^(?P<h>[01]?\d|2[0-3]):(?P<m>[0-5]\d)(?::(?P<s>[0-5]\d))?$")
REL = re.compile(r"^\+(?P<n>\d+)\s*(?P<unit>[hmd])$", re.I)
REL_CN = re.compile(r"^(?P<n>\d+)\s*(?P<unit>分钟|小时|个小时|天)后$")
DAYCN = re.compile(r"^(?P<day>今天|今晚|明天|明晚|后天|大后天)(?P<rest>.*)$")
WEEK = re.compile(r"^(?P<prefix>下)?(?:周|星期)(?P<wd>[一二三四五六日天])(?P<rest>.*)$")
PERIOD = re.compile(r"^(?P<p>早上|上午|中午|下午|傍晚|晚上|凌晨)(?P<rest>.*)$")
ABS = re.compile(r"^(?P<Y>\d{4})-(?P<M>\d{1,2})-(?P<D>\d{1,2})\s+(?P<h>[01]?\d|2[0-3]):(?P<m>[0-5]?\d)(?::(?P<s>[0-5]?\d))?$")

# 一次性任务排在 :00/:30，Claude Code 会提前最多 90 秒跑（官方 docs）。
# 避开整点/半点，也避开用户的"忙时多收费"窗口。
def snap_minute(m: int) -> tuple[int, str | None]:
    if m == 0:
        return 2, ":00 整点会提前最多 90 秒触发，已挪到 :02"
    if m == 30:
        return 32, ":30 会提前最多 90 秒触发，已挪到 :32"
    return m, None


def parse_hhmm(s: str):
    s = s.strip()
    if not s:
        return None, None, None
    m = CN_HALF.match(s)
    if m:
        return int(m.group("h")), 30, None
    m = CN_HOUR.match(s)
    if m:
        return int(m.group("h")), int(m.group("m") or 0), None
    m = COLON.match(s)
    if m:
        return int(m.group("h")), int(m.group("m")), m.group("s")
    return None, None, None


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "no_input",
                          "hint": "用法: parse-time.py '18点' | '明天9点' | '+2h'"}, ensure_ascii=False))
        return 1

    raw = sys.argv[1].strip()
    now = datetime.now().replace(microsecond=0)
    # 全角→半角：中文输入法下全角数字/冒号/空格极常见（如「14：50」），不规范化必解析失败
    raw = raw.translate(str.maketrans("０１２３４５６７８９：＋　", "0123456789:+ "))
    # 剥离衬词："18点运行"/"明天9点跑"/"18点执行" —— 用户自然写法，别让它解析失败
    raw = re.sub(r"\s*(运行|跑|执行|开始|启动|触发)\s*$", "", raw).strip()
    if not raw:
        raw = sys.argv[1].strip() or "（空）"
    if "--now" in sys.argv:
        i = sys.argv.index("--now")
        if i + 1 < len(sys.argv):
            now = datetime.strptime(sys.argv[i + 1], "%Y-%m-%d %H:%M:%S")

    expr = raw
    warnings = []
    base_day = now.date()

    m = ABS.match(expr)
    if m:
        at = datetime(int(m.group("Y")), int(m.group("M")), int(m.group("D")),
                      int(m.group("h")), int(m.group("m")), int(m.group("s") or 0))
        return emit(at, now, warnings, raw)

    m = REL.match(expr)
    if m:
        n, unit = int(m.group("n")), m.group("unit").lower()
        delta = {"h": timedelta(hours=n), "m": timedelta(minutes=n), "d": timedelta(days=n)}[unit]
        return emit(now + delta, now, warnings, raw)

    m = REL_CN.match(expr)
    if m:
        n, unit = int(m.group("n")), m.group("unit")
        delta = timedelta(days=n) if unit == "天" else timedelta(hours=n)
        return emit(now + delta, now, warnings, raw)

    day_off = 0
    pm_bias = False  # "今晚8点" 这类晚间词：裸小时数按下午/晚上理解
    m = DAYCN.match(expr)
    if m:
        tok = m.group("day")
        day_off = {"今天": 0, "今晚": 0, "明天": 1, "明晚": 1, "后天": 2, "大后天": 3}[tok]
        base_day = now.date() + timedelta(days=day_off)
        expr = m.group("rest").strip()
        if tok in ("今晚", "明晚"):
            pm_bias = True
            if not expr:
                expr = "20点"  # 不带钟点，默认 20:00

    if expr.startswith("周") or expr.startswith("星期") or expr.startswith("下周"):
        m = WEEK.match(expr)
        m = WEEK.match(expr)
        if m:
            next_week = m.group("prefix") == "下"
            target = WEEKDAYS[m.group("wd")]
            cur = now.weekday()
            days = (target - cur) % 7
            if next_week:
                # "下周一" = 下一个自然周的周一：先跳到本周日，再走到目标。
                days = (7 - cur) + target
            elif days == 0:
                days = 7  # 说"周三"而今天就是周三 → 下周
            base_day = now.date() + timedelta(days=days)
            expr = m.group("rest").strip() or "9点"

    h, mi, sec = parse_hhmm(expr)
    if h is None:
        # 时段前缀：「明天早上9点」→ 剥「早上」再试；前缀同时给出 am/pm 倾向
        m2 = PERIOD.match(expr)
        if m2:
            period = m2.group("p")
            rest = m2.group("rest").strip()
            # 光有时段词没钟点 → 取该时段的默认时刻
            if not rest:
                rest = {"早上": "8点", "上午": "9点", "中午": "12点",
                        "下午": "15点", "傍晚": "18点", "晚上": "20点", "凌晨": "2点"}[period]
            h, mi, sec = parse_hhmm(rest)
            if h is not None:
                if period in ("下午", "晚上", "傍晚") and h <= 11:
                    h += 12
                elif period in ("早上", "上午", "凌晨") and h == 12:
                    h = 0
    if h is not None and pm_bias and h <= 11:
        h += 12  # 今晚8点 → 20点
    if h is None:
        print(json.dumps({"ok": False, "error": "unparsed", "input": raw,
                          "hint": "支持: 18点 / 18:30 / 明天9点 / 后天14点 / 今晚8点 / 周三9点 / 下周一10点 / +2h / +30m / 3天后 / 2026-10-28 09:15"},
                         ensure_ascii=False))
        return 1

    at = datetime.combine(base_day, datetime.min.time()).replace(hour=h, minute=mi, second=sec or 0)
    if at <= now and day_off == 0 and not (raw.startswith("周") or raw.startswith("星期") or raw.startswith("下周")):
        at += timedelta(days=1)
        warnings.append("该时刻已过，顺延到明天")

    return emit(at, now, warnings, raw)


def emit(at: datetime, now: datetime, warnings: list, raw: str):
    mi2, snap_warn = snap_minute(at.minute)
    if snap_warn:
        at = at.replace(minute=mi2)
        warnings.append(snap_warn)

    if at <= now:
        print(json.dumps({"ok": False, "error": "in_past", "at": at.strftime("%F %T"),
                          "hint": "解析出的时刻已过去"}, ensure_ascii=False))
        return 1

    cron = f"{at.minute} {at.hour} {at.day} {at.month} *"
    out = {
        "ok": True,
        "cron": cron,
        "at": at.strftime("%Y-%m-%d %H:%M:%S"),
        "human": at.strftime("%Y-%m-%d %H:%M") + " (" + "一二三四五六日"[at.weekday()] + ")",
        "delta_min": int((at - now).total_seconds() // 60),
        "input": raw,
    }
    if warnings:
        out["warn"] = warnings
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())