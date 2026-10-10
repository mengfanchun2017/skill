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
| 课程各产物的内容架构/骨架 | 飞书格式（lark-table 822 等）→ `ffeishu` |
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

## 课程级写作要求

- **飞书格式**：全部走 `ffeishu`（write-checklist §2 为真相源）
- **父文档**：所有子文档挂课程父文档（`root_doc_url`）下，禁止套用默认 wiki 节点
- **案例引用**（可选）：注入格式 `> [案例引用: <title>](<url>#<id>)`，调用协议见 fworch-course 的 `references/case-protocol.md`；无命中不阻断主流程
- **标题**：文档标题 = 产物名（如《商业分析入门-课程体系》），正文主节 H1，不重复文档名作标题
- **逐模块确认**：体系/教案/练习按模块或按章展示 → 用户改 → 确认 → 下一单元

## 关联

- `ffeishu` — 飞书格式（write-checklist §2 为真相源）
- `fworch-course` — 课程编排（orchestrator）
- `fworch-case` — 案例检索与注入协议
- `fsearch` / `fresearchframe` — 素材搜索
- `fdiagram` — 模块依赖图 / 知识图谱
