---
name: fpostpone
user-invocable: true
description: 定时延迟执行命令 —— 把一条命令排到将来某时刻再跑，输出回到本会话。用法：用户说"18点运行 XX"/"明天9点跑 XX"/"晚点执行 XX"/"到点跑 XX"/"+2h 跑 XX"/"列出定时任务"/"取消定时任务"触发。基于 Claude Code 官方 CronCreate（会话内投递），另提供 systemd 分离模式（关终端也能跑）。
allowed-tools: Bash, CronCreate, CronList, CronDelete, Read, Write, Workflow
---

# fpostpone — 定时延迟执行

把「现在想下、但不想现在跑」的命令排到将来某时刻执行。默认输出**回到本会话**。

```
/fpostpone 18点运行 /transliter "xxx.zip" 分析后给我建议
/fpostpone 明天9点 /transliter "a.zip"
/fpostpone +2h 跑完总结给我
/fpostpone list
/fpostpone cancel 8334d428
```

## 核心机制

**用 `CronCreate` 工具**，不是自己写调度。官方语义：把 prompt 排到未来，到点在**原会话**注入执行。
`prompt` 参数填「用户要跑的那条命令」原文，输出天然落在本会话。

本机实测（2026-10-27）：排 `12:52:00` 的任务，prompt 于 `12:59:18` 注入并执行成功。
延迟 7 分钟是因为期间会话一直 busy（我在跑工具）。→ 投递真实可用，但**排队等空闲**。

**硬约束（必须告知用户）**：只在会话活着且空闲时触发。关终端 → 不触发。
需要「关了终端也跑」→ 走 `--detach`，见下。

## 执行流程

### 1. 拆参数

`/fpostpone <时间表达式> <命令...>`，或 `list` / `cancel <id>`。

时间表达式与命令之间：用户可能写「18点运行」「明天9点」这种带「运行/跑/执行」衬词的，
衬词属于时间部分，剥掉。命令部分**原样保留**（含引号、斜杠命令、空格）。

判不出切分点 → 问用户，别猜。

### 2. 解析时间

```bash
python3 ~/git/skill/plugins/fpostpone/scripts/parse-time.py "<时间表达式>"
```

输出 JSON：`{ok, cron, at, human, delta_min, warn[]}`。

支持：`18点` `18:30` `明天9点` `后天14点` `今晚8点` `周三9点` `下周一10点`
`+2h` `+30m` `3天后` `13:07` `2026-10-28 09:15`

`ok:false` → 把 `hint` 给用户，AskUserQuestion 让他改，别自行编一个时间。

**整点自动挪到 :02**：官方文档明确一次性任务排在 `:00`/`:30` 会**提前最多 90 秒**跑。
脚本已自动 +2 分钟并在 `warn` 里说明 → **把 warn 转述给用户**，避免他以为时间算错了。

### 3. 确认

排之前把绝对时间念给用户一次（`human` 字段），尤其相对时间（`+2h`）和顺延过的
（`warn` 含「该时刻已过，顺延到明天」）。用户改口就重解析，别硬排。

### 4. 排任务

```
CronCreate({
  cron: "<parse-time 的 cron 字段>",
  prompt: "<命令原文>",
  recurring: false,   // 一次性；用完自删
})
```

- `recurring: false` —— fpostpone 是延迟执行，不是循环。用户明说「每天/每周」才 `true`（并提醒 7 天自动过期）。
- `durable` 默认**不加**。理由见 `references/scheduling-internals.md`：durable 会写
  `.claude/scheduled_tasks.json`，且**恢复时只认创建它的那个项目目录**，换目录不跑。
  用户明确要「跨会话/重启保留」才加 `true`。

排完回读 `CronList` 拿 id，把 `id` + `at` + 「会话需保持开启」一并报给用户。

### 5. 报告

输出：任务 id、绝对触发时间、`warn` 内容、以及这句约束：

> ⚠ 该任务只在**本会话开着且空闲**时触发。要关终端，用 `claude --bg` 把它转到后台会话，
> 或改用 `/fpostpone --detach ...`。

## list / cancel

- `/fpostpone list` → 调 `CronList`，表格列 id / 触发时间 / 命令摘要。
- `/fpostpone cancel <id>` → 先 `CronList` 核对 id 存在且是用户的，再 `CronDelete`。id 不存在就直说。

## --detach 模式（关终端也跑）

用户说「关了电脑也要跑」「关终端也要执行」或加 `--detach` 时用：

```bash
bash ~/git/skill/plugins/fpostpone/scripts/detach-run.sh \
  --at "<parse-time 的 at 字段>" \
  --cmd "<命令原文>" \
  --name "<任务名>"
```

它落一个 systemd user timer，到点无头跑 `claude -p "<命令>"`，结果写
`~/.cache/fpostpone/<name>/result.md`（摘要）+ `stdout.txt`（完整）。

本机实测（2026-10-27）：排 `13:03:14` → systemd `13:03:22` 触发 → `13:04:15` 完成，
输出正确、`CLAUDE_EXIT=0`、timer 自动回收、`result.md` 自动生成。

**它不吃 shell 环境**：claude 认证读 `~/.claude/settings.json` 的 `env` 块，
所以不用在 unit 里注入 key。新机器需 `loginctl enable-linger $USER`，否则登出后 timer 不跑。

**代价**：输出**不回到本会话**（分离进程），只能落盘 + 通知。用户若坚持要会话内输出，
说明只有 `CronCreate` 能做到、且需会话常开 —— 让他选。

## 已知坑

| 坑 | 说明 |
|----|------|
| 会话必须空闲 | 到点时你正忙于别的请求 → 排队等到空闲才跑，不是丢弃。官方 docs 明确 |
| 整点提前跑 | `:00`/`:30` 提前最多 90 秒。脚本已挪到 `:02`/`:32` |
| 恢复丢一次性任务 | `--resume` 恢复会话时，**已过期的**一次性任务不恢复 |
| 50 个上限 | 单会话最多 50 个定时任务 |
| recurring 7 天过期 | 循环任务 7 天后自删，长周期需重建 |
| durable 认目录 | 存盘任务只在创建它的项目目录里跑，复制到别处只列不跑 |

更多实测细节 → `references/scheduling-internals.md`