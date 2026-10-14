# Step 4 练习与测验

> fworch-course Step 4 执行细则。被编排器委派执行。

## 输入

全部教案（fetch 飞书，按 `lesson_docs` 列表遍历）

## 输出

飞书子文档《<课程名>-练习与测验》。返回格式按 `comm-contract.md`。

## 设计内容

按 `~/.claude/skills/fwstd-course/references/exercise-template.md`：

**每章测验**（10 题）：
- 5 道知识点题（选择/判断/填空）
- 3 道理解题（场景分析）
- 2 道实操题

**课程级项目**：场景 + 任务 + 评分标准 + 参考答案

## 流程

1. 逐章 fetch 教案
2. 每章出题 → 展示 → 你审 → 改 → 下一章
3. 全部确认后调 ffeishu 创建文档（使用 `~/.claude/skills/fwstd-course/references/exercise-template.md`）
4. 返回 `{status: "ok", doc_url: <练习集 URL>}`

## 依赖

- ffeishu — 飞书操作
