---
name: flogme
user-invocable: true
description: 个人管理系统 — OKR 目标管理、Worklog 工作日志、Reflect 反思、SUM 周期/领域总结生成。数据存飞书 Base，输出到飞书文档。
allowed-tools: Bash, Read, Write, Edit, Agent, WebSearch, mcp__tavily__tavily_search, mcp__minimax__web_search
---

# flogme — 个人管理系统

OKR → KR → Worklog → Reflect → SUM 五层架构，全部数据存飞书 Base。

## 架构

```
🎯 OKR（最高级）
   ├─ O: 方向性目标，季度/年度级别，变化慢
   └─ KR: 可量化关键结果，变化快，关联一个 O
        │
        ▼
📝 Worklog（日常记录）
   └─ 每条必须关联一个 KR，自动继承分类
        │
        ▼
🪞 Reflect（定期反思）
   └─ 周/月/季度，可选关联 O
        │
        ▼
📊 SUM（总结生成）双通道
   ├─ 个人总结: 读取以上三层 → 内置模板 → 飞书文档
   └─ 汇报输出: 学习外置模板 → Worklog+KR数据+用户输入 → 飞书文档
```

**核心原则**：O=why, KR=what success, Worklog=what I did, Reflect=what I learned, SUM=what it means.
**分类体系**：所有层级共用 `work / learn / project` 三类（工作/学习/项目）。

## 配置

> 📖 完整说明 → [config.aiagt.dev](https://config.aiagt.dev/flogme)

**ccconfig 用户**：真实值放 `ccprivate/skill/flogme.yaml`，`init-skill.sh sync` 自动覆盖。
**独立用户**：`cp config.yaml.example config.yaml` 填入真实值。

需提前准备：
- 飞书 Base（手动创建）→ 获取 Base token + 表 ID
- wiki 节点 token → OKR/SUM 文档输出位置
- `config.yaml.example` 含所有字段获取方式

config.yaml 在 ccprivate，含 Base tokens + table IDs + wiki node。数据结构见 [references/data-model.md](references/data-model.md)。

## 数据模型

4 个表（OKR_O / OKR_KR / Worklog / Reflect），完整字段规范 → [references/data-model.md](references/data-model.md)。

> KR_Progress 表已于 2026-06-09 废弃，详见 [ADR-0003](../../docs/adr/0003-deprecate-tasks-and-kr-progress.md)。

## 工作流

### 1. OKR 创建

```
用户: "新设一个 work 的 O：XXX，季度目标"
  → OKR_O 表创建 Objective → 拆解 2-5 个 KR → OKR_KR 表创建并关联 O
```

KR 写法：✅ "模型分流系统上线，P99 延迟降低 50%" ❌ "完成模型分流开发"（任务不是结果）。

### 2. Worklog 写入

**手动**：用户说"写日志"/"记录工作" → agent 判断 → 调 flogme skill → 写飞书 Base。
或直接运行 `log_write.py worklog --title ... --kr recXXX [--tokens-in N --tokens-out N --asst-msgs N --user-msgs N]`。

**周汇总（当前主路径）**：`weekly_rollup.py` 扫全部 session transcript，按 KR 聚合，
**每个 KR 每周一条 worklog**。多 session 合进同一条，已有本周记录则追加。
→ [references/weekly-rollup.md](references/weekly-rollup.md)

KR 自动路由、质量规则、合并策略、字段规范 → [references/data-model.md](references/data-model.md)。
整合脚本用法 → `worklog_consolidate.py --mode merge|weekly|monthly|dry-run`，详见 [references/data-model.md](references/data-model.md)。

### 3. Reflect 写入

```
用户: "做周反思" / "weekly reflect"
  → 拉取本周 Worklog → 引导填写四象限（做得好/待改进/学到/下阶段）
  → 调 log_write.py reflect 写入 Reflect 表
  → 注: 不自动改 KR 状态，KR 完成时主动跑 kr-status
```

写入命令：`log_write.py reflect --title "..." --period "周" --good "..." --improve "..." --learned "..." --next "..."`

### 4. SUM 总结生成

```
用户说"生成X总结"
  ├─ 个人总结（模板内置）→ 周期/领域/OKR复盘/年报
  │    拉取 Base 数据 → sum_generate.py 按模板生成 Markdown → 委托 ffeishu 创建飞书文档
  └─ 汇报输出（模板外置）→ 学习飞书文档模板 → 按模板结构填数据 → ffeishu 创建
       模板在 OKR wiki 节点「模板」文件夹，fetch 后提取 H1/H2/表格/固定文案
```

**个人总结类型**：
| 类型 | 触发示例 | 模板侧重 |
|------|---------|---------|
| 周期总结 | "生成本季度工作总结" | 时间维度：成果、不足、下阶段 |
| 领域总结 | "生成 AI 领域年度总结" | 领域维度：worklog 聚合 |
| OKR 复盘 | "复盘 Q2 OKR" | O 达成度、KR 评分、经验教训 |
| 综合年报 | "生成年度个人报告" | 三分类汇总 + 成长轨迹 + 新年 OKR |

模板详情 → [references/templates.md](references/templates.md)。

**SUM 生成命令**：拉取 Base 数据后用 `sum_generate.py` 生成 Markdown，详见 [references/commands.md](references/commands.md)。

## 数据写入

`log_write.py` 统一封装 worklog / reflect / kr-status 三个写入动作。命令用法 → [references/commands.md](references/commands.md)。

## Base 初始化

新建 Base 推荐 rename 默认表 + 加字段。auto_number 转 number、field-update vs raw API 选型 → [references/base-init.md](references/base-init.md)。

## 命令速查

lark-cli 环境变量、Base 数据拉取、SUM 生成全流程 → [references/commands.md](references/commands.md)。

## 集成点

| 系统 | 关系 |
|------|------|
| f-worklog | 简化版，flogme 是其升级替代 |
| ffeishu | SUM 输出目标：飞书文档，统一编排 lark-cli（不直接依赖 lark-* skill） |
| fpptx | 年度总结可选输出 PPT |
| fresearchframe | 领域总结前可联动做行业调研 |
| lark-cli | 所有飞书操作（文档/Base/表格/日历）通过 lark-cli（npm 全局） |

## 文档创建规则

SUM 生成飞书文档时，**必须通过 ffeishu skill 创建**（不裸调 lark-cli），原因：
- ffeishu 加载 write-checklist.md 等格式化约束，保证格式规则完整进 context
- 直接裸调会丢失格式化约束，导致编号标题、分割线、窄表格等问题

flogme 职责：从 Base 聚合数据 → 按模板填 Markdown → 交给 ffeishu 创建文档。

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

claude code 的 session transcript 只覆盖在终端里做的事，公司聊天、会议、线下沟通等不在记录范围内。以下三个扩展补全这些缺口。

### 扩展一：用户手动补充（Supplement 表）

用户手动写入 claude code 中缺失的工作信息（会议、沟通、非终端工作等）：

**如何识别**：用户以口语化方式说「flogme 记一下 xxx」或「帮我记录 xxx」，判断属于工作内容但不来自 session → 写入 Supplement 表。

**如何存储**：Base 内新增 `Supplement` 表（`tblwUDLiiho0AkjP`），4 个字段：

| 字段 | 类型 | 作用 |
|------|------|------|
| 标题 | text | 主字段，简短描述 |
| 日期 | datetime | 发生日期 |
| 内容 | text | 详细描述：背景、动作、结果、涉及方 |
| 来源 | select | 工作群消息 / 会议 / 文档 / 口头沟通 / 其他 |
| 关联KR | link → oKR | 双向关联，对侧字段为`补充记录` |

**写入方式**：同 worklog/reflect，用 `record-upsert` 写入：

```bash
export LARKSUITE_CLI_CONFIG_DIR="$HOME/.lark-cli-ailab"
BASE_TOKEN="LX5lb6VfdaJHWrsRbTgc8Y50nmj"
lark-cli base +record-upsert --base-token "$BASE_TOKEN" --table-id "tblwUDLiiho0AkjP" \
  --json '{"标题":"...","日期":"2026-11-01","内容":"...","来源":["会议"],"关联KR":[{"id":"rec..."}]}' \
  --as user
```

**weekly_rollup 整合**：跑周汇总时，同时读 Supplement 表中本周的记录，按 `关联KR` 分组，追加到该 KR 的 worklog 说明末尾的「补充来源：」段（`📝` 标记）。

**只有补充、没有 session 的 KR 也会出记录**——公司会议/沟通本来就不在终端里，这正是补充机制存在的理由。此时项目名记为「部门工作」，说明只有「周期：xxxx」+ 补充来源，不写 session 数/用量（那是噪音）。该 KR 本周已有 session 记录时不另开一条，补充文字并进主记录，避免 `Log.count` 翻倍。

### 扩展二：部门工作记录表读取

公司部门的工作记录多维表格（工作任务列表 Base，`Ei2ybk3FRagHbksfqXzcujsYnWf`）可作为独立数据源：

- Base 名：工作任务列表（wiki 节点 `ZDyhwRkHmiWFOHkuJBfc8I8Hn8b`）
- 工作记录表 `tblCdxkqxtpw0M6S`：241 条记录，含填写日期、周期、工作内容、ai简短总结、ai关联任务、记录人
- 工作总结表 `tblNMkFG8r8tAZj8`：40 条记录，含类别（周总结/详细周总结/AI培训总结）、本周总结、下周计划

**weekly_rollup 整合**：扫描窗口内 `记录人=孟繁春` 且 `周期=本周` 的记录，按 `ai关联任务` 查 `config.work_base.task_kr` 映射到 KR，追加到 worklog 说明（`📋` 标记）。

**映射必须显式配置，不做模糊匹配**。未映射的任务不进任何 worklog（否则同一段文字会被挂到所有 KR 上），只在跑汇总时打印「⚠ N 条未映射」提示补映射：

```yaml
work_base:
  token: "Ei2ybk3FRagHbksfqXzcujsYnWf"
  tables:
    records: "tblCdxkqxtpw0M6S"
    summary: "tblNMkFG8r8tAZj8"
  task_kr:                              # 部门任务名 → 本系统 KR record_id
    "运维AI大脑搭建": "recvmWXG8X7gZA"
    "运维知识智能问数": "recvmWTjTz0HTo"
    # ... 没列的任务不写入
```

**坑**：部门表的 `ai简短总结` 自带「任务名：」前缀，不去掉会写成 `📋 运维AI培训赋能：运维AI培训赋能：…` 双重前缀。

**局限性**：部门表按「本周/下周」分类而非具体日期，只能取「本周」这一档，无法精确到天。

### 扩展三：工作群消息（2026-11-01 已打通）

原先 ailab 没有 IM scope，`im +chat-list` 返回 0 个会话。2026-11-01 用 `lark-cli auth login --recommend` 重新授权后，**IM 已可读**——`+chat-list` 返回 24 个会话，`+chat-messages-list` 能读历史消息，包括转发合并消息（`merge_forward`，一条能含几千字的多人讨论）。

配置在 `config.im_chat`：

```yaml
im_chat:
  chats:
    - chat_id: "oc_xxx"
      label: "孟繁春（工作转发）"
  kw_kr:                    # 关键词 → KR，命中才挂
    "知识库": "recvmWTjTz0HTo"
    "培训": "reczz28TY5yh3Sx2"
    # ... 没命中的进 _unmapped，只统计条数不写入
```

**消息不自动挂 KR**：群里既有本人发言也有别人发言和系统卡片推送，靠关键词硬匹配必然错。只有命中 `kw_kr` 的才落到对应 KR，其余进 `_unmapped` 桶，跑汇总时只打印条数。

**消息清洗**（实测踩出来的）：

- 纯链接消息（转发文档地址，50-80 字）没有信息量，正文里只会堆一串 URL → 过滤。但**长转发消息即使含 URL 也要留**，里面是真讨论，链接只是引用，所以过滤条件是「长度 < 120 且全是 URL」
- `merge_forward` 消息要剥 `<forwarded_messages>` 标签、`[Image: img_xxx]` 占位符、`<file key=.../>` 附件标记，否则正文里全是噪音
- 消息截断到 240 字 + `…`：worklog 是索引不是存档，细节回群里查

**参数坑**：`+chat-messages-list` 的时间参数是 `--start` / `--end`（ISO 8601），不是 `--start-time` / `--end-time`。写错不报错，静默返回空列表。

### 汇总时怎么融合

四条数据源在 `_emit` 里合流，最终一条 worklog = session 正文 + 补充来源段：

```
build_desc(session transcript)          ← 主体：commit / 改动文件 / 任务
  + merge_supplements(部门工作记录)      ← 📋 按 task_kr 挂到对应 KR
  + merge_supplements(Supplement 表)     ← 📝 按关联KR 挂到对应 KR
  + merge_supplements(工作群消息)        ← 💬 按 kw_kr 挂到对应 KR
  = 该 KR 本周的 worklog 说明
```

来源标签（📋 / 📝 / 💬）保留在正文里，回看时能区分「终端里做的」和「别处发生的」。补充段只挂到映射命中的那一条 KR，不会串到别的 KR 上。

## 归档

主表只留当年，旧年份搬到 `Worklog_Archive`（同 Base 内，`tbld4zKDq0mrtd2H`）。

```bash
python3 archive_worklogs.py --before 2026-01-01          # 预览
python3 archive_worklogs.py --before 2026-01-01 --write  # 执行
```

**安全设计**：先写归档表、条数核对一致才删主表；不一致立即中止。
建议每年初跑一次。**执行前先备份**（`record-list` 全量导出 JSON）。

## 参考

- John Doerr, *Measure What Matters* (2018)
- Google re:Work OKR Guide
- Perdoo OKR Guide (2026)
- Julia Evans, Brag Documents
- Tiago Forte, PARA Method
