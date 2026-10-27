# 调度机制实测记录

2026-10-27 在本机（WSL2 Ubuntu / RedmiPro）实测。数字是实测值，不是推测。

## CronCreate（默认模式）

官方文档：https://code.claude.com/docs/en/scheduled-tasks

**实测**：排 `52 12 27 10 *`（12:52:00 触发），实际 prompt 于 **12:59:18 注入**。
延迟 7 分钟，原因是期间会话一直在跑工具调用（busy）。

→ 结论：`CronCreate` 的 prompt **确实投递回原会话**，但**只在会话空闲时**投递。
busy 期间是在队列里等，不是丢弃、也不是另起进程。

**实测**：排定后 `CronList` 立刻可见 id（8 字符，如 `8334d428`），
一次性任务跑完自动从列表消失。

### 整点提前跑（官方文档，未单独实测）

> A one-shot task scheduled for `:00` or `:30` runs up to 90 seconds early.

这直接影响「避开忙时」的用例：`18点` 若真排 `18:00`，可能在 17:58:30 就起，
仍踩在忙时段。故 `parse-time.py` 自动把 `:00`→`:02`、`:30`→`:32`，并在 `warn` 里说明。

其余分钟不偏移。

### durable 的取舍

- `durable:false`（默认）→ 只在内存，会话结束即失。
- `durable:true` → 写 `<项目>/.claude/scheduled_tasks.json`。

官方限制：**`.claude` 目录或该文件是 symlink 时报错拒绝调度**；
**任务只在创建它的项目目录里跑**，复制到别的目录只列出不执行。

本机 `~/git/ccconfig/.claude` 是真实目录（非 symlink），所以 durable 可用。
但 `~/git/skill`（skill 源头仓库）目录不同 → 在那排的 durable 任务换目录不跑。

**故默认不加 durable**。用户明确要跨重启保留时才加，并说明它会绑死创建目录。

### 公开仓库泄漏防护

ccconfig 是公开仓库。`durable:true` 会把 prompt 原文写进项目内文件，
prompt 可能含真实路径/业务数据。
本机 `.git/info/exclude` 已有 `**/.claude/scheduled_tasks.json`，
实测 `git check-ignore -v` 确认命中 → 不会进公开库。

**别的机器/新 clone 未必有此 exclude**，用 durable 前应确认：
```bash
cd <项目> && git check-ignore -v .claude/scheduled_tasks.json
```

## systemd timer（--detach 模式）

### 实测链路

```
13:03:14 排定 → 13:03:22 systemd 触发 → 13:04:15 claude 完成
输出: DETACH-E2E-4417 / CLAUDE_EXIT=0
timer 跑完自动回收（list-timers 里消失，service inactive）
```

### 关键点

| 项 | 实测结论 |
|----|---------|
| `--on-calendar` 相对 | `--on-active=2s` 可用 |
| `--on-calendar` 绝对 | `"2026-10-28 09:15:00"` 可用 |
| `--on-calendar` 中文 | `"18点"` **报错** `Failed to parse calendar event specification` → 必须自己转 |
| 认证 | unit 内 `claude -p` 成功。认证读 `~/.claude/settings.json` 的 `env` 块，**不吃 shell 继承** |
| linger | 本机 `Linger=yes`，故用户登出后 timer 仍跑。**新机器需 `loginctl enable-linger`** |
| XDG_RUNTIME_DIR | 脚本内自动补 `/run/user/$(id -u)`，否则 systemctl --user 报错 |

### TimeoutStartSec 坑（未实测但必然踩）

`systemd-run --user` 默认 `Type=simple`，service 起来就不管了——够用。
但若显式用 `Type=oneshot`，默认 `TimeoutStartSec=90s`，**transliter 跑百篇要 1 小时+，会被杀**。
脚本已传 `--property=TimeoutStartSec=infinity` 兜底。

### 为什么 detach 模式输出回不到原会话

它起的是**独立 `claude -p` 进程**，与用户当前会话无关，输出只能落盘。
这是架构决定的，不是 bug。要「输出回本会话」只能用 `CronCreate`。

## 两个模式的决策表

| 诉求 | 模式 | 输出落点 |
|------|------|---------|
| 晚点在同一会话里跑 | `CronCreate` | 原会话 ✓ |
| 关终端也跑 | `--detach` (systemd) | 落盘 + 通知 |
| 跨重启保留 | `CronCreate durable:true` | 原会话（须同项目目录） |
| 每天/每周循环 | `CronCreate recurring:true` | 原会话（7 天过期） |