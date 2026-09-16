---
name: fcourse
user-invocable: true
description: |
  系列课程创作 orchestrator。读 ccprivate/conf/fcourse/<slug>.yaml 配置 ->
  判断当前课程进度 -> 委派子 skill 完成对应步骤 -> 更新配置。
  所有产物存飞书父文档下的子文档。案例库委派 fcaselib。
  用法：用户说"做课程"/"创作课程"/"设计课程"/"继续课程"触发
allowed-tools: Read, Write, Bash, Glob, Grep
---

# fcourse — 系列课程创作 orchestrator

职责：读配置 → 判断进度 → 委派子 skill → 更新配置 → 循环
数据总线：飞书（每步产出 = 飞书子文档，下一步 fetch 读取）
配置：`ccprivate/conf/fcourse/<slug>.yaml`

每步原则：产出 → 展示飞书链接 → 你改飞书 → 确认 → 下一步

---

## Phase A: 课程选择

```bash
ls ~/git/ccprivate/conf/fcourse/*.yaml 2>/dev/null
```

**已有课程** → 展示列表（课程名 + 当前步骤 + 进度）→ 选一个继续
**新课程** → 问 slug/方向/需求文档 URL → 创建配置

课程 slug 命名：全小写英文+数字，无空格无横线。示例：baintro、aipm

---

## Phase B: 读配置

```bash
cat ~/git/ccprivate/conf/fcourse/<slug>.yaml
```

配置结构：

```yaml
slug: "baintro"
name: "商业分析入门"
direction: "商业分析"
status: "in_progress"
feishu:
  root_doc_url: "..."          # 飞书父文档（所有子文档挂此，必填）
  requirement_doc_url: "..."    # 需求文档（你提供）
  research_doc_url: "..."       # 调研报告
  syllabus_doc_url: "..."       # 课程体系
  overview_doc_url: "..."       # 课程总览
  lesson_docs:
    - chapter: 1
      title: "导入"
      url: "..."
  exercise_doc_url: "..."       # 练习测验
  summary_doc_url: "..."        # 完结总结
caselib_slugs:
  - "retail-analytics"          # 引用案例库
current_step: 0                 # 0-5
```

确认 current_step 后进入对应 Step。

---

## Phase C: 委派子 skill

| Step | 委派 | 产出 |
|------|------|------|
| 0 | 本 skill 直接处理 | fetch 需求文档 → 确认摘要 |
| 1 | fcourse-research | 《<课程名>-调研报告》 |
| 2 | fcourse-syllabus | 《<课程名>-课程体系》《<课程名>-课程总览》 |
| 3 | fcourse-lesson（每课一次） | 《N-章标题》 |
| 4 | fcourse-exercise | 《<课程名>-练习与测验》 |
| 5 | fcourse-summary | 《<课程名>-完结总结》 |

---

## Step 0: 读取需求文档

1. 调 ffeishu fetch 需求文档内容
2. 提取：主题/受众/水平/概览/方向
3. 问清不确定信息
4. 更新配置 requirement_doc_url → current_step=1

---

## Step 1: 课程调研

委派 fcourse-research。
调 fsearch + fresearchframe 按方向框架做三源搜索。
产出飞书子文档 → 展示链接 → 你改 → 确认 → 更新配置

---

## Step 2: 课程体系 + 总览

委派 fcourse-syllabus。
fetch 调研报告 → 设计体系（定位/目标/模块/评估/时间线）
产出《课程体系》+《课程总览》飞书子文档
逐模块确认 → 更新配置

---

## Step 3: 逐课教案（循环）

委派 fcourse-lesson（每课一次）。
按课程体系章节顺序一课一课走：
1. 展示当前章信息
2. 调 fsearch 补充素材 → 写教案
3. 调 ffeishu 创建子文档
4. 展示链接 → 你改 → 确认 → 下一课

---

## Step 4: 练习/测验

委派 fcourse-exercise。
fetch 全部教案 → 逐模块出题
每模块展示 → 改 → 下一模块

---

## Step 5: 课程完结总结

委派 fcourse-summary。
fetch 课程体系 + 全部教案 → 知识图谱/易错点/推荐路径
展示 → 改 → 定稿 → status=completed

---

## 配置更新规则

每步完成后：
1. current_step += 1
2. 记录新文档 URL
3. python3 -c "import yaml; ..." 写回

---

## 依赖

- fcourse-research — 调研
- fcourse-syllabus — 体系
- fcourse-lesson — 教案
- fcourse-exercise — 练习
- fcourse-summary — 完结
- fcaselab — 案例库（按需）
- ffeishu — 飞书操作
- fsearch / fresearchframe — 搜索
- fdiagram — 图

---

## 参考

教案模板、体系模板、练习模板 → references/
