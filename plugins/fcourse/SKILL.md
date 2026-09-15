---
name: fcourse
description: |
  系列课程创作 orchestrator。读 ccprivate/conf/fcourse/ 配置文件 →
  判断课程状态 → 委派子 skill 完成对应环节 → 更新配置。
  所有产物存飞书父文档下的子文档。
  案例库委派 fcaselib。
  用法：用户说"做课程"/"创作课程"/"设计课程"/"继续课程"触发
allowed-tools: Read, Write, Bash, Glob, Grep
---

# fcourse — 系列课程创作

> **输入**：飞书需求文档链接或课程 slug（已有课程时）
> **输出**：飞书父文档 + 子文档体系
> **定位**：商业分析 / 数据分析 / AI 能力 / 知识管理

**前置**: 本 skill 委派 ffeishu（飞书操作）、子 skill（各环节实现）。
  数据传递通过飞书文档完成（上一环节的产出是下一环节的输入）。

## 启动流程

### Phase A: 读取配置

```bash
ls ~/git/ccprivate/conf/fcourse/*.yaml 2>/dev/null
```

列出已有课程。每个课程一个 yaml：

```yaml
slug: "ba-intro"
name: "商业分析入门"
direction: "商业分析"      # 商业分析 / 数据分析 / AI 能力 / 知识管理
status: "in_progress"     # draft / in_progress / completed
feishu:
  parent_doc_url: "..."    # 飞书根文档（所有子文档挂此）
  requirement_doc_url: "..."  # 需求文档
  research_doc_url: "..."     # 调研报告
  syllabus_doc_url: "..."     # 课程体系
  overview_doc_url: "..."     # 课程总览
  lesson_docs:
    - chapter: 1
      title: "导入"
      url: "..."
  exercise_doc_url: "..."     # 练习测验
  summary_doc_url: "..."      # 完结总结
caselib_slugs:
  - "retail-analytics"      # 引用案例库
current_step: 0              # 0-5，标识进度
```

**已有课程** → 展示列表 + 进度 → 选一个继续。
**新课程** → 问 slug/方向/需求 → 创建配置 → 进入 Step 0。

### Phase B: 委派子 skill

根据 current_step 和 status，委派对应子 skill。

---

## Step 0: 读取需求文档

输入：你给飞书文档链接
处理：调 ffeishu fetch → 提取主题/受众/方向
产出：确认摘要 → 更新配置（requirement_doc_url）→ 进入 Step 1

---

## Step 1: 课程调研

委派：**fcourse-research**
输入：需求摘要 + 方向（来自配置）
处理：fcourse-research 调 fsearch + fresearchframe → 调 ffeishu
产出：飞书子文档《<课程名>-调研报告》
确认：展示链接 → 你改飞书 → 确认 → 更新配置 → 进入 Step 2

---

## Step 2: 课程体系 + 总览

委派：**fcourse-syllabus**
输入：调研报告（fetch 飞书）
处理：设计体系 → 调 ffeishu 创建
产出：飞书子文档《<课程名>-课程体系》《<课程名>-课程总览》
确认：逐模块展示 → 每块确认 → 更新配置 → 进入 Step 3

---

## Step 3: 逐课教案（循环）

委派：**fcourse-lesson**（每课一次）
输入：课程体系 + 章号
处理：调 fsearch 补充素材 → 写教案 → 调 ffeishu
产出：每课一个飞书子文档《N-标题》
确认：展示链接 → 你改 → 确认 → 下一课
循环结束 → 进入 Step 4

---

## Step 4: 练习/测验

委派：**fcourse-exercise**
输入：全部教案（fetch 飞书）
处理：逐模块出题 → 调 ffeishu
产出：飞书子文档《<课程名>-练习与测验》
确认：每模块展示 → 改 → 下一模块

---

## Step 5: 课程完结总结

委派：**fcourse-summary**
输入：课程体系 + 全部教案
产出：飞书子文档《<课程名>-完结总结》
确认：展示 → 改 → 定稿 → status = "completed"

---

## 配置更新规则

每步完成后更新 yaml：
1. 设置 current_step 为下一步序号
2. 记录新文档的 URL
3. 如引用案例库，写入 caselib_slugs

```bash
# 将当前配置写入 yaml
python3 -c "
import yaml
# ...
"
```

---

## 依赖

- `fcourse-research` — 调研（子 skill）
- `fcourse-syllabus` — 体系设计（子 skill）
- `fcourse-lesson` — 教案（子 skill）
- `fcourse-exercise` — 练习（子 skill）
- `fcourse-summary` — 完结（子 skill）
- `fcaselib` — 案例库管理（按需调用）
- `ishu` — 飞书操作
- `fsearch` / `fresearchframe` — 搜索
- `fdiagram` — 图（按需）