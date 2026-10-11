#!/usr/bin/env python3
"""report_check.py — 报告交付前质量门禁（f 系写作 skill 的机械层）

把"报告必须满足的客观规则"从模型认知任务变成可重跑的脚本：
  - 正文每个数据点句末 `[n]` 引用、编号按首次出现顺序递增、同一来源全文复用
  - 正文引用 ↔ 文末参考文献双向勾稽、参考文献 `[n]` 升序
  - 标题层级、Markdown 表格、飞书禁用项（配图 / 手写编号 / hr / 无"资料来源"行）

设计原则：
  - 通用、不绑体系：不假设固定章节名、不要求 6 分片、不要求 ≥15 条（阈值可调）
  - 只校验 markdown 源（ffeishu 再转 lark-table XML）
  - 单文件 + argparse，只依赖标准库
  - 退出码：0 通过 / 1 校验失败 / 2 用法错误

子命令:
  check      [file] [--profile research|analysis|comparison|proposal|generic] [--min-refs N] [--min-tables N] [--json]
  renumber   [file] [--in-place | --output OUT] [--check]   按正文首现顺序重排引用编号 + 同步参考文献
  outline    [file] [--json]                                列出章节结构 + 表格位置 + 引用/来源统计

用法示例:
  python3 report_check.py check report.md
  python3 report_check.py check report.md --profile research --min-refs 15 --json
  python3 report_check.py renumber report.md --in-place
  python3 report_check.py outline report.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---- 正则 ----------------------------------------------------------------

# 正文数字引用 [1] / [2]，排除图片 ![..](..) 与 markdown 链接 [..](..)
CITATION = re.compile(r"(?<!!)\[(\d+)\](?!\()")
# 参考文献条目：行首 [n] 空格
REF_LINE = re.compile(r"^\s*\[(\d+)\]\s+(.*)$", re.MULTILINE)
# Markdown 表格分隔行 |---|---|
TABLE_SEP = re.compile(r"^\s*\|.*\|\s*$\n^\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*$", re.MULTILINE)
IMAGE = re.compile(r"!\[[^\]]*\]\(")
HTML_TAG = re.compile(r"<[A-Za-z/][^>]*>")
HR = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", re.MULTILINE)
HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
MANUAL_NUM = re.compile(r"^(?:[一二三四五六七八九十]+[、.]|\d+(?:\.\d+)*[、.\s]|\(\d+\)|（\d+）)")
SOURCE_ROW = re.compile(r"资料来源[：:]")
REF_HEADING = re.compile(r"^#{1,6}\s*参考文献\s*$", re.MULTILINE)

# 引用位置：句末（数据点后、句号/分号/换行前）——允许引用后紧跟句末标点
SENTENCE_END = "。！？；\n"

# 飞书禁用：旧写入链路残留
OLD_PIPELINE = re.compile(r"docs\s+\+(?:create|update|fetch)|block_insert_after", re.IGNORECASE)


class CheckError(Exception):
    pass


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def split_reference_section(text: str) -> tuple[str, str]:
    """返回 (正文, 参考文献块)。找不到 `参考文献` 标题时参考文献块为空。"""
    m = REF_HEADING.search(text)
    if not m:
        return text, ""
    return text[: m.start()], text[m.end():]


def extract_citations(text: str) -> list[int]:
    return [int(x) for x in CITATION.findall(text)]


def extract_reference_numbers(ref_block: str) -> list[int]:
    return [int(n) for n, _ in REF_LINE.findall(ref_block)]


# ---- check 子命令 --------------------------------------------------------

def check_report(
    path: Path,
    profile: str = "generic",
    min_refs: int = 0,
    min_tables: int = 0,
) -> dict:
    text = read(path)
    problems: list[str] = []
    warnings: list[str] = []
    info: dict = {"file": str(path), "profile": profile}

    if not text.strip():
        return {"ok": False, "problems": ["文件为空"], "warnings": [], "info": info}

    # --- 飞书禁用项 ---
    if IMAGE.search(text):
        problems.append("含 Markdown 配图 `![...](...)`；本系列报告正文应用表格承载并列信息（图走独立子文档）")
    if OLD_PIPELINE.search(text):
        problems.append("含旧写入链路残留（docs +create/update、block_insert_after 等）")
    if HR.search(text):
        problems.append("含分割线 `<hr>`（--- / *** / ___）")
    # 只检查明显的 HTML 标签（跳过 lark-table 允许的？——飞书源用 XML 不写 markdown，这里抓漏网）
    for tag in set(HTML_TAG.findall(text)):
        if "lark-table" not in tag and not tag.startswith("</"):
            warnings.append(f"含 HTML/XML 标签 {tag}（确认非误用）")

    headings = [(len(lvl), name.strip()) for lvl, name in HEADING.findall(text)]
    info["heading_count"] = len(headings)
    max_level = max((lvl for lvl, _ in headings), default=0)
    if max_level > 3:
        problems.append(f"存在 H{max_level} 标题（`####`+）；飞书仅支持 H1-H3")
    if not any(lvl == 1 for lvl, _ in headings):
        warnings.append("无 H1 主标题（若整篇由父文档承载可忽略）")

    numbered = [name for _, name in headings if MANUAL_NUM.match(name)]
    if numbered:
        problems.append(f"{len(numbered)} 个标题含手动编号前缀（飞书自动生成目录）：{numbered[:3]}")

    # --- 表格 ---
    table_count = len(TABLE_SEP.findall(text))
    info["table_count"] = table_count
    if min_tables and table_count < min_tables:
        problems.append(f"表格数 {table_count} < 要求 {min_tables}")

    source_rows = len(SOURCE_ROW.findall(text))
    info["source_row_count"] = source_rows
    if table_count and source_rows < table_count:
        warnings.append(
            f"{table_count} 张表但仅 {source_rows} 处「资料来源：」行（建议每张表正下方标注来源）"
        )

    # --- 引用 ---
    body, ref_block = split_reference_section(text)
    citations = extract_citations(body)
    ref_numbers = extract_reference_numbers(ref_block)
    info["citation_count"] = len(citations)
    info["unique_citations"] = len(set(citations))
    info["reference_count"] = len(ref_numbers)

    if not citations:
        warnings.append("正文未检测到任何 `[n]` 引用编号")
    else:
        # 连续性：集合 == {1..max}
        uniq = sorted(set(citations))
        expected = list(range(1, uniq[-1] + 1))
        if uniq != expected:
            problems.append(f"引用编号不连续：{uniq}，期望 {expected}")
        # 首现顺序：新编号按正文首次出现顺序递增
        seen: list[int] = []
        for m in CITATION.finditer(body):
            n = int(m.group(1))
            if n not in seen:
                want = len(seen) + 1
                if n != want:
                    problems.append(
                        f"引用编号首现顺序错乱：期望新来源为 [{want}]，实际出现 [{n}]"
                        f"（首现序列 {seen + [n]}）；跑 `renumber --in-place` 自动修正"
                    )
                    break
                seen.append(n)

    # --- 勾稽 ---
    if ref_block.strip():
        if not ref_numbers:
            problems.append("有 `参考文献` 标题但未检测到 `[n]` 条目")
        else:
            if ref_numbers != sorted(ref_numbers):
                problems.append(f"参考文献未按编号升序：{ref_numbers}")
            cited, refs = set(citations), set(ref_numbers)
            missing = sorted(cited - refs)
            unused = sorted(refs - cited)
            if missing:
                problems.append(f"正文引用了未定义的来源编号：{missing}")
            if unused:
                warnings.append(f"参考文献条目未被正文引用：{unused}")
            if min_refs and len(ref_numbers) < min_refs:
                problems.append(f"参考文献 {len(ref_numbers)} 条 < 要求 {min_refs}")
    elif citations:
        warnings.append("正文有引用但无 `参考文献` 标题（若来源仅在表下标注可忽略）")

    # --- profile 附加 ---
    if profile == "research":
        if "回扣主线" not in text:
            warnings.append("research 报告建议各章末端有 `回扣主线` 小节")

    ok = not problems
    return {"ok": ok, "problems": problems, "warnings": warnings, "info": info}


# ---- renumber 子命令 -----------------------------------------------------

def renumber(path: Path, in_place: bool, output: Path | None, check_only: bool) -> tuple[bool, str]:
    text = read(path)
    body, ref_block = split_reference_section(text)
    if not ref_block.strip():
        raise CheckError("找不到 `参考文献` 标题，无法重排")

    # 正文首现顺序
    order: list[int] = []
    for m in CITATION.finditer(body):
        n = int(m.group(1))
        if n not in order:
            order.append(n)
    mapping = {old: new for new, old in enumerate(order, start=1)}

    # 参考文献条目（保持条目文本，按新编号排序）
    entries = {int(n): t for n, t in REF_LINE.findall(ref_block)}
    for old in order:
        if old not in entries:
            raise CheckError(f"正文引用 [{old}] 在参考文献中不存在")
    for n in entries:
        if n not in mapping:
            raise CheckError(f"参考文献 [{n}] 未被正文引用（编号 {n}）")

    already_ok = all(mapping[old] == old for old in order) and ref_is_sorted(entries)

    def repl(m: re.Match) -> str:
        old = int(m.group(1))
        return f"[{mapping[old]}]"

    new_body = CITATION.sub(repl, body)
    new_refs = "\n".join(f"[{mapping[o]}] {entries[o]}" for o in sorted(order, key=lambda x: mapping[x]))
    new_text = new_body.rstrip() + "\n\n## 参考文献\n\n" + new_refs + "\n"

    if check_only:
        return already_ok, "编号已符合首现顺序" if already_ok else "编号需重排"

    if already_ok:
        return True, "编号已符合首现顺序，未改动"

    if in_place:
        path.write_text(new_text, encoding="utf-8")
        return True, f"已重排 {len(order)} 个来源的引用编号与参考文献（原地写回）"
    if output:
        output.write_text(new_text, encoding="utf-8")
        return True, f"已重排 {len(order)} 个来源，写入 {output}"
    return True, "（未指定 --in-place / --output，仅演示）:\n\n" + new_text


def ref_is_sorted(entries: dict[int, str]) -> bool:
    nums = list(entries.keys())
    return nums == sorted(nums)


# ---- outline 子命令 ------------------------------------------------------

def outline(path: Path) -> dict:
    text = read(path)
    body, ref_block = split_reference_section(text)
    sections = []
    lines = text.splitlines()
    # 记录每个标题后到下一个标题前的表格/引用数
    positions = [(m.start(), len(m.group(1)), m.group(2).strip()) for m in HEADING.finditer(text)]
    for i, (pos, lvl, name) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        chunk = text[pos:end]
        sections.append(
            {
                "level": lvl,
                "title": name,
                "tables": len(TABLE_SEP.findall(chunk)),
                "citations": len(extract_citations(chunk)),
                "source_rows": len(SOURCE_ROW.findall(chunk)),
                "has_recap": "回扣主线" in chunk,
            }
        )
    return {
        "file": str(path),
        "sections": sections,
        "citation_count": len(extract_citations(body)),
        "reference_count": len(extract_reference_numbers(ref_block)),
    }


# ---- CLI -----------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="报告交付前质量门禁（f 系写作 skill 机械层）")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="校验报告 markdown")
    c.add_argument("file", type=Path)
    c.add_argument("--profile", default="generic",
                   choices=["generic", "research", "analysis", "comparison", "proposal"])
    c.add_argument("--min-refs", type=int, default=0, help="参考文献最少条数（0=不限）")
    c.add_argument("--min-tables", type=int, default=0, help="表格最少张数（0=不限）")
    c.add_argument("--strict", action="store_true", help="把 warning 也当失败")
    c.add_argument("--json", action="store_true", help="以 JSON 输出")

    r = sub.add_parser("renumber", help="按正文首现顺序重排引用编号 + 同步参考文献")
    r.add_argument("file", type=Path)
    g = r.add_mutually_exclusive_group()
    g.add_argument("--in-place", action="store_true")
    g.add_argument("--output", type=Path)
    g.add_argument("--check", action="store_true", help="只检查不写")

    o = sub.add_parser("outline", help="列出章节结构 + 统计")
    o.add_argument("file", type=Path)
    o.add_argument("--json", action="store_true")

    args = p.parse_args()

    try:
        if args.cmd == "check":
            res = check_report(args.file, args.profile, args.min_refs, args.min_tables)
            if args.strict:
                res["problems"] += res["warnings"]
                res["warnings"] = []
                res["ok"] = not res["problems"]
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                print(f"[report_check] {args.file}  profile={res['info'].get('profile')}")
                for k in ("heading_count", "table_count", "citation_count",
                          "unique_citations", "reference_count", "source_row_count"):
                    if k in res["info"]:
                        print(f"  {k}: {res['info'][k]}")
                for w in res["warnings"]:
                    print(f"  WARN  {w}")
                for pr in res["problems"]:
                    print(f"  FAIL  {pr}")
                print(f"[report_check] {'通过' if res['ok'] else '失败'}（{len(res['problems'])} 问题 / {len(res['warnings'])} 警告）")
            return 0 if res["ok"] else 1

        if args.cmd == "renumber":
            changed, msg = renumber(args.file, args.in_place, args.output, args.check)
            print(f"[report_check] {msg}")
            return 0

        if args.cmd == "outline":
            res = outline(args.file)
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                for s in res["sections"]:
                    pad = "  " * (s["level"] - 1)
                    flags = []
                    if s["tables"]:
                        flags.append(f"{s['tables']}表")
                    if s["citations"]:
                        flags.append(f"{s['citations']}引")
                    if s["has_recap"]:
                        flags.append("回扣主线")
                    tail = f"  [{', '.join(flags)}]" if flags else ""
                    print(f"{pad}{'#' * s['level']} {s['title']}{tail}")
                print(f"[report_check] 正文引用 {res['citation_count']} 处 / 参考文献 {res['reference_count']} 条")
            return 0
    except CheckError as e:
        print(f"[report_check] 失败: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"[report_check] 文件不存在: {e}", file=sys.stderr)
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
