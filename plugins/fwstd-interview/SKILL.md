---
name: fwstd-interview
description: |
  面试准备内容规范 — 岗位画像/组织行业/知识地图/能力模型/问题库/问答素材/未来工作思路/模拟清单/成稿包
  的内容架构与写作要求。面向"零经验应聘者"的全链条准备。飞书格式见 ffeishu，编排与执行见 fworch-interview。
  用法：被 fworch-interview 引用，或用户说"准备面试"/"岗位面试"触发
user-invocable: false
allowed-tools: Read, Glob, Grep
---

# fwstd-interview — 面试准备内容规范（L2）

横向规范层，定义「一份好的面试准备材料长什么样」。**不绑定执行**（编排走 `fworch-interview`），**不重复平台格式**（飞书格式走 `ffeishu`）。

## 职责边界

| 本 skill 负责 | 不负责（委派） |
|--------------|--------------|
| 各准备产物的内容架构/骨架 | 飞书格式（lark-table 822）→ `ffeishu` |
| 模板（`references/templates.md`） | 编排/进度 → `fworch-interview` |
| 岗位画像/知识地图/能力模型/问答/工作思路 的写法 | 搜索素材 → `fsearch` / `fresearchframe` |

## 产物与模板

模板骨架统一见 `references/templates.md`。产物：

| 产物 | 覆盖材料 | 骨架要点 |
|------|---------|---------|
| 岗位画像 | 岗位认知 | 职责/要求/级别定位/成功标准/汇报关系 |
| 组织与行业 | 岗位认知 | 单位概况/组织架构/行业格局/趋势 |
| 专业知识地图 | 岗位认知 | capability→skill→knowledge 三层 + 掌握程度 |
| 能力素质模型 | 岗位认知 | 硬能力+软素质 + 行为锚点 + 差距分析 |
| 问题库 | 工作思路 | 分类问题（动机/专业/案例/行为/思路/反问） |
| 问答素材 | 工作思路 | 重点题答案（STAR + 结构框架 + 追问） |
| 未来工作思路 | 工作思路（**核心**） | 问题诊断/理念/分阶段规划/重点举措/风险 |
| 模拟演练清单 | 综合 | 逐轮作战清单 + 模拟问答 + 临场要点 |
| 面试成稿包 | 综合 | 导航 + 一页速览 + 交付正文 + 检查清单 |

## 岗位能力拆解（SFIA 三层）

知识地图与能力模型统一用 SFIA 三层（同 `fwstd-course/references/framework-template.md`）：

- **capability** = 能力域（岗位职能，如"机队规划""引进评估"）
- **skill** = 可执行动作（如"评估租赁 vs 购买"）
- **knowledge** = 懂（概念/规章/方法/工具），不单列，附在 skill 下

JD 是唯一权威输入：从职责动词抽 capability → 展开 skill → 补 knowledge 要点。

## 面试线写作要求

- **飞书格式**：走 `ffeishu`（write-checklist §2 为真相源）
- **父文档**：所有子文档挂面试父文档（`root_doc_url`）下
- **基于真实背景**：答案不得编造用户经历；缺信息先问
- **零经验友好**：始终突出"可迁移能力"叙事
- **量化**：工作思路的能量化就量化
- **逐单元确认**：每步产出 → 展示 → 用户改 → 确认 → 下一步

## 关联

- `ffeishu` — 飞书格式
- `fworch-interview` — 面试准备编排（orchestrator）
- `fsearch` / `fresearchframe` — 岗位/行业/知识搜索
- `fdiagram` — 能力模型图 / 工作规划图
