# f-logme 数据模型

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

| 字段 | 类型 | 说明 |
|------|------|------|
| 标题 | 文本 | KR，可量化结果 |
| 关联O | 关联列 → OKR_O | 必须关联一个 O |
| 周期 | 单选 | 与关联 O 对齐 |
| 类型 | 单选 | Committed (100% 必达) / Aspirational (70% 即成功) / Learning (探索性) |
| KR.PARA | 单选 | projects（交付）/ areas（持续）/ research（探索）/ archive（归档） |
| KR.状态 | 单选 | Active（进行中）/ Done（已完成）/ Cancelled（取消） |
| 关联ADR | 文本 | 引用 ADR 文档 token（多 ADR 用空格分隔） |
| 最终评分 | 数字 | 0.0-1.0，周期结束时填入 |
| 说明 | 多行文本 | KR 的上下文 |

**状态语义**：KR.状态是 KR 进展的唯一状态字段。完成 KR 时主动跑 `log_write.py kr-status --kr recXXX --status Done`，不靠 worklog/reflect 自动触发。

## Worklog 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| 标题 | 文本 | LLM 自动生成，≤60 字 |
| 关联KR | 关联列 → OKR_KR | 必须关联一个 KR |
| 关联KR标题 | 查找引用 | 自动从 KR 表反查 |
| 成果类型 | 单选 | 工具开发 / 技术方案 / 文档输出 / 学习笔记 / 问题排查 / 项目交付 |
| 说明 | 多行文本 | 结构化摘要 + commits + edits + user prompts |
| 日期 | 日期 | 完成日期 |
| 输入Token | 数字 | transcript 统计 |
| 输出Token | 数字 | transcript 统计 |
| 助手消息数 | 数字 | assistant 消息条数 |
| 用户消息数 | 数字 | user 消息条数 |
| 量化结果 | 文本 | 可选。数字、百分比、前后对比 |

> 已删字段（2026-07）：model, 来源（100% 空值，从未使用）
> 分类（work/learn/project）通过关联 KR→O 自动继承，Worklog 不重复维护
> 标签、状态、耗时 — 见 `docs/design/worklog-field-extension.md` 扩展方案

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

## KR_Progress 表（已废弃）

KR_Progress 表已于 2025-07 废弃，不再维护。
