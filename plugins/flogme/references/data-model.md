# flogme 数据模型与质量规范

Base `okr_v2` 含 4 个表，token 在 ccprivate config.yaml 中。

## OKR_O 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| 标题 | 文本 | Objective，方向性描述 |
| 分类 | 单选 | work / learn / project |
| 周期 | 单选 | 2026Q1, 2026Q2, 2026Q3, 2026Q4, 2026 Full Year |
| 状态 | 单选 | Active / Completed / Abandoned |
| 说明 | 多行文本 | 职责范围、考核锚点、与其他 O 的边界 |

**O 表没有「优先级」字段**（2026-10-30 删除）。四个 O 是分工关系不是排名关系；投入程度由下属 KR 的 `KR.health` 按 `KR.type` 加权汇总得出，见「O 投入程度汇总」一节。
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
| KR.status | 单选 | `active` / `done` / `paused` / `cancelled` —— **只表示生命周期** |
| KR.health | 单选 | `on_track` / `at_risk` / `off_track` / `n_a` —— 只表示进展健康度 |
| KR.domain | 单选 | `work` / `personal` |
| 编号 | 数字 | |
| 说明 | 文本 | KR 的上下文 |
| 更新日期 | 日期 | |

**注意**：KR 表**没有**「周期」字段——周期从关联 O 继承（`sum_generate.py` 的
`_kr_period()` 处理）。也**没有**「进度 / 信心 / 最终评分」字段（v1 表有，v2 迁移时丢失）。

**状态语义**：`KR.status` 只表示生命周期，**不再表示进展好坏**。完成 KR 时主动跑
`log_write.py kr-status --kr recXXX --status done`，脚本会读回校验 `verified`。
KR 的进展好坏填 `KR.health`，每月 audit 检查时更新一次，判据见主文档「用 KR 状态
衡量 O 的投入程度」一节。

### O 投入程度汇总

O 层不手工填进度，从 KR 算：

1. 只算 `KR.status` 为 `active` / `paused` 的 KR；`done` 记 1.0；`cancelled` 完全排除（放弃的目标不该拉低健康分）
2. 折算：`on_track`=1.0 / `at_risk`=0.5 / `off_track`=0.0
3. 按 `KR.type` 加权：committed=3 / aspirational=2 / learning=1
4. O 健康分 = Σ(折算值 × 权重) ÷ Σ(权重)
5. 同时看 off_track 与 at_risk 的条数——同样的分数，一条满分一条零分与两条都 at_risk 含义完全不同

**值域陷阱（2026-10-30 已修）**：`KR.status` 选项曾是 `active/smooth/challenge/cancelled`，
而字段 description 却写「Active/Done/Cancelled」——**说明与选项不对应**。根因是
`smooth/challenge` 把「进展健康」混进了「生命周期」，两个轴挤在一个字段里，选了一个
就丢另一个。现已拆成两个字段：`KR.status`（active/done/paused/cancelled）与
`KR.health`（on_track/at_risk/off_track/n_a）。

**三根正交的轴**，改动任一字段前先确认自己在动哪根：

| 轴 | 字段 | 回答的问题 |
|---|---|---|
| 承诺强度 | KR.type | 失败时多难交代 |
| 生命周期 | KR.status | 还活着吗 |
| 进展健康 | KR.health | 按现在节奏能不能按时达成 |

## Worklog 表字段

| 字段 | 类型 | 写入方式 |
|------|------|---------|
| 标题 | 文本 | ≤60 字，无 `##`/`【】` 前缀 |
| 成果类型 | 单选 | `log_write.py --type`，默认工具开发 |
| 所属KR | 链接 → OKR_KR | kr_route 或 weekly_rollup 匹配，**每条必须关联** |
| 日期 | 日期 | 当天（周汇总取周一） |
| 说明 | 多行文本 | 结构化摘要 |
| KR标题 | 查找引用 | 自动从 KR 表反查（只读） |

⚠️ **字段真名以 `+field-list` 为准，本文档历史上漂移过**：KR 链接列在 Base 里叫
`所属KR`（旧名 `关联KR`），反查列叫 `KR标题`（旧名 `关联KR标题`）。脚本按旧名读写
→ 写报 `not_found`、读 `.get()` 恒 None，且**读错名完全不报错**（静默失效）。
代码里一律走 `log_write.field_name()` / `weekly_rollup._kr_field()` 运行时解析，不要写死。

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
