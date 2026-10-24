---
name: fworch-course
user-invocable: true
description: |
  系列课程创作 orchestrator。读 ccprivate/conf/fcourse/<slug>.yaml 配置 ->
  判断当前课程进度 -> 读取对应 step 细则执行 -> 更新配置。
  所有产物存飞书父文档下的子文档。fworch-case 案例库**可选**调用（按需、用户触发）。
  两种模式：Mode A 从零创作（调研→体系→教案）；Mode B 现有材料课程化（已有课件/PDF 抽取为 memo+update）。
  用法：用户说"做课程"/"创作课程"/"设计课程"/"继续课程"/"课程材料课程化"/"已有课程抽取"触发
allowed-tools: Read, Write, Bash, Glob, Grep
---

# fworch-course — 系列课程创作 orchestrator

职责：读配置 → 判断进度 → 按 step 执行（细则在 references/step-*.md）→ 更新配置 → 循环
体裁注册表：`ccprivate/conf/writing/registry.yaml`（course 条目）+ 真值 `conf/writing/course.yaml`
数据总线：飞书（每步产出 = 飞书子文档，下一步 fetch 读取）
配置：`ccprivate/conf/fcourse/<slug>.yaml`
通信契约：见 `references/comm-contract.md`

每步原则：产出 → 展示飞书链接 → 你改飞书 → 确认 → 下一步

## 两种模式

| 模式 | 场景 | 步骤 | 细则 |
|------|------|------|------|
| **Mode A** 从零创作 | 只有需求/方向，需原创课程 | Step 1 调研 → 2 体系 → 3 教案 → 4 练习 → 5 总结 | `references/step-*.md` |
| **Mode B** 现有材料课程化 | 已有课件（PDF/录屏/讲义），需整理入课 | ingest 0–4（见下） | `references/step-ingest.md` |

判模式：用户提供「已有课件/PDF/下载材料/录屏」→ Mode B；只说主题方向 → Mode A。

---

## Phase A: 课程选择

```bash
ls ${CCPRIVATE_HOME:-$HOME/git/ccprivate}/conf/fcourse/*.yaml 2>/dev/null
```

**配置真相源**：所有课程配置存**飞书在线**（Base / docx），`conf/fcourse/<slug>.yaml` 只是本地缓存镜像（用于 orchestrator 快速读取 + 离线可见）。在线源改了需重新生成 yaml 或人工同步。

**已有课程** → 展示列表（课程名 + 当前步骤 + 进度）→ 选一个继续
**新课程** → 问 slug/方向/需求文档 URL → 先在飞书建配置条目，再在本地 `conf/fcourse/` 创建 yaml 镜像

课程 slug 命名：全小写英文+数字，无空格无横线。示例：baintro、aipm

---

## Phase B: 读配置

```bash
cat ${CCPRIVATE_HOME:-$HOME/git/ccprivate}/conf/fcourse/<slug>.yaml
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
  exercise_doc_url: ""         # 练习测验
  summary_doc_url: ""          # 完结总结
caselib_direction:
  - "个性化推荐"                 # 引用案例专业领域（可选；值取 fworch-case「专业领域」枚举，省略表示全库检索）
current_step: 0                 # 0-5
```

确认 `current_step` 后进入对应 Step。

---

## Phase C: 飞书 auth 预检

首次调 ffeishu 前**必须**预检（详见 `~/.claude/rules/feishu.md` § 预检）：

```bash
lark-cli drive +search --query test --page-size 1 --as user 2>&1 \
  | sed '/^\[lark-cli\]/d' \
  | grep -q '"ok":true' || echo "AUTH_FAILED"
```

失败 → 终止当前 step，提示用户走 QR 授权流程。不在失败时硬闯会写入失败。

---

## Phase D: 按 step 执行

按 `current_step` 进入对应 step，**读取该步的 reference 细则**执行：

| Step | 执行细则 | 产出 |
|------|----------|------|
| 0 | 本 skill 直接处理 | fetch 需求文档 → 确认摘要 |
| 1 | `references/step-research.md` | 《<课程名>-调研报告》 |
| 2 | `references/step-syllabus.md` | 《<课程名>-课程体系》《<课程名>-课程总览》 |
| 3 | `references/step-lesson.md`（每课一次） | 《N-章标题》 |
| 4 | `references/step-exercise.md` | 《<课程名>-练习与测验》 |
| 5 | `references/step-summary.md` | 《<课程名>-完结总结》 |

每步完成后按 `references/comm-contract.md` 返回 `{status, doc_url, aux_docs, notes}`，编排器推进 `current_step`。

---

## Step 0: 读取需求文档

1. 调 ffeishu fetch 需求文档内容
2. 提取：主题/受众/水平/概览/方向
3. 问清不确定信息
4. 更新配置 `requirement_doc_url` → `current_step=1`

---

## Step 1: 课程调研

详见 `references/step-research.md`。调 fsearch + fresearchframe 按方向框架三源搜索 → 飞书子文档 → 展示 → 你改 → 确认 → 更新配置。

---

## Step 2: 课程体系 + 总览

详见 `references/step-syllabus.md`。fetch 调研报告 → 设计体系 → 产出《课程体系》+《课程总览》→ 逐模块确认 → 更新配置（`overview_doc_url`）。

---

## Step 3: 逐课教案（循环）

详见 `references/step-lesson.md`。按课程体系章节顺序一课一课走；含 fworch-case 案例为**可选**素材；`lesson_docs` 长度 = 已完成章数（中断恢复）。

---

## Step 4: 练习/测验

详见 `references/step-exercise.md`。fetch 全部教案 → 逐模块出题 → 每模块展示 → 改 → 下一模块。

---

## Step 5: 课程完结总结

详见 `references/step-summary.md`。fetch 课程体系 + 全部教案 → 知识图谱/易错点/推荐路径 → 展示 → 改 → 定稿 → `status=completed`。

---

## Mode B: 现有材料课程化（ingest）

将已下载的课程材料（PDF 讲义/逐字稿、Excel、案例论文）整理为飞书结构化文档。细则见 `references/step-ingest.md`。

**产物双层，命名规则**（slug = 课程名全小写英文）：

| 层 | 命名 | 内容 |
|----|------|------|
| memo | `<slug>-week<N>-memo` / `<slug>-<案例关键字>-memo` | **原始记录**：官方三源合并 / 原文全文，忠实呈现，不改写 |
| update | `<slug>-week<N>-update` / `<slug>-<案例关键字>-update` | **更新版（中文）**：课程化精读（学习目标/导入/核心框架/小结/练习）+ 2024—2026 现代表演进 |

- 父页命名：`memo <slug>`（如 `memo business-analytics-from-data-to-insights`）—— 父页是 memo 目录
- 每周一行、每个案例一个子文档；`-memo` 存原文，`-update` 出课程化内容
- 有内容就建，无内容跳过（不硬造）

**ingest 步骤**：

```
0 抽取      本地 PDF → 文本（pymupdf）；Excel/其他另存
1 memo      按「周/案例」合并相关材料 → <slug>-<weekN>-memo 子文档
2 骨架      从材料抽取要点骨架（spine），供 update 复用
3 演进      按单元主题搜 2024—2026 更新（fsearch/fresearchframe）
4 update    memo 骨架 + 演进 → 课程化 <slug>-<weekN>-update 子文档
5 归集      写回 Base（courselist/framework，见「课程归集」）
```

每个单元产出后展示 → 你改 → 确认 → 下一单元。数据总线仍为飞书。

---

## 课程归集（Base 写回）

课程化完成后，把课程与知识点写入框架 Base（表结构按项目 config）：

- **courselist 表**（课程→周/单元）：父记录=课程根行；每学习周期（周）一行子记录；`关联知识点` 挂在该周子记录上（不在课程根行）；`参考附件` 附该周下载的 PDF；课程链接用总 module/课表页
- **framework 表**（能力地图）：capability→skill 用**自引用父记录**建树（coursecap 行 + skill 行）；`关联课程` 指向 courselist 的**周子记录**（双向：两表各自动生成反向列）
- 命名/字段细则与当前 Base token 见 `<slug>.yaml` 的 `baframework_*` / `courselist_*` 字段

---

## 配置更新规则

收到 `status=ok` 后：
1. `current_step += 1`
2. 记录新文档 URL（按 `aux_docs[].purpose` 映射到对应字段）
3. 用 `ccprivate/bin/yaml-edit.sh` 写回（已落地，见 comm-contract § 配置文件写入）
4. status=in_progress（Step 5 后改为 completed）

```bash
E=${CCPRIVATE_HOME:-$HOME/git/ccprivate}/bin/yaml-edit.sh
CFG=${CCPRIVATE_HOME:-$HOME/git/ccprivate}/conf/fcourse/<slug>.yaml
$E "$CFG" set current_step 1
$E "$CFG" set feishu.research_doc_url "<url>"
$E "$CFG" append feishu.lesson_docs chapter=1 title="导入" url="<url>"
```

---

## 依赖

- fworch-case — 案例库（**可选**，按需调用，非强制依赖）
- ffeishu — 飞书操作
- fsearch / fresearchframe — 搜索
- fdiagram — 图（飞书画板入口，默认 `<whiteboard type="mermaid">` 嵌入课程文档）
- fwstd-course — 内容规范 + 模板

---

## 参考

**本目录**
- `references/comm-contract.md` — 通信契约（含配置文件写入 yaml-edit）
- `references/case-protocol.md` — fworch-case 调用协议
- `references/step-research.md` / `step-syllabus.md` / `step-lesson.md` / `step-exercise.md` / `step-summary.md` — Mode A 各 step 执行细则
- `references/step-ingest.md` — Mode B 现有材料课程化（memo/update）细则

**fwstd-course（内容规范 + 模板）**
- `~/.claude/skills/fwstd-course/SKILL.md` — 课程体裁规范总纲
- `~/.claude/skills/fwstd-course/references/{research,syllabus,lesson,exercise,summary}-template.md`