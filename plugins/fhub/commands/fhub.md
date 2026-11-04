---
description: 技能包总入口 — 描述需求，自动派发到合适的子技能
allowed-tools: Bash, Read, Glob, Grep, Skill, AskUserQuestion
---

# /fhub — 派发需求

用户需求：$ARGUMENTS

## 执行

1. 先跑派发判断（不要凭印象选技能）：

```bash
~/.claude/skills/fcore/bin/fcore genre "$ARGUMENTS"
```

2. 按输出派发：

| 输出 | 动作 |
|---|---|
| 有 `orchestrator` 字段 | `Skill(skill="<orchestrator>", args="$ARGUMENTS")` |
| 只有 `skill` 字段 | `Skill(skill="<skill>", args="$ARGUMENTS")` |
| `"domain": null` | 跑 `~/.claude/skills/fcore/bin/fcore genres` 列清单，用 AskUserQuestion 让用户选一个，再派发 |

3. 派发时传**用户原始描述**，不要改写。用户的具体约束（数据来源、目标读者、
   不要什么风格）改写就丢了。

## 约束

- 本命令不执行业务，只派发。
- `fcore genre` 已明确时不问用户"选哪个"。
- 判断确实模糊（多域同分/都像又都不像）时才 AskUserQuestion，一次问清。
