---
name: fcourse-lesson
user-invocable: false
description: |
  逐课教案生成子 skill。基于课程体系生成单课教案飞书文档。
  被 fcourse orchestrator 每课委派一次。
allowed-tools: Read, Write, Bash, Glob, Grep
---

# fcourse-lesson — 逐课教案

本 skill 被 fcourse orchestrator 按章循环调用。

## 输入

- 课程体系（fetch 飞书）
- 章号（参数传入）

## 输出

飞书子文档《N-章标题》

## 教案结构

- 学习目标（细粒度可衡量）
- 导入（故事/案例/问题）
- 核心知识点（逻辑展开）
- 主线案例引用（如有 fcaselib 注入）
- 实操/示例
- 本章小结
- 课后练习提示

## 流程

1. fetch 课程体系获取当前章信息
2. 如有 fcaselib 案例注入，读取案例内容
3. 调 fsearch 补充素材
4. 写教案
5. 调 ffeishu 创建飞书子文档（父文档 = 课程体系 root_doc_url）
6. 返回文档 URL

## 依赖

- ffeishu — 飞书操作
- fsearch — 搜索补充
- fcaselib — 案例注入（按需）
