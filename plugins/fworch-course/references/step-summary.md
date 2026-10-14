# Step 5 课程完结总结

> fworch-course Step 5 执行细则。被编排器委派执行。

## 输入

- 课程体系（fetch 飞书）
- 全部教案（fetch 飞书，按 `lesson_docs` 列表遍历）

## 输出

飞书子文档《<课程名>-完结总结》。返回格式按 `comm-contract.md`。

## 内容

按 `~/.claude/skills/fwstd-course/references/summary-template.md`：

- 课程知识图谱（知识点关系图，调 fdiagram）
- 常见误区和易错点汇编
- 关键能力评估
- 后续学习路径推荐
- 认证/考试指引（如有）

## 流程

1. fetch 课程体系 + 全部教案
2. 生成总结内容（套 `~/.claude/skills/fwstd-course/references/summary-template.md`）
3. 调 ffeishu 创建文档
4. 展示链接 → 你改 → 定稿
5. 返回 `{status: "ok", doc_url: <完结总结 URL>, notes: ["通知 orchestrator status=completed"]}`

## 依赖

- ffeishu — 飞书操作
- fdiagram — 图（按需）
