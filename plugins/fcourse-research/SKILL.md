---
name: fcourse-research
user-invocable: false
description: |
  课程调研子 skill。按方向框架做三源搜索，产出飞书调研报告。
  被 fcourse orchestrator 委派。
allowed-tools: Read, Write, Bash, Glob, Grep
---

# fcourse-research — 课程调研

本 skill 被 fcourse orchestrator 委派。

## 输入

- 需求摘要（主题/受众/方向）
- 课程方向（来自配置）

## 输出

飞书子文档《<课程名>-调研报告》

## 调研框架

按 4 方向选择：

**商业分析方向**：行业现状 + 方法论（SWOT/PEST/波特五力） + 工具 + 竞品课程
**数据分析方向**：技术栈（SQL/Python/BI） + 方法论（CRISP-DM） + 案例 + 竞品
**AI 能力方向**：技术栈（LLM/RAG/Agent） + 应用场景 + 工具链 + 竞品
**知识管理方向**：方法论（SECI/PARA/CODE） + 工具生态 + 实施案例 + 竞品

## 流程

1. 调 fsearch 做三源并行搜索（中文/英文/深度）
2. 按方向框架整理
3. 调 ffeishu 创建飞书子文档
4. 返回文档 URL

## 依赖

- fsearch — 搜索
- fresearchframe — 方法论
- ffeishu — 飞书操作
