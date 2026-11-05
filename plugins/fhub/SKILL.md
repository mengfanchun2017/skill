---
name: fhub
description: |
  f* 技能包总入口 — 用户描述需求后判断属于哪一类（撰写/飞书文档/Office/PDF/大宗报告/调研/个人管理/工具），
  派发到对应技能，用户不必记子技能名。
  用法：用户说"帮我做X"/"我要Y"/"这个怎么弄"/"该用哪个技能"，且不确定走哪个子技能时触发。
  已知技能时直接调那个技能，不必经过本入口。
user-invocable: true
allowed-tools: Bash, Read, Glob, Grep, Skill, AskUserQuestion
---

# fhub — 技能包总入口

职责只有两件：**判断该走哪个技能** → **派发过去**。不自己执行任何业务。

## 判断（先跑这条，不要凭印象）

```bash
~/.claude/skills/fcore/bin/fcore genre "<用户的原始描述>"
```

输出示例：

```json
{"domain":"write","genre":"report","skill":"forch-report",
 "orchestrator":"forch-report","spec":"fstander-report","config":"writing/report.yaml",
 "trigger":"分析报告","score":26}
```

| 字段 | 含义 |
|---|---|
| `domain` | 粗粒度域（write/doc/office/pdf/digest/research/personal/tool） |
| `genre` | 撰写域下的细分体裁（report/course/case/interview），其他域为 null |
| `orchestrator` | 该派的技能（有值时优先用它，比 `skill` 更具体） |
| `spec` | 内容规范技能 |

**匹配含词元兜底**：注册表里没写"PDF排到飞书"这种说法，但 `PDF`+`飞书` 两个词元
能拼出来 → 命中 pdf 域。所以描述可以口语化，不必背触发词。

### 三种情况的分支

| 输出 | 怎么做 |
|---|---|
| 有 `orchestrator` | 直接派给 `orchestrator`（如 forch-report） |
| 只有 `domain`，无 `genre` | 派给 `skill` 字段的技能 |
| `"domain": null` | 触发词没命中 → 用 `fcore genres` 列清单，AskUserQuestion 让用户选；仍不确定就问"你想做什么" |

## 派发

用 `Skill` 工具加载目标技能（本 skill 已声明该工具）。派发时把**原始需求原文**
传过去，不要自己改写或补充——改写会丢掉用户的具体约束。

```
Skill(skill="forch-report", args="<用户原始描述>")
```

**不要做的事**：
- 不要自己先写一半再交出去（用户会看到两套思路）
- 不要在派发前做"我理解你是要……"的长篇确认（判断不准才问）
- 不要在 `fcore genre` 已明确时还去问用户选哪个

## 域与技能对照

跑 `fcore genres` 拿准确清单。概览：

| 域 | 派给 | 覆盖 |
|---|---|---|
| write | 按体裁派 forch-report / -course / -case / -interview | 报告、课程、案例、面试 |
| doc | ffeishu | 飞书文档、表格、白板、图表 |
| office | fpptx / fdocx / fxlsx | PPT、Word、Excel |
| pdf | fpdf | PDF 精排上飞书 |
| digest | fdigest | 大宗报告阅读归档 |
| research | fresearchframe（配合 fsearch） | 外部调研 |
| personal | flogme | OKR、日志、反思、总结 |
| tool | fsecretcheck / fpostpone / flibaudit | 密钥检查、定时、仓库审计 |

## 注册表在哪

触发词**只有一份真相源**：`fcore.yaml`。自用机器在
<ccprivate>/conf/fcore.yaml，独立用户用 `fcore conf set` 写进
`~/.claude/skill-config/fcore.yaml`。

此前触发词散在三处（`~/CLAUDE.md`、writing/registry.yaml、各 SKILL.md 的
description），实测已漂移过：`~/CLAUDE.md` 曾写"写报告 → fresearchframe"
而实际该派 forch-report。现在一律以 `fcore.yaml` 为准。

## 斜杠命令

`/fhub <需求>` 等价于本 skill 的完整流程。装好后 `/` 菜单里能看到。

## 没配任何东西时

`fcore genre` 仍能跑（注册表带内置默认兜底）。派发出去的子技能若缺飞书授权，
它们各自 `fcore auth` 判断后降级——只做本地部分，不阻断。
