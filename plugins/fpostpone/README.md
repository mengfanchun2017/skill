# fpostpone — 定时延迟执行

> 把「现在想下、但不想现在跑」的命令排到将来某时刻执行，**输出回到发起它的那个会话**。

```bash
/fpostpone 18点运行 /transliter "xxx.zip" 分析后给我建议
```

到 18:02，命令在原会话里自动执行，结果就出现在你眼前——后续对话可以直接引用它
（"刚才那个翻译，你再分析下"）。

## 什么场景用它

| 场景 | 例子 |
|---|---|
| **避开忙时/高价时段** | 白天 LLM 忙时单价高，把批量任务排到闲时：`/fpostpone 中午闲时 /transliter "a.zip"` |
| **批量长任务延后跑** | 上百篇文档翻译要跑一小时，现在下达、晚点执行 |
| **想让结果留在当前对话里** | 跑完还要继续和 Claude 讨论结果，不是只收个通知 |
| **定时提醒自己做某事** | `/fpostpone 明天9点 提醒我提交周报` |
| **排队错峰** | 多个任务排不同时刻，避免同时打满上游 |

**不适合**：关了终端也要跑 / 每天固定跑 / 跨机器可靠执行 —— 见下方「与其他方案对比」。

## 安装

```bash
/plugin install fpostpone@mengfanchun2017-skills
```

依赖：只需 Claude Code 本身（会话内调度是官方内置能力）。`--detach` 模式额外需要
`systemd --user` + `linger`（Linux/WSL）。

## 用法

### 基本形式

```
/fpostpone <时间表达式> <命令>
```

命令可以是任意自然语言指令，也可以是其他 skill/workflow：

```
/fpostpone 18点运行 /transliter "C:\docs\batch.zip"
/fpostpone 明天9点 汇总昨天合并的 PR
/fpostpone +2h /fworch-report 生成季度报告
/fpostpone 中午闲时 用 fsearch 调研竞品动态
```

### 支持的时间写法

| 类别 | 例子 |
|---|---|
| 钟点 | `18点` `18:30` `13:07` |
| 日期 | `明天9点` `后天14点` `今晚8点` `周三9点` `下周一10点` |
| 相对 | `+2h` `+30m` `3天后` `10分钟以后` `半小时后` |
| 时段 | `明天早上9点` `明天下午3点` `晚上` |
| **闲时窗口** | `中午闲时`（12:00-14:00）`晚上闲时`（18:00 后）`闲时`（挑最近一个） |
| 绝对 | `2026-10-28 09:15` |

全角字符自动处理（中文输入法常见）：`14：50` `１８点` `＋2h`。
衬词自动剥离：`18点运行` `明天9点跑`。

### 管理任务

```
/fpostpone list              # 列出全部（待执行 + 已完成历史）
/fpostpone cancel <id>       # 取消
```

任务还会**常驻显示在 Claude Code 底栏**（statusLine）：

```
⏳ 15:58 计算100以内质数（还有 1 分钟）
✓ 15:58 计算100以内质数 已完成 15:58-16:04
```

跑完的记录**不自动清除**，你能看到自己做过什么。

### `--detach` 模式（关终端也跑）

```bash
bash ~/.claude/skills/fpostpone/scripts/detach-run.sh \
  --at "2026-10-27 18:02" --cmd "/transliter /path/x.zip" --name batch1
```

落一个 systemd timer，到点无头跑 `claude -p`，结果落
`~/.cache/fpostpone/<name>/result.md`。

**代价**：输出**不回到原会话**（分离进程）——只有落盘 + 通知。

## 重要限制

⚠️ **会话必须活着且空闲才触发**。这是会话内调度的固有约束（官方设计如此）：

- 关终端 / 会话退出 → **不触发**
- 到点时 Claude 正忙 → **排队等空闲**再跑，**不是丢弃**
  （实测延迟 4 秒 ~ 7 分钟不等）
- 想准点跑：到点前几秒别发新请求，让会话空着

其他：

- 单会话最多 50 个定时任务
- 循环任务 7 天后自动过期
- `--resume` 恢复会话时，**已过期**的一次性任务不恢复
- 一次性任务排在整点 `:00` / 半点 `:30` 会**提前最多 90 秒**触发 → 本 skill 自动挪到 `:02`/`:32`

需要「关了电脑也跑」→ 用 `--detach`，或改用官方 Desktop / cloud scheduled tasks。

## 与其他调度方案对比

Claude Code 有三种调度（官方文档「Compare scheduling options」）：

| | Cloud `/schedule` | Desktop | **本 skill（会话内）** |
|---|---|---|---|
| 跑在哪 | Anthropic 云 | 本机桌面 App | 本机会话内 |
| 要机器开着 | 否 | 是 | 是 |
| 要会话开着 | 否 | 否 | **是** |
| 读本地文件 | 否（新 clone） | 是 | 是 |
| **输出回原会话** | 否 | 否 | **是** |
| 订阅要求 | Pro/Max/Team/Ent | 桌面 App | 任意 |
| 需要 GitHub/API 触发 | 是 | 否 | 否 |

**选 fpostpone 当**：你要读本地文件、要结果留在当前对话、要避开特定时段。

**选官方方案当**：
- 关了电脑也要跑 → Desktop scheduled tasks
- 每天/每周固定跑、跨机器可靠 → cloud scheduled tasks
- GitHub 事件 / API 触发 → cloud 独有

## 它和官方 `CronCreate` 什么关系

**底层就是官方的 `CronCreate` 工具**（会话内调度），本 skill 只是包了一层，补上三个缺口：

1. **中文时间表达 → cron**：官方只接受 5 字段 cron 表达式
2. **任务可见性**：会话内任务不写任何落盘文件，用户在终端查不到 → 本 skill 维护影子表并显示在底栏
3. **执行留痕**：注入的 prompt 到点是普通消息，无从分辨是不是定时任务 → 包装里自带提示与打点

官方没有提供可直接敲的 slash command（`CronCreate` 是给 agent 调的工具，如同 `/bash` 不存在），
所以这层壳是必要的。

## 文件结构

```
plugins/fpostpone/
├── SKILL.md                          # skill 主流程
├── scripts/
│   ├── parse-time.py                 # 中文时间表达式 → cron
│   ├── tasks.sh                      # 任务影子表（按会话隔离）
│   ├── statusline.sh                 # 底栏显示
│   └── detach-run.sh                 # systemd 分离模式
└── references/
    └── scheduling-internals.md       # 实测记录与坑
```

数据落在 `~/.cache/fpostpone/tasks.json`（不进仓库）。

## 许可

同仓库 LICENSE。