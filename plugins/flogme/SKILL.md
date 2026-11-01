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

## 定时任务（已就绪）

| 时间 | 命令 | 内容 |
|------|------|------|
| 每周一 00:01 | `weekly_rollup.py --last-week --write` | 汇总上一个完整周 |
| 每周五 00:01 | `weekly_rollup.py --this-week --write` | 汇总本周一到此刻 |

已注册为 Claude durable cron（`434d675d` 周一 / `5243e810` 周五），**7 天后自动过期**，
到时说「重建 worklog 周汇总定时」即可重注册。

⚠️ 周一那条原写的是 `--since-last-week`（脚本没这个参数，每次跑都
`unrecognized arguments` 直接失败），2026-10-30 已改成 `--last-week` 并重注册。
改 cron 命令后**必须实跑一次**验证参数有效 —— 定时任务失败不报错，只在没人看的输出里。

## 手动跑

```bash
cd ~/git/skill/plugins/flogme
export LARKSUITE_CLI_CONFIG_DIR="$HOME/.lark-cli-ailab"

# 汇总上一个完整周（周一该跑的那个）
python3 weekly_rollup.py --last-week

# 汇总本周至今（周五该跑的那个）
python3 weekly_rollup.py --this-week

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

**weekly_rollup 整合**：跑周汇总时，同时读 Supplement 表中本周的记录，按 KR 分组追加到对应 worklog 的说明末尾（标注 `📝 补充来源`）。

### 扩展二：部门工作记录表读取

公司部门的工作记录多维表格（工作任务列表 Base，`Ei2ybk3FRagHbksfqXzcujsYnWf`）可作为独立数据源：

- Base 名：工作任务列表（wiki 节点 `ZDyhwRkHmiWFOHkuJBfc8I8Hn8b`）
- 工作记录表 `tblCdxkqxtpw0M6S`：241 条记录，含填写日期、周期、工作内容、ai简短总结、ai关联任务、记录人
- 工作总结表 `tblNMkFG8r8tAZj8`：40 条记录，含类别（周总结/详细周总结/AI培训总结）、本周总结、下周计划

**weekly_rollup 整合**：扫描窗口内记录人为「孟繁春」的记录，提取工作内容摘要，按 ai关联任务 关键词映射到对应 KR，追加到 worklog 说明（标注 `📋 部门周报`）。

**局限性**：部门工作记录表按「本周/下周」分类而非具体日期，无法精确到天。整合时取「本周」记录即可。

### 扩展三：ailab 工作群消息（当前不可行）

当前 ailab 账号的 scope 不含 IM 消息读取权限（`im +chat-list` 返回 0 个会话），**无法直接读取工作群消息**。

替代方案：
1. **用户通过「扩展一」手动转发**：将工作群中的重要消息描述后写入 Supplement 表（来源=工作群消息）
2. **后续扩展 ailab bot scope**：如需要自动读取，需在飞书开放平台给 ailab 应用添加 `im:message` 相关权限并重新授权
3. **转发给 ailab**：用户在工作群 @ailab bot 转发消息，bot 可收到事件（需额外开发消息接收处理）

### 汇总时的优先级融合

三条数据源在 weekly_rollup 中以固定优先级融合：

```
worklog 正文（session transcript 为主）
  + 部门工作记录（📋 标记）— 按 KR 映射挂在对应 KR 下
  + 用户补充（📝 标记）— 按关联KR 挂在对应 KR 下
= 完整周报
```

同一 KR 的记录按日期混合排序，来源标签保留原文可追溯。

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
