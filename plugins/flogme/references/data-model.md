# flogme 数据模型与质量规范

Base `okr_v2` 含 4 个表，token 在 ccprivate config.yaml 中。

## OKR_O 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| 标题 | 文本 | Objective，方向性描述 |
| 分类 | 单选 | work / learn / project |
| 周期 | 单选 | 2026Q1, 2026Q2, 2026Q3, 2026Q4, 2026 Full Year |
| 状态 | 单选 | Active / Completed / Abandoned |
| 优先级 | 数字 | 1-5，1 最高 |
| 说明 | 多行文本 | 为什么这个 O 重要 |
| 更新日期 | 日期 | 最后修改日期 |

## OKR_KR 表字段

> ⚠️ **字段真名以本表为准**。脚本曾按旧名（`KR.状态`、`KR.PARA`、`类型`）索引，
> Base 改过名后 API **静默丢弃未知字段、仍返回成功**，造成 kr-status 假成功、
> sum_generate KeyError 崩溃（2026-10-29 实测）。新增字段前先 `+field-list` 核对。

| 字段真名 | 类型 | 说明 |
|------|------|------|
| 标题 | 文本 | KR，可量化结果 |
| 关联O | 关联列 → OKR_O | 必须关联一个 O |
| KR.type | 单选 | `committed` / `aspirational` / `learning` |
| KR.para | 单选 | `projects` / `areas` / `research` / `archive` |
| KR.status | 单选 | `active` / `smooth` / `challenge` / `cancelled` |
| KR.domain | 单选 | `work` / `personal` |
| 编号 | 数字 | |
| 说明 | 文本 | KR 的上下文 |
| 更新日期 | 日期 | |

**注意**：KR 表**没有**「周期」字段——周期从关联 O 继承（`sum_generate.py` 的
`_kr_period()` 处理）。也**没有**「进度 / 信心 / 最终评分」字段（v1 表有，v2 迁移时丢失）。

**状态语义**：`KR.status` 是 KR 进展的唯一状态字段。完成 KR 时主动跑
`log_write.py kr-status --kr recXXX --status <选项值>`，脚本会读回校验 `verified`。
不靠 worklog/reflect 自动触发。

**值域陷阱**：`KR.status` 选项是 `active/smooth/challenge/cancelled`，
不是文档曾写的 `Active/Done/Cancelled`。写错值会报错或被拒。

## Worklog 表字段

| 字段 | 类型 | 写入方式 |
|------|------|---------|
| 标题 | 文本 | ≤60 字，无 `##`/`【】` 前缀 |
| 成果类型 | 单选 | `log_write.py --type`，默认工具开发 |
| 关联KR | 链接 → OKR_KR | kr_route 或 weekly_rollup 匹配，**每条必须关联** |
| 日期 | 日期 | 当天（周汇总取周一） |
| 说明 | 多行文本 | 结构化摘要 |
| 关联KR标题 | 查找引用 | 自动从 KR 表反查（只读） |

分类（work/learn/project）通过关联 KR→O 自动继承，Worklog 不重复维护。

**「必须关联 KR」现在是脚本硬拦**（2026-10-29 前只是文档约定，导致 33 条裸记录）：
缺 `--kr` 直接退出；确实无法归类用 `--allow-no-kr` 显式豁免。

**成果类型合法值**：`项目交付` / `技术方案` / `学习笔记` / `问题排查` / `会议/沟通` / `文档输出` / `工具开发`

## Reflect 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| 标题 | 文本 | `2026Q2 Week 3 Reflect` |
| 周期类型 | 单选 | 周 / 月 / 季度 / 年 |
| 关联O | 关联列 → OKR_O | 可选 |
| 做得好 | 文本 | 这周/月/季度做得好的 |
| 待改进 | 文本 | 需要改进的地方 |
| 学到 | 文本 | 学到了什么 |
| 下阶段 | 文本 | 下阶段聚焦什么 |
| 日期 | 日期 | |

## 质量规则

| 规则 | 动作 |
|------|------|
| 0 条 user 消息 | **跳过**，不写入（空 session 噪音） |
| LLM 标题生成失败 | fallback → commit message → 首条 user prompt |
| 标题为 `session 工作` 格式 | 标记为低质量，待人工修正 |
| 同 session 多次触发 | **合并**到第一条（累加 token/轮数，标题取较长者） |

**KR 自动路由**：根据 session cwd 匹配 `config.yaml` → `kr_route` 配置，自动关联到对应 KR。

## 合并策略

| 条件 | 动作 | 是否自动 |
|------|------|---------|
| 完全同标题 | 保留说明最长记录，合并说明，删除其余 | ✅ 自动 |
| 标题相似 > 85% + 同日期 | 候选合并 | ❌ 人工 |
| 标题相似 > 85% + 跨日期 + 递进更新 | 合并说明到最早记录 | ✅ 自动 |
| 0 user_msgs 且 0 commits 0 edits | 删除 | ✅ 自动 |

### 调度

| 频率 | 触发方式 | 命令 |
|------|---------|------|
| 每周 | 自动（距上次 merge > 7 天时 hook 自动执行） | `python3 worklog_consolidate.py --mode merge --write` |
| 阶段（~30天） | 提醒 | `worklog_consolidate.py --mode monthly` 预览 |
| 手动 | 用户说 "做周整合" / "阶段总结" | 立即执行 |

## 已删字段

| 字段 | 表 | 删除时间 | 原因 |
|------|----|---------|------|
| 量化结果 | Worklog | 2026-07 | 100% 空值，从未使用 |
| model | Worklog | 2026-07 | 100% 空值，从未使用 |
| 来源 | Worklog | 2026-07 | 100% 空值，从未使用 |
| 分类 | Worklog | 2026-06 | 通过 KR→O 自动继承 |
| 输入Token | Worklog | 2026-08 | 用量拆到 maintain.sh token → 飞书多维表格 |
| 输出Token | Worklog | 2026-08 | 同上 |
| 助手消息数 | Worklog | 2026-08 | 同上 |
| 用户消息数 | Worklog | 2026-08 | 同上 |
| 标签/状态/耗时 | Worklog | — | 见 extension 方案 |
| KR_Progress 表 | — | 2025-07 | 表废弃，详见 ADR-0003 |
