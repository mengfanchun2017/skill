# flogme 自动化与定时任务

> SKILL.md 只留"什么时候自动跑"；cron 注册、手动补跑、边界条件在此。
> 历史上这里出过静默失败（cron 传了脚本没有的参数、字段名错被静默丢弃），
> 改动后必须实跑验证，不能只看 cron 注册成功。

## 自动化状态（2026-10-29 重构）

**旧架构已废弃**：2026-07-20 一次提交删掉了 `SessionEnd` hook + `session-end-aggregator.sh`
+ `session_end_aggregator.py` + `worklog_daily_research.py`（858 行），
worklog 因此**断裂 80 天**（最后一条 2026-08-10，发现于 2026-10-29）。
删除本身无报错、无告警 —— 自动化链路必须可观测。

**新架构**：每周一次 `weekly_rollup.py`，不再每 session 一条。

```
weekly_rollup.py
  ├─ 扫 ~/.claude/projects/**/*.jsonl（时间窗内）
  ├─ parse_transcript → commits / edits / user_prompts / tokens
  ├─ 按 cwd 匹配 kr_route → KR record_id
  ├─ 按 (KR, 项目) 聚合
  ├─ git log 补真提交（auto-sync 独占提交权，transcript 里没有 commit 命令）
  └─ 查本周是否已有该 KR 记录 → 有则追加，无则新建
```

**为什么不用 SessionEnd hook**：hook 删了静默失效、难观测、跨终端不汇总。
周汇总是有状态检查的显式命令，跑没跑一目了然。

## 定时任务（2026-11-01 改）

| 时间 | 命令 | 角色 |
|------|------|------|
| 周一 12:01 | `weekly_rollup.py --this-week --once --write` | 第一窗口 |
| 周二 12:01 | `weekly_rollup.py --this-week --once --write` | 第二窗口（周一没跑成才轮到） |
| 周三 12:01 | `weekly_rollup.py --this-week --once --write` | 最后窗口 |

已注册三个 durable cron（`da852822` 周一 / `e16b7868` 周二 / `f180f745` 周三），**7 天后自动过期**，
到时说「重建 worklog 周汇总定时」即可重注册。

**为什么三个窗口而不是一个**：定时任务靠 Claude session 空闲时投递，关机、重启、session 不在都会错过。三天三班倒，任一天跑成就够，剩下两天自动跳过。

**为什么中午而不是凌晨**：凌晨多半关机，12:01 是午饭时间，机器基本开着。

### 冲突问题：不存在，因为锚点是周一不是执行日

你问的「周三才记录，下周一又记录，怎么解决冲突」——天然不冲突：

- worklog 的 `日期` 字段**一律锚定该周周一**，不按实际执行日记
- 周三跑写入日期 = `2026-10-26`（那周周一）
- 下周一跑 `--last-week`，锚点还是 `2026-10-26`
- `find_existing` 按 `(KR, 日期)` 查 → 命中周三写的那条 → **覆盖，不新建**

这个锚点机制原本就是为「多终端并发跑同一周」设计的，三窗口只是同一个问题的另一种表现形式。2026-11-01 用 `--force` 重跑已实测验证：全部输出「已有本周记录 → 追加说明」，零重复。

### 每周只跑一次的守卫

`--once` 配合状态文件 `~/.claude/flogme_rollup_state.json`：

```json
{"last_anchor": "2026-10-26", "when": "2026-11-01T17:09:19", "ok": true, ...}
```

判据是**「同一锚点已成功写过」**，不是「今天跑过」：

| 情况 | 行为 |
|---|---|
| 周一写成功 | 周二周三读状态 → 跳过 |
| 周一写失败 | 状态没记 → 周二照常跑（自动补位） |
| 周一预览没加 `--write` | 状态没记 → 周二照常跑 |
| 周一二三都错过 | 下周一锚点换成新周一 → 正常跑 |
| 想手动重跑 | 加 `--force`，覆盖同一条不新建 |

预览（不带 `--write`）不写状态，只有真写入成功才标记 —— 否则看一遍预览就把本周锁死了。

### 已知限制

周一 12:01 跑的是「本周中段」（周一到周三），不是完整周。上周的完整数据要等下周一的 `--last-week` 才补全。这是三窗口方案的固有代价：早拿数据换取「这周到底做没做」的确认。

需要完整的上周数据时手动跑：`python3 weekly_rollup.py --last-week --force`

## 手动跑

```bash
cd ~/git/skill/plugins/flogme
export LARKSUITE_CLI_CONFIG_DIR="$HOME/.lark-cli-ailab"

# 汇总上一个完整周（补全程数据、或周一错过时补）
python3 weekly_rollup.py --last-week

# 汇总本周至今（cron 用的就是这条，加 --once 保证每周只跑一次）
python3 weekly_rollup.py --this-week --once --write

# 本周已写过状态、但想重跑（覆盖同一条，不新建）
python3 weekly_rollup.py --this-week --once --force --write

# 指定某一周
python3 weekly_rollup.py --week 2026-W43

# 指定任意 7 天窗口
python3 weekly_rollup.py --since 2026-10-19

# 以上全部默认预览；确认无误后加 --write 才写飞书
python3 weekly_rollup.py --last-week --write
```

**建议流程**：先不带 `--write` 跑一遍看聚合结果对不对（会打印每个 KR 的 session 数、提交数、文件数、标题），确认再加 `--write`。

## 数据补充扩展（2026-11-01）