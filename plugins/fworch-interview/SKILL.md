---
name: fworch-interview
user-invocable: true
description: |
  面试准备 orchestrator。读 ccprivate/conf/finterview/<slug>.yaml 配置 ->
  判断准备进度 -> 读取对应 step 细则执行 -> 更新配置。所有产物存飞书父文档下的子文档。
  面向"零经验应聘者"从岗位认知、行业组织、专业能力到未来工作思路的全链条准备。
  用法：用户说"准备面试"/"岗位面试"/"应聘准备"/"面试材料"触发
allowed-tools: Read, Write, Bash, Glob, Grep, AskUserQuestion
---

# fworch-interview — 面试准备 orchestrator

职责：读配置 → 判断进度 → 按 step 执行（细则在 references/step-*.md）→ 更新配置 → 循环
体裁注册表：`ccprivate/conf/writing/registry.yaml`（interview 条目）+ 真值 `conf/writing/interview.yaml`
数据总线：飞书（每步产出 = 飞书子文档，下一步 fetch 读取）
配置：`ccprivate/conf/finterview/<slug>.yaml`
通信契约：见 `references/comm-contract.md`
内容规范：`fwstd-interview`（模板）

每步原则：产出 → 展示飞书链接 → 你改飞书 → 确认 → 下一步

## 适用场景与前提

**面向"零经验／跨行应聘者"**：用户对应聘岗位没有直接经验，需要**非常全面**的准备。

准备链条（覆盖"岗位认知" + "未来工作思路"两大类材料）：

```
岗位认知线：岗位本身 → 组织/行业 → 专业知识 → 能力素质
工作思路线：问题诊断 → 工作规划 → 问答素材 → 模拟演练 → 成稿
```

## Phase A: 面试选择

```bash
ls ${CCPRIVATE_HOME:-$HOME/git/ccprivate}/conf/finterview/*.yaml 2>/dev/null
```

**已有** → 展示列表（岗位名 + 当前步骤 + 进度）→ 选一个继续
**新面试** → 问 slug / 岗位名称 / 单位 / 岗位级别 / 面试轮次 / 需求材料 URL

slug 命名：全小写英文+数字，无空格横线。示例：`airline-fleet-mgmt-9b`

### 情报采集（新面试必做）

一次性问清（用 AskUserQuestion）：

| 项 | 说明 |
|----|------|
| 岗位名称 | 如「机队管理专员」 |
| 应聘单位 | 航司名（如 XX 航空） |
| 岗位级别/职级 | 如「B 级，岗位级别 9B」——影响能力与思路的深度定位 |
| 面试轮次 | 通用面 / 专业面 / 终面 / HR 面；各轮考察侧重不同 |
| 招聘 JD/公告 | URL 或原文（岗位职责、任职要求）——最关键输入 |
| 个人背景 | 用户现有技能/经历（用于把可迁移能力对上岗位要求） |
| 交付材料 | 如「岗位认知 + 未来工作思路」；有无字数/形式限制 |
| 时间盘 | 面试日期 → 倒排准备计划 |

## Phase B: 读配置

```bash
cat ${CCPRIVATE_HOME:-$HOME/git/ccprivate}/conf/finterview/<slug>.yaml
```

配置结构：

```yaml
slug: "airline-fleet-mgmt-9b"
name: "机队管理专员"
employer: "XX 航空"
level: "B 级 / 9B"
status: "in_progress"
candidate_background: "..."        # 用户现有背景（可迁移能力）
rounds: [通用面, 专业面, 终面]
deadline: "2026-11-01"
feishu:
  root_doc_url: ""                 # 飞书父文档（所有子文档挂此）
  requirement_doc_url: ""          # JD/公告
  brief_doc_url: ""                # 岗位画像
  org_doc_url: ""                  # 组织与行业
  knowledge_doc_url: ""            # 专业知识
  competency_doc_url: ""           # 能力素质
  questions_doc_url: ""            # 问题库
  answers_doc_url: ""              # 问答素材
  workplan_doc_url: ""             # 未来工作思路
  mock_doc_url: ""                 # 模拟演练
  package_doc_url: ""              # 最终成稿包
current_step: 0                    # 0-8
```

## Phase C: 飞书 auth 预检

首次调 ffeishu 前**必须**预检：

```bash
lark-cli drive +search --query test --page-size 1 --as user 2>&1 \
  | sed '/^\[lark-cli\]/d' | grep -q '"ok":true' || echo "AUTH_FAILED"
```

失败 → 终止，走 QR 授权（见 `~/.claude/rules/feishu.md`），不硬闯。

## Phase D: 按 step 执行

按 `current_step` 进入对应 step，**读取该步的 reference 细则**执行：

| Step | 细则 | 产出（飞书子文档） | 覆盖材料 |
|------|------|------------------|---------|
| 0 | 本 skill 直接处理 | 《<岗位>-岗位画像》 | 岗位认知 |
| 1 | `references/step-org-industry.md` | 《<岗位>-组织与行业》 | 岗位认知 |
| 2 | `references/step-role-knowledge.md` | 《<岗位>-专业知识地图》 | 岗位认知 |
| 3 | `references/step-competency.md` | 《<岗位>-能力素质模型》 | 岗位认知 |
| 4 | `references/step-question-bank.md` | 《<岗位>-问题库》 | 工作思路 |
| 5 | `references/step-answer-prep.md` | 《<岗位>-问答素材（STAR）》 | 工作思路 |
| 6 | `references/step-work-plan.md` | 《<岗位>-未来工作思路》 | 工作思路（核心交付） |
| 7 | `references/step-mock.md` | 《<岗位>-模拟演练与逐轮清单》 | 综合 |
| 8 | `references/step-package.md` | 《<岗位>-面试成稿包》 | 综合 |

每步完成后按 `references/comm-contract.md` 返回 `{status, doc_url, notes}`，编排器推进 `current_step`。

## 配置更新规则

收到 `status=ok` 后：
1. `current_step += 1`
2. 记录新文档 URL（映射到 `feishu.<field>`）
3. 用 `ccprivate/bin/yaml-edit.sh` 写回
4. Step 8 后 `status=completed`

```bash
E=${CCPRIVATE_HOME:-$HOME/git/ccprivate}/bin/yaml-edit.sh
CFG=${CCPRIVATE_HOME:-$HOME/git/ccprivate}/conf/finterview/<slug>.yaml
$E "$CFG" set current_step 1
$E "$CFG" set feishu.org_doc_url "<url>"
```

## 依赖

- fwstd-interview — 内容规范 + 模板（岗位画像/知识地图/能力模型/问答/工作思路）
- ffeishu — 飞书操作（父文档 + 子文档）
- fsearch / fresearchframe — 岗位/行业/专业知识搜索
- fdiagram — 能力模型图 / 工作思路流程 / 组织架构图

## 参考

**本目录**
- `references/comm-contract.md` — 通信契约（含 yaml-edit）
- `references/step-org-industry.md` / `step-role-knowledge.md` / `step-competency.md` / `step-question-bank.md` / `step-answer-prep.md` / `step-work-plan.md` / `step-mock.md` / `step-package.md`

**fwstd-interview（内容规范 + 模板）**
- `~/.claude/skills/fwstd-interview/SKILL.md`
- `~/.claude/skills/fwstd-interview/references/{job-brief,knowledge-map,competency-model,question-bank,answer-star,work-plan,mock-checklist,package}-template.md`
