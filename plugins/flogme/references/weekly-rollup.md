# 周汇总（weekly_rollup.py）

每 KR 每周一条 worklog。取代 2026-07-20 删除的 SessionEnd hook 架构。

## 设计约束

| 约束 | 原因 |
|------|------|
| 每周一次，非每 session 一次 | 每天多 session 各一条 → 记录爆炸，看不动 |
| 每 KR 每周**最多一条** | 同一 KR 多 session 合并；跨终端同周也合并 |
| 已有本周记录 → 追加说明，不新建 | 多终端并发去重 |
| 空 session 跳过 | 0 user 消息 + 0 commit + 0 编辑 = 噪音 |
| /tmp 与作业目录的编辑不计入 | 临时文件不是工作产出 |

## 用法

```bash
cd ~/git/skill/plugins/flogme

python3 weekly_rollup.py                      # 本周（周一起），预览
python3 weekly_rollup.py --write              # 写入飞书
python3 weekly_rollup.py --week 2026-W43      # 指定 ISO 周
python3 weekly_rollup.py --since 2026-10-19   # 指定 7 天窗口起点
```

预览会打印每个 KR 的聚合结果和「新建 / 追加」判断，确认无误再加 `--write`。

## 聚合逻辑

```
扫 ~/.claude/projects/**/*.jsonl
  ↓ 时间窗过滤（timestamp 在 [周一, 下周一)）
parse_transcript
  ├─ commits      ← Bash tool_use 里的 git commit（实际很少，见下）
  ├─ edits        ← Write/Edit/MultiEdit 的 file_path（去重）
  ├─ user_prompts ← user 消息（过滤 <tag> 和 Caveat 开头的系统注入）
  └─ tokens       ← usage.input_tokens / output_tokens
  ↓ cwd 匹配 kr_route 前缀
按 (KR record_id, 项目名) 分组
  ↓ git log --since/--until 补真提交 + 提交计数
每组 → 一条 worklog（有则追加）
```

## ⚠️ commit 为什么从 git log 拿而不是 transcript

`~/git/` 下的仓库由 **auto-sync monitor 独占提交权**，session 从不自己执行 `git commit`
（见 ccconfig/CLAUDE.md 的约束）。所以 transcript 里根本没有 commit 命令 ——
实测上周 19 个 session，transcript 命中 0 个 commit，同期 git log 有 61 个。
真提交只在 git log 里有，必须去那里拉。

auto-sync 的提交信息是 `Auto-sync: <repo> N 文件`，语义为零，故只统计数量，
细节靠 transcript 的 edits（更精确）。

## 字段写入

| 字段 | 值 |
|------|-----|
| 标题 | `{项目} {ISO周} 工作汇总`，如 `ccconfig 2026-W43 工作汇总` |
| 成果类型 | `工具开发` |
| 关联KR | kr_route 匹配到的 KR；未匹配用 `_default` |
| 日期 | 周一（ISO 周起点） |
| 说明 | 周期 / session 数 / 提交数 / 改动文件 / 涉及任务 / 用量 |

## 踩坑

| 现象 | 原因 | 修法 |
|------|------|------|
| 第二次运行又新建一条 | `find_existing` 只查第一页 200 条，Worklog 已 240+ 条 | 必须翻页（`--offset` + `has_more`） |
| 每周重复新建（2026-10-30 修） | `find_existing` 读 `关联KR`，Base 里真名是 `所属KR` → 恒 None，去重永不命中；写也报 not_found | 运行时 `_kr_field()` 查真名 |
| 汇总里出现 `#!/bin/bash` 当提交信息 | `_extract_commit_msg` 在 `git commit` 之后贪心匹配 heredoc，抓到命令里更靠后的另一个 heredoc | 取位置最靠前的匹配 |
| `commit: 0` | transcript 里没有 commit 命令（auto-sync 独占提交） | 从 git log 拉 |
| `/tmp` 文件排第一 | 编辑统计没过滤临时路径 | `SKIP_EDIT_PATTERNS` |
| `ModuleNotFoundError: _skillconf_boot` | 在 `references/` 下 | `sys.path.insert(0, HERE/"references")` |
