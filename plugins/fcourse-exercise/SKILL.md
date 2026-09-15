---
name: fcourse-exercise
user-invocable: false
description: |
  练习/测验设计子 skill。被 fcourse orchestrator 委派。
  基于全部教案产出练习集飞书文档。
allowed-tools: Read, Write, Bash, Glob, Grep
---

# fcourse-exercise — 练习与测验

被 fcourse orchestrator 委派。

## 输入

全部教案（fetch 飞书）

## 输出

飞书子文档《<课程名>-练习与测验》

---

## 设计内容

每章测验（10 题）：
- 5 道知识点题（选择/判断/填空）
- 3 道理解题（场景分析）
- 2 道实操题

课程级项目：场景 + 任务 + 评分标准 + 参考答案

---

## 流程

1. 逐模块 fetch 教案
2. 每模块出题 → 展示 → 你审 → 改 → 下一模块
3. 全部确认后调 ffeishu 创建文档

---

## 依赖

- ffeishu — 飞书操作
