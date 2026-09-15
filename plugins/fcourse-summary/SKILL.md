---
name: fcourse-summary
user-invocable: false
description: |
  课程完结总结子 skill。被 fcourse orchestrator 委派。
  生成知识图谱/易错点/推荐路径飞书文档。
allowed-tools: Read, Write, Bash, Glob, Grep
---

# fcourse-summary — 课程完结总结

被 fcourse orchestrator 委派。

## 输入

- 课程体系（fetch 飞书）
- 全部教案（fetch 飞书）

## 输出

飞书子文档《<课程名>-完结总结》

---

## 内容

- 课程知识图谱（知识点关系图，调 fdiagram）
- 常见误区和易错点汇编
- 关键能力评估
- 后续学习路径推荐
- 认证/考试指引（如有）

---

## 流程

1. fetch 课程体系 + 教案
2. 生成总结内容
3. 调 ffeishu 创建文档
4. 展示链接 → 你改 → 定稿
5. 通知 orchestrator status=completed

---

## 依赖

- ffeishu — 飞书操作
- fdiagram — 知识图谱（按需）
