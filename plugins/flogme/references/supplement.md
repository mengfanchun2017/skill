# flogme 数据补充源（2026-11-01）

> 三类外部数据汇入 Worklog：用户手动补充、部门工作记录表、工作群消息。

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