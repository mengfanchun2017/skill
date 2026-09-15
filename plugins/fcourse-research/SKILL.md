---
name: fcourse-research
description: |
  课程调研子 skill。被 fcourse orchestrator 委派。
  按方向框架做三源搜索，产出飞书调研报告。
allowed-tools: Read, Write, Bash, Glob, Grep
---

# fcourse-research — 课程调研

被 fcourse orchestrator 委派。

## 输入

- 需求摘要（主题/受众/方向）
- 课程方向（来自配置）

## 输出

飞书子文档《<课程名>-调研报告》

---

## 调研框架

**商业分析**：行业现状 + 方法论（SWOT/PEST/波特五力/商业画布） + 工具数据源 + 岗位能力 + 竞品课程
**数据分析**：技术栈（SQL/Python/BI/可视化） + 方法论（CRISP-DM/A/B Test） + 行业案例 + 竞品
**AI 能力**：技术栈（LLM/RAG/Agent/传统ML） + 应用场景成熟度 + 工具链 + 竞品
**知识管理**：方法论（SECI/Zettelkasten/PARA/CODE） + 工具生态 + 实施案例 + 竞品

---

## 流程

1. 调 fsearch 三源并行（中文/英文/深度）
2. 按方向框架整理
3. 调 ffeishu 创建飞书子文档（父文档 = 配置的 root_doc_url）
4. 返回文档 URL

---

## 依赖

- fsearch — 搜索
- fresearchframe — 方法论
- ffeishu — 飞书操作
