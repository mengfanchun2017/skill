# Step 2 课程体系设计

> fworch-course Step 2 执行细则。被编排器按 step 委派执行。

## 输入

调研报告（fetch 飞书）

## 输出

- 《<课程名>-课程体系》飞书子文档
- 《<课程名>-课程总览》飞书子文档

返回格式按 `comm-contract.md`，aux_docs 一项：

```yaml
aux_docs:
  - url: "<overview_url>"
    purpose: "overview"
```

## 体系设计

1. **课程定位**：一句话 + 学员画像 + 前置知识
2. **学习目标**：课程级（Bloom） + 模块级
3. **模块划分**：模块名 + 学习目标 + 知识点 + 时长；模块依赖图（调 fdiagram 飞书画板，`<whiteboard type="mermaid">` 嵌入课程父页）
4. **各章结构**：标题 + 目标 + 核心概念 + 实践 + 时长
5. **评估设计**：测验形式 + 课程级项目
6. **时间线**：总时长 + 节奏

## 课程总览

- 完整目录（各章目标/时长）
- 模块依赖 Mermaid 图
- 授课方式说明
- 配套资产清单

## 流程

1. fetch 调研报告
2. 逐模块展示 → 你确认 → 下一模块
3. 全部确认后调 ffeishu 创建两个文档（使用 `~/.claude/skills/fwstd-course/references/syllabus-template.md`）
4. 返回 `{status: "ok", doc_url: <syllabus>, aux_docs: [{url, purpose: "overview"}]}`

## 依赖

- ffeishu — 飞书操作
- fdiagram — 图（按需）
