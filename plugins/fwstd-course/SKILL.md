---
name: fwstd-course
description: |
  课程文档内容规范 — 系列课程各产物（调研报告/课程体系/教案/练习/总结）的
  内容架构、骨架与写作要求。飞书格式见 ffeishu，编排与执行见 fworch-course。
  用法：被 fworch-course 及其子 skill 引用，一般不直接触发
user-invocable: false
allowed-tools: Read, Glob, Grep
---

# fwstd-course — 课程内容规范（L2）

横向规范层，定义「一份好的课程文档长什么样」。**不绑定执行**（编排/委派走 `fworch-course`），**不重复平台格式**（飞书格式走 `ffeishu`）。

## 职责边界

| 本 skill 负责 | 不负责（委派） |
|--------------|--------------|
| 课程各产物的内容架构/骨架 | 飞书格式（表格 XML 822 等）→ `ffeishu` |
| 各产物模板（templates） | 编排/进度/委派 → `fworch-course` |
| 案例注入的内容约定 | 案例检索 → `fworch-case` |
| 课程级写作要求 | 搜索素材 → `fsearch`/`fresearchframe` |

## 产物与模板

| 产物 | 模板 | 内容骨架要点 |
|------|------|-------------|
| 调研报告 | `references/research-template.md` | 按方向框架（商业分析/数据分析/AI 能力/知识管理）组织领域现状+方法论+工具+岗位+竞品 |
| 课程体系 | `references/syllabus-template.md` | 定位/学习目标(Bloom)/模块划分/各章结构/评估/时间线 |
| 课程总览 | `references/syllabus-template.md` | 完整目录/模块依赖图/授课方式/配套资产 |
| 教案（逐课） | `references/lesson-template.md` | 学习目标/导入/核心知识点/案例引用(可选)/实操/小结/练习提示 |
| 练习与测验 | `references/exercise-template.md` | 每章 10 题(5知识+3理解+2实操) + 课程级项目(场景+任务+评分+参考答案) |
| 完结总结 | `references/summary-template.md` | 知识图谱/易错点汇编/能力评估/后续路径/认证指引 |
| 单元 memo（现有材料） | `references/memo-template.md` | 原始记录：官方多源合并 / 原文全文，忠实呈现不改写 |
| 单元 update（现有材料） | 复用 `lesson-template.md` | 课程化精读（学习目标/导入/核心框架/小结/练习）+ 现代演进 |
| 能力框架（capability→skill） | `references/framework-template.md` | 按 SFIA 三层：capability 能力域 → skill 可执行动作 → knowledge 入库外 |

## 课程级写作要求

- **飞书格式**：全部走 `ffeishu`（write-checklist §2 为真相源）
- **父文档**：所有子文档挂课程父文档（`root_doc_url`）下，禁止套用默认 wiki 节点
- **案例引用**（可选）：注入格式 `> [案例引用: <title>](<url>#<id>)`，调用协议见 fworch-course 的 `references/case-protocol.md`；无命中不阻断主流程
- **标题**：文档标题 = 产物名（如《商业分析入门-课程体系》），正文主节 H1，不重复文档名作标题
- **逐模块确认**：体系/教案/练习按模块或按章展示 → 用户改 → 确认 → 下一单元

## 现有材料课程化（memo/update 双层）

对**已下载的课程材料**（PDF 讲义/逐字稿、Excel、案例论文），产物分两层，命名 `<slug>-<weekN|case>-memo` / `-update`：

| 层 | 命名 | 内容定位 | 骨架 |
|----|------|---------|------|
| memo | `<slug>-<weekN>-memo` | **原始记录**（忠实，不改写） | 官方多源合并（要点讲稿+讲义卡片+逐字稿）或案例原文 |
| update | `<slug>-<weekN>-update` | **更新版（中文，课程化）** | 复用 `lesson-template.md` + 现代演进段落 |

- 父页命名 `memo <slug>`；每周一 doc、每案例一 doc
- 有材料才建，无内容跳过
- 模板见 `references/memo-template.md`；执行细则见 fworch-course `references/step-ingest.md`

## 能力框架（capability → skill → knowledge）

用 **SFIA 三层语义**定义课程/领域的能力地图：

| 层 | 定义（SFIA/ISO） | 命名规范 | 入表？ |
|----|----------------|---------|--------|
| knowledge | **懂**：facts/concepts，acquired 但未必应用 | 名词短语 | **否**，写进 skill 文档 |
| skill | **能做**：apply knowledge 完成 task，有产出 | 名词短语（SFIA 惯例，如 "Availability management"） | 是 |
| capability | **可靠交付**：knowledge+skill 在专业情境下负责地应用 | 能力域名词短语 | 是（作父级） |

- **capability 命名 = 能力域**（业务问题框定 / 描述性分析 / 预测性分析 / 规范性分析 …）
- **skill 命名 = 可执行动作/专业能力**（回归分析 / 线性优化建模 …）；一 cap 下 skill 数不限，逻辑清晰即可
- **knowledge 不入表**：作 skill 文档内容 + 可引外部 Bodies of Knowledge（SFIA 官方做法）
- 结构细则 + 飞书表设计见 `references/framework-template.md`

## 关联

- `ffeishu` — 飞书格式（write-checklist §2 为真相源）
- `fworch-course` — 课程编排（orchestrator）
- `fworch-case` — 案例检索与注入协议
- `fsearch` / `fresearchframe` — 素材搜索
- `fdiagram` — 模块依赖图 / 知识图谱
