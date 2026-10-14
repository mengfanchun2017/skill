# Step 3 逐课教案（循环）

> fworch-course Step 3 执行细则。被编排器每课委派一次。

## 输入

- 课程体系（fetch 飞书）
- 章号（orchestrator 传入）

## 输出

飞书子文档《N-章标题》。返回格式按 `comm-contract.md`。

## 教案结构

按 `~/.claude/skills/fwstd-course/references/lesson-template.md`：

- 学习目标（细粒度可衡量）
- 导入（故事/案例/问题）
- 核心知识点（逻辑展开）
- 主线案例引用（**可选**：仅当用户要求或课程配置 `caselib_direction` 非空时，按 `case-protocol.md` 调 fworch-case 注入）
- 实操/示例
- 本章小结
- 课后练习提示

## 流程

1. fetch 课程体系获取当前章信息
2. **可选**：如配置有 `caselib_direction` 且用户/上下文需要案例，调 fworch-case（按 `case-protocol.md`）注入案例内容；否则跳过
3. 调 fsearch 补充素材
4. 写教案（套 `~/.claude/skills/fwstd-course/references/lesson-template.md`）
5. 调 ffeishu 创建飞书子文档（父文档 = `root_doc_url`）
6. 返回 `{status: "ok", doc_url: <章 URL>, notes: ["注入案例 N 个" 或 "未调案例"]}`

## 中断恢复

orchestrator 通过 `lesson_docs` 数组长度判断已完成章数。
当前章号 = `len(lesson_docs) + 1`。

## 依赖

- ffeishu — 飞书操作
- fsearch — 搜索补充
- fworch-case — 案例（**可选**，按用户/上下文需要触发）
