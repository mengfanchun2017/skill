---
name: fcourse-syllabus
user-invocable: false
description: |
  课程体系设计子 skill。被 fcourse orchestrator 委派。
  基于调研报告产出课程体系+课程总览飞书文档。
allowed-tools: Read, Write, Bash, Glob, Grep
---

# fcourse-syllabus — 课程体系设计

被 fcourse orchestrator 委派。

## 输入

调研报告（fetch 飞书）

## 输出

- 《<课程名>-课程体系》飞书子文档
- 《<课程名>-课程总览》飞书子文档

---

## 体系设计

1. 课程定位：一句话 + 学员画像 + 前置知识
2. 学习目标：课程级（Bloom） + 模块级
3. 模块划分：模块名 + 学习目标 + 知识点 + 时长
   模块间依赖图（调 fdiagram）
4. 各章结构：标题 + 目标 + 核心概念 + 实践 + 时长
5. 评估设计：每章测验形式 + 课程级项目
6. 时间线：总时长 + 节奏

## 课程总览

- 完整目录
- 模块依赖 Mermaid 图
- 授课方式说明
- 配套资产清单

---

## 流程

1. fetch 调研报告
2. 逐模块展示 → 你确认 → 下一模块
3. 全部确认后调 ffeishu 创建两个文档
4. 返回文档 URL

---

## 依赖

- ffeishu — 飞书操作
- fdiagram — 图（按需）
