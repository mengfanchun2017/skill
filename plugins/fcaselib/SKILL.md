---
name: fcaselib
user-invocable: false
description: |
  案例库管理。读 ccprivate/conf/fcaselib/<slug>.yaml 案例配置，
  按方向/标签检索案例，读取案例飞书文档注入课程上下文。
  被 fcourse orchestrator 按需调用。
allowed-tools: Read, Write, Bash, Glob, Grep
---

# fcaselib — 案例库管理

职责：管理案例配置 → 按需读案例飞书文档 → 注入课程上下文
配置：`ccprivate/conf/fcaselib/<slug>.yaml`
调用方：fcourse orchestrator（Step 2 体系 + Step 3 教案时注入）

---

## 案例配置结构

```yaml
slug: "retail-analytics"
name: "零售行业分析案例集"
direction: "商业分析"
description: "一个零售门店的销售数据分析全流程案例"
tags:
  - "retail"
  - "beginner"
  - "python"
feishu:
  root_doc_url: "..."       # 案例飞书根文档
  docs:
    - title: "案例概述"
      url: "..."
    - title: "数据集说明"
      url: "..."
    - title: "分析模板"
      url: "..."
```

---

## 操作

### 列出案例

```bash
ls ~/git/ccprivate/conf/fcaselib/*.yaml 2>/dev/null
```

### 按方向检索

```bash
grep -l "direction: \"商业分析\"" ~/git/ccprivate/conf/fcaselib/*.yaml 2>/dev/null
```

### 按标签检索

```bash
grep -l "retail" ~/git/ccprivate/conf/fcaselib/*.yaml 2>/dev/null
```

### 读取案例内容

调 ffeishu fetch 案例根文档或指定子文档。

### 注入到课程

fcourse 在 Step 2/3 时调用：
1. 读课程配置的 caselib_slugs
2. 对每个 slug fetch 案例飞书文档
3. 案例内容作为上下文注入教案/练习生成

---

## 依赖

- ffeishu — 飞书文档

---

## 参考

案例模板 → references/
