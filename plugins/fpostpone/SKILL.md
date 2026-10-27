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

## 为什么不用官方的 `/schedule`（重要）

Claude Code 有**三种**调度，各自定位不同（官方 docs「Compare scheduling options」）：

| | **Cloud** (`/schedule`) | Desktop | **`/loop` + CronCreate** |
|---|---|---|---|
| 跑在哪 | Anthropic 云 | 你的机器（桌面 App） | 你的机器（session 内） |
| 要机器开着 | 否 | 是 | 是 |
| **要 session 开着** | 否 | 否 | **是** |
| 能读本地文件 | 否（新 clone） | 是 | 是 |
| 持久跨重启 | 是 | 是 | `--resume` 恢复（有例外） |
| 订阅要求 | Pro/Max/Team/Ent | Desktop App | 任意 |

**fpostpone 用 session 内 `CronCreate`**，理由：
1. 用户的场景是**本地批量翻译 zip**（transliter），必须读本地文件 → 排除 Cloud。
2. 要求**输出回到本会话**（用户明确说的）→ 只有 session 内的能做到，Cloud/Desktop 都做不到。
3. 本机用第三方 LLM 端点（非 claude.ai 账号），**没有 cloud scheduled tasks 能力**。

**什么时候该建议用户换官方方案**：
- 用户说「关了电脑也要跑/每天固定跑」→ 官方 **Desktop scheduled tasks**（`/schedule` 的 Desktop 版）
  或 cloud 版（若其有 claude.ai 付费账号）
- 用户要 GitHub 事件触发 / API 触发 → cloud scheduled tasks 独有
- 用户要跨机器、要可靠不依赖本机 → cloud

**fpostpone 的不可替代之处**：输出落在**当前会话的上下文里**——
后续对话能直接引用刚跑完的结果（"刚才那个翻译，你再分析下"）。
Cloud/Desktop 都是分离执行，结果得另取。

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
python3 ~/.claude/skills/fpostpone/scripts/parse-time.py "<时间表达式>"
```

输出 JSON：`{ok, cron, at, human, delta_min, warn[]}`。

支持：`18点` `18:30` `明天9点` `后天14点` `今晚8点` `周三9点` `下周一10点`
`+2h` `+30m` `3天后` `13:07` `2026-10-28 09:15`
相对：`10分钟以后` `半小时后` `2小时以后` `3天以后`（`以后`/`之后`/`后` 均可）
闲时窗口：`中午闲时`（=12:00-14:00）`晚上闲时`（=18:00 之后）`闲时`（挑最近一个）
时段词：`明天早上9点` `明天下午3点` `晚上`（光时段词取默认时刻）
衬词自动剥：`18点运行` `明天9点跑` `后天14点执行`
全角自动转半角：`14：50` `１８点` `＋2h`（中文输入法常见）
周六/日写作`周日`/`周天`均可。

**闲时窗口语义**（用户自定义）：中午闲时 = 12:00-14:00，晚上闲时 = 18:00 以后。
落点选窗口开头；已在窗口内则排到 +2 分钟。用户说「忙时多收费」时正是用这个。

`ok:false` → 把 `hint` 给用户，AskUserQuestion 让他改，别自行编一个时间。

**整点自动挪到 :02**：官方文档明确一次性任务排在 `:00`/`:30` 会**提前最多 90 秒**跑。
脚本已自动 +2 分钟并在 `warn` 里说明 → **把 warn 转述给用户**，避免他以为时间算错了。

### 3. 确认

排之前把绝对时间念给用户一次（`human` 字段），尤其相对时间（`+2h`）和顺延过的
（`warn` 含「该时刻已过，顺延到明天」）。用户改口就重解析，别硬排。

### 4. 排任务

**prompt 必须用统一包装格式**（下面解释为什么）：

```
CronCreate({
  cron: "<parse-time 的 cron 字段>",
  prompt: "【fpostpone 延时任务·原定 <at>】先输出一行：⏱ 执行 fpostpone 延时任务（原定 <at>），然后依次做三件事：① 执行 bash ~/.claude/skills/fpostpone/scripts/tasks.sh start --at \"<at>\"；② 执行下面的内容；③ 执行完后调用 bash ~/.claude/skills/fpostpone/scripts/tasks.sh done --at \"<at>\"。\n\n<命令原文>",
  recurring: false,   // 一次性；用完自删
})
```

**重要：用排定时间 `--at` 当键，不要用 id**。`CronCreate` 返回的 id 要等调用完才知道，
而 prompt 在调用时就固化了 → 没法把 id 写进 prompt。
`--at`（排定时间，如 `2026-10-27 15:20`）在排任务**之前**就算出来了，稳定可写。
`tasks.sh start/done` 同时接受 `--id`（支持前缀模糊）和 `--at`，二选一即可。

**为什么必须包装**（两个硬约束叠加）：

1. 注入的 prompt 到点时是**一条普通消息**，到点的 Claude 无法知道它是定时的还是刚打的
   → 必须靠 prompt 自带信息才能输出「这是延时任务」的提示。
2. 注入时 **fpostpone 的 SKILL.md 不会加载**（只有 `/fpostpone` 被调用时才进上下文）
   → 不能指望到点的 Claude 去读 skill；所有指令（提示、start、done）都得写进 prompt。

包装成自然语言还顺带解决另一个坑：slash 命令（如 `/transliter <zip>`）后面
**不能夹带说明文字**——本机实测（2026-10-27），那段说明会被**并进 `args`**
污染命令参数。包装后整体是自然语言，由到点的 Claude 自行调用 Skill/Workflow 工具，
不依赖 slash 文本展开，反而更稳。

**示例**（用户原始需求形态）：

用户打：`/fpostpone 18点运行 /transliter "xxx.zip" 分析后给我建议`

```
CronCreate({
  cron: "2 18 27 10 *",
  prompt: "【fpostpone 延时任务·原定 2026-10-27 18:02】先输出一行：⏱ 执行 fpostpone 延时任务（原定 2026-10-27 18:02），然后依次做三件事：① 执行 bash ~/.claude/skills/fpostpone/scripts/tasks.sh start --at \"2026-10-27 18:02\"；② 执行下面的内容；③ 执行完后调用 bash ~/.claude/skills/fpostpone/scripts/tasks.sh done --at \"2026-10-27 18:02\"。\n\n用 Workflow 工具跑 transliter workflow，args 传 /abs/path/xxx.zip。跑完读日志，分析失败/部分成功的文档，给出建议。",
  recurring: false,
})
```

> 实操顺序：① `parse-time.py` 算出 `at` → ② 用上面模板排任务（`at` 已知，直接写死）
> → ③ 拿到 `CronList` 的 id，用 `tasks.sh add --id <id> --at "<at>"` 登记
> → ④ 报告给用户。到点时执行侧靠 prompt 里的 `at` 定位记录，不依赖 id。

参数：
- `recurring: false` —— fpostpone 是延迟执行，不是循环。用户明说「每天/每周」才 `true`（并提醒 7 天自动过期）。
- `durable` 默认**不加**。理由见 `references/scheduling-internals.md`：durable 会写
  `.claude/scheduled_tasks.json`，且**恢复时只认创建它的那个项目目录**，换目录不跑。
  用户明确要「跨会话/重启保留」才加 `true`。

排完回读 `CronList` 拿 id，**并把任务登记进影子表**（用户可随时自查）：

```bash
bash ~/.claude/skills/fpostpone/scripts/tasks.sh add \
  --id "<CronList 拿到的 id>" --cron "<cron>" --at "<human>" --cmd "<命令>"
```

**为什么必须登记**：session-only 的 `CronCreate` 任务**没有任何用户可见文件**
（不写 `scheduled_tasks.json`），用户在终端里查不到 → 会怀疑任务没排上。
影子表落 `~/.cache/fpostpone/tasks.json`（不进公开仓库），`/fpostpone list` 读它。

⚠ **影子表是全局文件，但必须按 session 隔离显示**（用户反馈过 bug：多个 session
都看到提醒，误导）。`tasks.sh add` 自动记 `CLAUDE_CODE_SESSION_ID` 到 `session` 字段；
`statusline.sh` 从 stdin 的 `session_id` 读当前会话并按归属过滤。
→ 别的 session 不显示本 session 的任务（`CronCreate` 本就是 session-only，
在别的 session 里确实不会触发，显示了才是错的）。

把 `id` + `at` + 「会话需保持开启」一并报给用户。

### 4c. 执行侧：延时任务注入后必须调用 start/done

**这一步写在 prompt 包装里，到点的 Claude 照做**（见 4b 的包装格式）。
影子表状态机 `pending → running → finished`，**两端的实际时间都要记**：

```bash
bash ~/.claude/skills/fpostpone/scripts/tasks.sh start --id "<id>"   # 刚接手时
# …执行命令…
bash ~/.claude/skills/fpostpone/scripts/tasks.sh done  --id "<id>"   # 干完时
```

**为什么两端都要**：用户要看到底栏显示「已完成 15:20-15:34」这种**实际执行区间**。
只记完成时间算不出区间；排定时间 ≠ 实际执行（实测延迟 4 秒~7 分钟不等）。

**已完成记录不主动清除**——用户明确要求"不消除，让我知道做了什么"。
底栏无待执行任务时回显最近 3 条已完成；`/fpostpone list` 列全部历史。
只保留最近 50 条已完成，超出用 `tasks.sh prune --keep N`。

### 5. 报告

输出：任务 id、绝对触发时间、`warn` 内容、以及这句约束：

> ⚠ 该任务只在**本会话开着且空闲**时触发。要关终端，用 `claude --bg` 把它转到后台会话，
> 或改用 `/fpostpone --detach ...`。

## list / cancel

- `/fpostpone list` → **两个来源都查**：
  1. `CronList`（真伪权威——任务跑完自删，这里没了就是真没了）
  2. `bash ~/.claude/skills/fpostpone/scripts/tasks.sh list`（影子表，含历史）
  两边对不上时以 `CronList` 为准，并把影子表里已消失的标成 finished
  （`tasks.sh done --id <id>`）。
- `/fpostpone cancel <id>` → 先 `CronList` 核对 id 存在且是用户的，再 `CronDelete`，
  然后 `tasks.sh done --id <id>`。id 不存在就直说。

## 待执行任务的提醒

用户问「有任务在等吗」「待执行任务」→ `CronList` + `tasks.sh list --pending-only`。

**主动提醒时机**（用户明确要求过）：
- 每次用 `/fpostpone` 排完新任务后，顺带列一下**全部**待执行任务
  （用户想知道自己积压了几个）
- 用户开工新对话、或问「现在有什么任务」时，主动报 pending 清单
- 报的时候带**相对时间**（"还有 6 分钟" / "明天 9:02，还有 19 小时"），
  比绝对时间更直观

## 定时前能否跑别的对话

**能，正常跑。** 排完任务后你可以继续正常交互、开新话题、跑别的工具。

唯一注意事项（实测过三次）：
- 到点时**若我正忙于别的请求**，任务会**排队等空闲**再跑，**不是丢弃、不是取消**。
  实测：排 12:52 → 12:59:18 才注入（延迟 7 分，因期间一直在跑工具）；
  排 13:23 → 13:26:12 注入（延迟 3 分）。
- 所以**延迟几秒到几分钟是正常现象**，不是坏了。
- 想准点跑 → 到点前几秒别发新请求，让 session 空着。
- 任务不会因为你在跑别的对话而被顶掉。它跟你的对话是**排队**关系，不是抢占。

## --detach 模式（关终端也跑）

用户说「关了电脑也要跑」「关终端也要执行」或加 `--detach` 时用：

```bash
bash ~/.claude/skills/fpostpone/scripts/detach-run.sh \
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
| 会话必须空闲 | 到点时你正忙于别的请求 → 排队等到空闲才跑，不是丢弃（实测延迟 3-7 分钟） |
| 整点提前跑 | `:00`/`:30` 提前最多 90 秒。脚本已挪到 `:02`/`:32` |
| 用户查不到任务 | session-only 任务无落盘文件 → 必须登记影子表，否则用户以为没排上 |
| 全角字符 | 中文输入法的 `14：50` `１８点` 需转半角，脚本已处理 |
| 恢复丢一次性任务 | `--resume` 恢复会话时，**已过期的**一次性任务不恢复 |
| 50 个上限 | 单会话最多 50 个定时任务 |
| recurring 7 天过期 | 循环任务 7 天后自删，长周期需重建 |
| durable 认目录 | 存盘任务只在创建它的项目目录里跑，复制到别处只列不跑 |

更多实测细节 → `references/scheduling-internals.md`